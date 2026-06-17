import pandas as pd

from config import RAW_DIR


def load_history() -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / "laliga_team_seasons.csv")


def load_promotions() -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / "segunda_promoted_seasons.csv")


def load_profiles() -> pd.DataFrame:
    profiles = pd.read_csv(RAW_DIR / "club_profiles.csv")
    return profiles.drop_duplicates(subset=["team"], keep="first")


def load_prediction_context() -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / "team_context_2026_27.csv")


def load_key_players() -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / "key_players_2026_27.csv")
