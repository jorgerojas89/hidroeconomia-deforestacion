#!/usr/bin/env python3
"""
T6 — Panel de Tesis 2.0 (unidad-año y unidad-mes, 2001–2024).

Une T2 (tabla maestra), T3 (cuencas IGAC), T4 (Earth Engine) y T5 (XM) en:
  02_datos/panel/panel_anual.csv / .parquet
  02_datos/panel/panel_mensual.csv / .parquet
  02_datos/panel/diccionario_datos.csv / .md
  02_datos/panel/conteo_observaciones.csv
  02_datos/panel/reporte_qc_t6.md

REGLA: este script NO calcula correlaciones ni regresiones entre deforestación y
generación. Solo une, marca y revisa calidad. La especificación está fijada (plan, 4.5).

Correr desde cualquier carpeta:  python3 03_codigo/04_panel/construir_panel.py
Requiere pandas; pyarrow para el Parquet (si falta, escribe solo CSV y lo avisa).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]          # 03_tesis
D = BASE / "02_datos"
OUT = D / "panel"
A0, A1 = 2001, 2024
ANIOS = list(range(A0, A1 + 1))

# --------------------------------------------------------------------------------------
# Decisiones de T6 (se fijan sin ver resultados; ver registro de cambios del plan, 4.5)
# --------------------------------------------------------------------------------------
DECISIONES = {
    # Época seca principal para la prueba 4.3.3: "cuenca_4m", "nal_dic_mar" o "PENDIENTE".
    # Las dos definiciones se calculan siempre; esta clave solo dice cuál es la principal.
    "epoca_seca_principal": "cuenca_4m",   # Jorge, 18-nov-2026: robustez con nal_dic_mar
    # Años de operación parcial (entrada a mitad de año, salida de Sonsón en 2022, datos XM
    # que empiezan el 23-ene-2003): "excluir" de la muestra de estimación o "incluir".
    "anios_parciales": "excluir",          # Jorge, 18-nov-2026: robustez con fc_horas_operacion
    # Miel I: "atch_control_trasvase" (ATCH todo el periodo + control de trasvase activo),
    # "atch_solo_marcas" o "excluir_antes_2014". Solo cambia la documentación y los conteos.
    "miel_i": "atch_control_trasvase",       # Jorge, 18-nov-2026: robustez sin Miel I 2001–2013
    # Medida principal de la prueba de caudales 4.3.6 (Jorge, 18-nov-2026)
    "variabilidad_principal": "cv_diario; segunda: q7min_rel; las demás al anexo",
}

ANIOS_NINO = {2009, 2010, 2015, 2016, 2023, 2024}
CADENA_CHINCHINA = {"ESMERALDA", "SAN FRANCISCO", "INSULA", "MUNICIPAL"}
HUECO_CHINCHINA = (2018, 2022)
MIEL = "MIEL I"
GUARINO_DESDE = (2010, 12)   # T5: XM publica DESV. GUARINO desde dic-2010 (primer caudal > 0: ene-2011)
MANSO_DESDE = (2013, 6)      # primer mes con caudal > 0 de DESV. MANSO en la API
SONSON = "SONSON"
SECA_NAL_DIC_MAR = {12, 1, 2, 3}
N_MESES_SECOS_CUENCA = 4


def leer(p: Path, **kw) -> pd.DataFrame:
    return pd.read_csv(p, encoding="utf-8-sig", **kw)


def escribir(df: pd.DataFrame, nombre: str) -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / f"{nombre}.csv", index=False, encoding="utf-8")
    hechos = [f"{nombre}.csv"]
    try:
        df.to_parquet(OUT / f"{nombre}.parquet", index=False)
        hechos.append(f"{nombre}.parquet")
    except Exception as e:  # pyarrow ausente
        print(f"AVISO: no se escribió {nombre}.parquet ({e}). Instala pyarrow: python3 -m pip install pyarrow")
    return hechos


# --------------------------------------------------------------------------------------
# 1. Insumos
# --------------------------------------------------------------------------------------
tm = leer(D / "tabla_maestra/tabla_maestra.csv")
pxm = leer(D / "tabla_maestra/panel_xm_unidad_anio.csv")
sh = leer(D / "cuencas_igac/sistemas_hidricos.csv")
ha = leer(D / "cuencas_igac/hectareas_por_unidad.csv")
cu = leer(D / "cuencas_igac/cuencas_atch_unidad.csv")
de = leer(D / "earth_engine/deforestacion_cuenca_anio.csv")
llm = leer(D / "earth_engine/lluvia_cuenca_mes.csv")
lla = leer(D / "earth_engine/lluvia_cuenca_anio.csv")
X = D / "xm_procesado"
gm = leer(X / "generacion_mensual_unidad.csv")
apm = leer(X / "aportes_unidad_mensual.csv")
vum = leer(X / "volumen_util_unidad_mensual.csv")
reg = leer(X / "regulacion_unidad.csv")
var = leer(X / "variabilidad_caudal_unidad_anio.csv")
pba = leer(X / "precio_bolsa_anual.csv")
pbm = leer(X / "precio_bolsa_mensual.csv")
onia = leer(X / "oni_anual.csv")
onim = leer(X / "oni_mensual.csv")
ipc = leer(X / "ipc_anual.csv")

# --------------------------------------------------------------------------------------
# 2. Atributos fijos por unidad
# --------------------------------------------------------------------------------------
u = tm[["unidad", "nombre", "codigo_xm", "tipo_propuesto", "muestra_principal", "igac_ok", "igac_en_cola",
        "acueducto", "incluir_analisis", "muestra_2019", "fecha_entrada", "inicio_gen_xm", "fin_gen_xm",
        "anio_fin_panel"]].copy()
u = u.rename(columns={"tipo_propuesto": "tipo"})
u["embalse"] = (u["tipo"] == "embalse").astype(int)
u["acueducto"] = (u["acueducto"].astype(str).str.lower() == "sí").astype(int)
u["inicio_gen_xm"] = pd.to_datetime(u["inicio_gen_xm"])
u["fin_gen_xm"] = pd.to_datetime(u["fin_gen_xm"])
u["entrada_real_anterior"] = u["fecha_entrada"].astype(str).str.contains("o antes").astype(int)
u["anio_inicio_xm"] = u["inicio_gen_xm"].dt.year

r = reg[["unidad", "tipo_regulacion", "regulacion_dias", "regulacion_anios", "unidad_cadena"]].copy()
r["embalse_por_cadena"] = (r["tipo_regulacion"] == "embalse por cadena").astype(int)
u = u.merge(r, on="unidad", how="left")
u = u.merge(sh[["unidad", "sistema_geom_A", "sistema_geom_B", "dentro_de"]], on="unidad", how="left")
u = u.merge(cu[["unidad", "radicado", "area_union_ha", "n_proyectos"]].rename(
    columns={"area_union_ha": "ha_atch"}), on="unidad", how="left")
hh = ha[~ha["unidad"].str.startswith("TOTAL")][["unidad", "ha_exclusivas", "ha_compartidas_con_otras", "frac_compartida"]]
u = u.merge(hh, on="unidad", how="left")

# --------------------------------------------------------------------------------------
# 3. Panel anual
# --------------------------------------------------------------------------------------
pa = u[["unidad"]].merge(pd.DataFrame({"anio": ANIOS}), how="cross")
pa = pa.merge(u, on="unidad", how="left")

# 3.1 Operación
ini = pa["inicio_gen_xm"]
pa["antes_inicio_xm"] = (pa["anio"] < pa["anio_inicio_xm"]).astype(int)
pa["despues_fin"] = (pa["anio_fin_panel"].notna() & (pa["anio"] > pa["anio_fin_panel"])).astype(int)
dias_anio = np.where(pd.to_datetime(pa["anio"].astype(str) + "-12-31").dt.is_leap_year, 366, 365)
inicio_op = pd.concat([ini, pd.to_datetime(pa["anio"].astype(str) + "-01-01")], axis=1).max(axis=1)
fin_real = pd.Series(np.where(pa["anio_fin_panel"].notna(), pa["fin_gen_xm"], pd.NaT), index=pa.index)
fin_real = pd.to_datetime(fin_real)
fin_op = pd.concat([fin_real.fillna(pd.Timestamp("2100-01-01")),
                    pd.to_datetime(pa["anio"].astype(str) + "-12-31")], axis=1).min(axis=1)
dias_op = ((fin_op - inicio_op).dt.days + 1).clip(lower=0)
pa["frac_anio_operacion"] = np.where(pa["antes_inicio_xm"].eq(1) | pa["despues_fin"].eq(1), 0.0,
                                     (dias_op / dias_anio).round(4))
pa["anio_parcial"] = ((pa["frac_anio_operacion"] > 0) & (pa["frac_anio_operacion"] < 0.999)).astype(int)

# 3.2 Generación y factor de capacidad (T2, panel XM; capacidad efectiva neta promedio del año)
g = pxm[["unidad", "anio", "gen_gwh", "dias_gen", "cap_mw", "fuente_cap", "fc", "fc_ajustado"]].rename(
    columns={"dias_gen": "dias_con_generacion", "fc_ajustado": "fc_cap_observada"})
pa = pa.merge(g, on=["unidad", "anio"], how="left")
fuera = pa["antes_inicio_xm"].eq(1) | pa["despues_fin"].eq(1)
# Años en operación sin ningún registro (Caracolí 2021–2022): la regla T5-4 (meses sin registro = 0)
# se aplica también al año, para que el panel anual sea la suma del mensual.
gsm = gm.groupby(["unidad", "anio"], as_index=False)["gen_mwh"].sum()
pa = pa.merge(gsm.rename(columns={"gen_mwh": "_gen_mes"}), on=["unidad", "anio"], how="left")
llenar = pa["gen_gwh"].isna() & ~fuera & pa["_gen_mes"].notna()
horas_anio = np.where(pd.to_datetime(pa["anio"].astype(str) + "-12-31").dt.is_leap_year, 8784, 8760)
pa.loc[llenar, "gen_gwh"] = pa.loc[llenar, "_gen_mes"] / 1000
pa.loc[llenar, "fc"] = pa.loc[llenar, "gen_gwh"] * 1000 / (pa.loc[llenar, "cap_mw"] * horas_anio[llenar])
pa.loc[llenar, "fc_cap_observada"] = pa.loc[llenar, "fc"]
pa["gen_anual_desde_mensual"] = llenar.astype(int)
pa = pa.drop(columns="_gen_mes")
for c in ["gen_gwh", "fc", "fc_cap_observada"]:
    pa.loc[fuera, c] = np.nan
pa["cap_retropolada"] = pa["fuente_cap"].astype(str).str.contains("hacia atrás").astype(int)
pa["fc_mayor_1"] = (pa["fc"] > 1).astype(int)
# FC sobre las horas en operación (para la decisión de años parciales; en años completos = fc)
horas_op = pa["frac_anio_operacion"] * dias_anio * 24
pa["fc_horas_operacion"] = np.where(horas_op > 0, pa["gen_gwh"] * 1000 / (pa["cap_mw"] * horas_op), np.nan)

# meses sin registro de generación (T5, decisión 4)
msr = gm.groupby(["unidad", "anio"], as_index=False)["mes_sin_registro"].sum().rename(
    columns={"mes_sin_registro": "n_meses_sin_registro"})
pa = pa.merge(msr, on=["unidad", "anio"], how="left")
pa["n_meses_sin_registro"] = pa["n_meses_sin_registro"].fillna(0).astype(int)
pa["anio_con_mes_sin_registro"] = (pa["n_meses_sin_registro"] > 0).astype(int)

# 3.3 Deforestación (T4) con rezagos y adelantos
dd = de.rename(columns={"area_ha": "area_ee_ha", "perdida_ha": "def_flujo_ha",
                        "perdida_pct_bosque2000": "def_flujo_pct", "perdida_acum_ha": "def_acum_ha",
                        "perdida_acum_pct_bosque2000": "def_acum_pct"}).drop(columns=["codigo_xm"])
dd = dd.sort_values(["unidad", "anio"])
for k in (1, 2, 3):
    s = dd.groupby("unidad")
    for v in ["def_acum_pct", "def_flujo_ha", "def_flujo_pct"]:
        dd[f"{v}_l{k}"] = s[v].shift(k)
        dd[f"{v}_f{k}"] = s[v].shift(-k)
    # acumulado desde 2001: antes de 2001 vale 0 por definición
    dd.loc[dd["anio"] - k < A0, f"def_acum_pct_l{k}"] = 0.0
pa = pa.merge(dd, on=["unidad", "anio"], how="left")

# 3.4 Lluvia anual (T4, CHIRPS v3)
la = lla.rename(columns={"lluvia_media_2001_2024": "lluvia_media_mm", "lluvia_anomalia_pct": "lluvia_anom_pct"})
la["lluvia_anom_mm"] = (la["lluvia_mm"] - la["lluvia_media_mm"]).round(2)
pa = pa.merge(la.drop(columns=["codigo_xm"]), on=["unidad", "anio"], how="left")

# 3.5 Controles y variables de año
pa = pa.merge(onia.rename(columns={"oni_prom": "oni"}), on="anio", how="left")
p = pba.merge(ipc[["anio", "factor_a_pesos_2024"]], on="anio")
p["precio_bolsa_cop2024_kwh"] = (p["precio_cop_kwh"] * p["factor_a_pesos_2024"]).round(4)
pa = pa.merge(p.rename(columns={"precio_cop_kwh": "precio_bolsa_corriente_kwh"})[
    ["anio", "precio_bolsa_corriente_kwh", "factor_a_pesos_2024", "precio_bolsa_cop2024_kwh"]], on="anio", how="left")

# 3.6 Variabilidad del caudal (T5)
vv = var.rename(columns={"completo": "q_anio_completo", "asignacion": "asignacion_caudal",
                         "meses": "q_meses", "dias": "q_dias"}).drop(columns=["tipo"])
vv["q_anio_completo"] = vv["q_anio_completo"].astype(str).str.lower().eq("true").astype(int)
pa = pa.merge(vv, on=["unidad", "anio"], how="left")

# 3.7 Marcas de robustez
pa["anio_nino"] = pa["anio"].isin(ANIOS_NINO).astype(int)
pa["hueco_caudal_chinchina"] = (pa["unidad"].isin(CADENA_CHINCHINA)
                                & pa["anio"].between(*HUECO_CHINCHINA)).astype(int)


def frac_meses_desde(anio: pd.Series, desde: tuple[int, int]) -> pd.Series:
    a0, m0 = desde
    return np.where(anio < a0, 0.0, np.where(anio > a0, 1.0, (12 - m0 + 1) / 12))


es_miel = pa["unidad"].eq(MIEL)
pa["miel_trasvase_guarino"] = np.where(es_miel, frac_meses_desde(pa["anio"], GUARINO_DESDE), 0.0).round(4)
pa["miel_trasvase_manso"] = np.where(es_miel, frac_meses_desde(pa["anio"], MANSO_DESDE), 0.0).round(4)
es_son = pa["unidad"].eq(SONSON)
pa["sonson_sin_generar"] = np.where(es_son, frac_meses_desde(pa["anio"], (2022, 5)), 0.0).round(4)

# 3.8 Observación utilizable en la especificación principal (sin aplicar decisiones pendientes)
base_ok = (pa["muestra_principal"].eq(1) & pa["frac_anio_operacion"].gt(0) & pa["fc"].notna()
           & pa["lluvia_mm"].notna() & pa["sistema_geom_A"].notna())
pa["obs_base_acum"] = (base_ok & pa["def_acum_pct"].notna()).astype(int)
pa["obs_base_flujo"] = (base_ok & pa["def_flujo_pct"].notna()).astype(int)
if DECISIONES["anios_parciales"] == "excluir":
    pa["obs_principal"] = (pa["obs_base_acum"].eq(1) & pa["anio_parcial"].eq(0)).astype(int)
elif DECISIONES["anios_parciales"] == "incluir":
    pa["obs_principal"] = pa["obs_base_acum"]
if DECISIONES["miel_i"] == "excluir_antes_2014" and "obs_principal" in pa:
    pa.loc[es_miel & pa["anio"].lt(2014), "obs_principal"] = 0

orden_a = ["unidad", "anio", "codigo_xm", "nombre", "muestra_principal", "tipo", "embalse", "embalse_por_cadena",
           "unidad_cadena", "tipo_regulacion", "regulacion_dias", "regulacion_anios", "sistema_geom_A",
           "sistema_geom_B", "dentro_de", "radicado", "n_proyectos", "ha_atch", "area_ee_ha", "ha_exclusivas",
           "ha_compartidas_con_otras", "frac_compartida", "bosque2000_ha", "bosque2000_pct_cuenca",
           "gen_gwh", "dias_con_generacion", "cap_mw", "fuente_cap", "cap_retropolada", "fc", "fc_cap_observada",
           "fc_horas_operacion", "gen_anual_desde_mensual", "def_acum_pct", "def_acum_ha", "def_flujo_ha", "def_flujo_pct"]
orden_a += [f"{v}_{s}{k}" for s in ("l", "f") for k in (1, 2, 3) for v in ("def_acum_pct", "def_flujo_ha", "def_flujo_pct")]
orden_a += ["lluvia_mm", "lluvia_media_mm", "lluvia_anom_mm", "lluvia_anom_pct", "oni", "meses_nino", "meses_nina",
            "precio_bolsa_corriente_kwh", "factor_a_pesos_2024", "precio_bolsa_cop2024_kwh",
            "asignacion_caudal", "usar_prueba_mecanismo", "q_anio_completo", "q_meses", "q_dias", "q_media_m3s",
            "cv_mensual", "cv_diario", "q_min_mes_rel", "q_max_mes_rel", "q_p10_rel", "q_p90_rel", "razon_p90_p10",
            "q7min_rel",
            "fc_mayor_1", "n_meses_sin_registro", "anio_con_mes_sin_registro", "anio_nino", "antes_inicio_xm",
            "entrada_real_anterior", "despues_fin", "frac_anio_operacion", "anio_parcial", "hueco_caudal_chinchina",
            "miel_trasvase_guarino", "miel_trasvase_manso", "sonson_sin_generar", "obs_base_acum", "obs_base_flujo"]
if "obs_principal" in pa:
    orden_a.append("obs_principal")
orden_a += ["igac_ok", "igac_en_cola", "acueducto", "incluir_analisis", "muestra_2019", "fecha_entrada",
            "anio_inicio_xm", "anio_fin_panel"]
pa = pa[orden_a].sort_values(["unidad", "anio"]).reset_index(drop=True)

# --------------------------------------------------------------------------------------
# 4. Panel mensual
# --------------------------------------------------------------------------------------
meses = pd.DataFrame([(a, m) for a in ANIOS for m in range(1, 13)], columns=["anio", "mes"])
pm = u[["unidad", "codigo_xm", "muestra_principal", "tipo", "embalse", "embalse_por_cadena", "regulacion_dias",
        "sistema_geom_A", "sistema_geom_B", "inicio_gen_xm", "fin_gen_xm", "anio_fin_panel",
        "entrada_real_anterior"]].merge(meses, how="cross")
fecha = pd.to_datetime(dict(year=pm["anio"], month=pm["mes"], day=1))
pm["antes_inicio_xm"] = (fecha + pd.offsets.MonthEnd(0) < pm["inicio_gen_xm"]).astype(int)
pm["mes_entrada"] = ((pm["inicio_gen_xm"].dt.year == pm["anio"]) & (pm["inicio_gen_xm"].dt.month == pm["mes"])
                     & (pm["inicio_gen_xm"].dt.day > 1)).astype(int)
pm["despues_fin"] = (pm["anio_fin_panel"].notna() & (fecha > pm["fin_gen_xm"])).astype(int)

gg = gm[["unidad", "anio", "mes", "gen_mwh", "dias_con_registro", "dias_mes", "mes_sin_registro", "cap_mw", "fc"]]
pm = pm.merge(gg, on=["unidad", "anio", "mes"], how="left")
fuera_m = pm["antes_inicio_xm"].eq(1) | pm["despues_fin"].eq(1)
pm.loc[fuera_m, ["gen_mwh", "fc"]] = np.nan
pm["dias_mes"] = fecha.dt.days_in_month
pm["mes_sin_registro"] = pm["mes_sin_registro"].fillna(0).astype(int)
pm["fc_mayor_1"] = (pm["fc"] > 1).astype(int)

# lluvia mensual, climatología 2001–2024 y meses secos de cada cuenca
lm = llm[llm["anio"].between(A0, A1)].drop(columns=["codigo_xm"])
clim = lm.groupby(["unidad", "mes"], as_index=False)["lluvia_mm"].mean().rename(columns={"lluvia_mm": "lluvia_clim_mm"})
clim["rango_seco"] = clim.groupby("unidad")["lluvia_clim_mm"].rank(method="first")
clim["seca_cuenca_4m"] = (clim["rango_seco"] <= N_MESES_SECOS_CUENCA).astype(int)
pm = pm.merge(lm, on=["unidad", "anio", "mes"], how="left")
pm = pm.merge(clim[["unidad", "mes", "lluvia_clim_mm", "seca_cuenca_4m"]], on=["unidad", "mes"], how="left")
pm["lluvia_clim_mm"] = pm["lluvia_clim_mm"].round(2)
pm["lluvia_anom_mm"] = (pm["lluvia_mm"] - pm["lluvia_clim_mm"]).round(2)
pm["lluvia_anom_pct"] = (100 * pm["lluvia_anom_mm"] / pm["lluvia_clim_mm"]).round(2)
pm["seca_nal_dic_mar"] = pm["mes"].isin(SECA_NAL_DIC_MAR).astype(int)
if DECISIONES["epoca_seca_principal"] == "cuenca_4m":
    pm["seca_principal"] = pm["seca_cuenca_4m"]
elif DECISIONES["epoca_seca_principal"] == "nal_dic_mar":
    pm["seca_principal"] = pm["seca_nal_dic_mar"]

# deforestación anual (con rezagos) asignada a cada mes de su año
cols_def = ["def_acum_pct", "def_flujo_ha", "def_flujo_pct", "def_acum_pct_l1", "def_flujo_ha_l1", "def_flujo_pct_l1"]
pm = pm.merge(dd[["unidad", "anio"] + cols_def], on=["unidad", "anio"], how="left")

pm = pm.merge(onim, on=["anio", "mes"], how="left")
q = pbm.merge(ipc[["anio", "factor_a_pesos_2024"]], on="anio")
q["precio_bolsa_cop2024_kwh"] = (q["precio_cop_kwh"] * q["factor_a_pesos_2024"]).round(4)
pm = pm.merge(q.rename(columns={"precio_cop_kwh": "precio_bolsa_corriente_kwh"})[
    ["anio", "mes", "precio_bolsa_corriente_kwh", "precio_bolsa_cop2024_kwh"]], on=["anio", "mes"], how="left")
pm = pm.merge(apm.rename(columns={"asignacion": "asignacion_caudal"}), on=["unidad", "anio", "mes"], how="left")
pm = pm.merge(vum[["unidad", "anio", "mes", "vol_util_m3_prom"]], on=["unidad", "anio", "mes"], how="left")

ym = pm["anio"] * 100 + pm["mes"]
pm["anio_nino"] = pm["anio"].isin(ANIOS_NINO).astype(int)
pm["hueco_caudal_chinchina"] = (pm["unidad"].isin(CADENA_CHINCHINA) & pm["anio"].between(*HUECO_CHINCHINA)).astype(int)
pm["miel_trasvase_guarino"] = (pm["unidad"].eq(MIEL) & (ym >= GUARINO_DESDE[0] * 100 + GUARINO_DESDE[1])).astype(int)
pm["miel_trasvase_manso"] = (pm["unidad"].eq(MIEL) & (ym >= MANSO_DESDE[0] * 100 + MANSO_DESDE[1])).astype(int)
pm["sonson_sin_generar"] = (pm["unidad"].eq(SONSON) & (ym >= 202205)).astype(int)
pm["obs_base_mes"] = (pm["muestra_principal"].eq(1) & pm["fc"].notna() & pm["lluvia_mm"].notna()
                      & pm["def_acum_pct"].notna() & pm["sistema_geom_A"].notna()
                      & pm["antes_inicio_xm"].eq(0) & pm["despues_fin"].eq(0)).astype(int)
# muestra de estimación mensual: sin el mes de entrada parcial (análogo a la decisión de años parciales)
pm["obs_principal_mes"] = (pm["obs_base_mes"].eq(1) & (pm["mes_entrada"].eq(0)
                           if DECISIONES["anios_parciales"] == "excluir" else True)).astype(int)

orden_m = ["unidad", "anio", "mes", "codigo_xm", "muestra_principal", "tipo", "embalse", "embalse_por_cadena",
           "regulacion_dias", "sistema_geom_A", "sistema_geom_B", "gen_mwh", "dias_con_registro", "dias_mes",
           "cap_mw", "fc", "lluvia_mm", "lluvia_clim_mm", "lluvia_anom_mm", "lluvia_anom_pct",
           "seca_cuenca_4m", "seca_nal_dic_mar"] + (["seca_principal"] if "seca_principal" in pm else []) + cols_def + [
           "oni", "precio_bolsa_corriente_kwh", "precio_bolsa_cop2024_kwh", "caudal_m3s", "asignacion_caudal",
           "vol_util_m3_prom", "fc_mayor_1", "mes_sin_registro", "anio_nino", "antes_inicio_xm",
           "entrada_real_anterior", "mes_entrada", "despues_fin", "hueco_caudal_chinchina",
           "miel_trasvase_guarino", "miel_trasvase_manso", "sonson_sin_generar", "obs_base_mes", "obs_principal_mes"]
pm = pm[orden_m].sort_values(["unidad", "anio", "mes"]).reset_index(drop=True)

# --------------------------------------------------------------------------------------
# 5. Diccionario de datos
# --------------------------------------------------------------------------------------
TM, SH, HA, CU = ("02_datos/tabla_maestra/tabla_maestra.csv", "02_datos/cuencas_igac/sistemas_hidricos.csv",
                  "02_datos/cuencas_igac/hectareas_por_unidad.csv", "02_datos/cuencas_igac/cuencas_atch_unidad.csv")
PX, DE = "02_datos/tabla_maestra/panel_xm_unidad_anio.csv", "02_datos/earth_engine/deforestacion_cuenca_anio.csv"
LA, LM = "02_datos/earth_engine/lluvia_cuenca_anio.csv", "02_datos/earth_engine/lluvia_cuenca_mes.csv"
GM, RG = "02_datos/xm_procesado/generacion_mensual_unidad.csv", "02_datos/xm_procesado/regulacion_unidad.csv"
VA = "02_datos/xm_procesado/variabilidad_caudal_unidad_anio.csv"
PB, PBM, IPC = ("02_datos/xm_procesado/precio_bolsa_anual.csv", "02_datos/xm_procesado/precio_bolsa_mensual.csv",
                "02_datos/xm_procesado/ipc_anual.csv")
ONA, ONM = "02_datos/xm_procesado/oni_anual.csv", "02_datos/xm_procesado/oni_mensual.csv"
AP, VU = "02_datos/xm_procesado/aportes_unidad_mensual.csv", "02_datos/xm_procesado/volumen_util_unidad_mensual.csv"
F_XM, F_H, F_C = "XM (Sinergox / API XM)", "Hansen et al. GFC v1.12 (Earth Engine)", "CHIRPS v3 diario (Earth Engine)"
F_IG, F_T6 = "IGAC, certificados de delimitación TSE (ATCH)", "Construida en T6"

dic = [
    # llaves y atributos
    ("unidad", "Unidad de análisis: central o grupo de centrales que XM reporta juntas", "texto", "Tabla maestra (T2)", TM, "ambos"),
    ("anio", "Año calendario", "año", "—", "—", "ambos"),
    ("mes", "Mes calendario", "1–12", "—", "—", "mensual"),
    ("codigo_xm", "Código de recurso de XM", "texto", F_XM, TM, "ambos"),
    ("nombre", "Nombre de la central", "texto", "Tabla maestra (T2)", TM, "anual"),
    ("muestra_principal", "1 si la unidad está en la muestra principal (IGAC ok, sin acueducto)", "0/1", "Tabla maestra (T2)", TM, "ambos"),
    ("tipo", "Tipo de central: embalse o filo (incluye embalse por cadena)", "texto", "Tabla maestra (T2), decisiones de Jorge", TM, "ambos"),
    ("embalse", "Indicadora de embalse (propio o por cadena); 0 = filo de agua. Variable de la especificación 4.5", "0/1", "Tabla maestra (T2)", TM, "ambos"),
    ("embalse_por_cadena", "1 si es embalse porque la regula un embalse aguas arriba de su cadena (Riogrande I, Río Grande, Ínsula; decisión T5-3)", "0/1", F_XM + "; decisión de Jorge", RG, "ambos"),
    ("unidad_cadena", "Unidad cuyo embalse regula a la unidad por cadena", "texto", F_XM, RG, "anual"),
    ("tipo_regulacion", "filo, embalse propio o embalse por cadena", "texto", F_XM, RG, "anual"),
    ("regulacion_dias", "Regulación continua: capacidad útil del embalse / aporte medio, en días de aporte almacenables. 0 en filo; vacío en Ínsula (cadena sin embalse en XM). Prueba secundaria (decisión T5-1)", "días", F_XM + " (CapaUtilDiarMasa, AporCaudal)", RG, "ambos"),
    ("regulacion_anios", "Igual que regulacion_dias, en años", "años", F_XM, RG, "anual"),
    ("sistema_geom_A", "Sistema hídrico, variante A (10 sistemas): agrupación de errores de la especificación principal", "texto", "IGAC ATCH, análisis T3", SH, "ambos"),
    ("sistema_geom_B", "Sistema hídrico, variante B (14 sistemas): verificación (4.3.9)", "texto", "IGAC ATCH, análisis T3", SH, "ambos"),
    ("dentro_de", "Unidad cuya ATCH contiene a esta (cuencas anidadas)", "texto", "IGAC ATCH, análisis T3", SH, "anual"),
    ("radicado", "Radicado del certificado IGAC de la cuenca", "texto", F_IG, CU, "anual"),
    ("n_proyectos", "Número de proyectos IGAC unidos en la unidad", "conteo", F_IG, CU, "anual"),
    ("ha_atch", "Área de la cuenca ATCH (unión de proyectos)", "ha", F_IG, CU, "anual"),
    ("area_ee_ha", "Área de la cuenca medida en Earth Engine (área real de píxel)", "ha", F_H, DE, "anual"),
    ("ha_exclusivas", "Hectáreas de la ATCH que no comparte con otra unidad de la muestra (valoración sin doble conteo)", "ha", "Análisis T3", HA, "anual"),
    ("ha_compartidas_con_otras", "Hectáreas de la ATCH compartidas con otras unidades de la muestra", "ha", "Análisis T3", HA, "anual"),
    ("frac_compartida", "Fracción de la ATCH compartida", "0–1", "Análisis T3", HA, "anual"),
    ("bosque2000_ha", "Bosque en 2000 dentro de la cuenca (treecover2000 ≥ 30 %)", "ha", F_H, DE, "anual"),
    ("bosque2000_pct_cuenca", "Bosque 2000 como % del área de la cuenca", "%", F_H, DE, "anual"),
    # generación
    ("gen_gwh", "Generación anual (vacía antes del inicio en XM y después de la salida)", "GWh", F_XM, PX, "anual"),
    ("gen_mwh", "Generación mensual (0 en meses sin registro dentro de la operación, decisión T5-4)", "MWh", F_XM, GM, "mensual"),
    ("dias_con_generacion", "Días del año con registro de generación", "días", F_XM, PX, "anual"),
    ("dias_con_registro", "Días del mes con registro de generación", "días", F_XM, GM, "mensual"),
    ("dias_mes", "Días del mes", "días", "—", "—", "mensual"),
    ("cap_mw", "Capacidad efectiva neta declarada en XM, promedio del periodo", "MW", F_XM, PX + " / " + GM, "ambos"),
    ("fuente_cap", "Origen del dato de capacidad (diaria XM o primer valor de 2007 hacia atrás)", "texto", F_XM, PX, "anual"),
    ("cap_retropolada", "1 si la capacidad del año es el primer valor de XM (2007) llevado hacia atrás", "0/1", F_T6, PX, "anual"),
    ("fc", "Factor de capacidad = generación / (capacidad × horas del periodo). Variable dependiente de 4.5. Se conserva si pasa de 1", "fracción", F_XM, PX + " / " + GM, "ambos"),
    ("fc_cap_observada", "FC con la capacidad observada (percentil 99 de la generación horaria) cuando supera la declarada. Solo referencia", "fracción", F_XM, PX, "anual"),
    ("gen_anual_desde_mensual", "1 si XM no tiene registro en todo el año y la generación anual se tomó como la suma mensual (0), regla T5-4 (Caracolí 2021–2022)", "0/1", F_T6, GM, "anual"),
    ("fc_horas_operacion", "FC calculado sobre las horas en operación del año (igual a fc en años completos). Para años parciales", "fracción", F_T6, PX, "anual"),
    # deforestación
    ("def_acum_pct", "Medida A: pérdida de bosque acumulada 2001–t como % del bosque de 2000 de la cuenca", "% del bosque 2000", F_H, DE, "ambos"),
    ("def_acum_ha", "Pérdida de bosque acumulada 2001–t", "ha", F_H, DE, "anual"),
    ("def_flujo_ha", "Medida B: pérdida de bosque en el año t", "ha", F_H, DE, "ambos"),
    ("def_flujo_pct", "Medida B: pérdida de bosque en el año t como % del bosque de 2000", "% del bosque 2000", F_H, DE, "ambos"),
]
for k in (1, 2, 3):
    dic += [
        (f"def_acum_pct_l{k}", f"Rezago {k}: def_acum_pct del año t−{k} (0 si t−{k} < 2001, por definición del acumulado)", "% del bosque 2000", F_H, DE, "ambos" if k == 1 else "anual"),
        (f"def_flujo_ha_l{k}", f"Rezago {k}: def_flujo_ha del año t−{k} (vacío si t−{k} < 2001)", "ha", F_H, DE, "ambos" if k == 1 else "anual"),
        (f"def_flujo_pct_l{k}", f"Rezago {k}: def_flujo_pct del año t−{k} (vacío si t−{k} < 2001)", "% del bosque 2000", F_H, DE, "ambos" if k == 1 else "anual"),
    ]
for k in (1, 2, 3):
    dic += [
        (f"def_acum_pct_f{k}", f"Adelanto {k} (placebo 4.3.4): def_acum_pct del año t+{k} (vacío si t+{k} > 2024)", "% del bosque 2000", F_H, DE, "anual"),
        (f"def_flujo_ha_f{k}", f"Adelanto {k} (placebo): def_flujo_ha del año t+{k}", "ha", F_H, DE, "anual"),
        (f"def_flujo_pct_f{k}", f"Adelanto {k} (placebo): def_flujo_pct del año t+{k}", "% del bosque 2000", F_H, DE, "anual"),
    ]
dic += [
    # lluvia
    ("lluvia_mm", "Precipitación promedio de la cuenca (anual o mensual)", "mm", F_C, LA + " / " + LM, "ambos"),
    ("lluvia_media_mm", "Media anual 2001–2024 de la cuenca", "mm", F_C, LA, "anual"),
    ("lluvia_anom_mm", "Anomalía: lluvia − media 2001–2024 (anual) o − climatología del mes (mensual)", "mm", F_C + "; T6", LA + " / " + LM, "ambos"),
    ("lluvia_anom_pct", "Anomalía en % de la media (anual) o de la climatología del mes (mensual)", "%", F_C + "; T6", LA + " / " + LM, "ambos"),
    ("lluvia_clim_mm", "Climatología mensual de la cuenca: media 2001–2024 del mes", "mm", F_C + "; T6", LM, "mensual"),
    ("seca_cuenca_4m", "Época seca propia de la cuenca: los 4 meses de menor lluvia en la climatología 2001–2024 (CHIRPS)", "0/1", F_C + "; T6", LM, "mensual"),
    ("seca_nal_dic_mar", "Época seca nacional fija: diciembre a marzo", "0/1", F_T6, "—", "mensual"),
    ("seca_principal", "Época seca principal de la prueba 4.3.3 = seca_cuenca_4m (decisión T6, 18-nov); robustez: seca_nal_dic_mar", "0/1", F_T6, LM, "mensual"),
    # controles
    ("oni", "Índice ONI (El Niño 3.4): promedio del año (anual) o valor del trimestre centrado en el mes (mensual)", "°C", "NOAA CPC", ONA + " / " + ONM, "ambos"),
    ("meses_nino", "Meses del año con ONI ≥ 0,5", "meses", "NOAA CPC", ONA, "anual"),
    ("meses_nina", "Meses del año con ONI ≤ −0,5", "meses", "NOAA CPC", ONA, "anual"),
    ("precio_bolsa_corriente_kwh", "Precio de bolsa nacional promedio (pesos corrientes)", "COP/kWh", F_XM + " (PrecBolsNaci)", PB + " / " + PBM, "ambos"),
    ("factor_a_pesos_2024", "Factor IPC para llevar a pesos de 2024 (IPC 2024 / IPC del año)", "factor", "Banco Mundial FP.CPI.TOTL (DANE vía FMI), respaldo", IPC, "anual"),
    ("precio_bolsa_cop2024_kwh", "Precio de bolsa en pesos constantes de 2024. Sale del modelo principal (efectos fijos de año); sirve para la valoración", "COP de 2024/kWh", F_XM + "; IPC", PB + " / " + PBM + " / " + IPC, "ambos"),
    # caudales
    ("caudal_m3s", "Caudal medio mensual de la unidad (aportes XM; ver asignación)", "m³/s", F_XM + " (AporCaudal)", AP, "mensual"),
    ("asignacion_caudal", "Cómo se asignó el caudal: directa, cuenca_total, propuesta, proxy_anidada", "texto", "T5", AP + " / " + VA, "ambos"),
    ("vol_util_m3_prom", "Volumen útil promedio del mes de los embalses de la unidad", "m³", F_XM + " (VoluUtilDiarMasa)", VU, "mensual"),
    ("usar_prueba_mecanismo", "1 si la serie de caudal de la unidad entra a la prueba 4.3.6 (T5)", "0/1", "T5", VA, "anual"),
    ("q_anio_completo", "1 si el año de caudal tiene los 12 meses", "0/1", "T5", VA, "anual"),
    ("q_meses", "Meses con caudal en el año", "meses", "T5", VA, "anual"),
    ("q_dias", "Días con caudal en el año", "días", "T5", VA, "anual"),
    ("q_media_m3s", "Caudal medio anual", "m³/s", F_XM, VA, "anual"),
    ("cv_mensual", "Coeficiente de variación de los caudales mensuales del año", "adimensional", "T5", VA, "anual"),
    ("cv_diario", "Coeficiente de variación de los caudales diarios del año. Medida principal de la prueba 4.3.6 (decisión T6, 18-nov)", "adimensional", "T5", VA, "anual"),
    ("q_min_mes_rel", "Caudal del mes más bajo / caudal medio del año", "razón", "T5", VA, "anual"),
    ("q_max_mes_rel", "Caudal del mes más alto / caudal medio del año", "razón", "T5", VA, "anual"),
    ("q_p10_rel", "Percentil 10 del caudal diario / media del año", "razón", "T5", VA, "anual"),
    ("q_p90_rel", "Percentil 90 del caudal diario / media del año", "razón", "T5", VA, "anual"),
    ("razon_p90_p10", "Percentil 90 / percentil 10 del caudal diario", "razón", "T5", VA, "anual"),
    ("q7min_rel", "Mínimo de la media móvil de 7 días / media del año (caudal base). Segunda medida de la prueba 4.3.6 (decisión T6, 18-nov)", "razón", "T5", VA, "anual"),
    # marcas
    ("fc_mayor_1", "1 si el FC pasa de 1 (se conserva; robustez 4.3.8 sin esas observaciones)", "0/1", F_T6, PX + " / " + GM, "ambos"),
    ("mes_sin_registro", "1 si el mes no tiene registro de generación en XM y se tomó como 0 (decisión T5-4; robustez que los excluye)", "0/1", "T5", GM, "mensual"),
    ("n_meses_sin_registro", "Meses del año con mes_sin_registro = 1", "meses", "T5", GM, "anual"),
    ("anio_con_mes_sin_registro", "1 si el año tiene al menos un mes sin registro", "0/1", F_T6, GM, "anual"),
    ("anio_nino", "1 en 2009–2010, 2015–2016 y 2023–2024 (robustez 4.3.5)", "0/1", "Plan 4.3.5", "—", "ambos"),
    ("antes_inicio_xm", "1 antes del primer registro de generación en XM (antes de la entrada en operación; si entrada_real_anterior = 1, XM aún no reportaba la planta)", "0/1", F_XM, TM, "ambos"),
    ("entrada_real_anterior", "1 si la fecha de entrada es 'o antes': la planta operaba antes de que XM la reportara", "0/1", "Tabla maestra (T2)", TM, "ambos"),
    ("despues_fin", "1 después de la última generación en XM de una unidad que salió del panel (Sonsón desde 2023)", "0/1", "Tabla maestra (T2)", TM, "ambos"),
    ("frac_anio_operacion", "Fracción del año entre el inicio en XM y la salida", "0–1", F_T6, TM, "anual"),
    ("anio_parcial", "1 si la unidad operó (o XM la reportó) solo parte del año: año de entrada, Sonsón 2022, 2003 de Caracolí, Riofrío y Sonsón", "0/1", F_T6, TM, "anual"),
    ("mes_entrada", "1 en el mes de entrada si empezó después del día 1", "0/1", F_T6, TM, "mensual"),
    ("hueco_caudal_chinchina", "1 en Esmeralda, San Francisco, Ínsula y Municipal 2018–2022: XM sin caudales de la cadena (generación sí hay)", "0/1", "T5", AP, "ambos"),
    ("miel_trasvase_guarino", "Miel I: trasvase Guarinó activo (desde dic-2010). Anual: fracción del año; mensual: 0/1. 0 en las demás unidades. Control en todas las especificaciones (decisión T6, 18-nov)", "0–1", "T5 (DESV. GUARINO en XM)", AP, "ambos"),
    ("miel_trasvase_manso", "Miel I: trasvase Manso activo (desde jun-2013, primer caudal en XM). Anual: fracción del año; mensual: 0/1. Control en todas las especificaciones (decisión T6, 18-nov)", "0–1", "T5 (DESV. MANSO en XM)", AP, "ambos"),
    ("sonson_sin_generar", "Sonsón sin generación desde mayo de 2022 (último registro: 26-abr-2022). Anual: fracción del año", "0–1", F_XM, GM, "ambos"),
    ("obs_base_acum", "1 si la unidad-año es de la muestra principal, opera y tiene FC, def_acum_pct, lluvia y sistema A", "0/1", F_T6, "—", "anual"),
    ("obs_base_flujo", "Igual que obs_base_acum con def_flujo_pct", "0/1", F_T6, "—", "anual"),
    ("obs_principal", "Observación de la estimación principal tras las decisiones de T6 (años parciales, Miel I)", "0/1", F_T6, "—", "anual"),
    ("obs_principal_mes", "Unidad-mes de la estimación mensual (época seca): obs_base_mes sin el mes de entrada parcial", "0/1", F_T6, "—", "mensual"),
    ("obs_base_mes", "1 si la unidad-mes es de la muestra principal, opera y tiene FC, lluvia, deforestación y sistema A", "0/1", F_T6, "—", "mensual"),
    ("igac_ok", "1 si la delimitación IGAC está en estado ok", "0/1", F_IG, TM, "anual"),
    ("igac_en_cola", "1 si la delimitación está en revisión (Rev)", "0/1", F_IG, TM, "anual"),
    ("acueducto", "1 si es planta de acueducto (excluida)", "0/1", "Tabla maestra (T2)", TM, "anual"),
    ("incluir_analisis", "Marca de inclusión de la tabla maestra", "0/1", "Tabla maestra (T2)", TM, "anual"),
    ("muestra_2019", "1 si la central estaba en la muestra de 2019", "0/1", "Tabla maestra (T2)", TM, "anual"),
    ("fecha_entrada", "Fecha de entrada (inicio de generación en XM; 'o antes' si XM no la reportaba antes)", "texto", "Tabla maestra (T2)", TM, "anual"),
    ("anio_inicio_xm", "Año del primer registro de generación en XM", "año", F_XM, TM, "anual"),
    ("anio_fin_panel", "Último año en el panel para unidades que salieron (Sonsón 2022)", "año", "Tabla maestra (T2)", TM, "anual"),
]
dicc = pd.DataFrame(dic, columns=["variable", "definicion", "unidad_medida", "fuente", "archivo_origen", "panel"])
dicc = dicc[dicc["variable"].isin(set(pa.columns) | set(pm.columns))]
faltan = (set(pa.columns) | set(pm.columns)) - set(dicc["variable"])
assert not faltan, f"variables sin diccionario: {faltan}"

# --------------------------------------------------------------------------------------
# 6. Conteo de observaciones por especificación (sin estimar)
# --------------------------------------------------------------------------------------
mp = pa[pa["muestra_principal"].eq(1)]


def conteo(nombre: str, mask: pd.Series, df: pd.DataFrame = mp, nota: str = "") -> dict:
    s = df[mask]
    return {"especificacion": nombre, "obs": len(s), "unidades": s["unidad"].nunique(),
            "unidades_embalse": s.loc[s["embalse"].eq(1), "unidad"].nunique(),
            "unidades_filo": s.loc[s["embalse"].eq(0), "unidad"].nunique(),
            "sistemas_A": s["sistema_geom_A"].nunique(), "sistemas_B": s["sistema_geom_B"].nunique(), "nota": nota}


b, bf = mp["obs_base_acum"].eq(1), mp["obs_base_flujo"].eq(1)
pr = mp["obs_principal"].eq(1)
lag3a = pr & mp[["def_acum_pct_l1", "def_acum_pct_l2", "def_acum_pct_l3"]].notna().all(axis=1)
lag3f = pr & mp[["def_flujo_pct_l1", "def_flujo_pct_l2", "def_flujo_pct_l3"]].notna().all(axis=1)
lead3a = pr & mp[["def_acum_pct_f1", "def_acum_pct_f2", "def_acum_pct_f3"]].notna().all(axis=1)
lead1a = pr & mp["def_acum_pct_f1"].notna()
filas = [
    conteo("Base, medida A (acumulado)", b, nota="todas las unidad-año en operación con datos, incluidos años parciales"),
    conteo("Base, medida B (flujo)", bf),
    conteo("Principal A, muestra de estimación (obs_principal)", mp["obs_principal"].eq(1), nota="sin años parciales (decisión T6, 18-nov)"),
    conteo("Principal B, muestra de estimación", mp["obs_principal"].eq(1) & mp["def_flujo_pct"].notna()),
    conteo("Robustez: con años parciales (fc_horas_operacion)", b),
    conteo("Robustez: sin Miel I 2001–2013", mp["obs_principal"].eq(1) & ~(mp["unidad"].eq(MIEL) & mp["anio"].lt(2014))),
    conteo("Rezagos 1–3, medida A", lag3a),
    conteo("Rezagos 1–3, medida B", lag3f, nota="pierde 2001–2003"),
    conteo("Placebo adelanto 1, medida A", lead1a, nota="pierde 2024"),
    conteo("Placebo adelantos 1–3, medida A", lead3a, nota="pierde 2022–2024"),
    conteo("Sin años de El Niño (4.3.5)", pr & mp["anio_nino"].eq(0)),
    conteo("Sin FC > 1 (4.3.8)", pr & mp["fc_mayor_1"].eq(0)),
    conteo("Sin años con meses sin registro", pr & mp["anio_con_mes_sin_registro"].eq(0)),
    conteo("Fuente alterna SMByC 2013–2024 (4.3.7)", pr & mp["anio"].ge(2013), nota="falta la serie SMByC"),
    conteo("Regulación continua (secundaria)", pr & mp["regulacion_dias"].notna(), nota="sin Ínsula"),
    conteo("Caudales 4.3.6 (usar_prueba_mecanismo, año completo)",
           mp["muestra_principal"].eq(1) & mp["usar_prueba_mecanismo"].eq(1) & mp["q_anio_completo"].eq(1)
           & mp["def_acum_pct"].notna()),
    conteo("Caudales 4.3.6 sin hueco del Chinchiná",
           mp["usar_prueba_mecanismo"].eq(1) & mp["q_anio_completo"].eq(1) & mp["hueco_caudal_chinchina"].eq(0)),
]
pmm = pm[pm["muestra_principal"].eq(1)]
bm = pmm["obs_principal_mes"].eq(1)
filas += [
    conteo("Mensual, todos los meses", bm, pmm),
    conteo("Mensual, época seca propia de la cuenca (4 meses) — principal", bm & pmm["seca_cuenca_4m"].eq(1), pmm),
    conteo("Mensual, época seca nacional dic–mar — robustez", bm & pmm["seca_nal_dic_mar"].eq(1), pmm),
    conteo("Mensual, sin meses sin registro", bm & pmm["mes_sin_registro"].eq(0), pmm),
]
por_u = mp[pr].groupby("unidad").size()
filas.append({"especificacion": "Regresión por unidad (4.3.9): años por unidad", "obs": int(por_u.sum()),
              "unidades": len(por_u), "unidades_embalse": np.nan, "unidades_filo": np.nan,
              "sistemas_A": np.nan, "sistemas_B": np.nan,
              "nota": f"mín {por_u.min()} ({por_u.idxmin()}), mediana {int(por_u.median())}, máx {por_u.max()}; "
                      f"unidades con < 10 años: {', '.join(por_u[por_u < 10].index)}"})
cnt = pd.DataFrame(filas)

# --------------------------------------------------------------------------------------
# 7. Reporte de calidad
# --------------------------------------------------------------------------------------
qc: list[tuple[str, str, str, str]] = []


def prueba(sec, nombre, ok, detalle="", revisar=False, info=False):
    estado = "INFO" if info else ("OK" if ok else ("REVISAR" if revisar else "FALLA"))
    qc.append((sec, nombre, estado, detalle))


n_u = tm["unidad"].nunique()
prueba("1 Llaves", "unidad-año única (anual)", not pa.duplicated(["unidad", "anio"]).any())
prueba("1 Llaves", "unidad-mes única (mensual)", not pm.duplicated(["unidad", "anio", "mes"]).any())
prueba("1 Llaves", "unidad única en la tabla maestra", tm["unidad"].is_unique)
prueba("2 Panel completo", "anual = unidades de la tabla maestra × 24 años", len(pa) == n_u * len(ANIOS),
       f"{len(pa)} filas = {n_u} unidades × {len(ANIOS)} años")
prueba("2 Panel completo", "mensual = unidades × 288 meses", len(pm) == n_u * len(ANIOS) * 12, f"{len(pm)} filas")
ms = tm[tm["muestra_principal"].eq(1)]
n_emb = ms["tipo_propuesto"].eq("embalse").sum()
prueba("2 Panel completo", "muestra principal: 26 unidades (14 embalse, 12 filo)",
       (len(ms), n_emb) == (26, 14), f"{len(ms)} unidades, {n_emb} embalse, {len(ms) - n_emb} filo")
op = mp[mp["frac_anio_operacion"].gt(0)]
sin_fc = op[op["fc"].isna()]
prueba("2 Panel completo", "muestra: FC presente en todos los años en operación", sin_fc.empty,
       "; ".join(f"{a} {b}" for a, b in zip(sin_fc["unidad"], sin_fc["anio"])))
for v in ["def_acum_pct", "def_flujo_pct", "lluvia_mm", "sistema_geom_A", "sistema_geom_B", "ha_atch", "ha_exclusivas",
          "oni", "precio_bolsa_cop2024_kwh"]:
    f = mp[mp[v].isna()]
    prueba("2 Panel completo", f"muestra: {v} sin faltantes 2001–2024", f.empty,
           ", ".join(sorted(f["unidad"].unique())))
f = mp[mp["regulacion_dias"].isna()]["unidad"].unique()
prueba("2 Panel completo", "muestra: regulación continua presente", list(f) == ["INSULA"],
       f"sin valor: {', '.join(f)} (esperado: solo Ínsula)", revisar=True)
nr = pm[pm["muestra_principal"].eq(1) & pm["antes_inicio_xm"].eq(0) & pm["despues_fin"].eq(0) & pm["fc"].isna()]
prueba("2 Panel completo", "mensual: FC presente en todos los meses en operación", nr.empty, f"{len(nr)} unidad-mes")
ent = mp[mp["antes_inicio_xm"].eq(1)].groupby("unidad")["anio"].agg(["min", "max"])
prueba("2 Panel completo", "años antes del inicio en XM (FC vacío)", True,
       "; ".join(f"{k} {r['min']}–{r['max']}" for k, r in ent.iterrows()), info=True)

# FC
fcv = pa["fc"]
prueba("3 Factor de capacidad", "FC ≥ 0", (fcv.dropna() >= 0).all())
prueba("3 Factor de capacidad", "FC ≤ 1 o marcado (fc_mayor_1)", ((fcv <= 1) | fcv.isna() | pa["fc_mayor_1"].eq(1)).all())
m1 = mp[mp["fc_mayor_1"].eq(1)]
prueba("3 Factor de capacidad", "muestra: unidad-año con FC > 1 (se conservan, regla 4.5)", True,
       f"{len(m1)}: " + "; ".join(f"{k} {len(v)} años (máx {v['fc'].max():.2f})" for k, v in m1.groupby("unidad")),
       info=True)
m1m = pm[pm["muestra_principal"].eq(1) & pm["fc_mayor_1"].eq(1)]
prueba("3 Factor de capacidad", "mensual: FC > 1 marcado", ((pm["fc"] <= 1) | pm["fc"].isna() | pm["fc_mayor_1"].eq(1)).all(),
       f"{len(m1m)} unidad-mes en la muestra (máx {m1m['fc'].max():.2f})")
par = mp[mp["anio_parcial"].eq(1)]
prueba("3 Factor de capacidad", "años parciales marcados (FC con horas del año completo, regla 4.5)", True,
       "; ".join(f"{a} {b} ({c:.0%}, FC {d:.3f} → {e:.3f} con horas de operación)" for a, b, c, d, e in
                 zip(par["unidad"], par["anio"], par["frac_anio_operacion"], par["fc"], par["fc_horas_operacion"])),
       info=True)
gsum = pm.groupby(["unidad", "anio"])["gen_mwh"].sum(min_count=1).reset_index().merge(
    pa[["unidad", "anio", "gen_gwh"]], on=["unidad", "anio"])
dif = (gsum["gen_mwh"] / 1000 - gsum["gen_gwh"]).abs().max()
prueba("3 Factor de capacidad", "suma mensual = generación anual (±0,001 GWh)", dif < 0.001, f"máx. diferencia {dif:.5f} GWh")

# Lluvia
lv = mp["lluvia_mm"]
prueba("4 Lluvia", "lluvia anual entre 500 y 9.000 mm", lv.between(500, 9000).all(), f"rango {lv.min():.0f}–{lv.max():.0f} mm")
lvm = pm.loc[pm["muestra_principal"].eq(1), "lluvia_mm"]
prueba("4 Lluvia", "lluvia mensual entre 0 y 2.000 mm", lvm.between(0, 2000).all(), f"rango {lvm.min():.0f}–{lvm.max():.0f} mm")
med = mp.groupby("anio")["lluvia_mm"].median()
dev = (med / med.mean() - 1).abs()
prueba("4 Lluvia", "ningún año con mediana atípica (±40 %; la falla de 2011–2013 de 2019)", (dev < 0.4).all(),
       f"máx. desvío {dev.max():.0%} en {dev.idxmax()}")
chk = (pm.groupby(["unidad", "anio"])["lluvia_mm"].sum().reset_index()
       .merge(pa[["unidad", "anio", "lluvia_mm"]], on=["unidad", "anio"], suffixes=("_m", "_a")).dropna())
dl = (chk["lluvia_mm_m"] - chk["lluvia_mm_a"]).abs().max()
prueba("4 Lluvia", "suma de meses = lluvia anual (±1 mm)", dl <= 1, f"máx. diferencia {dl:.2f} mm")
nsec = pm.groupby("unidad")["seca_cuenca_4m"].sum() / len(ANIOS)
prueba("4 Lluvia", "época seca de cuenca: 4 meses por unidad", (nsec[nsec.index.isin(ms["unidad"])] == 4).all())

# Deforestación
dsort = pa.dropna(subset=["def_acum_pct"]).sort_values(["unidad", "anio"])
baja = dsort.groupby("unidad")["def_acum_pct"].diff().lt(-1e-9).sum()
prueba("5 Deforestación", "acumulado nunca baja", baja == 0, f"{baja} bajadas")
recon = dsort.groupby("unidad")["def_flujo_ha"].cumsum()
prueba("5 Deforestación", "acumulado = suma de flujos (±0,01 ha)", (recon - dsort["def_acum_ha"]).abs().max() < 0.01)
prueba("5 Deforestación", "flujo ≥ 0 y acumulado ≤ 100 %", (dsort["def_flujo_ha"] >= 0).all() and (dsort["def_acum_pct"] <= 100).all())
lag_ok = (dsort.groupby("unidad")["def_flujo_ha"].shift(1).fillna(-1) == dsort["def_flujo_ha_l1"].fillna(-1)).all()
lead_ok = (dsort.groupby("unidad")["def_acum_pct"].shift(-3).fillna(-1) == dsort["def_acum_pct_f3"].fillna(-1)).all()
prueba("5 Deforestación", "rezagos y adelantos alineados con el año correcto", lag_ok and lead_ok)
prueba("5 Deforestación", "acumulado rezagado = 0 antes de 2001", (pa.loc[pa["anio"].eq(2001) & pa["area_ee_ha"].notna(), "def_acum_pct_l1"] == 0).all())

# Áreas
ar = pa.drop_duplicates("unidad").dropna(subset=["area_ee_ha"])
dif_a = (ar["area_ee_ha"] / ar["ha_atch"] - 1).abs()
prueba("6 Áreas", "área Earth Engine = ATCH IGAC (±1 %)", (dif_a < 0.01).all(),
       f"{len(ar)} unidades; máx. diferencia {dif_a.max():.3%} ({ar.loc[dif_a.idxmax(), 'unidad']})")
s2 = sh.merge(cu[["unidad", "area_union_ha"]], on="unidad")
d2 = (s2["ha_atch"] / s2["area_union_ha"] - 1).abs().max()
prueba("6 Áreas", "ATCH de sistemas_hidricos = ATCH de cuencas_atch_unidad (±0,01 %)", d2 < 1e-4, f"máx. {d2:.5%}")
h2 = ha[~ha["unidad"].str.startswith("TOTAL")].merge(cu[["unidad", "area_union_ha"]], on="unidad")
d3 = (h2["ha_atch"] / h2["area_union_ha"] - 1).abs().max()
prueba("6 Áreas", "hectareas_por_unidad: ATCH coherente y exclusivas ≤ ATCH",
       d3 < 1e-4 and (h2["ha_exclusivas"] <= h2["ha_atch"] + 1e-6).all(), f"máx. {d3:.5%}")
prueba("6 Áreas", "bosque 2000 ≤ área de la cuenca", (ar["bosque2000_ha"] <= ar["area_ee_ha"]).all())
tot = ha[ha["unidad"].str.startswith("TOTAL")].set_index("unidad")["ha_atch"]
prueba("6 Áreas", "hectáreas sin doble conteo (T3)", True,
       "; ".join(f"{k}: {v / 1e6:.2f} millones de ha" for k, v in tot.items()), info=True)

# Tipos y sistemas
t_sh = sh.set_index("unidad")["tipo"]
t_tm = ms.set_index("unidad")["tipo_propuesto"]
dif_t = [k for k in t_tm.index if t_sh.get(k) != t_tm[k]]
prueba("7 Tipos y sistemas", "tipo de la tabla maestra = tipo en sistemas_hidricos.csv", not dif_t,
       f"difieren: {', '.join(dif_t)} — el panel usa la tabla maestra (T3 no se ha vuelto a correr tras el cambio de RIO GRANDE a embalse)",
       revisar=True)
t_rg = reg.set_index("unidad")["tipo"]
dif_r = [k for k in t_tm.index if t_rg.get(k) != t_tm[k]]
prueba("7 Tipos y sistemas", "tipo de la tabla maestra = tipo en regulacion_unidad.csv", not dif_r, ", ".join(dif_r))
prueba("7 Tipos y sistemas", "10 sistemas A y 14 sistemas B en la muestra",
       (mp["sistema_geom_A"].nunique(), mp["sistema_geom_B"].nunique()) == (10, 14),
       f"A: {mp['sistema_geom_A'].nunique()}, B: {mp['sistema_geom_B'].nunique()}")
prueba("7 Tipos y sistemas", "embalse por cadena = Riogrande I, Río Grande, Ínsula",
       set(mp.loc[mp["embalse_por_cadena"].eq(1), "unidad"]) == {"RIOGRANDE I", "RIO GRANDE", "INSULA"})

# Controles
prueba("8 Controles", "ONI 2001–2024 completo (anual y mensual)", pa["oni"].notna().all() and pm["oni"].notna().all())
prueba("8 Controles", "precio constante 2001–2024 completo; factor 2024 = 1",
       pa["precio_bolsa_cop2024_kwh"].notna().all() and pm["precio_bolsa_cop2024_kwh"].notna().all()
       and np.isclose(pa.loc[pa["anio"].eq(2024), "factor_a_pesos_2024"].iloc[0], 1.0))
prueba("8 Controles", "IPC: fuente oficial (BanRep o DANE)", False,
       "se usa Banco Mundial FP.CPI.TOTL (DANE vía FMI) como respaldo; pendiente opcional de T5", revisar=True)

# Marcas
prueba("9 Marcas", "años de El Niño: 2009–2010, 2015–2016, 2023–2024",
       set(pa.loc[pa["anio_nino"].eq(1), "anio"]) == ANIOS_NINO)
prueba("9 Marcas", "hueco Chinchiná: 4 unidades × 5 años", pa["hueco_caudal_chinchina"].sum() == 20)
mi = pa[pa["unidad"].eq(MIEL)].set_index("anio")
prueba("9 Marcas", "trasvases Miel I", mi.loc[2010, "miel_trasvase_guarino"] > 0 and mi.loc[2009, "miel_trasvase_guarino"] == 0
       and mi.loc[2013, "miel_trasvase_manso"] > 0 and mi.loc[2012, "miel_trasvase_manso"] == 0,
       "Guarinó desde dic-2010 (2010 = 1/12), Manso desde jun-2013 (2013 = 7/12)")
so = pa[pa["unidad"].eq(SONSON)].set_index("anio")
prueba("9 Marcas", "Sonsón sin generar desde mayo de 2022; FC vacío 2023–2024",
       so.loc[[2023, 2024], "fc"].isna().all() and so.loc[2022, "sonson_sin_generar"] > 0)
msr_m = pm[pm["muestra_principal"].eq(1) & pm["mes_sin_registro"].eq(1)].groupby("unidad").size()
prueba("9 Marcas", "meses sin registro en la muestra (= 0, decisión T5-4)", True,
       f"{msr_m.sum()} unidad-mes: " + "; ".join(f"{k} {v}" for k, v in msr_m.items()), info=True)

# Regla de no mirar resultados
prueba("10 Regla", "el script no calcula correlaciones ni regresiones deforestación–generación", True,
       "solo une, marca y cuenta observaciones", info=True)
gdm = mp[mp["gen_anual_desde_mensual"].eq(1)]
prueba("9 Marcas", "años sin ningún registro en XM tomados como 0 (regla T5-4 llevada al año)", True,
       "; ".join(f"{a} {b}" for a, b in zip(gdm["unidad"], gdm["anio"])) + " (12 meses sin registro; marcados)", info=True)

# --------------------------------------------------------------------------------------
# 8. Salidas
# --------------------------------------------------------------------------------------
hechos = escribir(pa, "panel_anual") + escribir(pm, "panel_mensual")
dicc.to_csv(OUT / "diccionario_datos.csv", index=False, encoding="utf-8")
cnt.to_csv(OUT / "conteo_observaciones.csv", index=False, encoding="utf-8")


def md_tabla(df: pd.DataFrame) -> str:
    df = df.fillna("")
    lin = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    lin += ["| " + " | ".join(str(x).replace("|", "/") for x in fila) + " |" for fila in df.itertuples(index=False)]
    return "\n".join(lin)


with open(OUT / "diccionario_datos.md", "w", encoding="utf-8") as fh:
    fh.write("# Diccionario de datos del panel (T6)\n\nGenerado por `03_codigo/04_panel/construir_panel.py`. "
             "`panel`: anual, mensual o ambos.\n\n" + md_tabla(dicc) + "\n")

estados = pd.Series([x[2] for x in qc]).value_counts()
with open(OUT / "reporte_qc_t6.md", "w", encoding="utf-8") as fh:
    fh.write("# Reporte de calidad T6 — panel\n\n")
    fh.write(f"Generado por `03_codigo/04_panel/construir_panel.py` el {dt.datetime.now():%Y-%m-%d %H:%M}. "
             "No contiene correlaciones ni regresiones entre deforestación y generación.\n\n")
    fh.write(f"Panel anual: {len(pa)} filas ({n_u} unidades × {len(ANIOS)} años); "
             f"panel mensual: {len(pm)} filas. Muestra principal: {len(ms)} unidades.\n\n")
    fh.write("Decisiones de T6 aplicadas: " + "; ".join(f"`{k}` = {v}" for k, v in DECISIONES.items()) + "\n\n")
    fh.write("Resumen: " + " · ".join(f"{v} {k}" for k, v in estados.items()) + "\n\n")
    fh.write(md_tabla(pd.DataFrame(qc, columns=["Sección", "Prueba", "Estado", "Detalle"])) + "\n\n")
    fh.write("## Conteo de observaciones por especificación (muestra principal)\n\n")
    fh.write(md_tabla(cnt) + "\n")

print("Escritos en 02_datos/panel:", ", ".join(hechos + ["diccionario_datos.csv/.md", "conteo_observaciones.csv",
                                                       "reporte_qc_t6.md"]))
print("QC:", dict(estados))
