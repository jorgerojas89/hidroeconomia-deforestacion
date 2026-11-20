"""
T7 · 05 · Horas con generación (insumo de la hipótesis exploratoria H2, registro de cambios del 20-nov-2026).

Lee los Excel horarios de XM en 02_datos/Generacion (2001–2024), deja solo las plantas hidráulicas y cuenta,
por recurso y día, las horas con generación mayor que cero y las horas con dato. No toca ninguna variable
de deforestación.

Salida: 02_datos/xm_procesado/horas_generacion_hidro_diaria.csv.gz  (fecha, recurso, horas_gen, horas_dato, kwh)
Uso (desde 03_tesis): python3 -m pip install python-calamine pandas
                      python3 03_codigo/05_estimacion/05_horas_generacion.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "02_datos"
OUT = D / "xm_procesado" / "horas_generacion_hidro_diaria.csv.gz"


def leer(f: Path) -> pd.DataFrame:
    crudo = pd.read_excel(f, engine="calamine", header=None, nrows=15)
    fila = next(i for i, r in crudo.iterrows() if str(r.iloc[0]).strip().lower() == "fecha")
    df = pd.read_excel(f, engine="calamine", header=fila)
    df.columns = [str(c).strip() for c in df.columns]
    return df


partes = []
for f in sorted((D / "Generacion").glob("*.xls*")):
    m = re.search(r"(20\d\d)", f.name)
    if not m or not 2001 <= int(m.group(1)) <= 2024:
        continue
    df = leer(f)
    tc = next(c for c in df.columns if c.lower().startswith("tipo gener") or c.lower().startswith("tipo de gener"))
    horas = [c for c in df.columns if re.fullmatch(r"\d{1,2}(\.0)?", c)]
    assert len(horas) == 24, f"{f.name}: {len(horas)} columnas de hora"
    h = df[df[tc].astype(str).str.upper().str.startswith("HIDR")]
    v = h[horas].apply(pd.to_numeric, errors="coerce")
    partes.append(pd.DataFrame({"fecha": pd.to_datetime(h["Fecha"]).dt.date, "recurso": h["Recurso"].astype(str).str.strip(),
                                "horas_gen": (v > 0).sum(axis=1), "horas_dato": v.notna().sum(axis=1),
                                "kwh": v.sum(axis=1)}))
    print(f.name, len(h), "filas hidráulicas")
g = pd.concat(partes).groupby(["fecha", "recurso"], as_index=False).sum()
g.to_csv(OUT, index=False)
print("Escrito", OUT, len(g), "filas;", g["fecha"].min(), "a", g["fecha"].max())
