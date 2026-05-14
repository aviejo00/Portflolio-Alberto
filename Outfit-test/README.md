# Outfit Planner

Outfit Planner is a small local web app that recommends what to wear from a saved wardrobe. It combines garment metadata, weather conditions, compatibility rules, and recent outfit history so the same clothes are not repeated on the same weekday within a 30 day window.

The project is intentionally lightweight:

- Backend: FastAPI
- Validation: Pydantic models
- Frontend: plain HTML, CSS, and JavaScript
- Storage: local JSON files
- Runtime: Uvicorn

## What The App Does

The app lets a user:

- Register or log in with a username and password.
- Save a personal garment list.
- Add garments with type, warmth, and waterproof metadata.
- Enter a target date and weather conditions.
- Request an outfit recommendation.
- Receive the selected outfit, score, recommendation date, weekday, and blocked garments.

The recommendation engine builds valid outfits from:

- One `top`
- One `bottom`
- One `shoes`
- Optional `outerwear`

It then scores each candidate against the weather and recent outfit history.

## Core Rules

### Weather Matching

Each garment has a `warmth` value from `0` to `1`.

The engine calculates the average temperature:

```text
average_temperature = (min_temp + max_temp) / 2
```

Then it converts that temperature into a target warmth:

```text
target_warmth = average_temperature / 40
```

The closer the outfit total warmth is to the target warmth, the better the temperature score.

### Rain Matching

If rain is enabled for the requested date, the outfit receives a rain score of `1` only when at least one garment is waterproof.

If rain is not enabled, the rain score is always `1`.

### Repetition Avoidance

The app stores every successful recommendation in `history.json`.

When recommending for a specific weekday, it blocks garments that were used on that same weekday during the previous 30 days.

Example:

- A recommendation is made for Thursday, 2026-05-14.
- Those garments are blocked for future Thursday recommendations until the 30 day window has passed.
- They are not automatically blocked for other weekdays.

The engine also looks at recent outfits for the same weekday and applies a similarity penalty, so outfits that resemble recent ones score lower.

### Final Score

The final score is calculated in `engine.py`:

```text
score = 0.6 * temperature_score + 0.4 * rain_score - 0.5 * repetition_penalty
```

The highest scoring available outfit is returned.

## Architecture

The app is split into four main areas:

```text
.
+-- main.py              FastAPI app, HTTP routes, static file serving
+-- models.py            Pydantic request and data models
+-- engine.py            Outfit generation, history handling, scoring logic
+-- data.py              User registration, login, sessions, saved garments
+-- static/
|   +-- index.html       Frontend layout
|   +-- app.js           Browser-side workflow and API calls
|   +-- styles.css       Responsive UI styling
+-- history.json         Recommendation history
+-- users.json           User accounts and saved wardrobes
+-- requirements.txt     Python dependencies
+-- README.md            Project documentation
```

### Backend Layer

`main.py` creates the FastAPI application and exposes the HTTP routes.

It is responsible for:

- Mounting the `/static` directory.
- Serving `static/index.html` from `/`.
- Providing `/health`.
- Receiving recommendation requests.
- Calling the recommendation engine.
- Exposing profile and garment persistence endpoints.
- Converting validation or authentication failures into HTTP errors.

### Model Layer

`models.py` defines the Pydantic models used by the API:

```text
Garment
  id: string
  type: string
  warmth: float
  waterproof: boolean

Weather
  min_temp: float
  max_temp: float
  rain: boolean
  day: optional string
  date: optional date

OutfitRequest
  garments: list[Garment]
  compatibility: dict[str, list[str]]
  weather: Weather

AuthRequest
  username: string
  password: string

UserSession
  username: string
  token: string

SaveGarmentsRequest
  username: string
  token: string
  garments: list[Garment]
```

### Recommendation Layer

`engine.py` contains the domain logic:

- Normalizes weekday names in Spanish and English.
- Resolves a requested date or weekday.
- Loads and saves outfit history.
- Migrates legacy history shapes into the current `entries` shape.
- Builds candidate outfits from garments and compatibility rules.
- Blocks recently used garments for the target weekday.
- Scores candidates by temperature, rain, and repetition.
- Saves the winning outfit back into history.

### User Data Layer

`data.py` handles local account storage:

- Usernames are normalized to lowercase.
- Usernames must be 3 to 24 characters and may contain letters, numbers, `_`, or `-`.
- Passwords must be at least 6 characters.
- Passwords are hashed with PBKDF2-HMAC-SHA256.
- Each user has a random salt.
- Each login creates a new session token.
- Saved garments are stored per user in `users.json`.

This is useful for a local prototype, but it is not a production authentication system.

### Frontend Layer

The frontend lives in `static/`.

`index.html` defines the UI:

- Weather panel
- Profile form
- Recommendation result panel
- Garment table
- Reusable garment row template

`app.js` handles browser behavior:

- Reads and validates garment rows.
- Registers and logs in users.
- Stores the active session in `localStorage`.
- Loads saved garments after login.
- Saves garment lists to the backend.
- Builds a compatibility graph.
- Sends recommendation requests.
- Renders the result, blocked garments, or error messages.

`styles.css` provides the responsive layout and visual styling.

## Request Workflow

### Frontend Recommendation Flow

1. The user enters weather information.
2. The user creates garment rows.
3. The user clicks `Recommend outfit`.
4. `static/app.js` reads all garment rows.
5. The frontend checks that at least one top, bottom, and shoes exist.
6. The frontend builds a compatibility graph.
7. The frontend sends `POST /recommend-outfit`.
8. The backend validates the payload with Pydantic.
9. `engine.generate_outfits()` creates valid candidate outfits.
10. `engine.select_best()` filters, scores, and selects the best outfit.
11. The selected outfit is saved to `history.json`.
12. The frontend renders the recommendation.

### Profile Flow

1. The user enters a username and password.
2. Register sends `POST /register`.
3. Login sends `POST /login`.
4. The backend returns a username, session token, and saved garments.
5. The browser stores the session in `localStorage`.
6. Saving garments sends `POST /garments/save`.
7. Loading garments sends `POST /garments/load`.

## Compatibility Graph

The recommendation endpoint accepts a compatibility graph:

```json
{
  "white_shirt": ["jeans", "boots", "jacket"],
  "jeans": ["white_shirt", "boots", "jacket"],
  "boots": ["white_shirt", "jeans"],
  "jacket": ["white_shirt", "jeans"]
}
```

The backend checks compatibility between garment pairs while generating outfits.

The current frontend keeps this simple by making every garment compatible with every other garment. More advanced compatibility rules can be added later in `static/app.js` or sent directly to the API.

## Local Data Files

### `history.json`

Stores successful outfit recommendations:

```json
{
  "entries": [
    {
      "date": "2026-05-14",
      "day": "jueves",
      "outfit": ["black_tshirt", "chinos", "trainers"]
    }
  ]
}
```

Fields:

- `date`: ISO date used for the recommendation.
- `day`: normalized weekday.
- `outfit`: garment IDs selected by the engine.

### `users.json`

Stores local user records:

```json
{
  "users": {
    "alberto": {
      "salt": "random_hex_salt",
      "password_hash": "pbkdf2_hash",
      "token": "session_token",
      "garments": []
    }
  }
}
```

Fields:

- `salt`: random salt used for password hashing.
- `password_hash`: PBKDF2-HMAC-SHA256 password hash.
- `token`: active session token.
- `garments`: saved wardrobe for the user.

Do not commit real user data or real tokens if this project is shared.

## API Reference

Interactive API documentation is available while the server is running:

```text
http://127.0.0.1:8001/docs
```

### `GET /`

Serves the frontend application.

### `GET /health`

Returns a simple health check:

```json
{
  "status": "ok"
}
```

### `POST /register`

Creates a new user.

Request:

```json
{
  "username": "alberto",
  "password": "secret1"
}
```

Response:

```json
{
  "username": "alberto",
  "token": "session_token",
  "garments": []
}
```

Possible errors:

- `400` if the username is invalid.
- `400` if the password is too short.
- `400` if the username already exists.

### `POST /login`

Authenticates an existing user and rotates the session token.

Request:

```json
{
  "username": "alberto",
  "password": "secret1"
}
```

Response:

```json
{
  "username": "alberto",
  "token": "new_session_token",
  "garments": []
}
```

Possible errors:

- `401` if the username or password is invalid.

### `POST /garments/load`

Loads the saved wardrobe for a logged in user.

Request:

```json
{
  "username": "alberto",
  "token": "session_token"
}
```

Response:

```json
{
  "garments": [
    {
      "id": "white_shirt",
      "type": "top",
      "warmth": 0.2,
      "waterproof": false
    }
  ]
}
```

Possible errors:

- `401` if the session is invalid.

### `POST /garments/save`

Saves the wardrobe for a logged in user.

Request:

```json
{
  "username": "alberto",
  "token": "session_token",
  "garments": [
    {
      "id": "white_shirt",
      "type": "top",
      "warmth": 0.2,
      "waterproof": false
    }
  ]
}
```

Response:

```json
{
  "saved": 1
}
```

Possible errors:

- `401` if the session is invalid.

### `POST /recommend-outfit`

Returns the best available outfit for the requested weather and date.

Request:

```json
{
  "garments": [
    {
      "id": "white_shirt",
      "type": "top",
      "warmth": 0.2,
      "waterproof": false
    },
    {
      "id": "jeans",
      "type": "bottom",
      "warmth": 0.35,
      "waterproof": false
    },
    {
      "id": "boots",
      "type": "shoes",
      "warmth": 0.2,
      "waterproof": true
    },
    {
      "id": "jacket",
      "type": "outerwear",
      "warmth": 0.45,
      "waterproof": true
    }
  ],
  "compatibility": {
    "white_shirt": ["jeans", "boots", "jacket"],
    "jeans": ["white_shirt", "boots", "jacket"],
    "boots": ["white_shirt", "jeans", "jacket"],
    "jacket": ["white_shirt", "jeans", "boots"]
  },
  "weather": {
    "date": "2026-05-14",
    "min_temp": 12,
    "max_temp": 22,
    "rain": false
  }
}
```

Successful response:

```json
{
  "score": 0.73,
  "outfit": ["white_shirt", "jeans", "boots"],
  "date": "2026-05-14",
  "day": "jueves",
  "blocked_garments": [],
  "available_outfits": 2,
  "total_outfits": 2
}
```

No valid outfit combinations:

```json
{
  "error": "No valid outfits found"
}
```

No outfit available after weekday blocking:

```json
{
  "error": "No outfit available without repeating clothes on the same weekday in the next 30 days",
  "date": "2026-05-14",
  "day": "jueves",
  "blocked_garments": ["white_shirt", "jeans"],
  "available_outfits": 0,
  "total_outfits": 2
}
```

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

If the existing virtual environment is already available, dependencies can be installed directly with:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running The App

Start the server:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

Or use the existing virtual environment directly:

```powershell
.\.venv\Scripts\uvicorn.exe main:app --reload --host 127.0.0.1 --port 8001
```

Open the app:

```text
http://127.0.0.1:8001/
```

Useful local URLs:

```text
Frontend:     http://127.0.0.1:8001/
Health check: http://127.0.0.1:8001/health
API docs:     http://127.0.0.1:8001/docs
```

## How To Use The Frontend

1. Open `http://127.0.0.1:8001/`.
2. Register a profile or log in.
3. Add garments to the wardrobe table.
4. For each garment, choose:
   - ID or name
   - Type
   - Warmth
   - Waterproof status
5. Click `Save garments` to persist the wardrobe.
6. Choose the target date and weather.
7. Click `Recommend outfit`.
8. Review the selected outfit and any blocked garments.

## Development Notes

- The backend uses synchronous file reads and writes because the data is stored in small local JSON files.
- The history file is shared globally across users.
- User garment lists are stored per user.
- A login rotates the session token.
- The browser stores the current session in `localStorage`.
- The frontend currently generates an all-to-all compatibility graph.
- The API can accept stricter compatibility rules than the frontend currently exposes.
- `history.json` supports legacy weekday-based data and normalizes it into the current `entries` format.

## Limitations

This project is designed as a local prototype. Before using the same approach in production, consider:

- Replacing JSON files with a database.
- Adding server-side session expiry.
- Moving secrets and configuration to environment variables.
- Adding CSRF protection if cookie-based sessions are introduced.
- Separating history per user if recommendations should not share global outfit history.
- Adding automated tests for scoring, blocking, auth, and API behavior.
- Adding UI controls for compatibility rules.

## Troubleshooting

### The app does not start

Check that dependencies are installed:

```powershell
python -m pip install -r requirements.txt
```

Then run Uvicorn again:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

### Port 8001 is already in use

Use another port:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8002
```

Then open:

```text
http://127.0.0.1:8002/
```

### Login fails after editing `users.json`

The session token and password hash must match the expected structure. If the file is only test data, delete the affected user entry and register again from the UI.

### No outfit is recommended

Check that:

- At least one top, one bottom, and one shoes item exist.
- The compatibility graph allows the garments to combine.
- The target weekday does not have all usable garments blocked by the 30 day history rule.
- The garment IDs are unique.
