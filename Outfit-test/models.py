from pydantic import BaseModel
from datetime import date as Date
from typing import List, Dict, Optional

class Garment(BaseModel):
    id: str
    type: str  # "top", "bottom", "shoes", "outerwear"
    warmth: float  # 0-1
    waterproof: bool

class Weather(BaseModel):
    min_temp: float
    max_temp: float
    rain: bool
    day: Optional[str] = None  # "lunes", "sunday", etc.
    date: Optional[Date] = None

class OutfitRequest(BaseModel):
    garments: List[Garment]
    compatibility: Dict[str, List[str]]
    weather: Weather


class AuthRequest(BaseModel):
    username: str
    password: str


class UserSession(BaseModel):
    username: str
    token: str


class SaveGarmentsRequest(UserSession):
    garments: List[Garment]
