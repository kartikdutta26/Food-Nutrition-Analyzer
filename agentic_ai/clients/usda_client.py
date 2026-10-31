"""Bounded USDA HTTP requests. No credentials are included in errors or cache keys."""

import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from agentic_ai.nutrition_config import NutritionSettings
from agentic_ai.nutrition_errors import (FoodNotFoundError, MissingCredentialsError, USDAAuthenticationError, USDAConnectionError, USDARateLimitError, USDAResponseError, USDATimeoutError)

BASE_URL = "https://api.nal.usda.gov/fdc/v1"
MAX_BYTES = 4_000_000


class USDAClient:
    def __init__(self, settings=None, *, sleeper=time.sleep):
        self.settings = settings if settings is not None else NutritionSettings.from_environment()
        self.sleeper = sleeper
        self._details = {}
        self._searches = {}

    def _request(self, path, payload=None):
        secret = self.settings.api_key
        if secret is None or not secret.get_secret_value().strip():
            raise MissingCredentialsError("Live USDA lookup requires USDA_API_KEY in the environment or agentic_ai/.env.")
        url = BASE_URL + path + "?" + urlencode({"api_key": secret.get_secret_value()})
        request = Request(url, data=json.dumps(payload).encode() if payload is not None else None, headers={"Accept": "application/json", "Content-Type": "application/json"})
        for attempt in range(self.settings.retries + 1):
            try:
                with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                    raw = response.read(MAX_BYTES + 1)
            except HTTPError as error:
                status = error.code
                retry_after = error.headers.get("Retry-After") if error.headers else None
                error.close()
                if status in {401, 403}:
                    raise USDAAuthenticationError("USDA rejected the API credentials.") from None
                if status == 404:
                    raise FoodNotFoundError("The requested USDA food record was not found.") from None
                wait = None
                if status == 429 and retry_after is not None:
                    try:
                        parsed = float(retry_after)
                        if 0 <= parsed <= self.settings.max_retry_wait:
                            wait = parsed
                    except ValueError:
                        pass
                elif status in {500, 502, 503, 504}:
                    wait = min(0.25 * (attempt + 1), self.settings.max_retry_wait)
                if wait is not None and attempt < self.settings.retries:
                    self.sleeper(wait)
                    continue
                if status == 429:
                    raise USDARateLimitError("USDA rate limit reached; try later. No snapshot fallback was substituted.") from None
                raise USDAResponseError(f"USDA request failed with HTTP {status}.") from None
            except TimeoutError:
                raise USDATimeoutError("USDA lookup timed out.") from None
            except URLError as error:
                if isinstance(error.reason, TimeoutError):
                    raise USDATimeoutError("USDA lookup timed out.") from None
                raise USDAConnectionError("Cannot connect to USDA FoodData Central.") from None
            except (OSError, HTTPException):
                raise USDAConnectionError("USDA connection failed or was interrupted.") from None
            if len(raw) > MAX_BYTES:
                raise USDAResponseError("USDA returned an oversized response.")
            try:
                return json.loads(raw, parse_float=Decimal, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            except (ValueError, UnicodeError):
                raise USDAResponseError("USDA returned unreadable JSON.") from None
        raise AssertionError("Retry loop must return or raise")

    def search(self, query):
        if query not in self._searches:
            self._searches[query] = self._request("/foods/search", {"query": query, "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"], "pageSize": self.settings.page_size})
        return self._searches[query]

    def food(self, fdc_id):
        if isinstance(fdc_id, bool) or not isinstance(fdc_id, int) or fdc_id <= 0:
            raise FoodNotFoundError("A positive integer USDA food ID is required.")
        if fdc_id not in self._details:
            self._details[fdc_id] = (self._request(f"/food/{fdc_id}"), datetime.now(timezone.utc).isoformat())
        return self._details[fdc_id]
