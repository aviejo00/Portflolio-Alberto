from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, VotingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from config import (
    CHAMPION_POSITION,
    CHAMPIONS_POSITIONS,
    CONFERENCE_POSITION,
    EUROPA_LEAGUE_POSITIONS,
    FEATURE_COLUMNS,
    RANDOM_STATE,
    RELEGATION_POSITIONS,
)
from features import validate_feature_columns


@dataclass
class ModelReport:
    cv_mae_points: float
    cv_rank_mae: float
    train_rows: int
    seasons_tested: int


def create_model() -> Pipeline:
    ridge = make_pipeline(StandardScaler(), RidgeCV(alphas=(0.1, 1.0, 3.0, 10.0, 30.0)))
    forest = RandomForestRegressor(
        n_estimators=600,
        max_depth=7,
        min_samples_leaf=3,
        random_state=RANDOM_STATE,
    )
    boosting = GradientBoostingRegressor(
        n_estimators=220,
        learning_rate=0.035,
        max_depth=3,
        random_state=RANDOM_STATE,
    )
    ensemble = VotingRegressor(
        estimators=[
            ("ridge", ridge),
            ("forest", forest),
            ("boosting", boosting),
        ],
        weights=[0.25, 0.45, 0.30],
    )
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("model", ensemble),
        ]
    )


def _rank_from_points(frame: pd.DataFrame, points_column: str) -> pd.Series:
    ranked = frame[["team", points_column]].copy()
    ranked["rank"] = ranked[points_column].rank(method="first", ascending=False).astype(int)
    return ranked.set_index("team")["rank"]


def cross_validate_by_season(training: pd.DataFrame) -> ModelReport:
    validate_feature_columns(training)
    seasons = sorted(training["season"].unique())
    point_errors: list[float] = []
    rank_errors: list[float] = []

    for season in seasons:
        train = training[training["season"] != season]
        test = training[training["season"] == season].copy()
        if train.empty or test.empty:
            continue

        model = create_model()
        model.fit(train[FEATURE_COLUMNS], train["target_points"])
        test["predicted_points"] = model.predict(test[FEATURE_COLUMNS])
        point_errors.append(mean_absolute_error(test["target_points"], test["predicted_points"]))

        actual_rank = _rank_from_points(test.rename(columns={"target_points": "actual_points"}), "actual_points")
        pred_rank = _rank_from_points(test, "predicted_points")
        rank_errors.append(float((actual_rank - pred_rank).abs().mean()))

    return ModelReport(
        cv_mae_points=float(np.mean(point_errors)),
        cv_rank_mae=float(np.mean(rank_errors)),
        train_rows=int(len(training)),
        seasons_tested=len(point_errors),
    )


def fit_model(training: pd.DataFrame) -> Pipeline:
    validate_feature_columns(training)
    model = create_model()
    model.fit(training[FEATURE_COLUMNS], training["target_points"])
    return model


def _label_from_position(position: int) -> str:
    if position == CHAMPION_POSITION:
        return "campeon"
    if position in CHAMPIONS_POSITIONS:
        return "champions"
    if position in EUROPA_LEAGUE_POSITIONS:
        return "europa_league"
    if position == CONFERENCE_POSITION:
        return "conference"
    if position in RELEGATION_POSITIONS:
        return "descenso"
    return "media_tabla"


def predict_table(model: Pipeline, prediction_features: pd.DataFrame) -> pd.DataFrame:
    validate_feature_columns(prediction_features)
    table = prediction_features[["team"]].copy()
    table["predicted_points"] = model.predict(prediction_features[FEATURE_COLUMNS])
    table["predicted_points"] = table["predicted_points"].clip(18, 96).round(1)
    table = table.sort_values(["predicted_points", "team"], ascending=[False, True]).reset_index(drop=True)
    table["predicted_position"] = np.arange(1, len(table) + 1)
    table["bucket"] = table["predicted_position"].apply(_label_from_position)
    return table


def monte_carlo_probabilities(
    table: pd.DataFrame,
    cv_mae_points: float,
    simulations: int = 20000,
    seed: int = RANDOM_STATE,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    teams = table["team"].to_numpy()
    base_points = table["predicted_points"].to_numpy(dtype=float)
    sigma = max(4.8, float(cv_mae_points))

    counts = {
        "prob_campeon": np.zeros(len(teams), dtype=float),
        "prob_champions": np.zeros(len(teams), dtype=float),
        "prob_europa_league": np.zeros(len(teams), dtype=float),
        "prob_conference": np.zeros(len(teams), dtype=float),
        "prob_descenso": np.zeros(len(teams), dtype=float),
    }

    for _ in range(simulations):
        sampled = base_points + rng.normal(0.0, sigma, len(teams))
        order = np.argsort(-sampled, kind="mergesort")
        positions = np.empty(len(teams), dtype=int)
        positions[order] = np.arange(1, len(teams) + 1)

        counts["prob_campeon"] += positions == CHAMPION_POSITION
        counts["prob_champions"] += np.isin(positions, list(CHAMPIONS_POSITIONS))
        counts["prob_europa_league"] += np.isin(positions, list(EUROPA_LEAGUE_POSITIONS))
        counts["prob_conference"] += positions == CONFERENCE_POSITION
        counts["prob_descenso"] += np.isin(positions, list(RELEGATION_POSITIONS))

    probs = pd.DataFrame({"team": teams})
    for column, values in counts.items():
        probs[column] = (values / simulations).round(4)
    return probs
