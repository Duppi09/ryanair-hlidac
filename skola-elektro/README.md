# Elektro dril – denní cvičení k závěrečným zkouškám (červen 2027)

Aplikace: https://claude.ai/artifact/NPwzLqGKGSqP9iURTsihsy

## Jak to funguje
- Každý den 10 otázek (stejná sada celý den, i na jiném zařízení).
- Špatná odpověď → otázka přijde znovu hned zítra a pak častěji (Leitnerovy krabičky: 1, 2, 4, 8, 16, 32 dní).
- Správně zodpovězené otázky občas přijdou i předčasně, takže se nezapomenou.
- Témata, kde se chybuje víc, dostávají ve výběru větší váhu (max. 3 otázky z jednoho tématu za den).
- Záložky: **Dnes** (cvičení + nejslabší témata), **Chyby** (seznam a procvičení chyb), **Témata** (úspěšnost a 10 otázek z vybraného tématu).
- Postup se ukládá do úložiště artefaktu (`stav/statistiky`, `dny/<datum>`), takže ho Claude může přečíst a doplnit otázky tam, kde se chybuje.

## Banka otázek
Otázky jsou v `banka/*.txt` (čitelný formát, popsaný v `sestav_banku.py`).
Po úpravě spusť:

```
python3 sestav_banku.py
```

Tím se vytvoří `otazky.json`, který aplikace načítá. ID otázky vychází z jejího textu,
takže přidáním nových otázek se statistiky neztratí (změna textu otázky = nová otázka).

Zdroj: školní podklady (úraz el. proudem, vyhl. 50, EN 50110, ochrany, rozvody, koupelny,
spínače, kabely, datové kabely, E.ON, hromosvod, revize, světelné zdroje, součástky,
EZ1–EZ8, Elektrotechnika 1 a 2, měření, technická dokumentace, ruční zpracování kovů).
Otázky označené „doplněno“ jsou nad rámec podkladů (např. nařízení vlády 194/2022 Sb.,
které od roku 2022 nahradilo vyhlášku 50/1978).
