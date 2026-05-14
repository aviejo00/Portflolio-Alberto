import json
import os
import unicodedata
from datetime import date, timedelta

HISTORY_FILE = "history.json"
HISTORY_WINDOW_DAYS = 30

WEEKDAYS = [
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
]

DAY_ALIASES = {
    "lunes": "lunes",
    "monday": "lunes",
    "mon": "lunes",
    "martes": "martes",
    "tuesday": "martes",
    "tue": "martes",
    "miercoles": "miercoles",
    "wednesday": "miercoles",
    "wed": "miercoles",
    "jueves": "jueves",
    "thursday": "jueves",
    "thu": "jueves",
    "viernes": "viernes",
    "friday": "viernes",
    "fri": "viernes",
    "sabado": "sabado",
    "saturday": "sabado",
    "sat": "sabado",
    "domingo": "domingo",
    "sunday": "domingo",
    "sun": "domingo",
}


# -----------------------
# HISTORIAL
# -----------------------

def normalize_day(day):
    if not day:
        return None

    normalized = unicodedata.normalize("NFKD", str(day).strip().lower())
    ascii_day = "".join(c for c in normalized if not unicodedata.combining(c))
    return DAY_ALIASES.get(ascii_day, ascii_day)


def weekday_from_date(target_date):
    return WEEKDAYS[target_date.weekday()]


def next_date_for_day(target_day, today=None):
    today = today or date.today()
    normalized_day = normalize_day(target_day)
    if normalized_day not in WEEKDAYS:
        return today

    days_ahead = (WEEKDAYS.index(normalized_day) - today.weekday()) % 7
    return today + timedelta(days=days_ahead)


def resolve_weather_date_and_day(weather):
    if weather.date:
        target_date = weather.date
        return target_date, weekday_from_date(target_date)

    normalized_day = normalize_day(weather.day)
    target_date = next_date_for_day(normalized_day) if normalized_day else date.today()
    return target_date, normalized_day or weekday_from_date(target_date)


def normalize_history(raw_history):
    entries = []

    if isinstance(raw_history, dict):
        for item in raw_history.get("entries", []):
            if not isinstance(item, dict):
                continue

            outfit = item.get("outfit", [])
            if not isinstance(outfit, list):
                continue

            entries.append({
                "date": item.get("date"),
                "day": normalize_day(item.get("day")),
                "outfit": [str(g) for g in outfit],
            })

        # Legacy shape: {"lunes": [["camisa", "vaqueros"]]}
        for day_name, day_outfits in raw_history.items():
            if day_name == "entries" or not isinstance(day_outfits, list):
                continue

            for outfit in day_outfits:
                if isinstance(outfit, list):
                    entries.append({
                        "date": None,
                        "day": normalize_day(day_name),
                        "outfit": [str(g) for g in outfit],
                    })

    return {"entries": entries}


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {"entries": []}
    with open(HISTORY_FILE, "r") as f:
        return normalize_history(json.load(f))


def save_history(history):
    normalized = normalize_history(history)
    with open(HISTORY_FILE, "w") as f:
        json.dump(normalized, f, indent=2)


def parse_history_date(raw_date):
    if not raw_date:
        return None

    try:
        return date.fromisoformat(raw_date)
    except ValueError:
        return None


def blocked_garment_ids(history, target_day, target_date):
    blocked = set()

    for entry in history.get("entries", []):
        if entry.get("day") != target_day:
            continue

        entry_date = parse_history_date(entry.get("date"))
        if not entry_date:
            continue

        days_since = (target_date - entry_date).days
        if 0 < days_since <= HISTORY_WINDOW_DAYS:
            blocked.update(entry.get("outfit", []))

    return blocked


def recent_outfits_for_day(history, target_day, target_date, limit=4):
    dated = []
    legacy = []

    for entry in history.get("entries", []):
        if entry.get("day") != target_day:
            continue

        outfit = entry.get("outfit", [])
        entry_date = parse_history_date(entry.get("date"))
        if entry_date:
            if entry_date <= target_date:
                dated.append((entry_date, outfit))
        else:
            legacy.append(outfit)

    dated.sort(key=lambda item: item[0])
    return legacy[-limit:] + [outfit for _, outfit in dated[-limit:]]


def add_history_entry(history, target_day, target_date, outfit):
    normalized = normalize_history(history)
    normalized["entries"].append({
        "date": target_date.isoformat(),
        "day": target_day,
        "outfit": [g.id for g in outfit],
    })
    return normalized


# -----------------------
# COMPATIBILIDAD
# -----------------------

def compatible(g1, g2, graph):
    return g2.id in graph.get(g1.id, [])


# -----------------------
# GENERACION (SIN FUERZA BRUTA)
# -----------------------

def generate_outfits(garments, graph):
    tops = [g for g in garments if g.type == "top"]
    bottoms = [g for g in garments if g.type == "bottom"]
    shoes = [g for g in garments if g.type == "shoes"]
    outerwears = [g for g in garments if g.type == "outerwear"]

    outfits = []

    for top in tops:
        for bottom in bottoms:
            if not compatible(top, bottom, graph):
                continue

            for shoe in shoes:
                if not (compatible(top, shoe, graph) and compatible(bottom, shoe, graph)):
                    continue

                for outer in outerwears + [None]:
                    if outer:
                        if not (compatible(top, outer, graph) and compatible(bottom, outer, graph)):
                            continue

                    outfit = [top, bottom, shoe]
                    if outer:
                        outfit.append(outer)

                    outfits.append(outfit)

    return outfits


# -----------------------
# SCORING
# -----------------------

def temp_score(outfit, weather):
    avg_temp = (weather.min_temp + weather.max_temp) / 2
    total_warmth = sum(g.warmth for g in outfit)

    target = avg_temp / 40
    return 1 - abs(total_warmth - target)


def rain_score(outfit, weather):
    if weather.rain:
        return 1 if any(g.waterproof for g in outfit) else 0
    return 1


def repetition_penalty(outfit, history_day):
    if not history_day:
        return 0

    outfit_ids = set(g.id for g in outfit)

    def similarity(o1, o2):
        return len(set(o1) & set(o2)) / len(set(o1) | set(o2))

    return max(similarity(outfit_ids, set(h)) for h in history_day)


def score_outfit(outfit, weather, history_day):
    t = temp_score(outfit, weather)
    r = rain_score(outfit, weather)
    rep = repetition_penalty(outfit, history_day)

    return 0.6 * t + 0.4 * r - 0.5 * rep


# -----------------------
# SELECCION FINAL
# -----------------------

def select_best(outfits, weather, include_details=False):
    history = load_history()
    target_date, target_day = resolve_weather_date_and_day(weather)
    blocked_ids = blocked_garment_ids(history, target_day, target_date)
    available_outfits = [
        outfit
        for outfit in outfits
        if not any(g.id in blocked_ids for g in outfit)
    ]
    history_day = recent_outfits_for_day(history, target_day, target_date)[-4:]

    best = None
    best_score = -999

    for outfit in available_outfits:
        score = score_outfit(outfit, weather, history_day)
        if score > best_score:
            best_score = score
            best = outfit

    if best:
        history = add_history_entry(history, target_day, target_date, best)
        save_history(history)

    details = {
        "date": target_date.isoformat(),
        "day": target_day,
        "blocked_garments": sorted(blocked_ids),
        "available_outfits": len(available_outfits),
        "total_outfits": len(outfits),
    }

    if include_details:
        return best, best_score, details

    return best, best_score
