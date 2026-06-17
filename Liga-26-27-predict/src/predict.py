import joblib
import pandas as pd

from config import MODELS_DIR, OUTPUTS_DIR, PREDICTION_SEASON, PROCESSED_DIR
from data_loader import (
    load_history,
    load_key_players,
    load_prediction_context,
    load_profiles,
    load_promotions,
)
from features import build_prediction_dataset, build_training_dataset
from model import cross_validate_by_season, fit_model, monte_carlo_probabilities, predict_table


def _load_or_train_model():
    model_path = MODELS_DIR / "laliga_points_model.joblib"
    if model_path.exists():
        bundle = joblib.load(model_path)
        return bundle["model"], bundle.get("report", {})

    history = load_history()
    promotions = load_promotions()
    profiles = load_profiles()
    training = build_training_dataset(history, promotions, profiles)
    report = cross_validate_by_season(training)
    model = fit_model(training)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "report": report.__dict__}, model_path)
    return model, report.__dict__


def _write_summary(table: pd.DataFrame, report: dict) -> None:
    champion = table.loc[table["bucket"] == "campeon", "team"].tolist()
    champions = table.loc[table["bucket"] == "champions", "team"].tolist()
    europa = table.loc[table["bucket"] == "europa_league", "team"].tolist()
    conference = table.loc[table["bucket"] == "conference", "team"].tolist()
    descenso = table.loc[table["bucket"] == "descenso", "team"].tolist()

    lines = [
        "# Prediccion LaLiga 2026-27",
        "",
        "Asignacion de plazas: liga regular pura, sin Copa del Rey ni European Performance Spot.",
        "",
        f"- Campeon: {', '.join(champion)}",
        f"- Champions: {', '.join(champions)}",
        f"- Europa League: {', '.join(europa)}",
        f"- Conference: {', '.join(conference)}",
        f"- Descenso: {', '.join(descenso)}",
        "",
        "Metricas de validacion historica:",
        f"- MAE puntos: {report.get('cv_mae_points', 'n/a')}",
        f"- MAE ranking: {report.get('cv_rank_mae', 'n/a')}",
    ]
    (OUTPUTS_DIR / "summary_2026_27.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    history = load_history()
    promotions = load_promotions()
    profiles = load_profiles()
    context = load_prediction_context()
    key_players = load_key_players()

    prediction_features = build_prediction_dataset(
        context=context,
        key_players=key_players,
        history=history,
        promotions=promotions,
        profiles=profiles,
        season=PREDICTION_SEASON,
    )
    prediction_features.to_csv(PROCESSED_DIR / "prediction_features_2026_27.csv", index=False)

    model, report = _load_or_train_model()
    table = predict_table(model, prediction_features)
    cv_mae = float(report.get("cv_mae_points", 6.0))
    probabilities = monte_carlo_probabilities(table, cv_mae_points=cv_mae)

    output = table.merge(probabilities, on="team", how="left")
    output.to_csv(OUTPUTS_DIR / "prediction_2026_27.csv", index=False)
    _write_summary(output, report)
    print(output.to_string(index=False))


if __name__ == "__main__":
    main()
