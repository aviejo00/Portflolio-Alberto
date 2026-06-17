import math
from typing import Iterable

import pandas as pd

from config import FEATURE_COLUMNS


SEASON_ORDER = [
    "2016-17",
    "2017-18",
    "2018-19",
    "2019-20",
    "2020-21",
    "2021-22",
    "2022-23",
    "2023-24",
    "2024-25",
    "2025-26",
    "2026-27",
]


def previous_season(season: str) -> str:
    idx = SEASON_ORDER.index(season)
    return SEASON_ORDER[idx - 1]


def seasons_before(season: str) -> list[str]:
    return SEASON_ORDER[: SEASON_ORDER.index(season)]


def europe_level_from_previous_position(position: float) -> int:
    if pd.isna(position):
        return 0
    if position <= 4:
        return 3
    if position <= 6:
        return 2
    if position == 7:
        return 1
    return 0


def _scaled_points(points: float, tier: int) -> float:
    if pd.isna(points):
        return 0.0
    divisor = 114.0 if tier == 1 else 126.0
    return float(points) / divisor


def _scaled_position(position: float, tier: int) -> float:
    if pd.isna(position):
        return 1.0
    max_position = 20.0 if tier == 1 else 22.0
    return float(position) / max_position


def _safe_log(value: float) -> float:
    if pd.isna(value) or value <= 0:
        return 0.0
    return math.log1p(float(value))


def _recent_features(history: pd.DataFrame, team: str, season: str) -> dict[str, float]:
    prior = history[
        (history["team"] == team) & (history["season"].isin(seasons_before(season)))
    ].copy()
    if prior.empty:
        return {
            "last3_points_avg": 0.0,
            "last3_position_avg": 20.0,
            "last5_top_tier_seasons": 0.0,
            "best_recent_position": 20.0,
        }

    prior["season_index"] = prior["season"].map(SEASON_ORDER.index)
    prior = prior.sort_values("season_index")
    last3 = prior.tail(3)
    last5 = prior.tail(5)
    return {
        "last3_points_avg": float(last3["points"].mean()),
        "last3_position_avg": float(last3["final_position"].mean()),
        "last5_top_tier_seasons": float(len(last5)),
        "best_recent_position": float(last5["final_position"].min()),
    }


def _profile_features(profiles: pd.DataFrame, team: str) -> dict[str, float]:
    row = profiles.loc[profiles["team"] == team]
    if row.empty:
        return {
            "long_term_power": 40.0,
            "financial_power": 35.0,
            "fanbase_score": 40.0,
            "european_pedigree": 15.0,
            "academy_score": 45.0,
        }
    record = row.iloc[0]
    return {
        "long_term_power": float(record["long_term_power"]),
        "financial_power": float(record["financial_power"]),
        "fanbase_score": float(record["fanbase_score"]),
        "european_pedigree": float(record["european_pedigree"]),
        "academy_score": float(record["academy_score"]),
    }


def _key_player_aggregates(key_players: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        key_players.groupby("team")
        .agg(
            key_player_value=("market_value_m_eur", "sum"),
            key_player_goal_sum=("prev_season_goals", "sum"),
            key_player_importance_avg=("importance_score", "mean"),
        )
        .reset_index()
    )
    grouped["key_player_value_log"] = grouped["key_player_value"].apply(_safe_log)
    return grouped.drop(columns=["key_player_value"])


def build_training_dataset(
    history: pd.DataFrame, promotions: pd.DataFrame, profiles: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    training_seasons = SEASON_ORDER[1:-1]

    for season in training_seasons:
        previous = previous_season(season)
        season_rows = history[history["season"] == season]
        prev_rows = history[history["season"] == previous].set_index("team")

        for _, current in season_rows.iterrows():
            team = current["team"]
            profile = _profile_features(profiles, team)
            promoted_row = promotions[
                (promotions["season"] == season) & (promotions["team"] == team)
            ]

            if team in prev_rows.index:
                prev = prev_rows.loc[team]
                prev_tier = 1
                prev_position = float(prev["final_position"])
                prev_points = float(prev["points"])
                promoted = 0
                direct_promotion = 0
                playoff_winner = 0
            elif not promoted_row.empty:
                promoted_data = promoted_row.iloc[0]
                prev_tier = 2
                prev_position = float(promoted_data["prev_segunda_position"])
                prev_points = float(promoted_data["prev_segunda_points"])
                promoted = 1
                direct_promotion = int(promoted_data["direct_promotion"])
                playoff_winner = int(promoted_data["playoff_winner"])
            else:
                # Rare historical teams outside our promoted table get a conservative
                # second-tier prior instead of being dropped.
                prev_tier = 2
                prev_position = 8.0
                prev_points = 62.0
                promoted = 1
                direct_promotion = 0
                playoff_winner = 0

            market_proxy = max(20.0, profile["financial_power"] * 7.5 + profile["long_term_power"] * 2.5)
            top_player_proxy = max(3.0, profile["financial_power"] * 1.35)
            international_proxy = max(1.0, profile["financial_power"] / 8.0)
            key_goal_proxy = max(8.0, 70.0 - prev_position * 2.2 + profile["long_term_power"] / 4.0)

            features = {
                "season": season,
                "team": team,
                "prev_tier": prev_tier,
                "prev_position_scaled": _scaled_position(prev_position, prev_tier),
                "prev_points_scaled": _scaled_points(prev_points, prev_tier),
                "promoted": promoted,
                "direct_promotion": direct_promotion,
                "playoff_winner": playoff_winner,
                "europe_level": europe_level_from_previous_position(prev_position)
                if prev_tier == 1
                else 0,
                "coach_continuity": 0.75,
                "market_value_log": _safe_log(market_proxy),
                "top_player_value_log": _safe_log(top_player_proxy),
                "squad_avg_age": 26.8,
                "squad_size": 25.0,
                "international_players": international_proxy,
                "transfer_momentum": 0.0,
                "key_player_value_log": _safe_log(top_player_proxy * 2.4),
                "key_player_goal_sum": key_goal_proxy,
                "key_player_importance_avg": 58.0 + profile["long_term_power"] * 0.35,
                "target_points": float(current["points"]),
                "target_position": int(current["final_position"]),
            }
            features.update(_recent_features(history, team, season))
            features.update(profile)
            rows.append(features)

    df = pd.DataFrame(rows)
    return df[["season", "team", *FEATURE_COLUMNS, "target_points", "target_position"]]


def build_prediction_dataset(
    context: pd.DataFrame,
    key_players: pd.DataFrame,
    history: pd.DataFrame,
    promotions: pd.DataFrame,
    profiles: pd.DataFrame,
    season: str,
) -> pd.DataFrame:
    key_agg = _key_player_aggregates(key_players)
    rows: list[dict[str, float | str]] = []

    for _, row in context.iterrows():
        team = row["team"]
        prev_tier = int(row["prev_tier"])
        prev_position = float(row["prev_position"])
        prev_points = float(row["prev_points"])
        promoted = int(row["promoted"])
        promotion = promotions[
            (promotions["season"] == season) & (promotions["team"] == team)
        ]

        direct_promotion = int(promotion["direct_promotion"].iloc[0]) if not promotion.empty else 0
        playoff_winner = int(promotion["playoff_winner"].iloc[0]) if not promotion.empty else 0
        key_row = key_agg[key_agg["team"] == team]

        features = {
            "season": season,
            "team": team,
            "prev_tier": prev_tier,
            "prev_position_scaled": _scaled_position(prev_position, prev_tier),
            "prev_points_scaled": _scaled_points(prev_points, prev_tier),
            "promoted": promoted,
            "direct_promotion": direct_promotion,
            "playoff_winner": playoff_winner,
            "europe_level": float(row["uefa_level"]),
            "coach_continuity": float(row["coach_continuity"]),
            "market_value_log": _safe_log(row["market_value_m_eur"]),
            "top_player_value_log": _safe_log(row["top_player_value_m_eur"]),
            "squad_avg_age": float(row["squad_avg_age"]),
            "squad_size": float(row["squad_size"]),
            "international_players": float(row["international_players"]),
            "transfer_momentum": float(row["transfer_momentum"]),
        }
        if key_row.empty:
            features.update(
                {
                    "key_player_value_log": 0.0,
                    "key_player_goal_sum": 0.0,
                    "key_player_importance_avg": 75.0,
                }
            )
        else:
            features.update(
                {
                    "key_player_value_log": float(key_row["key_player_value_log"].iloc[0]),
                    "key_player_goal_sum": float(key_row["key_player_goal_sum"].iloc[0]),
                    "key_player_importance_avg": float(
                        key_row["key_player_importance_avg"].iloc[0]
                    ),
                }
            )
        features.update(_recent_features(history, team, season))
        features.update(_profile_features(profiles, team))
        rows.append(features)

    df = pd.DataFrame(rows)
    return df[["season", "team", *FEATURE_COLUMNS]]


def validate_feature_columns(frame: pd.DataFrame, required: Iterable[str] = FEATURE_COLUMNS) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
