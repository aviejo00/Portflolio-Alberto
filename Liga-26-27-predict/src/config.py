from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = ROOT_DIR / "models"
OUTPUTS_DIR = ROOT_DIR / "outputs"

RANDOM_STATE = 42
PREDICTION_SEASON = "2026-27"

# League-only allocation used for the bounded prediction.
# Cup winners and UEFA European Performance Spots are not assumed.
CHAMPION_POSITION = 1
CHAMPIONS_POSITIONS = {2, 3, 4}
EUROPA_LEAGUE_POSITIONS = {5, 6}
CONFERENCE_POSITION = 7
RELEGATION_POSITIONS = {18, 19, 20}

FEATURE_COLUMNS = [
    "prev_tier",
    "prev_position_scaled",
    "prev_points_scaled",
    "promoted",
    "direct_promotion",
    "playoff_winner",
    "last3_points_avg",
    "last3_position_avg",
    "last5_top_tier_seasons",
    "best_recent_position",
    "europe_level",
    "coach_continuity",
    "market_value_log",
    "top_player_value_log",
    "squad_avg_age",
    "squad_size",
    "international_players",
    "transfer_momentum",
    "key_player_value_log",
    "key_player_goal_sum",
    "key_player_importance_avg",
    "long_term_power",
    "financial_power",
    "fanbase_score",
    "european_pedigree",
    "academy_score",
]
