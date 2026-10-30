"""Supabase access-token verification for user-owned API operations."""

import logging
import os
import re
import socket
import ssl
import threading
import uuid
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

import certifi
import httpx
import jwt
from fastapi import Header, HTTPException, status


_ALLOWED_ALGORITHMS = ("ES256", "RS256")
_AUTHENTICATED_AUDIENCE = "authenticated"
_JWKS_TIMEOUT_SECONDS = 5
_AUTH_USER_TIMEOUT_SECONDS = 5
_JWKS_CLIENTS: dict[str, jwt.PyJWKClient] = {}
_JWKS_CLIENTS_LOCK = threading.Lock()
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SupabaseAuthConfig:
    issuer: str
    jwks_url: str
    user_url: str
    publishable_key: str


@dataclass(frozen=True)
class AuthenticatedUser:
    """Identity derived only from a verified Supabase access token."""

    user_id: str


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="A valid verified-user access token is required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _service_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication service is temporarily unavailable",
    )


def _bad_upstream_response() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Supabase authentication returned an invalid response",
    )


def _configuration_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Supabase authentication is not configured correctly",
    )


def _first_configured_value(*names: str) -> str:
    """Read the first non-empty setting, preferring backend-specific names."""

    for name in names:
        value = os.getenv(name, "")
        if value.strip():
            return value.strip()
    return ""


def _auth_config() -> SupabaseAuthConfig:
    # Keep the documented backend-specific names canonical while accepting the
    # Vite-prefixed names already used by this repository's shared local env.
    supabase_url = _first_configured_value("SUPABASE_URL", "VITE_SUPABASE_URL").rstrip("/")
    publishable_key = _first_configured_value(
        "SUPABASE_PUBLISHABLE_KEY",
        "VITE_SUPABASE_PUBLISHABLE_KEY",
    )

    missing = []
    if not supabase_url:
        missing.append("SUPABASE_URL")
    if not publishable_key:
        missing.append("SUPABASE_PUBLISHABLE_KEY")
    if missing:
        _LOGGER.error(
            "Supabase authentication configuration is missing: %s",
            ", ".join(missing),
        )
        raise _configuration_error()

    try:
        parsed = urlsplit(supabase_url)
    except ValueError:
        _LOGGER.error("Supabase authentication URL configuration is malformed")
        raise _configuration_error() from None
    local_http = parsed.scheme == "http" and parsed.hostname in {
        "localhost",
        "127.0.0.1",
        "::1",
    }
    if (
        parsed.scheme != "https" and not local_http
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise _configuration_error()

    issuer = f"{supabase_url}/auth/v1"
    return SupabaseAuthConfig(
        issuer=issuer,
        jwks_url=f"{issuer}/.well-known/jwks.json",
        user_url=f"{issuer}/user",
        publishable_key=publishable_key,
    )


def _jwks_client_for(jwks_url: str) -> jwt.PyJWKClient:
    """Reuse public JWKS keys and verify TLS with the installed CA bundle."""

    with _JWKS_CLIENTS_LOCK:
        client = _JWKS_CLIENTS.get(jwks_url)
        if client is None:
            client = jwt.PyJWKClient(
                jwks_url,
                timeout=_JWKS_TIMEOUT_SECONDS,
                cache_jwk_set=True,
                lifespan=600,
                ssl_context=ssl.create_default_context(cafile=certifi.where()),
            )
            _JWKS_CLIENTS[jwks_url] = client
        return client


def _exception_chain(error: BaseException) -> list[BaseException]:
    chain = []
    seen = set()
    current: BaseException | None = error
    while isinstance(current, BaseException) and id(current) not in seen and len(chain) < 8:
        chain.append(current)
        seen.add(id(current))
        next_error = current.__cause__ or current.__context__
        if next_error is None and isinstance(current, URLError):
            next_error = current.reason if isinstance(current.reason, BaseException) else None
        current = next_error
    return chain


def _safe_jwks_error_message(
    error: BaseException,
    config: SupabaseAuthConfig,
    token: str,
) -> str:
    if isinstance(error, HTTPError):
        message = f"HTTP response {error.code}"
    elif isinstance(error, ssl.SSLCertVerificationError):
        message = error.verify_message or "TLS certificate verification failed"
    elif isinstance(error, ssl.SSLError):
        message = f"TLS error: {error.reason or 'handshake failed'}"
    elif isinstance(error, socket.gaierror):
        message = "DNS resolution failed"
    elif isinstance(error, (TimeoutError, socket.timeout)):
        message = "Network request timed out"
    else:
        message = str(error)

    sensitive_values = (
        config.jwks_url,
        config.issuer,
        config.user_url,
        config.publishable_key,
        token,
    )
    for value in sensitive_values:
        if value:
            message = message.replace(value, "[REDACTED]")
    message = re.sub(r"(?i)\bbearer\s+[^\s,;]+", "Bearer [REDACTED]", message)
    message = re.sub(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\s*[:=]\s*[^\s,;]+",
        "[REDACTED]",
        message,
    )
    message = re.sub(r"https?://[^\s\"'<>]+", "[URL REDACTED]", message)
    return message[:240]


def _log_jwks_failure(
    error: BaseException,
    config: SupabaseAuthConfig,
    token: str,
) -> None:
    chain = _exception_chain(error)
    root_error = chain[-1] if chain else error
    try:
        hostname = urlsplit(config.jwks_url).hostname or "unknown"
    except ValueError:
        hostname = "unknown"
    http_status = next(
        (item.code for item in chain if isinstance(item, HTTPError)),
        None,
    )
    exception_types = ">".join(type(item).__name__ for item in chain)
    message = _safe_jwks_error_message(root_error, config, token)
    _LOGGER.warning(
        "Supabase JWKS request failed host=%s http_status=%s exception_types=%s message=%s",
        hostname,
        http_status if http_status is not None else "unavailable",
        exception_types,
        message,
    )


def _token_header(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise _unauthorized() from None
    if header.get("alg") not in _ALLOWED_ALGORITHMS or not isinstance(header.get("kid"), str):
        raise _unauthorized()
    return header


def _verify_access_token(token: str, config: SupabaseAuthConfig) -> dict:
    header = _token_header(token)
    try:
        algorithm = header.get("alg")
        signing_key = _jwks_client_for(config.jwks_url).get_signing_key_from_jwt(token)
    except jwt.PyJWKClientConnectionError as exc:
        _log_jwks_failure(exc, config, token)
        raise _service_unavailable() from None
    except jwt.PyJWKSetError as exc:
        _log_jwks_failure(exc, config, token)
        raise _bad_upstream_response() from None
    except jwt.PyJWKError as exc:
        _log_jwks_failure(exc, config, token)
        raise _bad_upstream_response() from None
    except jwt.PyJWKClientError as exc:
        # An unknown kid is an invalid credential. Other client errors mean
        # the JWKS endpoint did not return a usable response.
        if str(exc).startswith("Unable to find a signing key that matches:"):
            raise _unauthorized() from None
        _log_jwks_failure(exc, config, token)
        raise _bad_upstream_response() from None
    except jwt.PyJWTError:
        raise _unauthorized() from None

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[header.get("alg")],
            issuer=config.issuer,
            audience=_AUTHENTICATED_AUDIENCE,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError:
        raise _unauthorized() from None

    subject = claims.get("sub")
    try:
        canonical_subject = str(uuid.UUID(subject))
    except (ValueError, TypeError, AttributeError):
        raise _unauthorized() from None

    if (
        claims.get("role") != _AUTHENTICATED_AUDIENCE
        or claims.get("is_anonymous") is True
        or claims.get("email_verified") is False
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A verified, non-anonymous user account is required",
        )

    claims["sub"] = canonical_subject
    return claims


def _fetch_supabase_user(token: str, config: SupabaseAuthConfig) -> dict:
    """Ask Auth for current email-confirmation state using a public API key."""

    try:
        response = httpx.get(
            config.user_url,
            headers={
                "apikey": config.publishable_key,
                "Authorization": f"Bearer {token}",
            },
            timeout=_AUTH_USER_TIMEOUT_SECONDS,
            follow_redirects=False,
        )
    except httpx.HTTPError as exc:
        _LOGGER.warning("Supabase current-user request failed (%s)", type(exc).__name__)
        raise _service_unavailable() from None

    if response.status_code in (401, 403):
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = {}
        if isinstance(error_payload, dict):
            error_text = " ".join(
                str(error_payload.get(key, ""))
                for key in ("message", "code", "error", "hint")
            ).casefold()
            if "invalid api key" in error_text or "invalid_api_key" in error_text:
                _LOGGER.error("Supabase rejected the configured publishable key")
                raise _configuration_error()
        raise _unauthorized()
    if response.status_code == 429 or response.status_code >= 500:
        _LOGGER.warning("Supabase current-user endpoint returned status %s", response.status_code)
        raise _service_unavailable()
    if response.status_code != 200:
        _LOGGER.warning("Supabase current-user endpoint returned status %s", response.status_code)
        raise _bad_upstream_response()

    try:
        user = response.json()
    except ValueError:
        _LOGGER.warning("Supabase current-user endpoint returned invalid JSON")
        raise _bad_upstream_response() from None
    if not isinstance(user, dict):
        _LOGGER.warning("Supabase current-user endpoint returned an unexpected payload")
        raise _bad_upstream_response()
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
) -> AuthenticatedUser:
    """Verify a bearer token and require a currently email-confirmed user."""

    if not authorization:
        raise _unauthorized()

    parts = authorization.split()
    if len(parts) != 2 or parts[0].casefold() != "bearer" or len(parts[1]) > 8192:
        raise _unauthorized()

    token = parts[1]
    _token_header(token)
    config = _auth_config()
    claims = _verify_access_token(token, config)
    user = _fetch_supabase_user(token, config)

    if user.get("id") != claims["sub"]:
        raise _unauthorized()
    if not user.get("email_confirmed_at"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email address before using personal data endpoints",
        )

    return AuthenticatedUser(user_id=claims["sub"])
