# NutriAI Food Nutrition Analyzer

NutriAI has a React + Vite frontend and a FastAPI backend. The backend stores meal logs and a single development profile in MongoDB Atlas. It exposes six clearly labeled sample meals and looks up other food names in USDA FoodData Central. Uploaded images are previewed locally and are not analyzed.

USDA lookups use the selected food's USDA nutrient data and serving size. The USDA API key stays in the backend environment. Manual meal logging can still store nutrition values supplied by the caller.

## Backend setup

From the repository root, install the backend and test dependencies into the existing Python 3.14 environment:

```bash
cd backend
./venv/bin/python -m pip install -r requirements-dev.txt
```

If you need to create the virtual environment first:

```bash
cd backend
python3.14 -m venv venv
./venv/bin/python -m pip install -r requirements-dev.txt
```

Create `backend/.env` locally with your Atlas connection details:

```dotenv
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-host>/?retryWrites=true&w=majority&appName=NutriAI
MONGODB_DATABASE=nutriai_db
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
USDA_API_KEY=<your USDA FoodData Central API key>
```

Keep the real URI and API key private. `backend/.env` and `backend/venv/` are excluded from Git. TLS certificate verification remains enabled through `certifi`.

Start the API from the `backend` directory:

```bash
./venv/bin/python -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive OpenAPI docs are at `http://127.0.0.1:8000/docs`.

## API

Nutrition amounts are per serving. Calories are kcal; protein, carbs, fats, and fiber are grams. Dates and meal-day grouping use UTC. A timezone-aware `consumed_at` is converted to UTC; a timestamp without a timezone is treated as UTC.

### Health checks

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/db-health
```

`/api/health` checks that the service responds. `/api/db-health` pings Atlas and returns `503` if it cannot connect. The API requires a valid `MONGODB_URI` and reachable database during startup.

### Analyze a food

`POST /api/food/analyze` accepts exactly one of `preset_id` or `food_name`. A preset ID or exact preset name returns labeled sample nutrition. Other food names are searched in USDA FoodData Central:

```bash
curl -X POST http://127.0.0.1:8000/api/food/analyze \
  -H 'Content-Type: application/json' \
  -d '{"preset_id":"paneer-rice"}'
```

Sample IDs are `paneer-rice`, `masala-dosa`, `dal-tadka`, `chicken-tikka-bowl`, `palak-paneer`, and `fruit-acai-bowl`. Sample results include `data_source: "sample_preset"` and a notice that the values are demonstration data. USDA results include the selected `name`, `fdc_id`, `serving` (`description` and `gram_weight`), per-serving `nutrition`, and `data_source: "usda_food_data_central"`. A default serving portion is used when USDA provides one; otherwise values are returned per 100 g. Fiber is `null` when USDA does not report it.

### Create, list, and delete meals

Create a meal from a supported preset. Nutrition values are read from the server-side preset catalog:

```bash
curl -X POST http://127.0.0.1:8000/api/meals \
  -H 'Content-Type: application/json' \
  -d '{"preset_id":"paneer-rice","meal_slot":"Lunch"}'
```

To log a USDA result, send its returned `name`, `nutrition`, `fdc_id`, `serving`, and `data_source` fields to `POST /api/meals`, along with the chosen `meal_slot`. The frontend does this automatically and preserves the source in the saved meal record.

Or log a meal with nutrition values supplied by the caller:

```bash
curl -X POST http://127.0.0.1:8000/api/meals \
  -H 'Content-Type: application/json' \
  -d '{"name":"Homemade lentil soup","meal_slot":"Dinner","nutrition":{"calories":280,"protein":16,"carbs":38,"fats":6,"fiber":9}}'
```

For custom meals, `name` and `nutrition` are both required. `nutrition` requires `calories`, `protein`, `carbs`, and `fats`; `fiber` is optional and defaults to `0` for manual meals. USDA meals require `data_source`, `fdc_id`, and `serving`; the meal record keeps that attribution. `meal_slot` is optional, defaults to `Lunch`, and accepts `Breakfast`, `Lunch`, `Dinner`, or `Snack` in any letter case. `consumed_at` is optional and accepts an ISO 8601 timestamp.

List up to 100 most recent meals, or filter by UTC day using `date=YYYY-MM-DD` (the limit can be set from 1 to 500):

```bash
curl 'http://127.0.0.1:8000/api/meals?date=2026-10-15&limit=50'
```

Delete using the meal `id` returned on creation:

```bash
curl -X DELETE http://127.0.0.1:8000/api/meals/<meal-id>
```

### Daily nutrition totals

`GET /api/nutrition/daily` calculates totals from meal records for the required UTC date. Totals are computed from the source meal documents rather than stored separately.

```bash
curl 'http://127.0.0.1:8000/api/nutrition/daily?date=2026-10-15'
```

### User profile

The development API stores one profile with ID `default`. The first `GET` creates it with empty dietary preferences and no nutrition targets (`targets: null`). Set targets explicitly with `PATCH /api/profile`; the app does not infer or recommend target values. The Profile page requires calories, protein, carbohydrates, and fats before saving, and the Nutrition Journey prompts you to configure them while they are unset.

```bash
curl http://127.0.0.1:8000/api/profile

curl -X PATCH http://127.0.0.1:8000/api/profile \
  -H 'Content-Type: application/json' \
  -d '{"dietary_preferences":["Vegetarian","Dairy-free"],"targets":{"calories":2100,"protein":115,"carbs":230,"fats":70}}'
```

Profile updates are partial: send dietary preferences, targets, or both. Targets are replaced as a complete set when provided and each value must be positive. Dietary preferences accept up to 30 non-empty strings of at most 80 characters; duplicate preferences are removed case-insensitively. Send `[]` to clear the preference list.

## Errors and persistence

- Invalid request bodies, invalid dates, and malformed meal IDs return `422`.
- Validation responses use `{"detail":[{"loc":[...],"msg":"...","type":"..."}]}`. `loc` identifies the request field or query parameter; `msg` describes the correction. For example, an omitted daily date returns a message to add `?date=YYYY-MM-DD`.
- Foods with no related USDA match and missing meal IDs return `404`.
- A missing USDA key returns `503`; USDA timeouts return `504`, and upstream errors return a generic `502` or `503` without exposing credentials.
- MongoDB operation failures return `503` with a generic message; connection details and credentials are not included in API responses.
- MongoDB uses `meals` and `profiles` collections. Meal nutrition is stored as a snapshot; daily totals are derived. A compound index supports date-filtered meal queries.

## Tests

The automated API tests use an in-memory MongoDB fake, so they do not need Atlas credentials or a running database:

```bash
cd backend
./venv/bin/python -m pytest -q
```

For a live Atlas check, start the backend and call `/api/db-health` as shown above. Test suite health checks use a fake client; they do not verify the credentials or network access in your local `.env`.
