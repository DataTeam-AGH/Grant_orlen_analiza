# W wielkim skrócie

Sensowne wyniki wyszły tylko dla metanu, tam też było najwięcej danych - wyszedł trend dodatni i w sumie brak jakiejś istotnej sezonowości. NO2 to wgl strata czasu (dane są tylko z marca 2026 XDDDD), HCHO ma tylko 13 unikalnych dat, CO powiedzmy, że coś się da wyczytać, a SO2 niedomaga, ale jakieś wykresy są. No i co, tyle XDDDDD
Jeżeli ktoś się dziwi, jak może wyjść tak mało danych faktycznych z tylu wierszy, ile jest w danych oryginalnych, to odsyłam do tej platformy, z której je pobieraliśmy - można zrobić w jeden dzień 15 pomiarów, ale to nie oznacza, że całość będzie istotna statystycznie

## CH4 - tutaj jeszcze ok

Tutaj jest najwięcej do obgadania, dużo danych, można coś faktycznie wyczytać:

<img width="1800" height="750" alt="CH4_01_trend_szereg_czasowy" src="https://github.com/user-attachments/assets/0e61410c-647c-44de-b9ec-771274cf394a" />

Wyraźnie widać trend dodatni, testy istotności statystycznej go potwierdzają przy alpha = 0.05, slope około 1.5 - wzrost o około 175 jednostek na przestrzeni 7 lat.

<img width="1500" height="750" alt="CH4_04_sezonowosc_boxplot_miesiac" src="https://github.com/user-attachments/assets/8017086c-479f-4785-bcce-b2f507da1a50" />

Jakiejś sezonowości mocnej nie widać, jak już to zimą nieco wyżej (miałoby sens, biorąc pod uwagę korelację z temperaturą r~=-0.17).

<img width="1800" height="1500" alt="CH4_10_dekompozycja" src="https://github.com/user-attachments/assets/ca7eb484-3684-4018-abea-b3c50906617b" />

Reszty po dekompozycji dalej mają jakieś piki niewytłumaczalne, ale bez dramatu jakiegoś.

<img width="1500" height="600" alt="CH4_11_autokorelacja" src="https://github.com/user-attachments/assets/27461012-9520-4103-af8f-853f6df8e514" />

Autokorelacja powoli sobie zanika, typowo bardzo dla trendu, poniżej błędu statystycznego schodzi dopiero w okolicach pół roku.

## SO2

Tutaj ogólnie zaczynamy jazdę z brakami danych, więc proszę zapiąć pasy. 

<img width="1800" height="750" alt="SO2_01_trend_szereg_czasowy" src="https://github.com/user-attachments/assets/42d1da12-2790-4daa-8a9f-dfc2f5d06910" />

Linia trendu tam jest dla dekoracji, bo nikt niczego się i tak nie dopatrzy, tutaj bardziej widać cokolwiek:

<img width="1350" height="750" alt="SO2_03_srednia_roczna" src="https://github.com/user-attachments/assets/fd008fe9-843d-487d-9d2c-fbf70409605a" />

Widać, że trudno tutaj mówić o jakimkolwiek trendzie, bo mamy dziwnie odjechane wartości w 2022/2023??? Może jest na to jakieś wyjaśnienie, literatura potrzebna do dalszej inwestygacji. Oprócz tego płasko.

<img width="1500" height="900" alt="SO2_07_heatmapa_rok_miesiac" src="https://github.com/user-attachments/assets/56422ef1-b665-4ccb-b182-cd0c91bc83d6" />

To tutaj tak co do tych braków - nie ma żadnych danych ze stycznia/lutego, więc wnioski o miesiącach "zimowych" opieramy tylko na marcu, przez ogólnie pojęte społeczeństwo uznawanym za miesiąc wiosenny. Dla miesięcy letnich za to nie ma praktycznie danych z ostatnich czterech lat, więc jakiekolwiek wnioski, które tutaj wyciągnę będą bazowały na moich przypuszczeniach. 

<img width="1500" height="750" alt="SO2_04_sezonowosc_boxplot_miesiac" src="https://github.com/user-attachments/assets/f950b976-21b1-464c-85d2-ee5923236caf" />

Tutaj bardzo fajne boxploty dla sezonowości, widać, że w marcu jest większa wariancja niż w miesiącach letnich, mamy wyższe wartości i więcej wysokich outlierów. Wszystko byłoby elegancko, gdyby nie fakt, że dla tych miesięcy letnich mamy ponad dwa razy mniej danych niż dla marca, więc teoretycznie te outliery mogły wystąpić, tylko nikt ich nie uchwycił. Inny krytyczny błąd - dla miesięcy letnich nie ma danych z lat 2022/23, które odnotowały się dziwnymi anomaliami w marcu, więc ciężko tutaj zauważyć czy na dziwnie wysokich latach ta sezonowość też się utrzymuje.

Jedynym ratunkiem jest korelacja z temperaturą r~=-0.34 (mocne jak na warunki naturalne btw), czyli z tą sezonowością może coś być na rzeczy, ale głowy uciąć nie dam.

<img width="1800" height="1500" alt="SO2_10_dekompozycja" src="https://github.com/user-attachments/assets/5b5aa9fe-733b-4f46-a6bb-ff90da670ea1" />

Reszty dalej wyglądają, jakby tam były jakieś zależności, więc ja wymiękam.

## NO2

Brak komentarza, w ramach ciekawostki, wykres wygląda tak:

<img width="1800" height="750" alt="NO2_01_trend_szereg_czasowy" src="https://github.com/user-attachments/assets/0fed0b76-5925-4260-b513-fb2d6b77c38a" />

#### Dla nerdów
Jedyne co tutaj istotne do zauważenia to w sumie podział w danych na NO2 ogólne i troposferyczne. Sposób pomiaru tego zapomnianego przez Boga narzędzia, którego używamy to ile jest jednostek danego gazu w całej kolumnie powietrza ponad tym danym punktem, czyli od podłogi do satelity praktycznie. Na chłopski rozum, nie wszystko, co tam się znajdzie będzie winą ludzką, więc przyjmuje się też podział na warstwę troposferyczną (od poziomu podłogi jakieś 10/15km w górę, tam mamy głównie zanieczyszczenia) i stratosferyczną (wszystko, co nad nią). Dla niektórych gazów nie ma tu jakiejś różnicy, ale NO2 występuje w dużych ilościach akurat w stratosferze z jakichś tam procesów naturalnych (cykl ozonowy, procesy fotochemiczne), więc wyższa jego ilość w całej kolumnie mało znaczy, bierze się ile go jest w niższej warstwie. Miałoby to większe znaczenie gdybyśmy mieli więcej danych, ale eh

## HCHO

Jeden z testów pokazał tutaj niby istotność statystyczną, ale czy da się o czymś takim mówić przy 13 unikalnych dniach no nie wiem XDDDD

<img width="1500" height="750" alt="HCHO_07_heatmapa_rok_miesiac" src="https://github.com/user-attachments/assets/dcaffaed-21d2-47ff-9c57-ba9371356968" />

Podejrzanie to wygląda na moje oko, ale niby jakiś trend jest. Tym bardziej bym tutaj nie szukała podstaw do jakiejkolwiek sezonowości.

<img width="1350" height="750" alt="HCHO_03_srednia_roczna" src="https://github.com/user-attachments/assets/00a9ac3c-7e35-467d-bc25-bfffad133484" />

## CO

Grzechy główne - brak trendu, nie ma 2023 roku w danych, wcześniej niż 2021 też nie ma, i jak są to tylko z lutego i marca. 

<img width="1500" height="675" alt="CO_07_heatmapa_rok_miesiac" src="https://github.com/user-attachments/assets/ec6318ba-aa3b-49e7-9f63-f9d8d6d48f72" />

Tak to wygląda btw

<img width="1350" height="750" alt="CO_03_srednia_roczna" src="https://github.com/user-attachments/assets/42007128-9fc1-490f-b1a3-bd19b5dc5b4d" />

Jedyne co dało się z tego wycisnąć to korelację z temperaturą r~=-0.384, więc to może wskazywać na jakąś sezonowość? No ale za mało danych, żeby czegoś tutaj dowodzić.













