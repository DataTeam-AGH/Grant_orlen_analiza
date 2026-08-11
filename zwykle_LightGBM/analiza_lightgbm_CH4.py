"""
Model LightGBM - przewidywanie CH4 na zbiorczym pliku (wiele miast)
Walidacja czasowa (TimeSeriesSplit), strojenie hiperparametrów, ważność cech, SHAP
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
from sklearn.metrics import r2_score, mean_absolute_error
from lightgbm import LGBMRegressor
import shap

# ---------------------------------------------------------
# 1. Wczytanie danych
# ---------------------------------------------------------
plik = "wszystkie_miasta_CH4.csv"   # <- plik powstały ze skryptu łączącego
df = pd.read_csv(plik, parse_dates=["Data"]).sort_values("Data").reset_index(drop=True)

CH4 = "CH4_column_volume_mixing_ratio_dry_air"

zmienne_pogodowe = [
    "temperature_2m_mean", "temperature_2m_min", "temperature_2m_max",
    "dewpoint_temperature_2m_mean", "dewpoint_temperature_2m_min", "dewpoint_temperature_2m_max",
    "wilgotnosc_wzgledna_mean", "wilgotnosc_wzgledna_min", "wilgotnosc_wzgledna_max",
    "predkosc_wiatru_mean", "predkosc_wiatru_min", "predkosc_wiatru_max",
    "surface_pressure_mean", "surface_pressure_min", "surface_pressure_max",
    "total_precipitation_hourly_sum", "kierunek_wiatru_sredni",
]

df["sezon_kod"] = df["Sezon"].astype("category").cat.codes

# "miejsce" jako cecha kategoryczna - ważne przy kilku miastach w jednym pliku
df["miejsce_kod"] = df["miejsce"].astype("category").cat.codes if "miejsce" in df.columns else 0

cechy = zmienne_pogodowe + ["odleglosc_m", "sezon_kod", "miejsce_kod"]
X = df[cechy]
y = df[CH4]

# LightGBM potrafi natywnie obsłużyć cechy kategoryczne
cechy_kategoryczne = ["sezon_kod", "miejsce_kod"]

# ---------------------------------------------------------
# 2. Podział czasowy (train = starsze dane, test = najnowsze 20%)
#    (przy danych czasowych losowy split zawyżałby wynik - data leakage)
# ---------------------------------------------------------
n_test = int(len(df) * 0.2)
X_train, X_test = X.iloc[:-n_test], X.iloc[-n_test:]
y_train, y_test = y.iloc[:-n_test], y.iloc[-n_test:]

tscv = TimeSeriesSplit(n_splits=5)

# ---------------------------------------------------------
# 3. LightGBM - baseline (domyślne parametry)
# ---------------------------------------------------------
model_baseline = LGBMRegressor(random_state=42, verbose=-1)
model_baseline.fit(X_train, y_train, categorical_feature=cechy_kategoryczne)
pred_baseline = model_baseline.predict(X_test)

print("--- LightGBM (baseline) ---")
print(f"R^2: {r2_score(y_test, pred_baseline):.3f}")
print(f"MAE: {mean_absolute_error(y_test, pred_baseline):.3f} ppb\n")

# ---------------------------------------------------------
# 4. Strojenie hiperparametrów (RandomizedSearchCV + TimeSeriesSplit)
# ---------------------------------------------------------
siatka_parametrow = {
    "n_estimators": [200, 400, 600, 800, 1000],
    "num_leaves": [15, 31, 63, 127],
    "max_depth": [-1, 4, 6, 8, 10],
    "learning_rate": [0.01, 0.03, 0.05, 0.1],
    "subsample": [0.6, 0.8, 1.0],
    "colsample_bytree": [0.6, 0.8, 1.0],
    "reg_alpha": [0, 0.1, 1],
    "reg_lambda": [0, 1, 5],
    "min_child_samples": [10, 20, 30, 50],
}

lgbm_bazowy = LGBMRegressor(random_state=42, verbose=-1)

szukanie = RandomizedSearchCV(
    estimator=lgbm_bazowy,
    param_distributions=siatka_parametrow,
    n_iter=40,
    scoring="r2",
    cv=tscv,
    random_state=42,
    n_jobs=-1,
    verbose=1,
)
szukanie.fit(X_train, y_train, categorical_feature=cechy_kategoryczne)

print("--- LightGBM: najlepsze parametry ---")
print(szukanie.best_params_)

model_lgbm = szukanie.best_estimator_
pred_lgbm = model_lgbm.predict(X_test)

print("\n--- LightGBM (dostrojony) ---")
print(f"R^2: {r2_score(y_test, pred_lgbm):.3f}")
print(f"MAE: {mean_absolute_error(y_test, pred_lgbm):.3f} ppb")

# ---------------------------------------------------------
# 5. Wykres: rzeczywiste vs przewidziane (baseline vs dostrojony)
# ---------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
for ax, pred, nazwa in zip(axes, [pred_baseline, pred_lgbm],
                           ["LightGBM (baseline)", "LightGBM (dostrojony)"]):
    ax.scatter(y_test, pred, alpha=0.3, s=15)
    lims = [min(y_test.min(), pred.min()), max(y_test.max(), pred.max())]
    ax.plot(lims, lims, color="red", linestyle="--")
    ax.set_xlabel("CH4 rzeczywiste [ppb]")
    ax.set_ylabel("CH4 przewidziane [ppb]")
    ax.set_title(f"{nazwa}\nR²={r2_score(y_test, pred):.3f}")
plt.tight_layout()
plt.savefig("ch4_lightgbm_rzeczywiste_vs_predykcja.png", dpi=150)
plt.show()

# ---------------------------------------------------------
# 6. Walidacja krzyżowa czasowa - sprawdzenie stabilności modelu
# ---------------------------------------------------------
wyniki_cv = []
for i, (idx_train, idx_val) in enumerate(tscv.split(X_train)):
    m = LGBMRegressor(**szukanie.best_params_, random_state=42, verbose=-1)
    m.fit(X_train.iloc[idx_train], y_train.iloc[idx_train],
          categorical_feature=cechy_kategoryczne)
    p = m.predict(X_train.iloc[idx_val])
    wynik = r2_score(y_train.iloc[idx_val], p)
    wyniki_cv.append(wynik)
    print(f"Fold {i+1}: R² = {wynik:.3f}")

print(f"\nŚredni R² z walidacji czasowej: {np.mean(wyniki_cv):.3f} (+/- {np.std(wyniki_cv):.3f})")

# ---------------------------------------------------------
# 7. Ważność cech (natywna z LightGBM)
# ---------------------------------------------------------
waznosc = pd.Series(model_lgbm.feature_importances_, index=cechy).sort_values()

plt.figure(figsize=(8, 7))
plt.barh(waznosc.index, waznosc.values, color="seagreen")
plt.xlabel("Ważność cechy (LightGBM, split gain)")
plt.title("Ważność zmiennych w przewidywaniu CH4 (LightGBM)")
plt.tight_layout()
plt.savefig("ch4_lightgbm_waznosc_cech.png", dpi=150)
plt.show()

# ---------------------------------------------------------
# 8. Interpretacja SHAP
# ---------------------------------------------------------
explainer = shap.TreeExplainer(model_lgbm)
shap_values = explainer.shap_values(X_test)

plt.figure()
shap.summary_plot(shap_values, X_test, show=False)
plt.tight_layout()
plt.savefig("ch4_lightgbm_shap_summary.png", dpi=150, bbox_inches="tight")
plt.show()

plt.figure()
shap.summary_plot(shap_values, X_test, plot_type="bar", show=False)
plt.tight_layout()
plt.savefig("ch4_lightgbm_shap_waznosc.png", dpi=150, bbox_inches="tight")
plt.show()

print("\nGotowe. Zapisane pliki: ch4_lightgbm_rzeczywiste_vs_predykcja.png, "
      "ch4_lightgbm_waznosc_cech.png, ch4_lightgbm_shap_summary.png, "
      "ch4_lightgbm_shap_waznosc.png")
