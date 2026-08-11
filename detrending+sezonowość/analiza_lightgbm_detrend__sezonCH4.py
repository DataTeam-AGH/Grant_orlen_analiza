"""
Model LightGBM z DETRENDINGIEM - przewidywanie CH4
Krok 1: usuwamy trend liniowy w czasie (regresja liniowa CH4 ~ czas)
Krok 2: LightGBM uczy się przewidywać RESZTY (odchylenia od trendu) na podstawie pogody/lokalizacji
Krok 3: finalna prognoza = trend + przewidziana reszta
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error
from lightgbm import LGBMRegressor
import shap

# ---------------------------------------------------------
# 1. Wczytanie danych
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

# cecha czasowa - liczba dni od pierwszego pomiaru (potrzebna do trendu)
df["dni_od_startu"] = (df["Data"] - df["Data"].min()).dt.days

# harmoniki roczne (sezonowość) - dzień roku przekształcony na sin/cos
# (jedna harmonika = cykl roczny; można dodać drugą dla bardziej "ostrego" sezonu)
dzien_roku = df["Data"].dt.dayofyear
df["sezon_sin_1"] = np.sin(2 * np.pi * dzien_roku / 365.25)
df["sezon_cos_1"] = np.cos(2 * np.pi * dzien_roku / 365.25)
df["sezon_sin_2"] = np.sin(4 * np.pi * dzien_roku / 365.25)   # 2. harmonika (półroczna)
df["sezon_cos_2"] = np.cos(4 * np.pi * dzien_roku / 365.25)

CECHY_TRENDU = ["dni_od_startu", "sezon_sin_1", "sezon_cos_1", "sezon_sin_2", "sezon_cos_2"]

cechy = zmienne_pogodowe + ["odleglosc_m", "sezon_kod", "miejsce_kod"]
cechy_kategoryczne = ["sezon_kod", "miejsce_kod"]

# ---------------------------------------------------------
# 2. Podział czasowy (train = starsze dane, test = najnowsze 20%)
# ---------------------------------------------------------
n_test = int(len(df) * 0.2)
train = df.iloc[:-n_test].copy()
test = df.iloc[-n_test:].copy()

# ---------------------------------------------------------
# 3. KROK 1: usunięcie trendu + sezonowości (dopasowanych TYLKO na treningu!)
#    CH4 = a*dni + b1*sin(rok) + b2*cos(rok) + b3*sin(2*rok) + b4*cos(2*rok) + c
# ---------------------------------------------------------
model_trend = LinearRegression()
model_trend.fit(train[CECHY_TRENDU], train[CH4])

train["trend"] = model_trend.predict(train[CECHY_TRENDU])
test["trend"] = model_trend.predict(test[CECHY_TRENDU])   # ekstrapolacja trendu w przód

train["reszta"] = train[CH4] - train["trend"]
test["reszta"] = test[CH4] - test["trend"]   # tylko do ewaluacji, model tego nie widzi

wspolczynnik_dni = model_trend.coef_[CECHY_TRENDU.index("dni_od_startu")]
print("Współczynniki modelu trend+sezonowość:")
for nazwa, wsp in zip(CECHY_TRENDU, model_trend.coef_):
    print(f"  {nazwa}: {wsp:.5f}")
print(f"Wzrost roczny wg trendu: {wspolczynnik_dni * 365:.2f} ppb/rok\n")

# amplituda sezonowości (na podstawie 1. harmoniki)
b1, b2 = model_trend.coef_[CECHY_TRENDU.index("sezon_sin_1")], model_trend.coef_[CECHY_TRENDU.index("sezon_cos_1")]
amplituda_sezonowa = np.sqrt(b1**2 + b2**2)
print(f"Amplituda sezonowości (1. harmonika): +/- {amplituda_sezonowa:.2f} ppb\n")

# wizualizacja trendu + sezonowości
plt.figure(figsize=(14, 5))
plt.scatter(train["Data"], train[CH4], alpha=0.15, s=10, label="Trening (rzeczywiste)")
plt.scatter(test["Data"], test[CH4], alpha=0.15, s=10, color="orange", label="Test (rzeczywiste)")
plt.plot(train["Data"], train["trend"], color="red", linewidth=1.2, label="Trend+sezonowość (trening)")
plt.plot(test["Data"], test["trend"], color="red", linewidth=1.2, linestyle="--", label="Trend+sezonowość (ekstrapolacja)")
plt.xlabel("Data")
plt.ylabel("CH4 [ppb]")
plt.title("Trend + sezonowość CH4 w czasie (harmoniki roczne)")
plt.legend()
plt.tight_layout()
plt.savefig("ch4_trend_sezonowosc.png", dpi=150)
plt.show()

# ---------------------------------------------------------
# 4. KROK 2: LightGBM uczy się przewidywać RESZTY (nie surowe CH4!)
# ---------------------------------------------------------
X_train, y_train_reszta = train[cechy], train["reszta"]
X_test, y_test_reszta = test[cechy], test["reszta"]

tscv = TimeSeriesSplit(n_splits=5)

siatka_parametrow = {
    "n_estimators": [200, 400, 600, 800, 1000],
    "num_leaves": [7, 15, 31, 63],
    "max_depth": [-1, 3, 4, 6, 8],
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
szukanie.fit(X_train, y_train_reszta, categorical_feature=cechy_kategoryczne)

print("--- LightGBM (na resztach): najlepsze parametry ---")
print(szukanie.best_params_)

model_lgbm = szukanie.best_estimator_
pred_reszta_test = model_lgbm.predict(X_test)

# ---------------------------------------------------------
# 5. KROK 3: finalna prognoza = trend + przewidziana reszta
# ---------------------------------------------------------
pred_finalna = test["trend"].values + pred_reszta_test

r2_finalny = r2_score(test[CH4], pred_finalna)
mae_finalny = mean_absolute_error(test[CH4], pred_finalna)

# dla porównania: sam trend bez modelu reszt
r2_sam_trend = r2_score(test[CH4], test["trend"])
mae_sam_trend = mean_absolute_error(test[CH4], test["trend"])

print("\n--- Wyniki na zbiorze testowym (surowe CH4, po rekonstrukcji) ---")
print(f"Sam trend (bez LightGBM):          R² = {r2_sam_trend:.3f}   MAE = {mae_sam_trend:.2f} ppb")
print(f"Trend + LightGBM (reszty):         R² = {r2_finalny:.3f}   MAE = {mae_finalny:.2f} ppb")
print(f"LightGBM samo (tylko reszty, cel):  R² = {r2_score(y_test_reszta, pred_reszta_test):.3f}")

# ---------------------------------------------------------
# 6. Wykres: rzeczywiste vs przewidziane (po rekonstrukcji trendu)
# ---------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(12, 6))

axes[0].scatter(test[CH4], test["trend"], alpha=0.3, s=15)
lims = [test[CH4].min(), test[CH4].max()]
axes[0].plot(lims, lims, color="red", linestyle="--")
axes[0].set_xlabel("CH4 rzeczywiste [ppb]")
axes[0].set_ylabel("CH4 przewidziane [ppb]")
axes[0].set_title(f"Sam trend liniowy\nR²={r2_sam_trend:.3f}")

axes[1].scatter(test[CH4], pred_finalna, alpha=0.3, s=15)
axes[1].plot(lims, lims, color="red", linestyle="--")
axes[1].set_xlabel("CH4 rzeczywiste [ppb]")
axes[1].set_ylabel("CH4 przewidziane [ppb]")
axes[1].set_title(f"Trend + LightGBM (reszty)\nR²={r2_finalny:.3f}")

plt.tight_layout()
plt.savefig("ch4_detrend_sezon_lightgbm_rzeczywiste_vs_predykcja.png", dpi=150)
plt.show()

# szereg czasowy: rzeczywiste vs finalna prognoza w czasie
plt.figure(figsize=(14, 5))
plt.plot(test["Data"], test[CH4], ".", alpha=0.3, label="CH4 rzeczywiste")
plt.plot(test["Data"], pred_finalna, ".", alpha=0.3, color="green", label="CH4 przewidziane (trend + LightGBM)")
plt.plot(test["Data"], test["trend"], color="red", linewidth=2, label="Sam trend")
plt.xlabel("Data")
plt.ylabel("CH4 [ppb]")
plt.title("Zbiór testowy: rzeczywiste vs prognoza (detrending + LightGBM)")
plt.legend()
plt.tight_layout()
plt.savefig("ch4_detrend_sezon_szereg_czasowy_test.png", dpi=150)
plt.show()

# ---------------------------------------------------------
# 7. Walidacja krzyżowa czasowa (na resztach, w obrębie treningu)
# ---------------------------------------------------------
wyniki_cv = []
for i, (idx_tr, idx_val) in enumerate(tscv.split(train)):
    fold_train = train.iloc[idx_tr]
    fold_val = train.iloc[idx_val]

    # trend+sezonowość dopasowane tylko na fold_train
    mt = LinearRegression()
    mt.fit(fold_train[CECHY_TRENDU], fold_train[CH4])
    trend_val = mt.predict(fold_val[CECHY_TRENDU])
    reszta_fold_train = fold_train[CH4] - mt.predict(fold_train[CECHY_TRENDU])

    m = LGBMRegressor(**szukanie.best_params_, random_state=42, verbose=-1)
    m.fit(fold_train[cechy], reszta_fold_train, categorical_feature=cechy_kategoryczne)
    pred_reszta_val = m.predict(fold_val[cechy])

    pred_val_final = trend_val + pred_reszta_val
    wynik = r2_score(fold_val[CH4], pred_val_final)
    wyniki_cv.append(wynik)
    print(f"Fold {i+1}: R² (po rekonstrukcji trendu) = {wynik:.3f}")

print(f"\nŚredni R² z walidacji czasowej (detrend + LightGBM): "
      f"{np.mean(wyniki_cv):.3f} (+/- {np.std(wyniki_cv):.3f})")

# ---------------------------------------------------------
# 8. Ważność cech + SHAP (dla modelu reszt)
# ---------------------------------------------------------
waznosc = pd.Series(model_lgbm.feature_importances_, index=cechy).sort_values()

plt.figure(figsize=(8, 7))
plt.barh(waznosc.index, waznosc.values, color="seagreen")
plt.xlabel("Ważność cechy (LightGBM, split gain)")
plt.title("Ważność zmiennych w przewidywaniu RESZT CH4 (po odjęciu trendu)")
plt.tight_layout()
plt.savefig("ch4_detrend_sezon_lightgbm_waznosc_cech.png", dpi=150)
plt.show()

explainer = shap.TreeExplainer(model_lgbm)
shap_values = explainer.shap_values(X_test)

plt.figure()
shap.summary_plot(shap_values, X_test, show=False)
plt.tight_layout()
plt.savefig("ch4_detrend_sezon_lightgbm_shap_summary.png", dpi=150, bbox_inches="tight")
plt.show()

print("\nGotowe. Zapisane pliki: ch4_trend_sezonowosc.png, "
      "ch4_detrend_sezon_lightgbm_rzeczywiste_vs_predykcja.png, "
      "ch4_detrend_sezon_szereg_czasowy_test.png, ch4_detrend_sezon_lightgbm_waznosc_cech.png, "
      "ch4_detrend_sezon_lightgbm_shap_summary.png")
