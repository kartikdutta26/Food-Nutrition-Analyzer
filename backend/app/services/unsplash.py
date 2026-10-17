import os
from collections import OrderedDict
from threading import Lock
from time import monotonic
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import HTTPException

from app.schemas.photos import FoodPhotoResponse


UNSPLASH_SEARCH_URL = "https://api.unsplash.com/search/photos"
_CACHE_TTL_SECONDS = 15 * 60
_CACHE_MAX_ENTRIES = 256
_CACHE: OrderedDict[str, tuple[float, FoodPhotoResponse | None]] = OrderedDict()
_CACHE_LOCK = Lock()
_ATTRIBUTION_SOURCE = "nutriai_food_nutrition_analyzer"


def _with_attribution_params(url: str) -> str | None:
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    hostname = (parts.hostname or "").lower()
    is_unsplash = hostname == "unsplash.com" or hostname.endswith(".unsplash.com")
    if parts.scheme != "https" or not is_unsplash:
        return None

    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({"utm_source": _ATTRIBUTION_SOURCE, "utm_medium": "referral"})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _cache_get(key: str) -> tuple[bool, FoodPhotoResponse | None]:
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            return False, None
        expires_at, photo = entry
        if expires_at <= monotonic():
            del _CACHE[key]
            return False, None
        _CACHE.move_to_end(key)
        return True, photo.model_copy(deep=True) if photo is not None else None


def _cache_set(key: str, photo: FoodPhotoResponse | None) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (monotonic() + _CACHE_TTL_SECONDS, photo.model_copy(deep=True) if photo else None)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_MAX_ENTRIES:
            _CACHE.popitem(last=False)


def _usable_photo(photo: object) -> FoodPhotoResponse | None:
    if not isinstance(photo, dict):
        return None
    urls = photo.get("urls")
    user = photo.get("user")
    links = photo.get("links")
    if not isinstance(urls, dict) or not isinstance(user, dict) or not isinstance(links, dict):
        return None

    image_url = urls.get("regular") or urls.get("small")
    try:
        image_parts = urlsplit(image_url) if isinstance(image_url, str) else None
    except ValueError:
        image_parts = None
    user_links = user.get("links")
    if not isinstance(user_links, dict):
        return None
    profile_url = _with_attribution_params(user_links.get("html", ""))
    attribution_url = _with_attribution_params(links.get("html", ""))
    photographer_name = user.get("name")
    if (
        image_parts is None
        or image_parts.scheme != "https"
        or image_parts.hostname != "images.unsplash.com"
        or not isinstance(photographer_name, str)
        or not photographer_name.strip()
        or profile_url is None
        or attribution_url is None
    ):
        return None

    return FoodPhotoResponse(
        image_url=image_url,
        photographer_name=photographer_name.strip(),
        photographer_profile_url=profile_url,
        attribution_url=attribution_url,
    )


def search_food_photo(food_name: str) -> FoodPhotoResponse:
    query = " ".join(food_name.split())
    if not query:
        raise HTTPException(status_code=422, detail="Enter a food name to search for a photo.")

    access_key = os.getenv("UNSPLASH_ACCESS_KEY", "").strip()
    if not access_key:
        raise HTTPException(
            status_code=503,
            detail="Food photo search is not configured. Add UNSPLASH_ACCESS_KEY to backend/.env.",
        )

    cache_key = query.casefold()
    cache_found, cached_photo = _cache_get(cache_key)
    if cache_found:
        if cached_photo is None:
            raise HTTPException(status_code=404, detail="No food photo was found.")
        return cached_photo

    try:
        response = httpx.get(
            UNSPLASH_SEARCH_URL,
            params={
                "query": f"{query} food photography",
                "per_page": 5,
                "order_by": "relevant",
                "orientation": "landscape",
                "content_filter": "high",
            },
            headers={"Authorization": f"Client-ID {access_key}", "Accept-Version": "v1"},
            timeout=5.0,
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Food photo search timed out. Please try again.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Food photo search is temporarily unavailable.")

    if response.status_code == 429:
        raise HTTPException(status_code=503, detail="Food photo search is temporarily rate limited.")
    if response.status_code < 200 or response.status_code >= 300:
        raise HTTPException(status_code=502, detail="Food photo search is temporarily unavailable.")

    try:
        payload = response.json()
    except (TypeError, ValueError):
        raise HTTPException(status_code=502, detail="Food photo search returned an invalid response.")
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise HTTPException(status_code=502, detail="Food photo search returned an invalid response.")

    if not payload["results"]:
        _cache_set(cache_key, None)
        raise HTTPException(status_code=404, detail="No food photo was found.")

    for result in payload["results"]:
        photo = _usable_photo(result)
        if photo is not None:
            _cache_set(cache_key, photo)
            return photo

    raise HTTPException(status_code=502, detail="Food photo search returned no usable photo details.")
