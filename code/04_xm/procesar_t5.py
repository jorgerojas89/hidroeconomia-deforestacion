"""
Tesis 2.0 · T5 · Procesamiento de datos XM para el panel (T6).

Uso, desde 03_tesis (en el Mac o en el chat):
    python3 03_codigo/03_xm/procesar_t5.py

Funciona con lo que haya: siempre usa los archivos viejos de XM (2000–2018) y la generación
diaria ya procesada; si existen las descargas de descargar_xm_t5.py (02_datos/crudos/xm_t5/),
completa 2019–2024 y compara ambas fuentes en los años que se traslapan.

Salidas en 02_datos/xm_procesado/ (todas con la llave `unidad` de tabla_maestra.csv):
    generacion_mensual_unidad.csv      1. generación y factor de capacidad mensual, todas las unidades
    relacion_rio_unidad.csv            2. qué río(s) y embalse(s) de XM corresponden a cada unidad
    aportes_rio_mensual.csv            2. caudal medio mensual por río XM (m3/s), con fuente
    aportes_rio_diario.csv.gz          2. caudal diario por río XM (solo con descarga de la API)
    aportes_unidad_mensual.csv         2. caudal mensual por unidad (suma de sus ríos)
    volumen_util_embalse_diario.csv.gz 3. volumen útil diario por embalse (m3)
    volumen_util_unidad_mensual.csv    3. volumen útil por unidad (promedio y mínimo del mes)
    capacidad_util_embalse.csv         5. capacidad útil por embalse (m3)
    regulacion_unidad.csv              5. capacidad útil / aporte medio anual
    variabilidad_caudal_unidad_anio.csv 6. variabilidad del caudal por unidad y año
    precio_bolsa_diario.csv / _mensual.csv / _anual.csv   4.
    oni_mensual.csv, oni_anual.csv, ipc_anual.csv          7.
    reporte_qc_t5.md                   reporte de calidad
"""
import re
import unicodedata
from glob import glob
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
D = BASE / "02_datos"
XP = D / "xm_procesado"
TM = D / "tabla_maestra"
OLD = D / "crudos" / "xm_generacion_y_mercado"
RAW = D / "crudos" / "xm_t5"
MACRO = D / "crudos" / "macro"
CU = D / "cuencas_igac"
EE = D / "earth_engine"
A0, A1 = 2000, 2024
SEG_ANIO = 365.25 * 86400

QC = []          # (sección, prueba, estado, detalle)
NOTAS = []       # texto libre para el reporte


def qc(sec, prueba, ok, det=""):
    estado = {True: "OK", False: "REVISAR", None: "PENDIENTE"}[ok]
    QC.append((sec, prueba, estado, str(det)))
    print(f"[{estado}] {sec} · {prueba} {('· ' + str(det)) if det else ''}")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]", "", s)


def col(df, *claves, obligatorio=True):
    for c in df.columns:
        if any(k.lower() in c.lower() for k in claves):
            return c
    if obligatorio:
        raise KeyError(f"No encuentro {claves} en {list(df.columns)}")
    return None


def leer_raw(metrica, entidad):
    fs = sorted(glob(str(RAW / f"{metrica}_{entidad}_*.csv")))
    partes = [pd.read_csv(f) for f in fs]
    partes = [p for p in partes if len(p)]
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def lista_xm(nombre):
    f = RAW / f"{nombre}.csv"
    if not f.exists():
        return {}
    li = pd.read_csv(f)
    c_cod = col(li, "code", "codigo")
    c_nom = col(li, "name", "nombre")
    return dict(zip(li[c_cod].astype(str), li[c_nom].astype(str)))


def diaria_api(metrica, entidad, mapa_nombres):
    """API XM diaria → (entidad_norm, nombre, fecha, valor)."""
    df = leer_raw(metrica, entidad)
    if df.empty:
        return df
    c_cod = col(df, "values_code", "code", "name")
    c_val = next(c for c in df.columns if c.lower() == "value" or c.lower().endswith("_value"))
    c_fec = col(df, "date", "fecha")
    out = pd.DataFrame({
        "codigo": df[c_cod].astype(str),
        "fecha": pd.to_datetime(df[c_fec]).dt.normalize(),
        "valor": pd.to_numeric(df[c_val], errors="coerce"),
    })
    out["nombre"] = out.codigo.map(mapa_nombres).fillna(out.codigo)
    out["clave"] = out.nombre.map(norm)
    return out


tm = pd.read_csv(TM / "tabla_maestra.csv")
MUESTRA = set(tm.loc[tm.muestra_principal == 1, "unidad"])
TIPO = dict(zip(tm.unidad, tm.tipo_propuesto))
sis = pd.read_csv(CU / "sistemas_hidricos.csv")
AREA = dict(zip(sis.unidad, sis.ha_atch))
DENTRO = dict(zip(sis.unidad, sis.dentro_de))

# =====================================================================================
# 1. Generación mensual
# =====================================================================================
print("\n== 1. Generación mensual ==")
gend = pd.read_csv(XP / "generacion_hidro_diaria.csv.gz", parse_dates=["fecha"], usecols=["fecha", "recurso", "kwh"])
capd = pd.read_csv(XP / "capacidad_hidro_diaria.csv.gz", parse_dates=["fecha"])
mapa = pd.read_csv(TM / "unidad_recursos_xm.csv")
pan = pd.read_csv(TM / "panel_xm_unidad_anio.csv")
cap_anual = pan.set_index(["unidad", "anio"]).cap_mw

filas = []
for uid, g in mapa.groupby("unidad"):
    nombres = list(g.recurso_xm)
    gu = gend[gend.recurso.isin(nombres)].groupby("fecha").kwh.sum()
    cu = capd[capd.recurso.isin(nombres)].groupby("fecha").kw.sum() / 1000
    if gu.empty:
        continue
    gm = gu.groupby([gu.index.year, gu.index.month]).agg(["sum", "size"])
    # XM no trae fila los días sin generación: un mes sin registro entre el primero y el último con
    # generación es un mes en 0 (parada), no un dato perdido. Se rellena con 0 y se marca.
    p0, p1 = pd.Period(gu.index.min(), "M"), pd.Period(gu.index.max(), "M")
    todos = pd.MultiIndex.from_tuples([(p.year, p.month) for p in pd.period_range(p0, p1, freq="M")])
    gm = gm.reindex(todos, fill_value=0)
    cm = cu.groupby([cu.index.year, cu.index.month]).agg(["mean", "size"])
    for (a, m), r in gm.iterrows():
        dias_mes = pd.Period(f"{a}-{m:02d}").days_in_month
        if (a, m) in cm.index and cm.loc[(a, m), "size"] >= 15:
            cap, fte = cm.loc[(a, m), "mean"], "XM CEN diaria"
        else:
            cap, fte = cap_anual.get((uid, a), np.nan), "panel anual (cap_mw)"
        mwh = r["sum"] / 1000
        filas.append(dict(unidad=uid, anio=a, mes=m, gen_mwh=mwh, dias_con_registro=int(r["size"]), dias_mes=dias_mes,
                          mes_sin_registro=int(r["size"] == 0),
                          cap_mw=cap, fuente_cap=fte, fc=mwh / (cap * 24 * dias_mes) if cap and cap > 0 else np.nan,
                          muestra_principal=int(uid in MUESTRA)))
genm = pd.DataFrame(filas).sort_values(["unidad", "anio", "mes"])
genm.round(4).to_csv(XP / "generacion_mensual_unidad.csv", index=False, encoding="utf-8-sig")

# QC generación
chk = genm.groupby(["unidad", "anio"]).gen_mwh.sum().div(1000).rename("gwh_mes").reset_index().merge(pan[["unidad", "anio", "gen_gwh"]])
dif = (chk.gwh_mes - chk.gen_gwh).abs()
qc("1 Generación", "suma de meses = generación anual del panel (±0,001 GWh, el panel redondea a 4 decimales)",
   bool((dif.fillna(0) < 1e-3).all()), f"máx. diferencia {dif.max():.5f} GWh")
gm_s = genm[genm.muestra_principal == 1]
sr = gm_s[gm_s.mes_sin_registro == 1].groupby("unidad").size()
qc("1 Generación", "meses sin registro dentro del periodo de operación (0 = parada, decisión de Jorge; marcados en mes_sin_registro: pueden ser ventas fuera del SIN)", sr.empty,
   "; ".join(f"{u}: {n}" for u, n in sr.items()))
fin_u = gm_s.groupby("unidad").anio.max()
qc("1 Generación", f"unidades que generan hasta {A1}", bool((fin_u >= A1).all()),
   "; ".join(f"{u}: último año {a}" for u, a in fin_u[fin_u < A1].items()))
NOTAS.append("Generación: XM no trae fila los días sin generación. `dias_con_registro` < `dias_mes` indica días en 0 "
             f"(paradas o mantenimiento), no datos perdidos: {(gm_s.dias_con_registro < gm_s.dias_mes).sum()} unidad-mes en la muestra.")
n_fc = (gm_s.fc > 1).sum()
qc("1 Generación", "FC mensual > 1 (se conserva, regla 4.5)", n_fc == 0,
   f"{n_fc} unidad-mes con FC>1: " + ", ".join(f"{u} {n}" for u, n in gm_s[gm_s.fc > 1].groupby("unidad").size().items())
   + f"; máx {gm_s.fc.max():.2f}")
qc("1 Generación", "valores negativos", bool((genm.gen_mwh >= 0).all()), f"{(genm.gen_mwh < 0).sum()} negativos")

# =====================================================================================
# 2. Aportes (caudales) por río y relación río → unidad
# =====================================================================================
print("\n== 2. Aportes ==")
# Nombres canónicos de río: el archivo viejo (2018) y la API (ListadoRios) usan nombres distintos.
# clave canónica: [variantes normalizadas]
ALIAS = {"BETANIACP": ["BETANIACP"], "PORCE2CP": ["PORCE2CP"], "PORCE3": ["PORCE3", "PORCEIII"],
         "FAGUACAMPOALEGRESANEUGENIO": ["FAGUACAMPOALEGRESANEUGENIO", "FAGUACAMPOALEGRE", "SANEUGENIO"],
         "URRA": ["URRA", "URRA1", "SINUURRA"], "NARE": ["NARE", "NARECP"], "MIEL": ["MIEL", "MIELI"],
         "GUARINO": ["GUARINO"], "MANSO": ["MANSO"], "GRANDE": ["GRANDE"],
         "BATA": ["BATA"], "BOGOTANR": ["BOGOTANR"], "AMOYA": ["AMOYA"], "SANFRANCISCO": ["SANFRANCISCO"]}
CANON = {v: k for k, vs in ALIAS.items() for v in vs}
# Desvíos que XM publica como "ríos": caudal trasvasado, no el caudal natural del río
DESVIOS = {"DESVGUARINO", "DESVMANSO"}


def canon(nombre):
    k = norm(nombre)
    return CANON.get(k, k)


# 2a. Archivo viejo: caudal medio mensual por río (m3/s), 1934–2017
xo = pd.ExcelFile(OLD / "Caudales_medios_Rios_SIN.XLSX")
viejo = []
for hoja in xo.sheet_names:
    c = pd.read_excel(xo, hoja).dropna(how="all")
    c = c[pd.to_numeric(c.iloc[:, 0], errors="coerce").notna()]
    c = c.melt(id_vars=c.columns[0], var_name="mes_txt", value_name="caudal_m3s")
    c.columns = ["anio", "mes_txt", "caudal_m3s"]
    meses = {m: i + 1 for i, m in enumerate(["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"])}
    c["mes"] = c.mes_txt.str.lower().str[:3].map(meses)
    c["rio"] = hoja
    viejo.append(c[["rio", "anio", "mes", "caudal_m3s"]])
viejo = pd.concat(viejo)
viejo["anio"] = viejo.anio.astype(int)
viejo["caudal_m3s"] = pd.to_numeric(viejo.caudal_m3s, errors="coerce")
viejo["clave"] = viejo.rio.map(canon)
viejo["fuente"] = "XM Caudales_medios_Rios_SIN.XLSX (mensual)"

# 2b. API: diario
rios_api = lista_xm("ListadoRios")
apd = diaria_api("AporCaudal", "Rio", rios_api)
if len(apd):
    apd = apd.rename(columns={"valor": "caudal_m3s", "nombre": "rio"})
    apd["clave"] = apd.rio.map(canon)
    apd[["rio", "clave", "fecha", "caudal_m3s"]].sort_values(["rio", "fecha"]).to_csv(
        XP / "aportes_rio_diario.csv.gz", index=False, compression="gzip")
    apm = (apd.assign(anio=apd.fecha.dt.year, mes=apd.fecha.dt.month)
           .groupby(["rio", "clave", "anio", "mes"]).caudal_m3s.agg(["mean", "size"]).reset_index()
           .rename(columns={"mean": "caudal_m3s", "size": "dias"}))
    apm["fuente"] = "API XM AporCaudal (media de días)"
    qc("2 Aportes", "descarga API AporCaudal", True, f"{apd.rio.nunique()} ríos, {apd.fecha.min().date()} a {apd.fecha.max().date()}")
else:
    apm = pd.DataFrame(columns=["rio", "clave", "anio", "mes", "caudal_m3s", "dias", "fuente"])
    qc("2 Aportes", "descarga API AporCaudal", None, "falta correr descargar_xm_t5.py: solo hay 2000–2017 mensual")

# 2c. Relación río/embalse → unidad. Fuente principal: Rio-planta-embalse.xlsx (XM, 29-ago-2018);
#     para unidades que no están ahí, la tabla maestra o la geometría (cuencas anidadas).
#     Dos listas de ríos por unidad:
#       rios_xm    = los que XM asigna a la planta (aporte propio; en cascadas es solo la cuenca intermedia)
#       rios_total = todos los ríos XM dentro de la ATCH: caudal natural total de la cuenca que se usa
#                    para la deforestación. Es el que se usa en regulación y variabilidad.
#     La suma de aportes naturales no depende de la regulación aguas arriba (XM reporta aportes naturales).
CHINCHINA_4 = ["ESTRELLA", "CAMPOALEGRE", "CHINCHINA", "FAGUACAMPOALEGRE (SAN EUGENIO)"]
GUADALUPE_3 = ["CONCEPCION", "GUADALUPE", "TENCHE"]
X18 = "XM Río-planta-embalse 2018"
REL = {  # unidad: (rios_xm, rios_total, embalses, fuente, nota)
    "BETANIA": (["BETANIA CP"], ["BETANIA CP", "EL QUIMBO"], ["BETANIA"], X18,
                "CP = cuenca propia, sin el río de El Quimbo (escorrentía 0,26 sola, 0,60 con El Quimbo)"),
    "EL QUIMBO": (["EL QUIMBO"], ["EL QUIMBO"], ["EL QUIMBO"], X18, ""),
    "ESMERALDA": (CHINCHINA_4, CHINCHINA_4, [], X18, "suma de 4 ríos"),
    "SAN FRANCISCO": (["SAN FRANCISCO"], ["SAN FRANCISCO"] + CHINCHINA_4, [], X18 + " + ATCH",
                      "total = aporte propio + los 4 ríos de Esmeralda, aguas arriba (escorrentía 0,06 → 0,55)"),
    "GUATAPE": (["NARE"], ["NARE"], ["PENOL"], X18, ""),
    "GUAVIO": (["GUAVIO"], ["GUAVIO"], ["GUAVIO"], X18, ""),
    "LA TASAJERA": (["GRANDE"], ["GRANDE"], ["RIOGRANDE2"], X18, ""),
    "MIEL I": (["MIEL", "DESV. GUARINO", "DESV. MANSO"], ["MIEL", "DESV. GUARINO", "DESV. MANSO"], ["AMANI"], X18 + " + API",
               "Miel + caudal trasvasado de Guarinó (desde dic-2010) y Manso (desde 2013); antes, 0. La ATCH incluye esas áreas todo el periodo"),
    "PORCE II": (["PORCE2CP"], ["PORCE2CP", "GRANDE"], ["PORCE II"], X18 + " + ATCH",
                 "total = cuenca propia + río Grande (Riogrande II dentro de la ATCH); escorrentía 0,33, la más baja"),
    "PORCE III": (["PORCE 3"], ["PORCE 3", "PORCE2CP", "GRANDE"] + GUADALUPE_3, ["PORCE III"], X18 + " + ATCH",
                  "total = aporte propio + Porce II + Grande + Guadalupe (escorrentía 0,07 → 0,41)"),
    "URRA": (["URRA"], ["URRA"], ["URRA1"], X18, ""),
    "GUATRON": (GUADALUPE_3, GUADALUPE_3, ["TRONERAS", "MIRAFLORES"], X18, "suma de 3 ríos"),
    "AMOYA LA ESPERANZA": (["AMOYA"], ["AMOYA"], [], X18, ""),
    "ITUANGO": (["ITUANGO"], ["ITUANGO"], ["ITUANGO"], "por confirmar con ListadoRios (entró en 2022; no está en el archivo 2018)",
                "serie desde el llenado; no cubre 2000–2018"),
    "PORCE III MENOR": (["PORCE 3"], ["PORCE 3", "PORCE2CP", "GRANDE"] + GUADALUPE_3, [], "misma ATCH que Porce III (IGAC)",
                        "filo; misma serie que Porce III"),
    "RIOGRANDE I": (["GRANDE"], ["GRANDE"], [], "ATCH casi igual a La Tasajera (traslape 95–100 %)",
                    "embalse por cadena (Riogrande II, de La Tasajera); misma serie que La Tasajera"),
    "INSULA": ([], ["CHINCHINA", "CAMPOALEGRE"], [], "propuesta por escorrentía; XM no asigna ríos a Ínsula",
               "Validado 18-nov-2026: la ATCH de Ínsula incluye la cuenca alta del Campoalegre (al sur, Risaralda); escorrentía 0,48 dentro del rango de la muestra (0,31–0,75); la serie alternativa Chinchiná + San Eugenio tiene correlación mensual 0,993 y CV intra-anual 0,978 con la elegida"),
}
# Decisión de Jorge (17-nov-2026): las unidades "embalse" sin embalse propio en XM son "embalse por cadena":
# las regula un embalse aguas arriba en la misma cadena. Su medida de regulación es la de ese embalse
# (capacidad útil / aporte medio de su propio río). None = la cadena no tiene embalse registrado en XM.
CADENA = {"RIOGRANDE I": "LA TASAJERA", "RIO GRANDE": "LA TASAJERA", "INSULA": None}
UMBRAL_PROXY = 0.25  # la unidad debe ocupar al menos 25 % de la cuenca de la serie que se le presta

claves_disp = set(viejo.clave) | set(apm.clave)


def claves_de(rio):
    return [canon(rio)]


rel = []
for uid in sorted(MUESTRA):
    if uid in REL:
        propios, rios, embs, fte, nota = REL[uid]
        disp = [r for r in rios if any(c in claves_disp for c in claves_de(r))]
        falt = [r for r in rios if r not in disp]
        asig = "directa" if propios == rios else ("propuesta" if not propios else "cuenca_total")
        rel.append(dict(unidad=uid, tipo=TIPO[uid], asignacion=asig if not falt else ("parcial" if disp else "sin_serie"),
                        rios_xm="; ".join(propios), rios_total="; ".join(rios), embalses_xm="; ".join(embs), unidad_origen=uid,
                        factor_area=1.0, rios_sin_serie="; ".join(falt), fuente=fte, nota=nota))
        continue
    # sin río propio: buscar la cuenca contenedora más cercana que tenga serie
    cont, cadena = DENTRO.get(uid), []
    while isinstance(cont, str) and cont not in REL:
        cadena.append(cont)
        cont = DENTRO.get(cont)
    if isinstance(cont, str):
        frac = AREA[uid] / AREA[cont]
        if frac >= UMBRAL_PROXY:
            _, rios, _, _, _ = REL[cont]
            rel.append(dict(unidad=uid, tipo=TIPO[uid], asignacion="proxy_anidada", rios_xm="", rios_total="; ".join(rios), embalses_xm="",
                            unidad_origen=cont, factor_area=round(frac, 4), rios_sin_serie="",
                            fuente="geometría ATCH (sistemas_hidricos.csv, dentro_de)",
                            nota=f"serie de {cont} escalada por área ({frac:.0%}); no es caudal propio"))
            continue
        nota = f"contenida en {cont} pero es solo el {frac:.1%} de esa cuenca"
    else:
        nota = "ninguna cuenca contenedora con serie XM" + (f" (dentro de {', '.join(cadena)})" if cadena else "")
    rel.append(dict(unidad=uid, tipo=TIPO[uid], asignacion="sin_rio", rios_xm="", rios_total="", embalses_xm="", unidad_origen="",
                    factor_area=np.nan, rios_sin_serie="", fuente="", nota=nota + "; XM no publica aportes de esta planta"))
rel = pd.DataFrame(rel)
rel.to_csv(XP / "relacion_rio_unidad.csv", index=False, encoding="utf-8-sig")
sin = rel[rel.asignacion == "sin_rio"]
qc("2 Aportes", "unidades de la muestra sin río XM", len(sin) == 0,
   f"{len(sin)}: " + ", ".join(f"{u} ({t})" for u, t in zip(sin.unidad, sin.tipo)))
prox = rel[rel.asignacion == "proxy_anidada"]
qc("2 Aportes", "unidades con serie prestada de una cuenca contenedora", len(prox) == 0,
   ", ".join(f"{u} ← {o} ({f:.0%})" for u, o, f in zip(prox.unidad, prox.unidad_origen, prox.factor_area)))
parc = rel[rel.asignacion.isin(["parcial", "sin_serie"])]
qc("2 Aportes", "ríos asignados que no aparecen en los datos", len(parc) == 0,
   "; ".join(f"{u}: {r}" for u, r in zip(parc.unidad, parc.rios_sin_serie)))

# Comparación viejo vs API en los años que se traslapan. Si un río difiere (razón mediana fuera de ±5 % o
# r < 0,95), no se mezclan fuentes: se usa solo la API, para no meter un quiebre artificial en la serie.
DIFIEREN = set()
if len(apm):
    cmp = viejo.merge(apm[["clave", "anio", "mes", "caudal_m3s"]], on=["clave", "anio", "mes"], suffixes=("_viejo", "_api"))
    if len(cmp):
        res = cmp.groupby(["rio", "clave"]).apply(lambda g: pd.Series(dict(
            meses=len(g), razon_mediana=(g.caudal_m3s_api / g.caudal_m3s_viejo).median(),
            correlacion=g.caudal_m3s_api.corr(g.caudal_m3s_viejo)))).reset_index()
        res.round(4).to_csv(XP / "comparacion_aportes_viejo_api.csv", index=False, encoding="utf-8-sig")
        malos = res[(res.razon_mediana - 1).abs().gt(0.05) | res.correlacion.lt(0.95)]
        DIFIEREN = set(malos.clave)
        qc("2 Aportes", "archivo 2000–2017 vs API (razón mediana ±5 %, r ≥ 0,95); los que difieren usan solo la API", malos.empty,
           f"{len(res)} ríos comparados; difieren: " + ", ".join(f"{r_.rio} (razón {r_.razon_mediana:.2f}, r {r_.correlacion:.2f})"
                                                              for r_ in malos.itertuples()) if len(malos) else f"{len(res)} ríos comparados")
    no_cruzan = sorted(set(viejo.clave) - set(apm.clave))
    if no_cruzan:
        NOTAS.append("Ríos del archivo viejo que no están en la API: " + ", ".join(no_cruzan))
else:
    qc("2 Aportes", "archivo 2000–2017 vs API", None, "espera la descarga")

# Serie mensual por río: API si hay; si no, archivo viejo (salvo los ríos que difieren)
base_m = viejo[viejo.anio.between(A0, A1) & ~viejo.clave.isin(DIFIEREN)].copy()
base_m["dias"] = np.nan
if len(apm):
    ya = set(zip(apm.clave, apm.anio, apm.mes))
    base_m = base_m[[(k, a, m) not in ya for k, a, m in zip(base_m.clave, base_m.anio, base_m.mes)]]
# Desvíos (trasvases): antes de que operaran, el caudal desviado es 0
ceros = []
for k in DESVIOS:
    g = apm[apm.clave == k]
    if len(g):
        p0 = pd.Period(f"{g.anio.min()}-{g[g.anio == g.anio.min()].mes.min():02d}", "M")
        for p in pd.period_range(f"{A0}-01", p0 - 1, freq="M"):
            ceros.append(dict(rio=g.rio.iloc[0], clave=k, anio=p.year, mes=p.month, caudal_m3s=0.0, dias=np.nan,
                              fuente="0: el desvío aún no operaba"))
        if len(apd):
            f0 = apd[apd.clave == k].fecha.min()
            fechas = pd.date_range(f"{A0}-01-01", f0 - pd.Timedelta(days=1))
            apd = pd.concat([apd, pd.DataFrame({"rio": g.rio.iloc[0], "clave": k, "fecha": fechas, "caudal_m3s": 0.0})], ignore_index=True)
rios_m = pd.concat([apm, base_m, pd.DataFrame(ceros)], ignore_index=True)[["rio", "clave", "anio", "mes", "caudal_m3s", "dias", "fuente"]]
rios_m.sort_values(["clave", "anio", "mes"]).to_csv(XP / "aportes_rio_mensual.csv", index=False, encoding="utf-8-sig")
hueco = []
for k in sorted({canon(x) for _, r_ in rel.iterrows() if r_.rios_total for x in r_.rios_total.split("; ")}):
    g = rios_m[rios_m.clave == k]
    falt = sorted(set(range(A0, A1 + 1)) - set(g.groupby("anio").size()[lambda x: x == 12].index))
    if falt and g.anio.min() <= A0 + 1:
        hueco.append(f"{k}: {falt[0]}–{falt[-1]} ({len(falt)} años)" if falt == list(range(falt[0], falt[-1] + 1)) else f"{k}: {falt}")
qc("2 Aportes", "ríos de la muestra sin huecos 2000–2024 (los que empiezan después de 2001 no cuentan)", not hueco, "; ".join(hueco))


# Caudal por unidad (mensual; diario si hay API)
def serie_unidad(r, tabla, llaves):
    if r.asignacion in ("sin_rio", "sin_serie") or not r.rios_total:
        return None
    partes = []
    for rio in r.rios_total.split("; "):
        ks = claves_de(rio)
        s = tabla[tabla.clave.isin(ks)].groupby(llaves).caudal_m3s.mean()
        if s.empty:
            return None
        partes.append(s.rename(rio))
    df = pd.concat(partes, axis=1, sort=True)
    return df.sum(axis=1, min_count=df.shape[1]) * (r.factor_area if pd.notna(r.factor_area) else 1)


um = []
for _, r in rel.iterrows():
    s = serie_unidad(r, rios_m, ["anio", "mes"])
    if s is not None:
        um.append(s.rename("caudal_m3s").reset_index().assign(unidad=r.unidad, asignacion=r.asignacion))
aum = pd.concat(um, ignore_index=True) if um else pd.DataFrame(columns=["unidad", "anio", "mes", "caudal_m3s", "asignacion"])
aum = aum[["unidad", "anio", "mes", "caudal_m3s", "asignacion"]].sort_values(["unidad", "anio", "mes"])
aum.round(4).to_csv(XP / "aportes_unidad_mensual.csv", index=False, encoding="utf-8-sig")

ud = []
if len(apd):
    for _, r in rel.iterrows():
        s = serie_unidad(r, apd, ["fecha"])
        if s is not None:
            ud.append(s.rename("caudal_m3s").reset_index().assign(unidad=r.unidad))
aud = pd.concat(ud, ignore_index=True) if ud else pd.DataFrame(columns=["unidad", "fecha", "caudal_m3s"])

# completitud por unidad
cobert = aum.dropna().groupby("unidad").agg(anio_ini=("anio", "min"), anio_fin=("anio", "max"), meses=("mes", "size"))
cobert["meses_esperados"] = (cobert.anio_fin - cobert.anio_ini + 1) * 12
inc = cobert[(cobert.anio_fin < A1) | (cobert.anio_ini > A0) | (cobert.meses < cobert.meses_esperados)]
qc("2 Aportes", f"unidades con serie completa {A0}–{A1}", inc.empty,
   "; ".join(f"{u}: {r.anio_ini}–{r.anio_fin}, {r.meses}/{r.meses_esperados} meses" for u, r in inc.iterrows()))
neg = (rios_m.caudal_m3s < 0).sum()
qc("2 Aportes", "caudales negativos", neg == 0, f"{neg} meses-río negativos (XM calcula algunos aportes por balance)")

# Coeficiente de escorrentía con la lluvia CHIRPS de T4: detecta ríos mal asignados o series de cuenca propia
if (EE / "lluvia_cuenca_anio.csv").exists() and len(aum):
    ll = pd.read_csv(EE / "lluvia_cuenca_anio.csv").groupby("unidad").lluvia_mm.mean()
    qm = aum.dropna().groupby("unidad").caudal_m3s.mean()
    esc = pd.DataFrame({"q_m3s": qm, "area_ha": pd.Series(AREA), "lluvia_mm": ll}).dropna()
    esc["escorrentia_mm"] = esc.q_m3s * SEG_ANIO / (esc.area_ha * 1e4) * 1000
    esc["coef_escorrentia"] = esc.escorrentia_mm / esc.lluvia_mm
    esc.round(3).rename_axis("unidad").to_csv(XP / "escorrentia_unidad.csv", encoding="utf-8-sig")
    raros = esc[~esc.coef_escorrentia.between(0.25, 1.0)]
    qc("2 Aportes", "coeficiente de escorrentía (caudal/área/lluvia) entre 0,25 y 1,0", raros.empty,
       "; ".join(f"{u}: {c:.2f}" for u, c in raros.coef_escorrentia.items()) or f"{len(esc)} unidades")

# =====================================================================================
# 3. Volumen útil por embalse
# =====================================================================================
print("\n== 3. Volumen útil ==")
v = pd.read_excel(OLD / "Volumen_Util_2000_2018.xlsx", header=None, skiprows=5)
v.columns = v.iloc[0]
v = v.iloc[1:].drop(columns=[c for c in v.columns if pd.isna(c)])
v = v.rename(columns={"FECHA (AÑO-MES-DÍA)": "fecha"})
vol_old = v.melt(id_vars="fecha", var_name="embalse", value_name="vol_util_m3")
vol_old["fecha"] = pd.to_datetime(vol_old.fecha, errors="coerce")
vol_old["vol_util_m3"] = pd.to_numeric(vol_old.vol_util_m3, errors="coerce")
vol_old = vol_old.dropna(subset=["fecha"])
vol_old["clave"] = vol_old.embalse.map(norm)
vol_old["fuente"] = "XM Volumen_Util_2000_2018.xlsx"

emb_api = lista_xm("ListadoEmbalses")
vapi = diaria_api("VoluUtilDiarMasa", "Embalse", emb_api)
papi = diaria_api("PorcVoluUtilDiar", "Embalse", emb_api)
capm = diaria_api("CapaUtilDiarMasa", "Embalse", emb_api)
if len(vapi):
    vapi = vapi.rename(columns={"nombre": "embalse", "valor": "vol_api"})
    ov = vol_old.merge(vapi[["clave", "fecha", "vol_api"]], on=["clave", "fecha"])
    if len(ov):
        r_ = (ov.vol_util_m3 / ov.vol_api).replace([np.inf, -np.inf], np.nan).median()
        factor = min([1, 1e3, 1e6], key=lambda f: abs(np.log10(f) - np.log10(r_))) if r_ and r_ > 0 else 1e6
    else:
        factor = 1e6
        NOTAS.append("Volumen útil API sin traslape con el archivo viejo: se asumió que viene en Mm3 (×1e6).")
    vapi["vol_util_m3"] = vapi.vol_api * factor
    vapi["fuente"] = "API XM VoluUtilDiarMasa"
    ya = set(zip(vapi.clave, vapi.fecha))
    vol = pd.concat([vapi[["embalse", "clave", "fecha", "vol_util_m3", "fuente"]],
                     vol_old[[(k, f) not in ya for k, f in zip(vol_old.clave, vol_old.fecha)]]], ignore_index=True)
    if len(ov):
        ov["vol_api_m3"] = ov.vol_api * factor
        cmpv = ov.groupby("embalse").apply(lambda g: pd.Series(dict(
            dias=len(g), razon_mediana=(g.vol_util_m3 / g.vol_api_m3).median(), correlacion=g.vol_util_m3.corr(g.vol_api_m3)))).reset_index()
        cmpv.round(4).to_csv(XP / "comparacion_volumen_viejo_api.csv", index=False, encoding="utf-8-sig")
        malos = cmpv[(cmpv.razon_mediana - 1).abs().gt(0.02) | cmpv.correlacion.lt(0.98)]
        qc("3 Volumen", f"archivo 2000–2018 vs API (factor de unidades {factor:g})", malos.empty,
           f"{len(cmpv)} embalses; difieren: " + ", ".join(malos.embalse) if len(malos) else f"{len(cmpv)} embalses")
else:
    vol = vol_old
    qc("3 Volumen", "descarga API VoluUtilDiarMasa", None, "falta correr descargar_xm_t5.py: solo hay 2000 – ago-2018")
vol.sort_values(["clave", "fecha"]).to_csv(XP / "volumen_util_embalse_diario.csv.gz", index=False, compression="gzip")

# volumen por unidad (suma de sus embalses), mensual
vu = []
for _, r in rel[rel.embalses_xm.astype(bool)].iterrows():
    ks = [norm(e) for e in r.embalses_xm.split("; ")]
    s = vol[vol.clave.isin(ks)].pivot_table(index="fecha", columns="clave", values="vol_util_m3")
    falt = [k for k in ks if k not in s.columns]
    if falt or s.empty:
        NOTAS.append(f"{r.unidad}: embalse(s) sin datos de volumen: {', '.join(falt) or 'todos'}")
        continue
    s = s.sum(axis=1, min_count=len(ks))
    g = s.groupby([s.index.year, s.index.month]).agg(["mean", "min", "size"])
    g.index.names = ["anio", "mes"]
    vu.append(g.reset_index().rename(columns={"mean": "vol_util_m3_prom", "min": "vol_util_m3_min", "size": "dias"}).assign(unidad=r.unidad))
vum = pd.concat(vu, ignore_index=True) if vu else pd.DataFrame()
if len(vum):
    vum = vum[["unidad", "anio", "mes", "vol_util_m3_prom", "vol_util_m3_min", "dias"]]
    vum.to_csv(XP / "volumen_util_unidad_mensual.csv", index=False, encoding="utf-8-sig")
    cob = vum.groupby("unidad").agg(ini=("anio", "min"), fin=("anio", "max"), meses=("mes", "size"))
    qc("3 Volumen", f"embalses de la muestra con volumen {A0}–{A1}", bool((cob.fin >= A1).all()),
       "; ".join(f"{u}: {r.ini}–{r.fin}" for u, r in cob.iterrows()))
    sin_emb = rel[(rel.tipo == "embalse") & ~rel.embalses_xm.astype(bool)].unidad
    NOTAS.append("Embalse por cadena (sin embalse propio en XM; decisión de Jorge, 17-nov): " + ", ".join(sin_emb))
negv = (vol.vol_util_m3 < 0).sum()
neg_emb = vol[vol.vol_util_m3 < 0].groupby("embalse").size()
qc("3 Volumen", "volumen útil negativo (posible: XM mide desde el nivel mínimo técnico; se conservan)", negv == 0,
   f"{negv} días-embalse: " + ", ".join(f"{e} {n}" for e, n in neg_emb.items()))

# =====================================================================================
# 5. Capacidad útil y regulación
# =====================================================================================
print("\n== 5. Regulación ==")
cap_rows = []
for k, g in vol.groupby("clave"):
    nombre = g.embalse.iloc[0]
    est_api = np.nan
    if len(papi):
        p = papi[papi.clave == k][["fecha", "valor"]].rename(columns={"valor": "porc"})
        m = g.merge(p, on="fecha")
        if len(m):
            esc_ = 100 if m.porc.max() > 1.5 else 1
            c = (m.vol_util_m3 / (m.porc / esc_)).replace([np.inf, -np.inf], np.nan)
            est_api = c[m.porc / esc_ > 0.2].median()
    p99 = g.vol_util_m3.quantile(0.99)
    directa = capm[capm.clave == k].valor.median() if len(capm) else np.nan
    if pd.notna(directa) and pd.notna(est_api) and est_api > 0:   # unidades: igualar a m3 con la estimada
        directa *= min([1, 1e3, 1e6], key=lambda f: abs(np.log10(f * directa / est_api)))
    if pd.notna(directa):
        cap, met = directa, "CapaUtilDiarMasa (API, mediana 2000–2024)"
    elif pd.notna(est_api):
        cap, met = est_api, "volumen / % de volumen útil (API)"
    else:
        cap, met = p99, "percentil 99 del volumen útil diario observado"
    cap_rows.append(dict(embalse=nombre, clave=k, cap_util_m3=cap, metodo=met, cap_util_m3_derivada=est_api,
                         p99_observado_m3=p99, anio_ini=g.fecha.dt.year.min(), anio_fin=g.fecha.dt.year.max()))
capu = pd.DataFrame(cap_rows)
capu.to_csv(XP / "capacidad_util_embalse.csv", index=False, encoding="utf-8-sig")
if capu.metodo.str.startswith("percentil").all():
    qc("5 Regulación", "capacidad útil oficial (API)", None, "provisional: percentil 99 del volumen 2000–2018; se reemplaza con la descarga")

CAP = dict(zip(capu.clave, capu.cap_util_m3))
qmed = aum.dropna().groupby("unidad").caudal_m3s.mean()
reg = []
TIPO_REG = {}
for _, r in rel.iterrows():
    fila = dict(unidad=r.unidad, tipo=r.tipo, embalses_xm=r.embalses_xm, asignacion_caudal=r.asignacion)
    if r.tipo == "filo":
        fila.update(tipo_regulacion="filo", regulacion_anios=0.0, regulacion_dias=0.0, nota="filo de agua: sin almacenamiento (0 por definición)")
    elif r.embalses_xm:
        ks = [norm(e) for e in r.embalses_xm.split("; ")]
        cap = sum(CAP.get(k, np.nan) for k in ks)
        q = qmed.get(r.unidad, np.nan)
        anios = cap / (q * SEG_ANIO) if q and q > 0 else np.nan
        fila.update(tipo_regulacion="embalse propio", cap_util_m3=cap, aporte_medio_m3s=q, regulacion_anios=anios,
                    regulacion_dias=anios * 365.25, nota=r.nota if "CP" in str(r.rios_xm) else "")
    else:
        fila.update(tipo_regulacion="embalse por cadena", regulacion_anios=np.nan, regulacion_dias=np.nan,
                    unidad_cadena=CADENA.get(r.unidad),
                    nota=("toma la regulación del embalse de " + CADENA[r.unidad]) if CADENA.get(r.unidad)
                    else "embalse por cadena sin embalse aguas arriba registrado en XM")
    reg.append(fila)
reg = pd.DataFrame(reg)
for i_, f_ in reg[reg.tipo_regulacion == "embalse por cadena"].iterrows():
    if isinstance(f_.unidad_cadena, str):
        src = reg[reg.unidad == f_.unidad_cadena].iloc[0]
        reg.loc[i_, ["cap_util_m3", "aporte_medio_m3s", "regulacion_anios", "regulacion_dias"]] = \
            src[["cap_util_m3", "aporte_medio_m3s", "regulacion_anios", "regulacion_dias"]].values

reg.round(5).to_csv(XP / "regulacion_unidad.csv", index=False, encoding="utf-8-sig")
falta_reg = reg[(reg.tipo == "embalse") & reg.regulacion_anios.isna()]
qc("5 Regulación", "embalses (propios o por cadena) con medida de regulación", falta_reg.empty,
   ", ".join(f"{u} ({t})" for u, t in zip(falta_reg.unidad, falta_reg.tipo_regulacion)))
NOTAS.append("Regulación (decisión de Jorge, 17-nov): se usa solo con los datos de XM ya descargados, como prueba secundaria; "
             "no reemplaza la indicadora de embalse de la especificación 4.5.")
fuera = reg[(reg.regulacion_dias > 3650)]
qc("5 Regulación", "regulación plausible (< 10 años de aporte)", fuera.empty, ", ".join(fuera.unidad))

# =====================================================================================
# 6. Variabilidad del caudal por unidad y año
# =====================================================================================
print("\n== 6. Variabilidad ==")
var = []
for uid, g in aum.dropna().groupby("unidad"):
    for a, ga in g.groupby("anio"):
        f = dict(unidad=uid, anio=a, meses=len(ga), q_media_m3s=ga.caudal_m3s.mean(),
                 cv_mensual=ga.caudal_m3s.std() / ga.caudal_m3s.mean() if ga.caudal_m3s.mean() else np.nan,
                 q_min_mes_rel=ga.caudal_m3s.min() / ga.caudal_m3s.mean() if ga.caudal_m3s.mean() else np.nan,
                 q_max_mes_rel=ga.caudal_m3s.max() / ga.caudal_m3s.mean() if ga.caudal_m3s.mean() else np.nan)
        var.append(f)
var = pd.DataFrame(var)
if len(aud):
    dd = []
    for uid, g in aud.dropna().groupby("unidad"):
        s = g.set_index("fecha").caudal_m3s.sort_index()
        m7 = s.rolling(7, min_periods=7).mean()
        for a, sa in s.groupby(s.index.year):
            mu = sa.mean()
            dd.append(dict(unidad=uid, anio=a, dias=len(sa), cv_diario=sa.std() / mu if mu else np.nan,
                           q_p10_rel=sa.quantile(0.10) / mu if mu else np.nan,   # caudal bajo (excedido 90 % del tiempo)
                           q_p90_rel=sa.quantile(0.90) / mu if mu else np.nan,
                           razon_p90_p10=sa.quantile(0.90) / sa.quantile(0.10) if sa.quantile(0.10) > 0 else np.nan,
                           q7min_rel=m7[m7.index.year == a].min() / mu if mu else np.nan))
    var = var.merge(pd.DataFrame(dd), on=["unidad", "anio"], how="outer")
else:
    qc("6 Variabilidad", "medidas con datos diarios (CV diario, Q7 mínimo, razón p90/p10)", None,
       "solo hay medidas mensuales hasta 2017; las diarias salen con la descarga de la API")
var["completo"] = (var.meses == 12) & (var.get("dias", pd.Series(365, index=var.index)).fillna(365) >= 330)
var = var.merge(rel[["unidad", "tipo", "asignacion"]], on="unidad", how="left")
# Decisión de Jorge (17-nov): la prueba del mecanismo usa solo series de XM (sin estaciones IDEAM).
# Entran las unidades con serie propia de su cuenca; las proxy repiten la serie de otra unidad y no entran.
var["usar_prueba_mecanismo"] = var.asignacion.isin(["directa", "cuenca_total", "propuesta"]).astype(int)
var.round(4).to_csv(XP / "variabilidad_caudal_unidad_anio.csv", index=False, encoding="utf-8-sig")
if len(var):
    indep = rel[~rel.asignacion.isin(["sin_rio", "proxy_anidada"])].drop_duplicates("rios_total")
    NOTAS.append(f"Series de caudal independientes en la muestra: {len(indep)} (de {len(rel)} unidades). "
                 "Comparten serie: Porce III y Porce III Menor; La Tasajera y Riogrande I; las proxy repiten la serie de su contenedora.")

# =====================================================================================
# 4. Precio de bolsa
# =====================================================================================
print("\n== 4. Precio de bolsa ==")
pv = []
for f in sorted(glob(str(OLD / "Precio_de_Bolsa" / "*"))):
    d = pd.read_excel(f, header=None)
    fila_h = d.index[d.iloc[:, 0].astype(str).str.strip().eq("Fecha")][0]
    d = d.iloc[fila_h + 1:]
    fechas = pd.to_datetime(d.iloc[:, 0], errors="coerce")
    horas = d.iloc[:, 1:25].apply(pd.to_numeric, errors="coerce")
    pv.append(pd.DataFrame({"fecha": fechas, "precio_cop_kwh": horas.mean(axis=1), "horas": horas.notna().sum(axis=1)}).dropna(subset=["fecha"]))
pold = pd.concat(pv).assign(fuente="XM Precio_Bolsa_Nacional 2000–2018 (Excel)")
praw = leer_raw("PrecBolsNaci", "Sistema")
if len(praw):
    hcols = [c for c in praw.columns if re.search(r"hour", c, re.I)]
    hh = praw[hcols].apply(pd.to_numeric, errors="coerce")
    papi_ = pd.DataFrame({"fecha": pd.to_datetime(praw[col(praw, "date")]).dt.normalize(),
                          "precio_cop_kwh": hh.mean(axis=1), "horas": hh.notna().sum(axis=1), "fuente": "API XM PrecBolsNaci"})
    ov = pold.merge(papi_, on="fecha", suffixes=("_viejo", "_api"))
    if len(ov):
        dmax = ((ov.precio_cop_kwh_api - ov.precio_cop_kwh_viejo).abs() / ov.precio_cop_kwh_viejo).quantile(0.99)
        qc("4 Precio", "Excel 2000–2018 vs API (percentil 99 de la diferencia diaria < 1 %)", bool(dmax < 0.01), f"{dmax:.4%} en {len(ov)} días")
    precio = pd.concat([papi_, pold[~pold.fecha.isin(papi_.fecha)]], ignore_index=True)
else:
    precio = pold
    qc("4 Precio", "descarga API PrecBolsNaci 2019–2024", None, "falta correr descargar_xm_t5.py: solo hay 2000–2018")
precio = precio.sort_values("fecha")
precio.round({"precio_cop_kwh": 4}).to_csv(XP / "precio_bolsa_diario.csv", index=False, encoding="utf-8-sig")
pm = precio.assign(anio=precio.fecha.dt.year, mes=precio.fecha.dt.month).groupby(["anio", "mes"]).agg(
    precio_cop_kwh=("precio_cop_kwh", "mean"), dias=("fecha", "size")).reset_index()
pm.round(4).to_csv(XP / "precio_bolsa_mensual.csv", index=False, encoding="utf-8-sig")
pa = pm.groupby("anio").agg(precio_cop_kwh=("precio_cop_kwh", "mean"), meses=("mes", "size")).reset_index()
pa.round(4).to_csv(XP / "precio_bolsa_anual.csv", index=False, encoding="utf-8-sig")
falt_p = sorted(set(range(A0, A1 + 1)) - set(pa[pa.meses == 12].anio))
qc("4 Precio", f"años completos {A0}–{A1}", not falt_p, f"faltan: {falt_p}" if falt_p else "")
qc("4 Precio", "días con 24 horas", bool((precio.horas == 24).all()), f"{(precio.horas != 24).sum()} días incompletos")
qc("4 Precio", "precio positivo y < 5.000 $/kWh", bool(precio.precio_cop_kwh.between(0, 5000).all()),
   f"rango {precio.precio_cop_kwh.min():.1f}–{precio.precio_cop_kwh.max():.1f}")

# =====================================================================================
# 7. ONI e IPC
# =====================================================================================
print("\n== 7. ONI e IPC ==")
f_oni = MACRO / "oni_noaa.txt"
if f_oni.exists():
    o = pd.read_csv(f_oni, sep=r"\s+")
    temporada = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6, "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}
    o["mes"] = o.SEAS.map(temporada)
    o = o.rename(columns={"YR": "anio", "ANOM": "oni"})[["anio", "mes", "oni"]]
    o.to_csv(XP / "oni_mensual.csv", index=False)
    oa = o.groupby("anio").agg(oni_prom=("oni", "mean"), meses_nino=("oni", lambda x: (x >= 0.5).sum()),
                               meses_nina=("oni", lambda x: (x <= -0.5).sum())).reset_index()
    oa.round(3).to_csv(XP / "oni_anual.csv", index=False)
    qc("7 ONI/IPC", f"ONI {A0}–{A1}", bool(set(range(A0, A1 + 1)) <= set(oa.anio)), f"{oa.anio.min()}–{oa.anio.max()}")
else:
    qc("7 ONI/IPC", "ONI (NOAA)", None, "falta correr descargar_xm_t5.py")

def leer_ipc_mensual(f):
    """Lee un Excel de IPC (BanRep serie 1.2.5 o anexo del DANE): busca la columna de fecha (AAAAMM, AAAA-MM o
    fecha) y la del número índice (encabezado con 'índice'; si no, la primera numérica creciente > 10)."""
    d = pd.read_excel(f, header=None)
    fechas = None
    for c in d.columns:
        x = d[c].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        fe = pd.to_datetime(x.where(x.str.fullmatch(r"(19|20)\d{4}")), format="%Y%m", errors="coerce")
        if fe.notna().sum() < 100:
            fe = pd.to_datetime(d[c], errors="coerce")
        if fe.notna().sum() >= 100:
            fechas, cfe = fe, c
            break
    if fechas is None:
        return leer_ipc_ancho(d)
    filas_txt = d.astype(str).apply(lambda col: col.str.lower())
    cand = [c for c in d.columns if c != cfe and filas_txt[c].str.contains("ndice").any()]
    cand += [c for c in d.columns if c not in cand and c != cfe]
    for c in cand:
        v = pd.to_numeric(d[c], errors="coerce")
        t = pd.DataFrame({"fecha": fechas, "ipc": v}).dropna().sort_values("fecha")
        if len(t) >= 100 and (t.ipc > 0).all() and t.ipc.is_monotonic_increasing is not None and \
                (t.ipc.diff().dropna() >= -0.05 * t.ipc.shift().dropna()).mean() > 0.95 and t.ipc.iloc[-1] > 10:
            return t
    return None


def leer_ipc_ancho(d):
    """Formato del DANE: una columna con los meses (Enero…Diciembre) y una columna por año."""
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    txt = d.astype(str).apply(lambda c: c.str.strip().str.lower())
    pos = [(i, c) for c in d.columns for i in d.index if txt.at[i, c] == "enero"]
    if not pos:
        return None
    i0, cm = pos[0]
    fila_anios = None
    for i in range(i0 - 1, -1, -1):  # fila de encabezado con años, encima de "Enero"
        anios = pd.to_numeric(d.loc[i], errors="coerce")
        if anios.between(1950, 2100).sum() >= 5:
            fila_anios = anios
            break
    if fila_anios is None:
        return None
    filas = []
    for k, mes in enumerate(meses):
        i = next((j for j in range(i0, min(i0 + 20, len(d))) if txt.at[j, cm] == mes), None)
        if i is None:
            continue
        for c, a in fila_anios.dropna().items():
            if 1950 <= a <= 2100:
                v = pd.to_numeric(d.at[i, c], errors="coerce")
                if pd.notna(v):
                    filas.append(dict(fecha=pd.Timestamp(int(a), k + 1, 1), ipc=float(v)))
    t = pd.DataFrame(filas).sort_values("fecha") if filas else None
    return t if t is not None and len(t) >= 100 else None


ipc = None
for nombre, etiqueta in [("ipc_dane.xlsx", "DANE, Índices – series de empalme (base dic-2018 = 100)"),
                         ("ipc_banrep.xlsx", "Banco de la República, serie 1.2.5 (DANE, base dic-2018)")]:
    f = MACRO / nombre
    if f.exists():
        t = leer_ipc_mensual(f)
        if t is not None:
            t.assign(fuente=etiqueta).to_csv(XP / "ipc_mensual.csv", index=False, encoding="utf-8-sig")
            ipc = t.groupby(t.fecha.dt.year).ipc.mean().rename_axis("anio").reset_index()
            ipc["fuente"] = etiqueta
            break
        NOTAS.append(f"No pude leer {nombre}: revisar el formato")
if ipc is None and (MACRO / "ipc_dane_variacion_anual.csv").exists():
    # Variación anual del IPC (diciembre a diciembre, DANE), cargada a mano por Jorge el 19-nov-2026.
    # Se encadena en un índice de fin de año (dic-1992 = 100); el factor a pesos de 2024 es IPC dic-2024 / IPC dic del año.
    v = pd.read_csv(MACRO / "ipc_dane_variacion_anual.csv").sort_values("anio")
    v["ipc"] = 100 * (1 + v.variacion_anual_pct / 100).cumprod()
    ipc = v[["anio", "ipc"]].assign(fuente="DANE, variación anual del IPC dic-dic (índice de fin de año encadenado)")
if ipc is None and (MACRO / "ipc_bancomundial_anual.csv").exists():
    ipc = pd.read_csv(MACRO / "ipc_bancomundial_anual.csv").assign(fuente="Banco Mundial FP.CPI.TOTL (DANE vía FMI), respaldo")
if ipc is not None:
    ipc = ipc[ipc.anio.between(A0, A1)].copy()
    base = ipc.loc[ipc.anio == ipc.anio.max(), "ipc"].iloc[0]
    ipc[f"factor_a_pesos_{int(ipc.anio.max())}"] = base / ipc.ipc
    ipc.round(5).to_csv(XP / "ipc_anual.csv", index=False, encoding="utf-8-sig")
    oficial = not ipc.fuente.iloc[0].startswith("Banco Mundial")
    qc("7 ONI/IPC", "IPC anual oficial (BanRep o DANE) 2000–2024", bool(set(range(A0, A1 + 1)) <= set(ipc.anio)) and oficial,
       f"fuente: {ipc.fuente.iloc[0]}" + ("" if oficial else " — falta el oficial: correr descargar_xm_t5.py --solo ipc"))
else:
    qc("7 ONI/IPC", "IPC", None, "pon el Excel del DANE o BanRep en 02_datos/crudos/macro/ (ver LEEME_T5.md) o corre la descarga")

# =====================================================================================
# Reporte
# =====================================================================================
q = pd.DataFrame(QC, columns=["seccion", "prueba", "estado", "detalle"])
lin = ["# Reporte de calidad T5 — datos XM", "",
       f"Generado por `03_codigo/03_xm/procesar_t5.py`. Muestra principal: {len(MUESTRA)} unidades "
       f"({sum(TIPO[u] == 'embalse' for u in MUESTRA)} embalse, {sum(TIPO[u] == 'filo' for u in MUESTRA)} filo).", "",
       f"Resumen: {sum(q.estado == 'OK')} OK · {sum(q.estado == 'REVISAR')} para revisar · {sum(q.estado == 'PENDIENTE')} pendientes de descarga", "",
       "| Sección | Prueba | Estado | Detalle |", "|---|---|---|---|"]
lin += [f"| {r.seccion} | {r.prueba} | {r.estado} | {r.detalle.replace('|', '/')} |" for r in q.itertuples()]
lin += ["", "## Relación río → unidad", "",
        "Asignación: `directa` (los ríos que XM asigna a la planta cubren la ATCH); `cuenca_total` (se suman ríos aguas arriba "
        "para cubrir la ATCH); `propuesta` (XM no asigna ríos; elegida por escorrentía, validar); `proxy_anidada` (serie de la "
        "cuenca contenedora escalada por área); `sin_rio`.", "",
        "| Unidad | Tipo | Asignación | Ríos XM de la planta | Ríos usados (cuenca total) | Embalses XM | Nota |", "|---|---|---|---|---|---|---|"]
lin += [f"| {r.unidad} | {r.tipo} | {r.asignacion} | {r.rios_xm} | {r.rios_total} | {r.embalses_xm} | {r.nota} |" for r in rel.itertuples()]
if len(reg):
    lin += ["", "## Regulación (capacidad útil / aporte medio anual)", "", "| Unidad | Tipo | Regulación | Días de aporte almacenables | Nota |", "|---|---|---|---|---|"]
    lin += [f"| {r.unidad} | {r.tipo} | {r.tipo_regulacion} | {'' if pd.isna(r.regulacion_dias) else f'{r.regulacion_dias:.1f}'} | {r.nota} |" for r in reg.itertuples()]
if NOTAS:
    lin += ["", "## Notas", ""] + [f"- {n}" for n in NOTAS]
(XP / "reporte_qc_t5.md").write_text("\n".join(lin) + "\n", encoding="utf-8")
print(f"\nReporte: {XP / 'reporte_qc_t5.md'}")
