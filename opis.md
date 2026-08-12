# Podsumowanie modelowania CH4 — LightGBM (3 podejścia)

O co ogólnie chodziło? Zamodelować stężenie CH4 (`CH4_column_volume_mixing_ratio_dry_air`) na podstawie zmiennych
pogodowych, odległości od punktu centralnego i lokalizacji, przy uczciwym (chronologicznym)
podziale na trening/test oraz walidacji krzyżowej `TimeSeriesSplit` (5 foldów).

- na podstawie danych ze wszystkich miast (jest link do tego pliku w folderze obok, nie zmieściło się na commit na gita, więc pobierajcie jkbc z dysku Google'a)

---

## Próba 1 — LightGBM bez detrendingu

Model uczony bezpośrednio na surowych wartościach CH4, bez usuwania trendu czasowego.

**Wyniki:**

| Metryka | Baseline | Po dostrojeniu (RandomizedSearchCV) |
|---|---|---|
| R² (test) | -2.134 | -1.685 |
| MAE (test) | 25.966 ppb | 24.396 ppb |

**Walidacja krzyżowa (foldy w obrębie treningu):**

| Fold | 1 | 2 | 3 | 4 | 5 | **Średnia** |
|---|---|---|---|---|---|---|
| R² | -1.582 | -0.949 | -0.693 | -1.896 | -1.735 | **-1.371 (± 0.467)** |

Najlepsze hiperparametry: `num_leaves=15, n_estimators=200, min_child_samples=30, max_depth=-1, learning_rate=0.01, colsample_bytree=1.0, subsample=0.6, reg_alpha=1, reg_lambda=0`.

**Wniosek:** R² mocno ujemne na każdym foldzie — model jest systematycznie gorszy niż zwykłe
zgadywanie średniej (big oof). Czemu? Silny trend wzrostowy CH4 w czasie, którego model drzewiasty
(LightGBM) nie potrafi ekstrapolować poza zakres wartości widziany w treningu - ogólnie nijak tego
nie zamodelujemy do przodu, a nawet w walidacji krzyżowej (na danych, które powinno ogarniać!!!) 
LightBGM strzela w Moskwę, a trafia w Bytom.

<img width="1190" height="590" alt="zwykle1" src="https://github.com/user-attachments/assets/80028da9-8295-4f8e-b1e5-250faf090210" />

Tutaj CH4 rzeczywiste vs przewidziane w opcji basic i opcji dostrojonej, chyba widać skąd bierze się ujemne R^2 XD

<img width="790" height="690" alt="zwykle2" src="https://github.com/user-attachments/assets/9995560a-9653-4ad3-a6ee-bc471c0de081" />

<img width="790" height="940" alt="zwykle3" src="https://github.com/user-attachments/assets/3ff5638b-ae5b-465e-bc8a-cffd6b3441dc" />

Trochę śmieszny wykres, więc co do interpretacji osi X - wartość SHAP: im dalej od zera, tym większy wpływ na prognozę CH4 danego punktu. 
Wartości dodatnie = podnoszą prognozę, ujemne = obniżają.
Kolor punktu — wysokość wartości samej cechy: czerwony = wysoka wartość cechy (np. wysoka temperatura), niebieski = niska wartość.
Każdy punkt = jedna obserwacja (jeden wiersz z danych).

Czyli - niebieski punkt po lewej - niskie wartości parametru obniżają prognozę; czerwony punkt po prawej - wysokie wartości parametru 
podwyższają prognozę itede, czaicie bazę.

<img width="789" height="940" alt="zwykle4" src="https://github.com/user-attachments/assets/44a2ad47-589e-4b31-9e39-bfc3ca102c56" />

"Ile śrendio ta cecha waży w decyzji modelu", i w jednym i w drugim porównaniu opady gdzieś tam na prowadzeniu 
się pojawiają, hallelujah.

---

## Próba 2 — Detrending (trend liniowy) + LightGBM na resztach

Krok 1: dopasowanie prostej `CH4 = a·dni + b` tylko na treningu.
Krok 2: LightGBM uczy się przewidywać reszty (CH4 − trend) na podstawie pogody/lokalizacji.
Krok 3: finalna prognoza = trend + przewidziana reszta.

**Wykryty trend:** `CH4 = 0.02631 · dni + 1838.51` → **wzrost roczny: 9.60 ppb/rok**
(zbliżony do globalnego trendu atmosferycznego metanu, ~10–12 ppb/rok — wynik fizycznie sensowny) - 
wychodzi nam na to, że takie procesy faktycznie zachodzą i jesteśmy w stanie to wykryć i odtrąbić
pokoleniowy triumf eksploracyjnej analizy danych.

Najlepsze hiperparametry: `num_leaves=7, n_estimators=200, min_child_samples=30, max_depth=-1, learning_rate=0.01, colsample_bytree=1.0, subsample=0.6, reg_alpha=1, reg_lambda=0`.

**Wyniki na zbiorze testowym (po rekonstrukcji, surowe CH4):**

| Wariant | R² | MAE |
|---|---|---|
| Sam trend (bez LightGBM) | -0.298 | 15.07 ppb |
| Trend + LightGBM (reszty) | -0.145 | 14.09 ppb |
| LightGBM samo (cel = reszty) | -0.097 | — |

**Walidacja krzyżowa:**

| Fold | 1 | 2 | 3 | 4 | 5 | **Średnia** |
|---|---|---|---|---|---|---|
| R² | 0.030 | -0.045 | -0.202 | 0.071 | 0.023 | **-0.025 (± 0.096)** |

**Wniosek:** Ogromna poprawa względem próby 1 (średnie R² CV z -1.371 do -0.025). Usunięcie
trendu było kluczowe. Model wciąż nie ekstrapoluje dobrze w nieznaną przyszłość (test R² ujemne),
ale w obrębie znanych danych (CV) jest już blisko zera, czyli w większości przypadków tak dobry,
jak zgadywanie średniej — nie szkodzi, ale działa analogicznie do tej ośmiornicy przewidującej 
wyniki na Euro 2012.

<img width="2100" height="750" alt="ch4_trend_liniowy" src="https://github.com/user-attachments/assets/3112936b-6242-459e-9dea-0a34f96740d8" />

<img width="2100" height="750" alt="ch4_detrend_szereg_czasowy_test" src="https://github.com/user-attachments/assets/96c3044a-65bf-4bb0-8fbc-d60f8aac8e53" />

<img width="1200" height="1050" alt="ch4_detrend_lightgbm_waznosc_cech" src="https://github.com/user-attachments/assets/f8855969-451b-4b94-8789-2d81b8179806" />

<img width="1184" height="1409" alt="ch4_detrend_lightgbm_shap_summary" src="https://github.com/user-attachments/assets/2d64b5a1-06df-41c0-b182-8ff97448742f" />

Co ciekawe, ten model uznaje za ważniejsze ciśnienie niż tamto wcześniejsze, co w sumie nam się pokrywa
z wcześniejszymi macierzami korelacji! 


<img width="1800" height="900" alt="ch4_detrend_lightgbm_rzeczywiste_vs_predykcja" src="https://github.com/user-attachments/assets/cd4cf467-33b8-4d68-92a9-2257bb4f6e8c" />


---

## Próba 3 — Detrending (trend + sezonowość) + LightGBM na resztach

Rozszerzenie modelu trendu o harmoniki roczne (sin/cos dnia roku) i półroczne, żeby wychwycić
sezonowość (jakaś jest) zamiast zostawiać ją w resztach dla LightGBM:

`CH4 = a·dni + b1·sin(rok) + b2·cos(rok) + b3·sin(2·rok) + b4·cos(2·rok) + c`

**Współczynniki modelu trend+sezonowość:**

| Zmienna | Współczynnik |
|---|---|
| dni_od_startu | 0.02682 |
| sezon_sin_1 | -5.54783 |
| sezon_cos_1 | 4.14203 |
| sezon_sin_2 | 2.23749 |
| sezon_cos_2 | -8.01289 |

**Wzrost roczny wg trendu:** 9.79 ppb/rok (spójne z próbą 2, potwierdza stabilność sygnału).
**Amplituda sezonowości (1. harmonika):** ± 6.92 ppb.

Najlepsze hiperparametry: `num_leaves=7, n_estimators=200, min_child_samples=30, max_depth=-1, learning_rate=0.01, colsample_bytree=1.0, subsample=0.6, reg_alpha=1, reg_lambda=0`.

**Wyniki na zbiorze testowym (po rekonstrukcji, surowe CH4):**

| Wariant | R² | MAE |
|---|---|---|
| Sam trend+sezon (bez LightGBM) | -0.179 | 14.53 ppb |
| Trend+sezon + LightGBM (reszty) | -0.063 | 13.69 ppb |
| LightGBM samo (cel = reszty) | -0.165 | — |

**Walidacja krzyżowa:**

| Fold | 1 | 2 | 3 | 4 | 5 | **Średnia** |
|---|---|---|---|---|---|---|
| R² | 0.120 | 0.199 | -0.104 | 0.106 | 0.139 | **0.092 (± 0.103)** |

**Wniosek:** Najlepszy wynik ze wszystkich trzech prób. Średnie R² z CV pierwszy raz **dodatnie**
(0.092), a 4 z 5 foldów wyraźnie dodatnie (0.10–0.20) — model realnie tłumaczy część zmienności
CH4 ponad samo zgadywanie średniej. Fold 3 pozostaje ujemny (-0.104), co sugeruje pojedynczy
nietypowy okres (możliwa anomalia pogodowa/pomiarowa), który psuje wynik na tym fragmencie danych,
ale już nie dominuje całości jak w próbach 1–2. Możemy tę wersję modelu ciągnąć dalej, jeżeli chcemy coś 
jeszcze dokładniejszego albo zostawić, gdzie jest i niech się dzieje wola nieba, i tak więcej z tych danych 
nie wyciągniemy.

<img width="2100" height="750" alt="ch4_trend_sezonowosc" src="https://github.com/user-attachments/assets/41348eba-e3cf-4ef2-b1a5-2ef5ffdde695" />

<img width="2100" height="750" alt="ch4_detrend_sezon_szereg_czasowy_test" src="https://github.com/user-attachments/assets/cab95588-0dfe-473d-92f9-252a435cb5ae" />

<img width="1200" height="1050" alt="ch4_detrend_sezon_lightgbm_waznosc_cech" src="https://github.com/user-attachments/assets/bc7071b1-3d4e-41f8-a1b5-c8d6e5a85342" />

<img width="1184" height="1409" alt="ch4_detrend_sezon_lightgbm_shap_summary" src="https://github.com/user-attachments/assets/526a810d-b31b-438a-bd82-1c639f7144e7" />

<img width="1800" height="900" alt="ch4_detrend_sezon_lightgbm_rzeczywiste_vs_predykcja" src="https://github.com/user-attachments/assets/79270f9f-9516-4cb6-b29e-ecba6feef92d" />

Nie ma tragedii!!!

---

## Zestawienie zbiorcze

| Próba | Średni R² (CV) | R² (test, po rekonstrukcji) | MAE (test) |
|---|---|---|---|
| 1. LightGBM bez detrendingu | -1.371 (± 0.467) | -1.685 | 24.40 ppb |
| 2. Detrend (trend liniowy) | -0.025 (± 0.096) | -0.145 | 14.09 ppb |
| 3. Detrend + sezonowość | **0.092 (± 0.103)** | **-0.063** | **13.69 ppb** |

**Kluczowy wniosek:** każdy kolejny krok (usunięcie trendu, potem dodanie sezonowości)
systematycznie poprawiał zarówno stabilność modelu w walidacji krzyżowej, jak i dokładność
na zbiorze testowym — to spójna, monotoniczna poprawa, a nie przypadkowa fluktuacja.
Model z trendem i sezonowością (próba 3) jest jedynym, który w typowych warunkach (CV)
wykazuje realną wartość predykcyjną, choć wciąż ma ograniczoną zdolność do ekstrapolacji
w nieznaną przyszłość, szczególnie w okresach z anomaliami.

Ogólnie bardzo mało jeszcze jesteśmy w stanie z tego wyczarować z jednego względu - 
to są dane atmosferyczne, z całego słupa powietrza. Szukać w tych litrach powietrza CH4
to jakby łapać woń drzewa sandałowego na wysypisku śmieci, zwłaszcza, że na naszych terenach jakieś
wielkie eksplozje/wycieki się nie zdarzają (a nawet jeśli, to nikt nam nie chce dać danych
kiedy by to mogło być - do Czarnobyla też się nikt nie chciał przyznać). Jeżeli czynniki pogodowe
mają realny wpływ na poziomy metanu, zatraca się ta relacja poprzez uśrednienie samych pomiarów. 
I tak jestem w szoku, że mamy ten trend wzrostowy widoczny, to tym się pochwalimy
przed pryncypałami.

**Co jeszcze możemy zrobić ewentualnie** (brak gwarancji, że to zadziała):
- zbadanie foldu 3 / okresu testowego pod kątem konkretnej anomalii (np. styczeń 2026),
- druga (nieliniowa) harmonika trendu długoterminowego zamiast czystej prostej.
