import logging
from datetime import UTC, datetime

import httpx
import pytest
from fastapi.testclient import TestClient
from pymongo.errors import ConfigurationError, PyMongoError

from app.main import create_app


def validation_errors(response):
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert errors
    assert all({"loc", "msg", "type"} <= error.keys() for error in errors)
    return errors


def test_health_routes(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/health").json()["status"] == "healthy"
    assert client.get("/api/db-health").json()["status"] == "connected"


def test_database_health_returns_503_when_ping_fails(client):
    client.app.state.mongodb_client.fail_ping = True
    response = client.get("/api/db-health")
    assert response.status_code == 503
    assert response.json()["detail"] == "MongoDB connection failed"


def test_atlas_srv_startup_error_is_diagnostic_and_redacted(monkeypatch, caplog):
    from app import main

    synthetic_uri = "mongodb+srv://audit_user:do-not-log@cluster.example.invalid/nutriai"

    def fail_during_srv_resolution(*args, **kwargs):
        assert kwargs["connectTimeoutMS"] == 30000
        raise ConfigurationError(
            "The resolution lifetime expired after 21 seconds. DNS SRV resolution "
            f"failed for {synthetic_uri}"
        )

    monkeypatch.setattr(main, "MONGODB_URI", synthetic_uri)
    monkeypatch.setattr(main, "MongoClient", fail_during_srv_resolution)

    with caplog.at_level(logging.ERROR, logger="app.main"):
        with pytest.raises(RuntimeError, match="DNS SRV/TXT resolution failed") as error:
            with TestClient(create_app()):
                pass

    assert "ConfigurationError" in str(error.value)
    assert "ConfigurationError" in caplog.text
    assert "DNS SRV/TXT resolution failed" in caplog.text
    assert synthetic_uri not in str(error.value)
    assert synthetic_uri not in caplog.text
    assert "audit_user" not in caplog.text
    assert "do-not-log" not in caplog.text


def test_food_analysis_returns_labeled_sample_preset(client):
    response = client.post(
        "/api/food/analyze",
        json={"food_name": "  paneer rice bowl  "},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["preset_id"] == "paneer-rice"
    assert result["nutrition"]["calories"] == 620
    assert result["data_source"] == "sample_preset"
    assert "sample" in result["notice"].lower()


def test_food_analysis_rejects_unsupported_food(client, monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.usda.httpx.get",
        lambda *args, **kwargs: _fdc_response({"foods": []}),
    )
    response = client.post("/api/food/analyze", json={"food_name": "unknown soup"})
    assert response.status_code == 404
    assert "No USDA FoodData Central match" in response.json()["detail"]


def _fdc_response(payload, status_code=200):
    class Response:
        def __init__(self):
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("GET", "https://example.test")
                response = httpx.Response(self.status_code, request=request)
                raise httpx.HTTPStatusError("upstream error", request=request, response=response)

        def json(self):
            return payload

    return Response()


def test_food_analysis_uses_usda_food_data_central_and_returns_serving(
    client, monkeypatch
):
    monkeypatch.setenv("USDA_API_KEY", "test-key-do-not-return")
    calls = []
    responses = [
        _fdc_response({
            "foods": [{
                "fdcId": 12345,
                "description": "Apples, raw, with skin",
                "dataType": "Foundation",
            }],
        }),
        _fdc_response({
            "fdcId": 12345,
            "description": "Apples, raw, with skin",
            "dataType": "Foundation",
            "foodPortions": [{
                "portionDescription": "1 cup, sliced",
                "gramWeight": 109,
            }],
            "foodNutrients": [
                {"nutrient": {"id": 1008, "name": "Energy", "unitName": "kcal"}, "amount": 52},
                {"nutrient": {"id": 1003, "name": "Protein", "unitName": "g"}, "amount": 0.26},
                {"nutrient": {"id": 1005, "name": "Carbohydrate, by difference", "unitName": "g"}, "amount": 13.81},
                {"nutrient": {"id": 1004, "name": "Total lipid (fat)", "unitName": "g"}, "amount": 0.17},
                {"nutrient": {"id": 1079, "name": "Fiber, total dietary", "unitName": "g"}, "amount": 2.4},
            ],
        }),
    ]

    def fake_get(url, *, params, timeout):
        calls.append((url, params, timeout))
        return responses.pop(0)

    monkeypatch.setattr("app.services.usda.httpx.get", fake_get)
    response = client.post("/api/food/analyze", json={"food_name": "apple"})

    assert response.status_code == 200
    result = response.json()
    assert result["name"] == "Apples, raw, with skin"
    assert result["fdc_id"] == 12345
    assert result["serving"] == {"description": "1 cup, sliced (109 g)", "gram_weight": 109}
    assert result["nutrition"]["calories"] == 56.68
    assert result["nutrition"]["protein"] == 0.2834
    assert result["data_source"] == "usda_food_data_central"
    assert "USDA FoodData Central" in result["notice"]
    assert "test-key-do-not-return" not in response.text
    assert len(calls) == 2
    assert calls[0][1][0] == ("api_key", "test-key-do-not-return")
    assert calls[0][2] == 8.0


def test_usda_analysis_uses_100g_and_keeps_unreported_fiber_null(client, monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "test-key")
    responses = [
        _fdc_response({"foods": [{"fdcId": 7, "description": "Egg, whole, raw"}]}),
        _fdc_response({
            "description": "Egg, whole, raw",
            "foodNutrients": [
                {"nutrient": {"id": 1008, "name": "Energy", "unitName": "kcal"}, "amount": 143},
                {"nutrient": {"id": 1003, "name": "Protein", "unitName": "g"}, "amount": 12.6},
                {"nutrient": {"id": 1005, "name": "Carbohydrate", "unitName": "g"}, "amount": 0.72},
                {"nutrient": {"id": 1004, "name": "Total lipid", "unitName": "g"}, "amount": 9.5},
            ],
        }),
    ]
    monkeypatch.setattr("app.services.usda.httpx.get", lambda *args, **kwargs: responses.pop(0))

    response = client.post("/api/food/analyze", json={"food_name": "egg"})

    assert response.status_code == 200
    assert response.json()["serving"] == {"description": "100 g", "gram_weight": 100}
    assert response.json()["nutrition"]["fiber"] is None


def test_usda_search_ranks_common_foods_and_servings_for_ambiguous_names(
    client, monkeypatch
):
    monkeypatch.setenv("USDA_API_KEY", "test-key")
    cases = [
        (
            "banana",
            [
                {"fdcId": 11, "description": "Bananas, dehydrated, or banana powder"},
                {"fdcId": 12, "description": "Bananas, raw, with added sugar"},
                {"fdcId": 13, "description": "Bananas, raw"},
            ],
            13,
            "Bananas, raw",
            [
                {"portionDescription": "1 inch", "gramWeight": 6.2},
                {"portionDescription": "1 medium (7\" to 8-7/8\" long)", "gramWeight": 118},
            ],
            "1 medium (7\" to 8-7/8\" long) (118 g)",
        ),
        (
            "apple",
            [
                {"fdcId": 21, "description": "Apples, dried"},
                {"fdcId": 22, "description": "Apples, raw, with skin, sliced"},
                {"fdcId": 23, "description": "Apples, raw, with skin"},
            ],
            23,
            "Apples, raw, with skin",
            [
                {"portionDescription": "1 slice", "gramWeight": 10},
                {"portionDescription": "1 medium", "gramWeight": 182},
            ],
            "1 medium (182 g)",
        ),
        (
            "rice",
            [
                {"fdcId": 31, "description": "Rice flour, white"},
                {"fdcId": 32, "description": "Rice, white, long-grain, regular, cooked"},
                {"fdcId": 33, "description": "Rice, long-grain, cooked"},
            ],
            33,
            "Rice, long-grain, cooked",
            [
                {"portionDescription": "1 tablespoon", "gramWeight": 15},
                {"portionDescription": "1 cup", "gramWeight": 158},
            ],
            "1 cup (158 g)",
        ),
    ]
    nutrients = [
        {"nutrient": {"id": 1008, "name": "Energy", "unitName": "kcal"}, "amount": 100},
        {"nutrient": {"id": 1003, "name": "Protein", "unitName": "g"}, "amount": 4},
        {"nutrient": {"id": 1005, "name": "Carbohydrate", "unitName": "g"}, "amount": 20},
        {"nutrient": {"id": 1004, "name": "Total lipid", "unitName": "g"}, "amount": 2},
    ]

    for query, candidates, selected_id, selected_name, portions, serving in cases:
        responses = [
            _fdc_response({"foods": candidates}),
            _fdc_response({
                "fdcId": selected_id,
                "description": selected_name,
                "foodPortions": portions,
                "foodNutrients": nutrients,
            }),
        ]
        monkeypatch.setattr(
            "app.services.usda.httpx.get",
            lambda *args, **kwargs: responses.pop(0),
        )

        response = client.post("/api/food/analyze", json={"food_name": query})

        assert response.status_code == 200
        result = response.json()
        assert result["fdc_id"] == selected_id
        assert result["name"] == selected_name
        assert result["serving"]["description"] == serving
        assert result["data_source"] == "usda_food_data_central"


def test_food_analysis_returns_match_choices_and_fetches_selected_usda_food(
    client, monkeypatch
):
    monkeypatch.setenv("USDA_API_KEY", "test-key")
    search_result = _fdc_response({
        "foods": [
            {"fdcId": 101, "description": "Bananas, raw", "dataType": "Foundation"},
            {"fdcId": 202, "description": "Bananas, frozen", "dataType": "SR Legacy"},
        ],
    })
    nutrients = [
        {"nutrient": {"id": 1008, "name": "Energy", "unitName": "kcal"}, "amount": 89},
        {"nutrient": {"id": 1003, "name": "Protein", "unitName": "g"}, "amount": 1.1},
        {"nutrient": {"id": 1005, "name": "Carbohydrate", "unitName": "g"}, "amount": 22.8},
        {"nutrient": {"id": 1004, "name": "Total lipid", "unitName": "g"}, "amount": 0.3},
    ]
    responses = [
        search_result,
        _fdc_response({
            "fdcId": 101,
            "description": "Bananas, raw",
            "foodPortions": [{"portionDescription": "1 medium", "gramWeight": 118}],
            "foodNutrients": nutrients,
        }),
    ]
    monkeypatch.setattr(
        "app.services.usda.httpx.get",
        lambda *args, **kwargs: responses.pop(0),
    )

    initial = client.post("/api/food/analyze", json={"food_name": "banana"})

    assert initial.status_code == 200
    assert initial.json()["fdc_id"] == 101
    assert initial.json()["matches"] == [
        {"fdc_id": 101, "name": "Bananas, raw", "category": "Foundation"},
        {"fdc_id": 202, "name": "Bananas, frozen", "category": "SR Legacy"},
    ]

    responses.extend([
        search_result,
        _fdc_response({
            "fdcId": 202,
            "description": "Bananas, frozen",
            "foodPortions": [{"portionDescription": "1 cup", "gramWeight": 225}],
            "foodNutrients": nutrients,
        }),
    ])
    selected = client.post(
        "/api/food/analyze",
        json={"food_name": "banana", "fdc_id": 202},
    )

    assert selected.status_code == 200
    assert selected.json()["fdc_id"] == 202
    assert selected.json()["name"] == "Bananas, frozen"
    assert selected.json()["serving"] == {
        "description": "1 cup (225 g)",
        "gram_weight": 225,
    }


def test_usda_analysis_handles_missing_key_timeout_and_no_match(client, monkeypatch):
    monkeypatch.delenv("USDA_API_KEY", raising=False)
    missing_key = client.post("/api/food/analyze", json={"food_name": "apple"})
    assert missing_key.status_code == 503
    assert "USDA_API_KEY" in missing_key.json()["detail"]

    monkeypatch.setenv("USDA_API_KEY", "test-key")

    def timeout(*args, **kwargs):
        raise httpx.TimeoutException("simulated timeout")

    monkeypatch.setattr("app.services.usda.httpx.get", timeout)
    timed_out = client.post("/api/food/analyze", json={"food_name": "apple"})
    assert timed_out.status_code == 504
    assert "took too long" in timed_out.json()["detail"]

    monkeypatch.setattr(
        "app.services.usda.httpx.get",
        lambda *args, **kwargs: _fdc_response({"foods": []}),
    )
    no_match = client.post("/api/food/analyze", json={"food_name": "unlisted fruit"})
    assert no_match.status_code == 404
    assert "No USDA FoodData Central match" in no_match.json()["detail"]


def test_usda_analysis_does_not_use_a_partially_related_result(client, monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.usda.httpx.get",
        lambda *args, **kwargs: _fdc_response({
            "foods": [{"fdcId": 1, "description": "Apples, raw, with skin"}],
        }),
    )

    response = client.post("/api/food/analyze", json={"food_name": "apple pie"})

    assert response.status_code == 404
    assert "No USDA FoodData Central match" in response.json()["detail"]


def test_usda_name_matching_handles_common_plural_food_names():
    from app.services.usda import _candidate_matches_query

    assert _candidate_matches_query("tomato", {"description": "Tomatoes, red, ripe, raw"})
    assert _candidate_matches_query("berry", {"description": "Berries, raw"})
    banana_powder = {"description": "Bananas, dehydrated, or banana powder"}
    assert not _candidate_matches_query("banana", banana_powder)
    assert _candidate_matches_query("banana powder", banana_powder)


def test_usda_analysis_handles_upstream_api_errors_without_details(client, monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.usda.httpx.get",
        lambda *args, **kwargs: _fdc_response({"message": "private upstream response"}, 429),
    )

    response = client.post("/api/food/analyze", json={"food_name": "apple"})

    assert response.status_code == 503
    assert "could not complete the lookup" in response.json()["detail"]
    assert "private upstream response" not in response.text


def test_usda_analysis_reports_food_matches_without_required_nutrients(client, monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "test-key")
    responses = [
        _fdc_response({"foods": [{"fdcId": 8, "description": "Apple, raw"}]}),
        _fdc_response({"description": "Apple, raw", "foodNutrients": []}),
    ]
    monkeypatch.setattr(
        "app.services.usda.httpx.get",
        lambda *args, **kwargs: responses.pop(0),
    )

    response = client.post("/api/food/analyze", json={"food_name": "apple"})

    assert response.status_code == 404
    assert "found this food but does not report complete" in response.json()["detail"]


def test_usda_lookup_meal_preserves_source_and_serving_in_storage(authenticated_client, database):
    response = authenticated_client.post(
        "/api/meals",
        json={
            "name": "Apples, raw, with skin",
            "meal_slot": "Snack",
            "data_source": "usda_food_data_central",
            "fdc_id": 12345,
            "serving": {"description": "1 cup, sliced (109 g)", "gram_weight": 109},
            "nutrition": {
                "calories": 56.68,
                "protein": 0.2834,
                "carbs": 15.0529,
                "fats": 0.1853,
                "fiber": None,
            },
        },
    )

    assert response.status_code == 201
    meal = response.json()
    assert meal["data_source"] == "usda_food_data_central"
    assert meal["fdc_id"] == 12345
    assert meal["serving"]["description"] == "1 cup, sliced (109 g)"
    assert database["user_meals"].documents[0]["data_source"] == "usda_food_data_central"

    daily = authenticated_client.get("/api/nutrition/daily", params={"date": meal["meal_day"]})
    assert daily.status_code == 200
    assert daily.json()["totals"]["calories"] == 56.68
    assert daily.json()["totals"]["fiber"] is None


def test_usda_meal_requires_lookup_metadata(authenticated_client):
    response = authenticated_client.post(
        "/api/meals",
        json={
            "name": "Food",
            "data_source": "usda_food_data_central",
            "nutrition": {"calories": 10, "protein": 1, "carbs": 2, "fats": 3},
        },
    )

    assert response.status_code == 422
    assert "fdc_id" in validation_errors(response)[0]["msg"]


def test_food_analysis_validates_exactly_one_identifier(client):
    response = client.post(
        "/api/food/analyze",
        json={"food_name": "Paneer Rice Bowl", "preset_id": "paneer-rice"},
    )
    assert response.status_code == 422
    errors = validation_errors(response)
    assert "remove the other field" in errors[0]["msg"]


def test_food_analysis_missing_identifier_explains_valid_fields(client):
    response = client.post("/api/food/analyze", json={})
    errors = validation_errors(response)
    assert "'preset_id' or 'food_name'" in errors[0]["msg"]


def test_food_analysis_blank_identifier_names_field_and_fix(client):
    response = client.post("/api/food/analyze", json={"preset_id": "   "})
    errors = validation_errors(response)
    assert any("preset_id" in error["loc"] for error in errors)
    assert any("too short" in error["msg"] for error in errors)


def test_malformed_json_explains_how_to_fix_body(client):
    response = client.post(
        "/api/food/analyze",
        content='{"preset_id":',
        headers={"Content-Type": "application/json"},
    )
    assert "not valid JSON" in validation_errors(response)[0]["msg"]


def test_create_list_daily_totals_and_delete_meal(authenticated_client, database):
    response = authenticated_client.post(
        "/api/meals",
        json={
            "preset_id": "paneer-rice",
            "meal_slot": "Lunch",
            "consumed_at": "2026-10-15T13:30:00+05:30",
        },
    )
    assert response.status_code == 201
    meal = response.json()
    assert meal["data_source"] == "sample_preset"
    assert meal["consumed_at"].startswith("2026-10-15T08:00:00")

    listing = authenticated_client.get("/api/meals", params={"date": "2026-10-15"})
    assert listing.status_code == 200
    assert listing.json()["count"] == 1
    assert listing.json()["items"][0]["id"] == meal["id"]

    daily = authenticated_client.get("/api/nutrition/daily?date=2026-10-15")
    assert daily.status_code == 200
    assert daily.json()["date"] == "2026-10-15"
    assert daily.json()["meal_count"] == 1
    assert daily.json()["totals"]["calories"] == 620
    assert daily.json()["totals"]["protein"] == 28

    deleted = authenticated_client.delete(f"/api/meals/{meal['id']}")
    assert deleted.status_code == 204
    assert authenticated_client.get("/api/meals").json()["count"] == 0
    assert database["meals"].documents == []
    assert database["user_meals"].documents == []


def test_create_manual_meal_stores_caller_provided_values(authenticated_client, database):
    response = authenticated_client.post(
        "/api/meals",
        json={
            "name": "Homemade soup",
            "meal_slot": "dinner",
            "nutrition": {
                "calories": 180,
                "protein": 8,
                "carbs": 24,
                "fats": 5,
            },
        },
    )
    assert response.status_code == 201
    assert response.json()["data_source"] == "user_provided"
    assert response.json()["meal_slot"] == "Dinner"
    assert response.json()["nutrition"]["fiber"] == 0
    assert database["user_meals"].documents[0]["user_id"] == "11111111-1111-4111-8111-111111111111"


def test_meal_validation_and_missing_delete(authenticated_client):
    invalid_nutrition = authenticated_client.post(
        "/api/meals",
        json={"name": "Bad meal", "nutrition": {"calories": -1}},
    )
    assert invalid_nutrition.status_code == 422

    missing_source = authenticated_client.post("/api/meals", json={"meal_slot": "Lunch"})
    assert missing_source.status_code == 422
    assert "'preset_id' alone" in validation_errors(missing_source)[0]["msg"]

    missing_custom_name = authenticated_client.post(
        "/api/meals",
        json={"nutrition": {"calories": 100, "protein": 5, "carbs": 10, "fats": 2}},
    )
    assert "'name' is required" in validation_errors(missing_custom_name)[0]["msg"]

    missing_custom_nutrition = authenticated_client.post(
        "/api/meals",
        json={"name": "Soup"},
    )
    assert "'nutrition' is required" in validation_errors(missing_custom_nutrition)[0]["msg"]

    incomplete_macros = authenticated_client.post(
        "/api/meals",
        json={"name": "Soup", "nutrition": {"calories": 100}},
    )
    missing_fields = validation_errors(incomplete_macros)
    assert any(error["loc"] == ["body", "nutrition", "protein"] for error in missing_fields)
    assert any("non-negative number" in error["msg"] for error in missing_fields)

    invalid_slot = authenticated_client.post(
        "/api/meals",
        json={
            "preset_id": "paneer-rice",
            "meal_slot": "Brunch",
        },
    )
    assert "meal_slot" in validation_errors(invalid_slot)[0]["msg"]

    invalid_timestamp = authenticated_client.post(
        "/api/meals",
        json={"preset_id": "paneer-rice", "consumed_at": "tomorrow afternoon"},
    )
    assert "ISO 8601 datetime" in validation_errors(invalid_timestamp)[0]["msg"]

    invalid_id = authenticated_client.delete("/api/meals/not-an-object-id")
    assert invalid_id.status_code == 422
    assert "24-character hexadecimal" in validation_errors(invalid_id)[0]["msg"]

    missing_id = authenticated_client.delete("/api/meals/64d111111111111111111111")
    assert missing_id.status_code == 404


def test_meal_database_error_returns_service_unavailable(authenticated_client, database):
    database["user_meals"].failure = PyMongoError("simulated failure")
    response = authenticated_client.get("/api/meals")
    assert response.status_code == 503
    assert response.json()["detail"] == "MongoDB operation failed"


def test_meal_list_query_validation_messages(authenticated_client):
    invalid_date = authenticated_client.get("/api/meals", params={"date": "15-10-2026"})
    assert "YYYY-MM-DD" in validation_errors(invalid_date)[0]["msg"]

    too_small = authenticated_client.get("/api/meals", params={"limit": 0})
    assert "'limit' must be at least 1" in validation_errors(too_small)[0]["msg"]

    too_large = authenticated_client.get("/api/meals", params={"limit": 501})
    assert "'limit' must be at most 500" in validation_errors(too_large)[0]["msg"]


def test_daily_nutrition_requires_valid_iso_date(authenticated_client):
    missing = authenticated_client.get("/api/nutrition/daily")
    assert "?date=YYYY-MM-DD" in validation_errors(missing)[0]["msg"]

    invalid = authenticated_client.get("/api/nutrition/daily", params={"date": "yesterday"})
    assert "ISO date format YYYY-MM-DD" in validation_errors(invalid)[0]["msg"]


def test_profile_get_returns_unconfigured_targets_and_patch_updates_profile(authenticated_client, database):
    initial = authenticated_client.get("/api/profile")
    assert initial.status_code == 200
    assert initial.json()["name"] is None
    assert initial.json()["age"] is None
    assert initial.json()["height_cm"] is None
    assert initial.json()["weight_kg"] is None
    assert initial.json()["activity_level"] is None
    assert initial.json()["goal"] is None
    assert initial.json()["water_liters"] is None
    assert initial.json()["dietary_preferences"] == []
    assert initial.json()["targets"] is None
    assert database["profiles"].documents == []
    assert database["user_profiles"].documents[0]["user_id"] == "11111111-1111-4111-8111-111111111111"

    updated = authenticated_client.patch(
        "/api/profile",
        json={
            "name": "Kartik Dutta",
            "age": 29,
            "height_cm": 181,
            "weight_kg": 78,
            "activity_level": "Active",
            "goal": "Gain Muscle",
            "water_liters": 3,
            "dietary_preferences": ["Vegetarian", "vegetarian", "Dairy-free"],
            "targets": {"calories": 2100, "protein": 115, "carbs": 230, "fats": 70},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Kartik Dutta"
    assert updated.json()["age"] == 29
    assert updated.json()["height_cm"] == 181
    assert updated.json()["weight_kg"] == 78
    assert updated.json()["activity_level"] == "Active"
    assert updated.json()["goal"] == "Gain Muscle"
    assert updated.json()["water_liters"] == 3
    assert updated.json()["dietary_preferences"] == ["Vegetarian", "Dairy-free"]
    assert updated.json()["targets"]["protein"] == 115
    assert updated.json()["updated_at"] is not None
    refreshed = authenticated_client.get("/api/profile").json()
    assert refreshed["name"] == "Kartik Dutta"
    assert refreshed["age"] == 29
    assert refreshed["targets"]["calories"] == 2100


def test_profile_rejects_empty_patch_and_invalid_targets(authenticated_client):
    empty = authenticated_client.patch("/api/profile", json={})
    assert "at least one profile field" in validation_errors(empty)[0]["msg"]

    null_preferences = authenticated_client.patch(
        "/api/profile",
        json={"dietary_preferences": None},
    )
    assert "cannot be null" in validation_errors(null_preferences)[0]["msg"]

    null_targets = authenticated_client.patch("/api/profile", json={"targets": None})
    assert "'targets' cannot be null" in validation_errors(null_targets)[0]["msg"]

    missing_target = authenticated_client.patch(
        "/api/profile",
        json={"targets": {"calories": 2000, "protein": 100, "carbs": 200}},
    )
    assert any(
        error["loc"] == ["body", "targets", "fats"]
        for error in validation_errors(missing_target)
    )

    invalid = authenticated_client.patch(
        "/api/profile",
        json={"targets": {"calories": 0, "protein": 80, "carbs": 180, "fats": 50}},
    )
    assert "'targets.calories' must be greater than 0" in validation_errors(invalid)[0]["msg"]


def test_profile_preferences_explain_invalid_items_and_unknown_fields(authenticated_client):
    blank_item = authenticated_client.patch("/api/profile", json={"dietary_preferences": ["  "]})
    blank_errors = validation_errors(blank_item)
    assert any("dietary_preferences" in error["loc"] for error in blank_errors)
    assert any("at least 1 character" in error["msg"] for error in blank_errors)

    extra_field = authenticated_client.patch(
        "/api/profile",
        json={"daily_target": 2000},
    )
    assert "not supported" in validation_errors(extra_field)[0]["msg"]


def test_profile_rejects_invalid_personal_fields(authenticated_client):
    invalid_values = [
        {"age": 0},
        {"age": 121},
        {"height_cm": 301},
        {"weight_kg": 0},
        {"activity_level": "Very active"},
        {"goal": "Lose 20 kg"},
        {"water_liters": 21},
        {"user_id": "22222222-2222-4222-8222-222222222222"},
    ]
    for payload in invalid_values:
        response = authenticated_client.patch("/api/profile", json=payload)
        assert response.status_code == 422, payload


def test_profile_can_be_created_by_patch_without_prior_get(authenticated_client, database):
    response = authenticated_client.patch(
        "/api/profile",
        json={"dietary_preferences": ["Vegan"]},
    )
    assert response.status_code == 200
    assert response.json()["dietary_preferences"] == ["Vegan"]
    assert response.json()["targets"] is None
    assert database["user_profiles"].documents[0]["dietary_preferences"] == ["Vegan"]


def test_profile_get_requires_write_access_to_create_user_defaults(authenticated_client, database):
    database["user_profiles"].read_only = True

    response = authenticated_client.get("/api/profile")

    assert response.status_code == 503
    assert database["profiles"].documents == []


def test_existing_user_profiles_without_new_personal_fields_remain_usable(authenticated_client, database):
    existing_profile = {
        "user_id": "11111111-1111-4111-8111-111111111111",
        "dietary_preferences": ["Vegetarian"],
        "targets": {"calories": 2000, "protein": 100, "carbs": 200, "fats": 60},
        "updated_at": datetime(2026, 10, 1, tzinfo=UTC),
    }
    database["user_profiles"].documents.append(existing_profile)

    initial = authenticated_client.get("/api/profile")
    updated = authenticated_client.patch("/api/profile", json={"name": "Account Owner"})

    assert initial.status_code == 200
    assert initial.json()["name"] is None
    assert initial.json()["dietary_preferences"] == ["Vegetarian"]
    assert initial.json()["targets"]["calories"] == 2000
    assert updated.status_code == 200
    assert updated.json()["name"] == "Account Owner"
    assert updated.json()["targets"]["calories"] == 2000
    assert len(database["user_profiles"].documents) == 1
    assert database["user_profiles"].documents[0]["user_id"] == existing_profile["user_id"]


def test_profile_endpoints_leave_legacy_profile_unread_and_unchanged(authenticated_client, database):
    legacy_profile = {
        "_id": "default",
        "dietary_preferences": ["legacy-private-preference"],
        "targets": {"calories": 1, "protein": 1, "carbs": 1, "fats": 1},
        "updated_at": datetime(2026, 10, 1, tzinfo=UTC),
    }
    database["profiles"].documents.append(legacy_profile)

    response = authenticated_client.get("/api/profile")
    update = authenticated_client.patch(
        "/api/profile",
        json={"dietary_preferences": ["New account preference"]},
    )

    assert response.status_code == 200
    assert response.json()["targets"] is None
    assert response.json()["dietary_preferences"] == []
    assert update.status_code == 200
    assert database["profiles"].documents == [legacy_profile]
    assert database["user_profiles"].documents[0]["dietary_preferences"] == [
        "New account preference",
    ]


def test_profile_preserves_explicitly_saved_one_value_targets(authenticated_client):
    targets = {"calories": 1, "protein": 1, "carbs": 1, "fats": 1}

    updated = authenticated_client.patch("/api/profile", json={"targets": targets})

    assert updated.status_code == 200
    assert updated.json()["targets"] == targets
    assert authenticated_client.get("/api/profile").json()["targets"] == targets


def test_profile_database_error_returns_service_unavailable(authenticated_client, database):
    database["user_profiles"].failure = PyMongoError("simulated failure")
    response = authenticated_client.get("/api/profile")
    assert response.status_code == 503


def test_profile_update_database_error_returns_service_unavailable(
    authenticated_client,
    database,
    caplog,
):
    database["user_profiles"].failure = PyMongoError("simulated database URI detail")
    response = authenticated_client.patch(
        "/api/profile",
        json={"targets": {"calories": 2000, "protein": 100, "carbs": 200, "fats": 60}},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "MongoDB operation failed"
    assert "MongoDB operation failed for /api/profile (PyMongoError)" in caplog.text
    assert "simulated database URI detail" not in caplog.text


def test_cors_allows_local_vite_origin(client):
    response = client.options(
        "/api/profile",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


@pytest.mark.parametrize(
    "origin", ["http://127.0.0.1:5174", "http://localhost:5174"]
)
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/food/photo"),
        ("POST", "/api/food/analyze"),
        ("PATCH", "/api/profile"),
        ("DELETE", "/api/meals/000000000000000000000000"),
    ],
)
def test_cors_allows_frontend_preflight_for_api_methods(
    client, origin, method, path
):
    response = client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert method in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in response.headers


def _unsplash_response(payload, status_code=200):
    class Response:
        def __init__(self):
            self.status_code = status_code

        def json(self):
            return payload

    return Response()


def _unsplash_photo(photo_id="test-photo"):
    return {
        "urls": {"regular": f"https://images.unsplash.com/{photo_id}?w=1080"},
        "user": {
            "name": "Test Photographer",
            "links": {"html": "https://unsplash.com/@test-photographer"},
        },
        "links": {"html": f"https://unsplash.com/photos/{photo_id}"},
    }


def test_food_photo_search_returns_hotlinked_photo_and_attribution(client, monkeypatch):
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-unsplash-access-key")
    calls = []

    def fake_get(url, *, params, headers, timeout):
        calls.append((url, params, headers, timeout))
        return _unsplash_response({"results": [_unsplash_photo()]})

    monkeypatch.setattr("app.services.unsplash.httpx.get", fake_get)
    response = client.get("/api/food/photo", params={"food_name": "  banana  "})
    cached_response = client.get("/api/food/photo", params={"food_name": "BANANA"})

    assert response.status_code == 200
    result = response.json()
    assert result["image_url"] == "https://images.unsplash.com/test-photo?w=1080"
    assert result["photographer_name"] == "Test Photographer"
    assert "utm_source=nutriai_food_nutrition_analyzer" in result["photographer_profile_url"]
    assert "utm_medium=referral" in result["photographer_profile_url"]
    assert "utm_source=nutriai_food_nutrition_analyzer" in result["attribution_url"]
    assert "utm_medium=referral" in result["attribution_url"]
    assert "test-unsplash-access-key" not in response.text
    assert cached_response.json() == result
    assert len(calls) == 1
    assert calls[0][0] == "https://api.unsplash.com/search/photos"
    assert calls[0][1]["query"] == "banana food photography"
    assert calls[0][1]["orientation"] == "landscape"
    assert calls[0][2]["Authorization"] == "Client-ID test-unsplash-access-key"
    assert calls[0][2]["Accept-Version"] == "v1"
    assert calls[0][3] == 5.0


def test_food_photo_search_handles_missing_access_key(client, monkeypatch):
    monkeypatch.delenv("UNSPLASH_ACCESS_KEY", raising=False)

    response = client.get("/api/food/photo", params={"food_name": "missing key test"})

    assert response.status_code == 503
    assert "UNSPLASH_ACCESS_KEY" in response.json()["detail"]


def test_food_photo_search_returns_no_match_and_caches_it(client, monkeypatch):
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-unsplash-access-key")
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(args)
        return _unsplash_response({"results": []})

    monkeypatch.setattr("app.services.unsplash.httpx.get", fake_get)
    first = client.get("/api/food/photo", params={"food_name": "no-result-pineapple"})
    second = client.get("/api/food/photo", params={"food_name": "no-result-pineapple"})

    assert first.status_code == 404
    assert second.status_code == 404
    assert "No food photo" in second.json()["detail"]
    assert len(calls) == 1


@pytest.mark.parametrize(("upstream_status", "expected_status"), [(429, 503), (500, 502), (401, 502)])
def test_food_photo_search_handles_unsplash_http_failures(
    client, monkeypatch, upstream_status, expected_status
):
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-unsplash-access-key")
    monkeypatch.setattr(
        "app.services.unsplash.httpx.get",
        lambda *args, **kwargs: _unsplash_response({}, status_code=upstream_status),
    )

    response = client.get(
        "/api/food/photo",
        params={"food_name": f"upstream-error-{upstream_status}"},
    )

    assert response.status_code == expected_status
    assert "temporarily" in response.json()["detail"].lower()
    assert "test-unsplash-access-key" not in response.text


def test_food_photo_search_handles_upstream_timeout(client, monkeypatch):
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-unsplash-access-key")

    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("test timeout")

    monkeypatch.setattr("app.services.unsplash.httpx.get", timeout)
    response = client.get("/api/food/photo", params={"food_name": "timeout-test-food"})

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"]
    assert "test-unsplash-access-key" not in response.text
