#!/usr/bin/env python3
"""
T6 — Anexo: comparación con la base de 2019 para las centrales comunes.

Compara áreas y variables (no estima nada): área de cuenca, tipo, generación, factor de
capacidad, deforestación (flujo, total y acumulado) y lluvia, en 2001–2015, entre
  - la base de 2019: 02_datos/DF.xlsx (hoja Mt; capacidades y tipos de la tabla maestra), y
  - los datos nuevos: ATCH IGAC (T3), Hansen v1.12 y CHIRPS v3 (T4), XM (T2/T5).
La lista de centrales comunes es la de 02_datos/cuencas_igac/comparacion_2019.csv (19 con ATCH).

REGLA: sin correlaciones ni regresiones entre deforestación y generación. La única
correlación que se calcula es entre la MISMA variable (pérdida anual de bosque) medida en
2019 y en 2026, como control de la fuente.

Salidas: 02_datos/panel/anexo_comparacion_2019.csv y .md
Supuestos sobre DF.xlsx (Mt), verificados con los datos:
  - Kwyear = generación anual en kWh.
  - Ha_Def = píxeles deforestados × 4,340278 ha; Per_defacum = acumulado / área de la cuenca (fracción).
  - Lluvia = suma de la lluvia de las celdas de 4,340278 ha; lluvia media (mm) = Lluvia / (Area / 4,340278).
    En 2011–2013 esa media vale ~11 mm (la falla documentada en la sección 2 del plan); se excluyen.
"""
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
D = BASE / "02_datos"
OUT = D / "panel"
A0, A1 = 2001, 2015
FALLA_LLUVIA = {2011, 2012, 2013}
CELDA_HA = 4.340278

comp = pd.read_csv(D / "cuencas_igac/comparacion_2019.csv")
tm = pd.read_csv(D / "tabla_maestra/tabla_maestra.csv", encoding="utf-8-sig")
mt = pd.read_excel(D / "DF.xlsx", sheet_name="Mt")
px = pd.read_csv(D / "tabla_maestra/panel_xm_unidad_anio.csv", encoding="utf-8-sig")
de = pd.read_csv(D / "earth_engine/deforestacion_cuenca_anio.csv")
ll = pd.read_csv(D / "earth_engine/lluvia_cuenca_anio.csv")

for c in ["Kwyear", "Ha_Def", "Per_defacum", "Lluvia", "Area"]:
    mt[c] = pd.to_numeric(mt[c], errors="coerce")
mt = mt.rename(columns={"t": "anio"})
mt = mt[mt["anio"].between(A0, A1)]

tm["tipo_2019"] = tm["fuentes_tipo"].astype(str).str.extract(r"tesis 2019=(\w+)")[0]
ch2 = pd.read_excel(D / "DF.xlsx", sheet_name="CH2")   # tipo de 2019 por central: Presa / Filo
ch2["t19"] = ch2["Type"].astype(str).str.strip().str.capitalize().map({"Presa": "embalse", "Filo": "filo"})
ch2["CH"] = ch2["CH"].astype(str).str.strip().str.upper()
tm["tipo_2019"] = tm["tipo_2019"].fillna(tm["unidad"].map(ch2.dropna(subset=["t19"]).set_index("CH")["t19"]))
info = tm.set_index("unidad")[["tipo_propuesto", "tipo_2019", "cap_tesis2019_mw"]]

filas = []
for _, c in comp.iterrows():
    u, ids = c["unidad"], str(c["ids_2019"]).split(";")
    v = mt[mt["id"].isin(ids)].groupby("anio").agg(gen_kwh=("Kwyear", "sum"), ha_def=("Ha_Def", "sum"),
                                                   lluvia=("Lluvia", "sum"), area=("Area", "first"),
                                                   per_acum=("Per_defacum", "last"))
    n = de[de["unidad"].eq(u) & de["anio"].between(A0, A1)].set_index("anio")
    g = px[px["unidad"].eq(u) & px["anio"].between(A0, A1)].set_index("anio")
    lnew = ll[ll["unidad"].eq(u) & ll["anio"].between(A0, A1)].set_index("anio")["lluvia_mm"]
    area19 = v["area"].dropna().iloc[0] if v["area"].notna().any() else c["area_cuenca_2019_ha"]
    ll19 = v["lluvia"] / (area19 / CELDA_HA)
    anios_ll = [a for a in ll19.dropna().index if a not in FALLA_LLUVIA and ll19[a] > 0]
    cap19 = info.loc[u, "cap_tesis2019_mw"] if u in info.index else np.nan
    gen19 = v["gen_kwh"].where(v["gen_kwh"] > 0) / 1e6           # GWh
    comunes_g = gen19.dropna().index.intersection(g["gen_gwh"].dropna().index)
    comunes_d = v["ha_def"].dropna().index.intersection(n.index)
    r_def = (np.corrcoef(v.loc[comunes_d, "ha_def"], n.loc[comunes_d, "perdida_ha"])[0, 1]
             if len(comunes_d) >= 5 and v.loc[comunes_d, "ha_def"].std() > 0 else np.nan)
    acum19 = v["per_acum"].dropna()
    filas.append({
        "unidad": u, "ids_2019": c["ids_2019"], "muestra_principal": c["muestra_principal"],
        "tipo_2019": info.loc[u, "tipo_2019"] if u in info.index else np.nan,
        "tipo_2026": info.loc[u, "tipo_propuesto"] if u in info.index else np.nan,
        "area_2019_ha": round(c["area_cuenca_2019_ha"], 1), "area_atch_ha": round(c["ha_atch_2026"], 1),
        "razon_area": c["razon_atch_sobre_2019"], "diagnostico_area": c["diagnostico"],
        "gen_media_2019_gwh": round(gen19.loc[comunes_g].mean(), 1) if len(comunes_g) else np.nan,
        "gen_media_xm_gwh": round(g.loc[comunes_g, "gen_gwh"].mean(), 1) if len(comunes_g) else np.nan,
        "anios_gen_comunes": len(comunes_g),
        "cap_2019_mw": cap19,
        "cap_xm_media_mw": round(g.loc[comunes_g, "cap_mw"].mean(), 1) if len(comunes_g) else np.nan,
        "fc_medio_2019": round((gen19.loc[comunes_g] * 1000 / (cap19 * 8760)).mean(), 3) if len(comunes_g) and cap19 > 0 else np.nan,
        "fc_medio_xm": round(g.loc[comunes_g, "fc"].mean(), 3) if len(comunes_g) else np.nan,
        "def_total_2019_ha": round(v["ha_def"].sum(), 1),
        "def_total_hansen_ha": round(n["perdida_ha"].sum(), 1),
        "razon_def_total": round(n["perdida_ha"].sum() / v["ha_def"].sum(), 2) if v["ha_def"].sum() > 0 else np.nan,
        "r_def_anual_2019_vs_hansen": round(r_def, 2) if pd.notna(r_def) else np.nan,
        "def_acum2015_2019_pct_area": round(100 * acum19.iloc[-1], 3) if len(acum19) else np.nan,
        "def_acum2015_hansen_pct_area": round(100 * n["perdida_acum_ha"].iloc[-1] / n["area_ha"].iloc[-1], 3) if len(n) else np.nan,
        "def_acum2015_hansen_pct_bosque2000": round(n["perdida_acum_pct_bosque2000"].iloc[-1], 3) if len(n) else np.nan,
        "lluvia_media_2019_mm": round(ll19.loc[anios_ll].mean(), 0) if anios_ll else np.nan,
        "lluvia_media_chirps_mm": round(lnew.loc[anios_ll].mean(), 0) if anios_ll else np.nan,
        "lluvia_2019_en_2011_2013_mm": round(ll19.loc[[a for a in FALLA_LLUVIA if a in ll19.index]].mean(), 1),
    })

an = pd.DataFrame(filas).sort_values(["muestra_principal", "unidad"], ascending=[False, True])
for a, b, nombre in [("gen_media_xm_gwh", "gen_media_2019_gwh", "razon_gen"),
                     ("lluvia_media_chirps_mm", "lluvia_media_2019_mm", "razon_lluvia")]:
    an[nombre] = (an[a] / an[b]).round(2)
OUT.mkdir(parents=True, exist_ok=True)
an.to_csv(OUT / "anexo_comparacion_2019.csv", index=False, encoding="utf-8")


def md(df):
    df = df.fillna("—")
    return "\n".join(["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)] +
                     ["| " + " | ".join(str(x) for x in r) + " |" for r in df.itertuples(index=False)])


cols1 = ["unidad", "muestra_principal", "tipo_2019", "tipo_2026", "area_2019_ha", "area_atch_ha", "razon_area", "diagnostico_area"]
cols2 = ["unidad", "anios_gen_comunes", "gen_media_2019_gwh", "gen_media_xm_gwh", "razon_gen", "cap_2019_mw", "cap_xm_media_mw",
         "fc_medio_2019", "fc_medio_xm"]
cols3 = ["unidad", "def_total_2019_ha", "def_total_hansen_ha", "razon_def_total", "r_def_anual_2019_vs_hansen",
         "def_acum2015_2019_pct_area", "def_acum2015_hansen_pct_area", "def_acum2015_hansen_pct_bosque2000"]
cols4 = ["unidad", "lluvia_media_2019_mm", "lluvia_media_chirps_mm", "razon_lluvia", "lluvia_2019_en_2011_2013_mm"]
mp = an[an["muestra_principal"].eq(1)]
with open(OUT / "anexo_comparacion_2019.md", "w", encoding="utf-8") as fh:
    fh.write("# Anexo — comparación con la base de 2019 (centrales comunes)\n\n")
    fh.write(f"Generado por `03_codigo/04_panel/anexo_comparacion_2019.py`. Periodo común {A0}–{A1}. "
             f"{len(an)} centrales con ATCH y base de 2019 ({len(mp)} en la muestra principal). "
             "Solo áreas y variables; sin regresiones ni correlaciones entre deforestación y generación.\n\n")
    fh.write("Resumen (muestra principal, medianas): "
             f"razón de áreas ATCH/2019 {mp['razon_area'].median():.2f}; "
             f"razón de deforestación total Hansen/2019 {mp['razon_def_total'].median():.2f}; "
             f"correlación de la pérdida anual 2019 vs Hansen {mp['r_def_anual_2019_vs_hansen'].median():.2f}; "
             f"razón de lluvia CHIRPS/2019 (sin 2011–2013) {mp['razon_lluvia'].median():.2f}; "
             f"razón de generación XM/2019 {mp['razon_gen'].median():.2f}.\n\n")
    fh.write("## 1. Áreas y tipo\n\n" + md(an[cols1]) + "\n\n")
    fh.write("## 2. Generación y factor de capacidad (años comunes)\n\nFC de 2019 = generación de 2019 / "
             "(capacidad de la tesis de 2019 × 8.760 h); FC nuevo con la capacidad XM de cada año.\n\n" + md(an[cols2]) + "\n\n")
    fh.write("## 3. Deforestación 2001–2015\n\n2019: grilla de 208 m (4,34 ha por celda), acumulado como % del área de la cuenca. "
             "Nuevo: Hansen v1.12 a 30 m dentro del bosque 2000 (treecover2000 ≥ 30 %); se muestra como % del área (comparable) "
             "y como % del bosque 2000 (medida A de 4.5). `r_def_anual` compara la misma variable en las dos fuentes.\n\n"
             + md(an[cols3]) + "\n\n")
    fh.write("## 4. Lluvia media anual 2001–2015 sin 2011–2013\n\nLa última columna muestra la falla de 2019: "
             "en 2011–2013 la lluvia media valía ~11–12 mm.\n\n" + md(an[cols4]) + "\n")
print(f"anexo_comparacion_2019: {len(an)} centrales")
