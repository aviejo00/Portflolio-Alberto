from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from data import get_user_garments, login_user, register_user, save_user_garments
from models import AuthRequest, OutfitRequest, SaveGarmentsRequest, UserSession
from engine import generate_outfits, select_best

app = FastAPI()
STATIC_DIR = Path(__file__).parent / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


def serialize_garment(garment):
    if hasattr(garment, "model_dump"):
        return garment.model_dump()
    return garment.dict()


@app.post("/register")
def register(request: AuthRequest):
    try:
        return register_user(request.username, request.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/login")
def login(request: AuthRequest):
    try:
        return login_user(request.username, request.password)
    except PermissionError as error:
        raise HTTPException(status_code=401, detail=str(error))


@app.post("/garments/load")
def load_garments(request: UserSession):
    try:
        return {"garments": get_user_garments(request.username, request.token)}
    except PermissionError as error:
        raise HTTPException(status_code=401, detail=str(error))


@app.post("/garments/save")
def save_garments(request: SaveGarmentsRequest):
    garments = [serialize_garment(garment) for garment in request.garments]

    try:
        saved = save_user_garments(request.username, request.token, garments)
    except PermissionError as error:
        raise HTTPException(status_code=401, detail=str(error))

    return {"saved": saved}


@app.post("/recommend-outfit")
def recommend_outfit(request: OutfitRequest):

    outfits = generate_outfits(request.garments, request.compatibility)

    if not outfits:
        return {"error": "No valid outfits found"}

    best, score, details = select_best(outfits, request.weather, include_details=True)

    if not best:
        return {
            "error": "No outfit available without repeating clothes on the same weekday in the next 30 days",
            **details,
        }

    return {
        "score": score,
        "outfit": [g.id for g in best],
        **details,
    }
