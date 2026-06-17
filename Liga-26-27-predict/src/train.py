import joblib

from config import MODELS_DIR, PROCESSED_DIR
from data_loader import load_history, load_profiles, load_promotions
from features import build_training_dataset
from model import cross_validate_by_season, fit_model


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    history = load_history()
    promotions = load_promotions()
    profiles = load_profiles()
    training = build_training_dataset(history, promotions, profiles)
    training.to_csv(PROCESSED_DIR / "training_features.csv", index=False)

    report = cross_validate_by_season(training)
    model = fit_model(training)
    joblib.dump(
        {
            "model": model,
            "report": report.__dict__,
        },
        MODELS_DIR / "laliga_points_model.joblib",
    )
    print(
        "trained model | "
        f"rows={report.train_rows} | "
        f"seasons={report.seasons_tested} | "
        f"cv_mae_points={report.cv_mae_points:.2f} | "
        f"cv_rank_mae={report.cv_rank_mae:.2f}"
    )


if __name__ == "__main__":
    main()
