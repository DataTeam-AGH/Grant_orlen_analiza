"""
FINALNY model CH4: trend + sezonowość + LightGBM (na resztach)
Trenowany na CAŁYM pliku (wszystkie miasta), z najlepszymi hiperparametrami
znalezionymi wcześniej w RandomizedSearchCV (bez ponownego strojenia).

Zapisuje wytrenowany model do plików .joblib, żeby można było go później
wczytać i użyć bez ponownego trenowania.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error
from lightgbm import LGBMRegressor

# ---------------------------------------------------------
# 1. Wczytanie danych (wszystkie miasta)
# ---------------------------------------------------------
plik = "wszystkie_miasta_CH4.csv"
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
df["miejsce_kod"] = df["miejsce"].astype("category").cat.codes if "miejsce" in df.columns else 0

# cecha czasowa + harmoniki sezonowe (roczna i półroczna)
df["dni_od_startu"] = (df["Data"] - df["Data"].min()).dt.days
dzien_roku = df["Data"].dt.dayofyear
df["sezon_sin_1"] = np.sin(2 * np.pi * dzien_roku / 365.25)
df["sezon_cos_1"] = np.cos(2 * np.pi * dzien_roku / 365.25)
df["sezon_sin_2"] = np.sin(4 * np.pi * dzien_roku / 365.25)
df["sezon_cos_2"] = np.cos(4 * np.pi * dzien_roku / 365.25)

CECHY_TRENDU = ["dni_od_startu", "sezon_sin_1", "sezon_cos_1", "sezon_sin_2", "sezon_cos_2"]
cechy = zmienne_pogodowe + ["odleglosc_m", "sezon_kod", "miejsce_kod"]
cechy_kategoryczne = ["sezon_kod", "miejsce_kod"]

# ---------------------------------------------------------
# 2. KROK 1: trend + sezonowość - dopasowanie na CAŁYM zbiorze
#    (model finalny, do produkcyjnego użytku - uczymy na wszystkich dostępnych danych)
# ---------------------------------------------------------
model_trend = LinearRegression()
model_trend.fit(df[CECHY_TRENDU], df[CH4])
df["trend"] = model_trend.predict(df[CECHY_TRENDU])
df["reszta"] = df[CH4] - df["trend"]

print("Współczynniki modelu trend+sezonowość:")
for nazwa, wsp in zip(CECHY_TRENDU, model_trend.coef_):
    print(f"  {nazwa}: {wsp:.5f}")
wzrost_roczny = model_trend.coef_[CECHY_TRENDU.index("dni_od_startu")] * 365
print(f"Wzrost roczny wg trendu: {wzrost_roczny:.2f} ppb/rok\n")

# ---------------------------------------------------------
# 3. KROK 2: LightGBM na resztach - NAJLEPSZE parametry (bez ponownego strojenia)
# ---------------------------------------------------------
NAJLEPSZE_PARAMETRY = {
    "subsample": 0.6,
    "reg_lambda": 0,
    "reg_alpha": 1,
    "num_leaves": 7,
    "n_estimators": 200,
    "min_child_samples": 30,
    "max_depth": -1,
    "learning_rate": 0.01,
    "colsample_bytree": 1.0,
}

model_lgbm = LGBMRegressor(**NAJLEPSZE_PARAMETRY, random_state=42, verbose=-1)
model_lgbm.fit(df[cechy], df["reszta"], categorical_feature=cechy_kategoryczne)

# ---------------------------------------------------------
# 4. Rekonstrukcja finalnej prognozy i ocena "in-sample"
#    (to NIE jest test na nowych danych - model widział te dane w treningu;
#     służy tylko do sprawdzenia jakości dopasowania, nie do oceny zdolności
#     prognostycznej - do tego użyj wcześniejszego skryptu z CV / podziałem czasowym)
# ---------------------------------------------------------
pred_reszta = model_lgbm.predict(df[cechy])
df["CH4_przewidziane"] = df["trend"] + pred_reszta

r2_insample = r2_score(df[CH4], df["CH4_przewidziane"])
mae_insample = mean_absolute_error(df[CH4], df["CH4_przewidziane"])
print(f"Dopasowanie in-sample (na danych treningowych): R² = {r2_insample:.3f}, MAE = {mae_insample:.2f} ppb")
print("(To NIE jest miara zdolności prognostycznej modelu - tylko jakość dopasowania do znanych danych)\n")

# ---------------------------------------------------------
# 5. Wykres: rzeczywiste vs przewidziane (in-sample) + szereg czasowy
# ---------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(13, 6))

axes[0].scatter(df[CH4], df["CH4_przewidziane"], alpha=0.15, s=10)
lims = [df[CH4].min(), df[CH4].max()]
axes[0].plot(lims, lims, color="red", linestyle="--")
axes[0].set_xlabel("CH4 rzeczywiste [ppb]")
axes[0].set_ylabel("CH4 przewidziane [ppb]")
axes[0].set_title(f"Model finalny (in-sample)\nR²={r2_insample:.3f}")

dzienne = df.groupby("Data")[[CH4, "CH4_przewidziane"]].mean().reset_index()
axes[1].plot(dzienne["Data"], dzienne[CH4], alpha=0.5, label="CH4 rzeczywiste")
axes[1].plot(dzienne["Data"], dzienne["CH4_przewidziane"], alpha=0.7, color="green", label="CH4 przewidziane")
axes[1].set_xlabel("Data")
axes[1].set_ylabel("CH4 [ppb]")
axes[1].set_title("Model finalny: szereg czasowy")
axes[1].legend()
axes[1].tick_params(axis="x", rotation=30)

plt.tight_layout()
plt.savefig("ch4_model_finalny_dopasowanie.png", dpi=150)
plt.show()

# ---------------------------------------------------------
# 6. Zapis wytrenowanego modelu (trend + LightGBM) do plików
# ---------------------------------------------------------
joblib.dump(model_trend, "model_trend_sezonowosc.joblib")
joblib.dump(model_lgbm, "model_lightgbm_reszty.joblib")
joblib.dump({"CECHY_TRENDU": CECHY_TRENDU, "cechy": cechy,
             "cechy_kategoryczne": cechy_kategoryczne}, "model_metadane.joblib")

print("Zapisano modele: model_trend_sezonowosc.joblib, model_lightgbm_reszty.joblib, "
      "model_metadane.joblib")
print("Zapisano wykres: ch4_model_finalny_dopasowanie.png")

# ---------------------------------------------------------
# 7. PRZYKŁAD: jak wczytać i użyć zapisanego modelu do nowej prognozy
# ---------------------------------------------------------
# model_trend = joblib.load("model_trend_sezonowosc.joblib")
# model_lgbm = joblib.load("model_lightgbm_reszty.joblib")
# metadane = joblib.load("model_metadane.joblib")
#
# nowe_dane["trend"] = model_trend.predict(nowe_dane[metadane["CECHY_TRENDU"]])
# nowe_dane["reszta_pred"] = model_lgbm.predict(nowe_dane[metadane["cechy"]])
# nowe_dane["CH4_przewidziane"] = nowe_dane["trend"] + nowe_dane["reszta_pred"]
