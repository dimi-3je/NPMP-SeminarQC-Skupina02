# Groverjev algoritem pod šumom

Seminarska naloga pri predmetu Nekonvencionalne platforme in metode procesiranja (UL FRI, 2026/27), skupina 02.
Avtor: Dimitrije Stefanović.

**Raziskovalno vprašanje:** pri katerem številu iteracij je verjetnost uspeha Groverjevega algoritma na simulatorju s šumnim modelom največja in ali nanj vpliva stopnja optimizacije pri prevajanju vezja (`optimization_level` od 0 do 3)?

## Vsebina

| Datoteka | Vsebina |
|---|---|
| `circuit.py` | Groverjevo vezje (označen element 0) in teoretična verjetnost uspeha |
| `experiment.py` | Poskus: n = 2, 3, 4 kubiti, k = 1 do 9 iteracij, stopnje 0 do 3, 10 semen prevajalnika, 4096 ponovitev. Prevajanje na Fake20QV1, zagon na idealnem in na šumnem simulatorju. |
| `analysis.py` | Preverjanje hipotez H1 do H3 in tabele za poročilo |
| `plots.py` | Slike za poročilo |
| `ibm_run.py` | Izbrani primeri na realnem procesorju IBM |
| `data/grid.csv` | Rezultati poskusa, ena vrstica na konfiguracijo (1080 vrstic) |
| `data/grid.json` | Različice paketov, datum kalibracije, povprečna napaka vrat CX |
| `data/analysis.txt` | Izpis `analysis.py` |
| `data/ibm.csv`, `data/ibm_job.json` | Rezultati in ID posla na procesorju IBM (po zagonu `ibm_run.py`) |
| `figures/` | Slike v formatu PDF |

## Namestitev

Python 3.10. Qiskit je pripet na 1.4.3, ker se Qiskit 2.x na Pythonu 3.10 ni dal uvoziti.

```
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

## Zagon

Iz te mape, po vrsti:

```
.venv/Scripts/python.exe experiment.py    # približno 15 minut, zapiše data/grid.csv in data/grid.json
.venv/Scripts/python.exe analysis.py      # zapiše data/analysis.txt
.venv/Scripts/python.exe plots.py         # zapiše figures/*.pdf
```

Vsi naključni procesi imajo fiksna semena, zato ponovni zagon da enake rezultate.

## Realni procesor IBM (neobvezno)

Potrebuje račun IBM Quantum (Open Plan) in ločeno okolje:

```
python -m venv .venv-ibm
.venv-ibm/Scripts/python.exe -m pip install -r requirements-ibm.txt
.venv-ibm/Scripts/python.exe ibm_run.py --login    # shrani API ključ
.venv-ibm/Scripts/python.exe ibm_run.py            # odda posel in počaka na rezultat
.venv-ibm/Scripts/python.exe ibm_run.py --fetch    # prevzame rezultat že oddanega posla
```

## Opombe

- Fake20QV1 je testni procesor, priložen Qiskitu (20 kubitov, kalibracijski podatki z dne 2020-08-07). Ni realna naprava.
- "Pred prevajanjem" pomeni vezje v osnovnih vratih procesorja brez upoštevanja topologije in brez optimizacije.
