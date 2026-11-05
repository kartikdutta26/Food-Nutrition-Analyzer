from datetime import UTC, datetime, timedelta
import ssl
from types import SimpleNamespace
from urllib.error import HTTPError
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app import auth
from app.auth import SupabaseAuthConfig
from tests.conftest import TEST_USER_ID


TEST_SUPABASE_URL = "https://test-project.supabase.co"
TEST_ISSUER = f"{TEST_SUPABASE_URL}/auth/v1"
OTHER_USER_ID = "22222222-2222-4222-8222-222222222222"


@pytest.fixture
def token_factory(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    user_records = {}
    real_fetch_supabase_user = auth._fetch_supabase_user

    class TestJwksClient:
        def get_signing_key_from_jwt(self, token):
            header = jwt.get_unverified_header(token)
            if header.get("kid") != "test-key-id":
                raise jwt.PyJWKClientError(
                    f'Unable to find a signing key that matches: "{header.get("kid")}"'
                )
            return SimpleNamespace(key=private_key.public_key())

    monkeypatch.setenv("SUPABASE_URL", TEST_SUPABASE_URL)
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test-publishable-key")
    monkeypatch.setattr(auth, "_jwks_client_for", lambda _url: TestJwksClient())
    monkeypatch.setattr(
        auth,
        "_fetch_supabase_user",
        lambda token, _config: user_records.get(token, {}),
    )

    def issue(
        user_id=TEST_USER_ID,
        *,
        claims=None,
        confirmed=True,
        auth_user_id=None,
        signing_key=None,
        key_id="test-key-id",
    ):
        now = datetime.now(UTC)
        payload = {
            "iss": TEST_ISSUER,
            "aud": "authenticated",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "iat": int(now.timestamp()),
            "sub": user_id,
            "role": "authenticated",
        }
        payload.update(claims or {})
        token = jwt.encode(
            payload,
            signing_key or private_key,
            algorithm="RS256",
            headers={"kid": key_id},
        )
        user_records[token] = {
            "id": auth_user_id or user_id,
            "email_confirmed_at": now.isoformat() if confirmed else None,
        }
        return token

    return SimpleNamespace(
        issue=issue,
        private_key=private_key,
        real_fetch_supabase_user=real_fetch_supabase_user,
    )


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_personal_endpoint_rejects_missing_and_malformed_authorization(client):
    missing = client.get("/api/profile")
    malformed = client.get("/api/profile", headers={"Authorization": "Basic abc"})
    malformed_token = client.get("/api/profile", headers=bearer("not-a-jwt"))

    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert malformed.status_code == 401
    assert malformed_token.status_code == 401


def test_personal_endpoint_rejects_expired_and_invalid_signature_tokens(
    client,
    token_factory,
):
    expired = token_factory.issue(
        claims={"exp": int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())},
    )
    wrong_signer = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    invalid_signature = token_factory.issue(signing_key=wrong_signer)

    assert client.get("/api/profile", headers=bearer(expired)).status_code == 401
    assert client.get("/api/profile", headers=bearer(invalid_signature)).status_code == 401


def test_personal_endpoint_rejects_unsupported_hs256_signing(client, token_factory):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": TEST_ISSUER,
            "aud": "authenticated",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "iat": int(now.timestamp()),
            "sub": TEST_USER_ID,
            "role": "authenticated",
        },
        "test-only-signing-key-value-with-at-least-32-bytes",
        algorithm="HS256",
        headers={"kid": "test-key-id"},
    )

    response = client.get("/api/profile", headers=bearer(token))

    assert response.status_code == 401


def test_personal_endpoint_maps_jwks_connection_failure_to_503_without_logging_token(
    client,
    caplog,
    monkeypatch,
    token_factory,
):
    token = token_factory.issue()
    upstream_message = (
        f"network failure with Bearer {token} apikey=test-publishable-key "
        f"{TEST_ISSUER}/.well-known/jwks.json"
    )

    class OfflineJwksClient:
        def get_signing_key_from_jwt(self, _token):
            raise jwt.PyJWKClientConnectionError(upstream_message)

    monkeypatch.setattr(auth, "_jwks_client_for", lambda _url: OfflineJwksClient())

    response = client.get("/api/profile", headers=bearer(token))

    assert response.status_code == 503
    assert response.json()["detail"] == "Authentication service is temporarily unavailable"
    assert f"host={TEST_SUPABASE_URL.removeprefix('https://')}" in caplog.text
    assert "http_status=unavailable" in caplog.text
    assert "exception_types=PyJWKClientConnectionError" in caplog.text
    assert "network failure" in caplog.text
    assert token not in caplog.text
    assert "test-publishable-key" not in caplog.text
    assert TEST_ISSUER not in caplog.text
    assert upstream_message not in caplog.text


def test_jwks_client_uses_certifi_ca_bundle_with_strict_tls_verification(monkeypatch):
    captured = {}
    real_create_default_context = auth.ssl.create_default_context

    def capture_context(*, cafile):
        captured["cafile"] = cafile
        captured["context"] = real_create_default_context(cafile=cafile)
        return captured["context"]

    class FakeJwksClient:
        def __init__(self, url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs

    monkeypatch.setattr(auth, "_JWKS_CLIENTS", {})
    monkeypatch.setattr(auth.ssl, "create_default_context", capture_context)
    monkeypatch.setattr(auth.jwt, "PyJWKClient", FakeJwksClient)

    auth._jwks_client_for(f"{TEST_ISSUER}/.well-known/jwks.json")

    context = captured["kwargs"]["ssl_context"]
    assert captured["cafile"] == auth.certifi.where()
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert captured["kwargs"]["timeout"] == auth._JWKS_TIMEOUT_SECONDS
    assert captured["kwargs"]["cache_jwk_set"] is True


def test_jwks_http_failure_logs_status_and_redacts_url_tokens_and_keys(caplog):
    config = SupabaseAuthConfig(
        issuer=TEST_ISSUER,
        jwks_url=f"{TEST_ISSUER}/.well-known/jwks.json",
        user_url=f"{TEST_ISSUER}/user",
        publishable_key="diagnostic-publishable-key",
    )
    access_token = "diagnostic.access.token"
    http_error = HTTPError(config.jwks_url, 503, "upstream unavailable", {}, None)
    wrapped = jwt.PyJWKClientConnectionError(
        f"request {config.jwks_url} failed: Bearer {access_token} apikey=diagnostic-publishable-key"
    )
    wrapped.__cause__ = http_error

    auth._log_jwks_failure(wrapped, config, access_token)

    assert "http_status=503" in caplog.text
    assert "exception_types=PyJWKClientConnectionError>HTTPError" in caplog.text
    assert "message=HTTP response 503" in caplog.text
    assert config.jwks_url not in caplog.text
    assert access_token not in caplog.text
    assert "diagnostic-publishable-key" not in caplog.text


def test_profile_returns_auth_503_before_touching_mongodb_when_supabase_user_check_is_unavailable(
    client,
    database,
    caplog,
    monkeypatch,
    token_factory,
):
    token = token_factory.issue()

    class UnavailableResponse:
        status_code = 503

        def json(self):
            return {"message": "provider detail that must not be returned"}

    monkeypatch.setattr(auth, "_fetch_supabase_user", token_factory.real_fetch_supabase_user)
    monkeypatch.setattr(auth.httpx, "get", lambda *args, **kwargs: UnavailableResponse())

    response = client.get("/api/profile", headers=bearer(token))

    assert response.status_code == 503
    assert response.json()["detail"] == "Authentication service is temporarily unavailable"
    assert "provider detail" not in response.text
    assert "Supabase current-user endpoint returned status 503" in caplog.text
    assert database["user_profiles"].documents == []


@pytest.mark.parametrize(
    ("jwks_error", "expected_status"),
    [
        (jwt.PyJWKClientError("The JWKS endpoint did not return a JSON object"), 502),
        (jwt.PyJWKSetError("The JWKS endpoint returned no usable keys"), 502),
        (jwt.PyJWKClientError('Unable to find a signing key that matches: "unknown-kid"'), 401),
    ],
)
def test_personal_endpoint_distinguishes_bad_jwks_from_unknown_token_key(
    client,
    monkeypatch,
    token_factory,
    jwks_error,
    expected_status,
):
    token = token_factory.issue()

    class BrokenJwksClient:
        def get_signing_key_from_jwt(self, _token):
            raise jwks_error

    monkeypatch.setattr(auth, "_jwks_client_for", lambda _url: BrokenJwksClient())
    response = client.get("/api/profile", headers=bearer(token))

    assert response.status_code == expected_status
    assert token not in response.text


@pytest.mark.parametrize(
    "claims",
    [
        {"iss": "https://attacker.example/auth/v1"},
        {"aud": "service_role"},
    ],
)
def test_personal_endpoint_rejects_invalid_issuer_or_audience(client, token_factory, claims):
    token = token_factory.issue(claims=claims)

    response = client.get("/api/profile", headers=bearer(token))

    assert response.status_code == 401


def test_personal_endpoint_rejects_unverified_and_anonymous_users(
    client,
    database,
    token_factory,
):
    unverified = token_factory.issue(confirmed=False)
    anonymous = token_factory.issue(
        user_id=str(uuid4()),
        claims={"is_anonymous": True},
    )

    unverified_response = client.get("/api/profile", headers=bearer(unverified))
    anonymous_response = client.get("/api/profile", headers=bearer(anonymous))

    assert unverified_response.status_code == 403
    assert anonymous_response.status_code == 403
    assert database["user_profiles"].documents == []


def test_personal_endpoint_rejects_auth_server_identity_mismatch(client, token_factory):
    token = token_factory.issue(auth_user_id=OTHER_USER_ID)

    response = client.get("/api/profile", headers=bearer(token))

    assert response.status_code == 401


def test_personal_endpoint_fails_closed_when_supabase_url_is_missing(
    client,
    monkeypatch,
    token_factory,
):
    token = token_factory.issue()
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("VITE_SUPABASE_URL", raising=False)

    response = client.get("/api/profile", headers=bearer(token))

    assert response.status_code == 500
    assert "SUPABASE_URL" not in response.text


@pytest.mark.parametrize(
    ("status_code", "payload", "expected_status"),
    [
        (401, {"message": "Invalid API key"}, 500),
        (401, {"message": "Invalid JWT"}, 401),
        (429, {"message": "rate limited"}, 503),
        (503, {"message": "upstream unavailable"}, 503),
        (404, {"message": "unexpected auth response"}, 502),
    ],
)
def test_supabase_user_check_maps_provider_failures_without_echoing_details(
    monkeypatch,
    status_code,
    payload,
    expected_status,
):
    class Response:
        def __init__(self):
            self.status_code = status_code

        def json(self):
            return payload

    monkeypatch.setattr(auth.httpx, "get", lambda *args, **kwargs: Response())
    config = SupabaseAuthConfig(
        issuer=TEST_ISSUER,
        jwks_url=f"{TEST_ISSUER}/.well-known/jwks.json",
        user_url=f"{TEST_ISSUER}/user",
        publishable_key="test-publishable-key",
    )

    with pytest.raises(HTTPException) as raised:
        auth._fetch_supabase_user("test-access-token", config)

    assert getattr(raised.value, "status_code", None) == expected_status
    assert "test-publishable-key" not in str(raised.value)
    assert "test-access-token" not in str(raised.value)


def test_supabase_user_check_maps_network_failure_to_service_unavailable(monkeypatch):
    def fail_request(*args, **kwargs):
        raise httpx.ConnectError("network unavailable")

    monkeypatch.setattr(auth.httpx, "get", fail_request)
    config = SupabaseAuthConfig(
        issuer=TEST_ISSUER,
        jwks_url=f"{TEST_ISSUER}/.well-known/jwks.json",
        user_url=f"{TEST_ISSUER}/user",
        publishable_key="test-publishable-key",
    )

    with pytest.raises(HTTPException) as raised:
        auth._fetch_supabase_user("test-access-token", config)

    assert getattr(raised.value, "status_code", None) == 503
    assert "test-publishable-key" not in str(raised.value)


@pytest.mark.parametrize("payload", [None, [], "unexpected"])
def test_supabase_user_check_maps_malformed_success_payload_to_bad_gateway(
    monkeypatch,
    payload,
):
    class Response:
        status_code = 200

        def json(self):
            if payload is None:
                raise ValueError("upstream body contains sensitive details")
            return payload

    monkeypatch.setattr(auth.httpx, "get", lambda *args, **kwargs: Response())
    config = SupabaseAuthConfig(
        issuer=TEST_ISSUER,
        jwks_url=f"{TEST_ISSUER}/.well-known/jwks.json",
        user_url=f"{TEST_ISSUER}/user",
        publishable_key="test-publishable-key",
    )

    with pytest.raises(HTTPException) as raised:
        auth._fetch_supabase_user("test-access-token", config)

    assert raised.value.status_code == 502
    assert "sensitive details" not in str(raised.value)
    assert "test-access-token" not in str(raised.value)


def test_profile_missing_supabase_configuration_fails_before_jwks_or_profile_access(
    client,
    database,
    caplog,
    monkeypatch,
    token_factory,
):
    token = token_factory.issue()
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("VITE_SUPABASE_URL", raising=False)
    monkeypatch.delenv("VITE_SUPABASE_PUBLISHABLE_KEY", raising=False)

    response = client.get("/api/profile", headers=bearer(token))

    assert response.status_code == 500
    assert response.json()["detail"] == "Supabase authentication is not configured correctly"
    assert "SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY" in caplog.text
    assert "test-publishable-key" not in caplog.text
    assert token not in caplog.text
    assert database["user_profiles"].documents == []


def test_backend_auth_config_loads_existing_vite_supabase_names_without_echoing_values(monkeypatch):
    for name in (
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
        "VITE_SUPABASE_URL",
        "VITE_SUPABASE_PUBLISHABLE_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("VITE_SUPABASE_URL", TEST_SUPABASE_URL)
    monkeypatch.setenv("VITE_SUPABASE_PUBLISHABLE_KEY", "test-publishable-key")

    config = auth._auth_config()

    assert config.issuer == TEST_ISSUER
    assert config.jwks_url == f"{TEST_ISSUER}/.well-known/jwks.json"
    assert config.user_url == f"{TEST_ISSUER}/user"
    assert config.publishable_key == "test-publishable-key"


def test_backend_auth_config_prefers_backend_specific_names_over_vite_aliases(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://backend-project.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "backend-publishable-key")
    monkeypatch.setenv("VITE_SUPABASE_URL", "https://vite-project.supabase.co")
    monkeypatch.setenv("VITE_SUPABASE_PUBLISHABLE_KEY", "vite-publishable-key")

    config = auth._auth_config()

    assert config.issuer == "https://backend-project.supabase.co/auth/v1"
    assert config.publishable_key == "backend-publishable-key"


def test_verified_user_profile_is_created_read_and_updated_without_legacy_access(
    client,
    database,
    token_factory,
):
    legacy_profile = {
        "_id": "default",
        "dietary_preferences": ["legacy-only"],
        "targets": {"calories": 1, "protein": 1, "carbs": 1, "fats": 1},
    }
    database["profiles"].documents.append(legacy_profile)
    headers = bearer(token_factory.issue())

    created = client.get("/api/profile?user_id=" + OTHER_USER_ID, headers=headers)
    updated = client.patch(
        "/api/profile",
        headers=headers,
        json={
            "user_id": OTHER_USER_ID,
            "dietary_preferences": ["Vegetarian"],
            "targets": {"calories": 2100, "protein": 110, "carbs": 220, "fats": 70},
        },
    )
    assert created.status_code == 200
    assert created.json()["dietary_preferences"] == []
    assert updated.status_code == 422
    assert "user_id" in validation_field_names(updated)

    successful_update = client.patch(
        "/api/profile",
        headers=headers,
        json={
            "dietary_preferences": ["Vegetarian"],
            "targets": {"calories": 2100, "protein": 110, "carbs": 220, "fats": 70},
        },
    )
    assert successful_update.status_code == 200
    read_back = client.get("/api/profile", headers=headers)
    assert read_back.json()["dietary_preferences"] == ["Vegetarian"]
    assert len(database["user_profiles"].documents) == 1
    assert database["user_profiles"].documents[0]["user_id"] == TEST_USER_ID
    assert database["profiles"].documents == [legacy_profile]


def test_profiles_are_isolated_between_verified_users(client, database, token_factory):
    first_headers = bearer(token_factory.issue(TEST_USER_ID))
    second_headers = bearer(token_factory.issue(OTHER_USER_ID))

    first_update = client.patch(
        "/api/profile",
        headers=first_headers,
        json={
            "name": "Account A",
            "age": 29,
            "height_cm": 181,
            "weight_kg": 78,
            "activity_level": "Active",
            "goal": "Gain Muscle",
            "water_liters": 3,
            "dietary_preferences": ["Vegetarian"],
        },
    )
    second_initial = client.get("/api/profile", headers=second_headers)
    second_update = client.patch(
        "/api/profile",
        headers=second_headers,
        json={
            "name": "Account B",
            "age": 35,
            "height_cm": 165,
            "weight_kg": 61,
            "activity_level": "Light",
            "goal": "Maintain Weight",
            "dietary_preferences": ["Gluten-free"],
        },
    )
    first_read_back = client.get("/api/profile", headers=first_headers)
    second_read_back = client.get("/api/profile", headers=second_headers)
    spoofed_get = client.get(
        "/api/profile",
        params={"user_id": OTHER_USER_ID},
        headers=first_headers,
    )
    spoofed_update = client.patch(
        "/api/profile",
        headers=first_headers,
        json={"user_id": OTHER_USER_ID, "name": "Overwrite Account B"},
    )

    assert first_update.status_code == 200
    assert second_initial.json()["dietary_preferences"] == []
    assert second_initial.json()["name"] is None
    assert second_update.status_code == 200
    assert second_read_back.json()["name"] == "Account B"
    assert second_read_back.json()["height_cm"] == 165
    assert first_read_back.json()["dietary_preferences"] == ["Vegetarian"]
    assert first_read_back.json()["name"] == "Account A"
    assert first_read_back.json()["age"] == 29
    assert first_read_back.json()["height_cm"] == 181
    assert first_read_back.json()["weight_kg"] == 78
    assert first_read_back.json()["activity_level"] == "Active"
    assert first_read_back.json()["goal"] == "Gain Muscle"
    assert first_read_back.json()["water_liters"] == 3
    assert spoofed_get.status_code == 200
    assert spoofed_get.json()["name"] == "Account A"
    assert spoofed_update.status_code == 422
    assert {document["user_id"] for document in database["user_profiles"].documents} == {
        TEST_USER_ID,
        OTHER_USER_ID,
    }


def validation_field_names(response):
    return {
        str(part)
        for issue in response.json().get("detail", [])
        for part in issue.get("loc", [])
    }


def test_user_meals_daily_totals_and_guessed_delete_are_isolated(
    client,
    database,
    token_factory,
):
    first_headers = bearer(token_factory.issue(TEST_USER_ID))
    second_headers = bearer(token_factory.issue(OTHER_USER_ID))

    first = client.post(
        "/api/meals",
        headers=first_headers,
        json={"preset_id": "paneer-rice", "meal_slot": "Lunch"},
    )
    second = client.post(
        "/api/meals",
        headers=second_headers,
        json={"preset_id": "paneer-rice", "meal_slot": "Dinner"},
    )

    assert first.status_code == second.status_code == 201
    first_meal = first.json()
    second_meal = second.json()
    assert database["user_meals"].documents[0]["user_id"] == TEST_USER_ID
    assert database["user_meals"].documents[1]["user_id"] == OTHER_USER_ID

    first_list = client.get(
        "/api/meals",
        params={"user_id": OTHER_USER_ID, "date": first_meal["meal_day"]},
        headers=first_headers,
    )
    second_list = client.get(
        "/api/meals",
        params={"date": second_meal["meal_day"]},
        headers=second_headers,
    )
    assert first_list.json()["count"] == 1
    assert first_list.json()["items"][0]["id"] == first_meal["id"]
    assert second_list.json()["items"][0]["id"] == second_meal["id"]

    first_daily = client.get(
        "/api/nutrition/daily",
        params={"date": first_meal["meal_day"]},
        headers=first_headers,
    )
    second_daily = client.get(
        "/api/nutrition/daily",
        params={"date": second_meal["meal_day"]},
        headers=second_headers,
    )
    assert first_daily.json()["meal_count"] == 1
    assert second_daily.json()["meal_count"] == 1

    guessed_delete = client.delete(
        f"/api/meals/{second_meal['id']}",
        headers=first_headers,
    )
    owner_delete = client.delete(
        f"/api/meals/{second_meal['id']}",
        headers=second_headers,
    )
    assert guessed_delete.status_code == 404
    assert owner_delete.status_code == 204
    assert client.get("/api/meals", headers=second_headers).json()["count"] == 0
    assert database["meals"].documents == []


def test_legacy_meals_are_inaccessible_and_unchanged(client, database, token_factory):
    from bson import ObjectId

    legacy_meal = {
        "_id": ObjectId("64d111111111111111111111"),
        "name": "legacy private meal",
        "meal_slot": "Lunch",
        "consumed_at": datetime(2026, 10, 15, 12, tzinfo=UTC),
        "meal_day": "2026-10-15",
        "nutrition": {"calories": 900},
        "data_source": "user_provided",
    }
    database["meals"].documents.append(legacy_meal)
    headers = bearer(token_factory.issue())

    listing = client.get("/api/meals?date=2026-10-15", headers=headers)
    daily = client.get("/api/nutrition/daily?date=2026-10-15", headers=headers)
    guessed_delete = client.delete(
        f"/api/meals/{legacy_meal['_id']}",
        headers=headers,
    )

    assert listing.status_code == 200
    assert listing.json()["count"] == 0
    assert daily.status_code == 200
    assert daily.json()["meal_count"] == 0
    assert guessed_delete.status_code == 404
    assert database["meals"].documents == [legacy_meal]
    assert database["user_meals"].documents == []


def test_preset_custom_and_usda_meals_are_owned_by_authenticated_user(
    client,
    database,
    token_factory,
):
    headers = bearer(token_factory.issue())
    requests = [
        {"preset_id": "paneer-rice", "meal_slot": "Lunch"},
        {
            "name": "Homemade soup",
            "nutrition": {"calories": 180, "protein": 8, "carbs": 24, "fats": 5},
        },
        {
            "name": "Apples, raw, with skin",
            "data_source": "usda_food_data_central",
            "fdc_id": 12345,
            "serving": {"description": "1 medium (182 g)", "gram_weight": 182},
            "nutrition": {"calories": 95, "protein": 0.5, "carbs": 25, "fats": 0.3},
        },
    ]

    responses = [client.post("/api/meals", headers=headers, json=body) for body in requests]

    assert [response.status_code for response in responses] == [201, 201, 201]
    assert [response.json()["data_source"] for response in responses] == [
        "sample_preset",
        "user_provided",
        "usda_food_data_central",
    ]
    assert all(document["user_id"] == TEST_USER_ID for document in database["user_meals"].documents)
    assert database["meals"].documents == []


def test_server_ignores_spoofed_owner_query_and_rejects_owner_body(client, token_factory):
    headers = bearer(token_factory.issue())
    created = client.post(
        "/api/meals",
        headers=headers,
        json={
            "user_id": OTHER_USER_ID,
            "preset_id": "paneer-rice",
        },
    )
    listed = client.get("/api/meals", params={"user_id": OTHER_USER_ID}, headers=headers)

    assert created.status_code == 422
    assert "user_id" in validation_field_names(created)
    assert listed.status_code == 200
    assert listed.json()["count"] == 0


def test_meal_day_uses_utc_when_consumption_crosses_midnight(client, token_factory):
    headers = bearer(token_factory.issue())
    created = client.post(
        "/api/meals",
        headers=headers,
        json={
            "preset_id": "paneer-rice",
            "consumed_at": "2026-10-15T23:30:00-02:00",
        },
    )

    assert created.status_code == 201
    assert created.json()["consumed_at"].startswith("2026-10-16T01:30:00")
    assert created.json()["meal_day"] == "2026-10-16"


def test_protected_collection_indexes_are_owner_scoped_and_legacy_data_is_not_indexed(
    authenticated_client,
    database,
):
    profile_index_names = [item["name"] for item in database["user_profiles"].indexes]
    meal_index_names = [item["name"] for item in database["user_meals"].indexes]

    assert profile_index_names == ["user_profiles_user_id_unique"]
    assert database["user_profiles"].indexes[0]["unique"] is True
    assert meal_index_names == [
        "user_meals_user_day_consumed_at",
        "user_meals_user_consumed_at",
    ]
    assert database["meals"].indexes == []
    assert database["profiles"].indexes == []


def test_auth_user_lookup_uses_publishable_key_and_bearer_token(monkeypatch):
    config = SupabaseAuthConfig(
        issuer=TEST_ISSUER,
        jwks_url=f"{TEST_ISSUER}/.well-known/jwks.json",
        user_url=f"{TEST_ISSUER}/user",
        publishable_key="test-publishable-key",
    )
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"id": TEST_USER_ID, "email_confirmed_at": "2026-10-01T00:00:00Z"}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(auth.httpx, "get", fake_get)
    user = auth._fetch_supabase_user("synthetic-access-token", config)

    assert captured["url"] == config.user_url
    assert captured["headers"] == {
        "apikey": "test-publishable-key",
        "Authorization": "Bearer synthetic-access-token",
    }
    assert user["id"] == TEST_USER_ID
