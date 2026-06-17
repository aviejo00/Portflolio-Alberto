# LaLiga 2026-27 Prediction Model

I built this project to predict the next Spanish LaLiga season in a bounded way. Instead of trying to forecast every match, the model estimates the final league table and then maps the result into the most important outcomes:

- league winner
- Champions League places
- Europa League places
- Conference League place
- relegated teams

For the unresolved final promotion spot, I use Almeria as the assumed promoted team.

## Current Prediction

The initial prediction is available in `outputs/prediction_2026_27.csv`.

- Winner: Barcelona
- Champions League: Real Madrid, Atletico Madrid, Villarreal
- Europa League: Real Betis, Real Sociedad
- Conference League: Athletic Bilbao
- Relegation: Levante, Deportivo La Coruna, Racing Santander

This allocation only uses league position. I do not assume Copa del Rey effects or extra European Performance Spot changes.

## Project Structure

- `data/raw/laliga_team_seasons.csv`: historical LaLiga positions and points from 2016-17 to 2025-26.
- `data/raw/segunda_promoted_seasons.csv`: recent promoted teams and their Segunda Division performance.
- `data/raw/team_context_2026_27.csv`: current context for the 20 teams in the 2026-27 prediction.
- `data/raw/key_players_2026_27.csv`: key player signals used by the model.
- `data/raw/club_profiles.csv`: long-term club strength, financial strength, fanbase, European pedigree and academy score.
- `src/features.py`: feature engineering for training and prediction.
- `src/model.py`: model definition, validation, ranking and Monte Carlo probabilities.
- `src/train.py`: trains the model and saves it to `models/`.
- `src/predict.py`: generates the 2026-27 prediction.
- `src/run_all.py`: runs training and prediction in one command.

## How I Run It

From the project root:

```powershell
python -m pip install -r requirements.txt
python src\run_all.py
```

If I only want to train the model:

```powershell
python src\train.py
```

If I only want to regenerate the prediction using an existing trained model:

```powershell
python src\predict.py
```

## Generated Files

Running `src\run_all.py` creates or updates:

- `data/processed/training_features.csv`
- `data/processed/prediction_features_2026_27.csv`
- `models/laliga_points_model.joblib`
- `outputs/prediction_2026_27.csv`
- `outputs/summary_2026_27.md`

## How The Model Works

The model predicts final points for each team. After predicting points, it sorts the teams into a league table and assigns each team to a final outcome bucket.

The main feature groups are:

- previous season position and points
- whether the team was promoted from Segunda
- direct promotion or playoff promotion
- recent LaLiga performance over the last few seasons
- number of recent top-flight seasons
- European competition load
- manager continuity
- squad market value estimate
- top player value estimate
- squad age and size
- number of international players
- key player goals, market value and importance
- long-term club strength
- financial strength
- fanbase size
- European pedigree
- academy strength

The model itself is an ensemble made of:

- Ridge regression
- Random Forest regression
- Gradient Boosting regression

I validate it season by season using historical data, then I use a Monte Carlo simulation around the predicted points to estimate the probability of each outcome.

## Assumptions

This is a modelling project, not a betting tool. Football is noisy, and a lot can change before and during the season.

Important assumptions:

- Almeria is treated as the final promoted team.
- The European places are assigned using league position only.
- Squad values are rounded modelling inputs and should be updated after the transfer window.
- Injuries, tactical changes, late transfers and fixture congestion are only indirectly represented.

## Data Sources

- LaLiga 2025-26: https://en.wikipedia.org/wiki/2025%E2%80%9326_La_Liga
- LaLiga 2024-25: https://en.wikipedia.org/wiki/2024%E2%80%9325_La_Liga
- Segunda Division 2025-26: https://en.wikipedia.org/wiki/2025%E2%80%9326_Segunda_Divisi%C3%B3n
- Promotion playoff context: https://as.com/futbol/segunda/asi-queda-el-playoff-de-laliga-hypermotion-fechas-horarios-cruces-y-cuadro-para-ascender-a-laliga-ea-sports-f202605-n/
- Squad value context: https://as.com/futbol/la-plantilla-del-athletic-pierde-valor-f202606-n/
- Segunda Division player value context: https://cadenaser.com/andalucia/2026/03/28/arribas-es-la-estrella-en-el-xi-mas-cotizado-de-la-historia-con-85-millones-ser-almeria/
