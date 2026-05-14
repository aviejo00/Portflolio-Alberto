import hashlib
import hmac
import json
import os
import re
import secrets

USERS_FILE = "users.json"
PBKDF2_ITERATIONS = 260_000
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,24}$")


def normalize_username(username):
    return username.strip().lower()


def validate_credentials(username, password):
    normalized = normalize_username(username)

    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("Username must be 3-24 characters using letters, numbers, _ or -.")

    if len(password) < 6:
        raise ValueError("Password must have at least 6 characters.")

    return normalized


def load_users():
    if not os.path.exists(USERS_FILE):
        return {"users": {}}

    with open(USERS_FILE, "r") as f:
        data = json.load(f)

    if not isinstance(data, dict) or not isinstance(data.get("users"), dict):
        return {"users": {}}

    return data


def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS,
    ).hex()


def create_token():
    return secrets.token_urlsafe(32)


def public_profile(username, user):
    return {
        "username": username,
        "token": user["token"],
        "garments": user.get("garments", []),
    }


def register_user(username, password):
    normalized = validate_credentials(username, password)
    data = load_users()

    if normalized in data["users"]:
        raise ValueError("This username is already registered.")

    salt = secrets.token_hex(16)
    user = {
        "salt": salt,
        "password_hash": hash_password(password, salt),
        "token": create_token(),
        "garments": [],
    }

    data["users"][normalized] = user
    save_users(data)
    return public_profile(normalized, user)


def login_user(username, password):
    normalized = normalize_username(username)
    data = load_users()
    user = data["users"].get(normalized)

    if not user:
        raise PermissionError("Invalid username or password.")

    expected_hash = user.get("password_hash", "")
    password_hash = hash_password(password, user.get("salt", ""))

    if not hmac.compare_digest(expected_hash, password_hash):
        raise PermissionError("Invalid username or password.")

    user["token"] = create_token()
    save_users(data)
    return public_profile(normalized, user)


def authenticate_user(username, token):
    normalized = normalize_username(username)
    data = load_users()
    user = data["users"].get(normalized)

    if not user or not hmac.compare_digest(user.get("token", ""), token):
        raise PermissionError("Invalid session.")

    return data, normalized, user


def get_user_garments(username, token):
    _, _, user = authenticate_user(username, token)
    return user.get("garments", [])


def save_user_garments(username, token, garments):
    data, normalized, user = authenticate_user(username, token)
    user["garments"] = garments
    data["users"][normalized] = user
    save_users(data)
    return len(garments)
