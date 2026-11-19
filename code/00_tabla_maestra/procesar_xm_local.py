"""
Tesis 2.0 · T2 · Procesa los Excel de XM que Jorge descargó (02_datos/Capacidad y 02_datos/Generacion).

Deja solo los recursos hidráulicos y produce, en 02_datos/xm_procesado/:
    capacidad_hidro_diaria.csv.gz     fecha, recurso, kW (capacidad efectiva neta)
    generacion_hidro_diaria.csv.gz    fecha, recurso, codigo, kWh del día, kWh de la hora máxima
    recursos_hidro.csv                nombre XM ↔ código de recurso, agente, despacho, menor, primer y último día
    cambios_capacidad_xm.csv          recurso, fecha, MW antes, MW después, tipo
    capacidad_anual_xm.csv            recurso × año: capacidad promedio (MW), regla de la sección 4.5
    generacion_anual_xm.csv           recurso × año: GWh
    gen_max_horaria_anual_xm.csv      recurso × año: máximo MWh en una hora (capacidad observada)
    revision_archivos.csv             cobertura de cada archivo (días, recursos, tipos de generación)

Uso (desde 03_tesis):  python3 -m pip install python-calamine pandas
                       python3 03_codigo/00_tabla_maestra/procesar_xm_local.py
"""
from pathlib import Path
import re
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
D = BASE / "02_datos"
OUT = D / "xm_procesado"
OUT.mkdir(exist_ok=True)
CACHE = OUT / "_cache"
CACHE.mkdir(exist_ok=True)


def leer(f):
    """Lee el Excel ubicando la fila de encabezado (la que empieza por 'Fecha')."""
    crudo = pd.read_excel(f, engine="calamine", header=None, nrows=15)
    fila = next(i for i, r in crudo.iterrows() if str(r.iloc[0]).strip().lower() == "fecha")
    df = pd.read_excel(f, engine="calamine", header=fila)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def tipo_col(df):
    return next(c for c in df.columns if c.lower().startswith("tipo de gener") or c.lower().startswith("tipo gener"))


revision = []

# ---------------- Capacidad ----------------
caps = []
for f in sorted((D / "Capacidad").glob("*.xls*")):
    c = CACHE / (f.stem + ".csv.gz")
    if not c.exists():
        df = leer(f)
        tc = tipo_col(df)
        vc = next(col for col in df.columns if "capacidad" in col.lower())
        revision.append(dict(archivo=f.name, filas=len(df), dias=pd.to_datetime(df.Fecha).dt.date.nunique(),
                             desde=pd.to_datetime(df.Fecha).min().date(), hasta=pd.to_datetime(df.Fecha).max().date(),
                             tipos="; ".join(f"{k}={v}" for k, v in df[tc].value_counts().items()),
                             recursos_hidro=df[df[tc] == "HIDRAULICA"].Recurso.nunique()))
        h = df[df[tc] == "HIDRAULICA"]
        h = pd.DataFrame({"fecha": pd.to_datetime(h.Fecha).dt.date, "recurso": h.Recurso.str.strip(),
                          "kw": pd.to_numeric(h[vc], errors="coerce"),
                          "agente": h.get("Código Agente"), "despacho": h.get("Tipo de Despacho"),
                          "menor": h.get("Es Menor")})
        h.to_csv(c, index=False)
        print("cap", f.name, len(h))
    caps.append(pd.read_csv(c, parse_dates=["fecha"]))
cap = pd.concat(caps).drop_duplicates(["fecha", "recurso"]).sort_values(["recurso", "fecha"])
cap[["fecha", "recurso", "kw"]].to_csv(OUT / "capacidad_hidro_diaria.csv.gz", index=False)

# ---------------- Generación ----------------
gens = []
for f in sorted((D / "Generacion").glob("*.xls*")):
    c = CACHE / (f.stem + ".csv.gz")
    if not c.exists():
        df = leer(f)
        tc = tipo_col(df)
        horas = [col for col in df.columns if re.fullmatch(r"\d{1,2}(\.0)?", col)]
        cod = next((col for col in df.columns if col.lower().startswith("código recurso") or col.lower().startswith("codigo recurso")), None)
        revision.append(dict(archivo=f.name, filas=len(df), dias=pd.to_datetime(df.Fecha).dt.date.nunique(),
                             desde=pd.to_datetime(df.Fecha).min().date(), hasta=pd.to_datetime(df.Fecha).max().date(),
                             tipos="; ".join(f"{k}={v}" for k, v in df[tc].value_counts().items()),
                             recursos_hidro=df[df[tc] == "HIDRAULICA"].Recurso.nunique(), horas=len(horas),
                             tiene_codigo=cod is not None))
        h = df[df[tc] == "HIDRAULICA"]
        hv = h[horas].apply(pd.to_numeric, errors="coerce")
        g = pd.DataFrame({"fecha": pd.to_datetime(h.Fecha).dt.date, "recurso": h.Recurso.str.strip(),
                          "codigo": h[cod] if cod else None, "kwh": hv.sum(axis=1, min_count=1),
                          "kwh_hora_max": hv.max(axis=1)})
        g.to_csv(c, index=False)
        print("gen", f.name, len(g))
    gens.append(pd.read_csv(c, parse_dates=["fecha"]))
gen = pd.concat(gens).drop_duplicates(["fecha", "recurso"])
gen.to_csv(OUT / "generacion_hidro_diaria.csv.gz", index=False)

if revision:
    rv = OUT / "revision_archivos.csv"
    old = pd.read_csv(rv) if rv.exists() else pd.DataFrame()
    pd.concat([old, pd.DataFrame(revision)]).drop_duplicates("archivo", keep="last").to_csv(rv, index=False)

# ---------------- Recursos ----------------
cods = (gen.dropna(subset=["codigo"]).groupby("recurso").codigo
        .agg(lambda s: "; ".join(sorted(set(s.astype(str))))))
r_cap = cap.groupby("recurso").agg(agente=("agente", "last"), despacho=("despacho", "last"), menor=("menor", "last"),
                                    cap_desde=("fecha", "min"), cap_hasta=("fecha", "max"), mw_ultimo=("kw", "last"))
r_cap["mw_ultimo"] = r_cap.mw_ultimo / 1000
r_gen = gen.groupby("recurso").agg(gen_desde=("fecha", "min"), gen_hasta=("fecha", "max"))
rec = r_gen.join(r_cap, how="outer").join(cods.rename("codigo"))
rec.to_csv(OUT / "recursos_hidro.csv")

# ---------------- Cambios y anuales ----------------
cap["mw"] = cap.kw / 1000
cap["antes"] = cap.groupby("recurso").mw.shift()
ch = cap[cap.antes.notna() & (cap.mw.round(3) != cap.antes.round(3))].copy()
ch["tipo"] = ch.apply(lambda r: "aumento" if r.mw > r.antes else "reducción", axis=1)
# cambios transitorios (vuelve al valor anterior en menos de 30 días) se marcan aparte
ch = ch.rename(columns={"antes": "mw_antes", "mw": "mw_despues"})
ch[["recurso", "fecha", "mw_antes", "mw_despues", "tipo"]].to_csv(OUT / "cambios_capacidad_xm.csv", index=False)

cap["anio"] = cap.fecha.dt.year
cap.groupby(["recurso", "anio"]).mw.mean().round(3).unstack().to_csv(OUT / "capacidad_anual_xm.csv")
gen["anio"] = gen.fecha.dt.year
gen.groupby(["recurso", "anio"]).kwh.sum().div(1e6).round(3).unstack().to_csv(OUT / "generacion_anual_xm.csv")
gen.groupby(["recurso", "anio"]).kwh_hora_max.max().div(1e3).round(3).unstack().to_csv(OUT / "gen_max_horaria_anual_xm.csv")
print(f"Capacidad {cap.fecha.min().date()}–{cap.fecha.max().date()}; generación {gen.fecha.min().date()}–{gen.fecha.max().date()}")
print(f"Recursos hidráulicos: {len(rec)}; cambios de capacidad: {len(ch)}")
