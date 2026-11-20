"""
T7 · 06 · Hipótesis exploratoria H2 (registro de cambios del 20-nov-2026; especificación subida en 7f76ba5
antes de procesar las horas y de estimar).

H2: en las centrales a filo de agua, una cuenca más conservada aumenta el tiempo en producción en la época seca.

- Muestra: unidades a filo de la muestra principal, años con obs_principal == 1; meses con obs_principal_mes == 1.
  Se exige que el año tenga sus 4 meses secos propios (seca_principal).
- Conservación (%) = bosque2000_pct_cuenca × (1 − def_acum_pct / 100): % de la cuenca con bosque en el año.
- Principal: % de horas con generación > 0 en los meses secos propios del año (05_horas_generacion.py).
- Secundaria: FC promedio de los meses secos / FC promedio de los demás meses del año.
- Diseño principal (dentro de cada unidad): y ~ conservación + lluvia seca + lluvia resto | unidad + año;
  errores por sistema A (5 grupos) y por unidad (12); WCR de Webb, 9.999 réplicas.
- Robustez: medidas calculadas sin los meses sin registro de generación.
- Contraste: el mismo modelo en las unidades con embalse (se espera ≈ 0).
- Diseño secundario, descriptivo: una fila por unidad (promedios); MCO con errores robustos (HC1) con lluvia seca
  y ln(capacidad), y correlación de Spearman.
Signo esperado: positivo.

Salidas: t7_06_h2_dentro, t7_06_h2_entre, t7_06_h2_datos (unidad-año), t7_06_h2_validacion_horas.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from t7_comun import PANEL, ROOT, cargar_anual, estimar, guardar

NOMBRES = {"AMOYA": "AMOYA LA ESPERANZA"}  # nombre de XM antes de 2014

a = cargar_anual()
m = pd.read_parquet(PANEL / "panel_mensual.parquet") if (PANEL / "panel_mensual.parquet").exists() else \
    pd.read_csv(PANEL / "panel_mensual.csv")
h = pd.read_csv(ROOT / "02_datos" / "xm_procesado" / "horas_generacion_hidro_diaria.csv.gz", parse_dates=["fecha"])
h["recurso"] = h["recurso"].replace(NOMBRES)
h["anio"], h["mes"] = h["fecha"].dt.year, h["fecha"].dt.month
hm = h.groupby(["recurso", "anio", "mes"], as_index=False)[["horas_gen", "kwh"]].sum().rename(columns={"recurso": "unidad"})

mm = m[m["muestra_principal"].eq(1) & m["obs_principal_mes"].eq(1)].merge(hm, on=["unidad", "anio", "mes"], how="left")
mm["horas_mes"] = pd.to_datetime(dict(year=mm["anio"], month=mm["mes"], day=1)).dt.days_in_month * 24
# meses sin ningún registro en XM: 0 horas (regla de T5); se marca si falta el dato sin ser mes sin registro
mm["sin_dato_horas"] = mm["horas_gen"].isna() & mm["mes_sin_registro"].eq(0)
mm["horas_gen"] = mm["horas_gen"].fillna(0)
val = (mm.assign(dif=(mm["kwh"].fillna(0) / 1000 - mm["gen_mwh"]).abs())
         .groupby(["unidad", "embalse"]).agg(meses=("mes", "size"), meses_sin_dato_horas=("sin_dato_horas", "sum"),
                                             meses_dif_mayor_1MWh=("dif", lambda s: int((s > 1).sum())),
                                             dif_max_MWh=("dif", "max")).reset_index())
guardar(val, "t7_06_h2_validacion_horas", "T7 · H2 · Validación de las horas contra la generación del panel",
        "Generación horaria sumada por mes frente a `gen_mwh` del panel mensual (misma fuente XM).")


def por_anio(d: pd.DataFrame) -> pd.DataFrame:
    s = d[d["seca_principal"].eq(1)]
    r = d[d["seca_principal"].eq(0)]
    o = s.groupby(["unidad", "anio"]).agg(meses_secos=("mes", "size"), horas_gen=("horas_gen", "sum"),
                                          horas=("horas_mes", "sum"), fc_seca=("fc", "mean"),
                                          lluvia_seca=("lluvia_mm", "sum"))
    o = o.join(r.groupby(["unidad", "anio"]).agg(fc_resto=("fc", "mean"), lluvia_resto=("lluvia_mm", "sum")))
    o["pct_horas_seca"] = o["horas_gen"] / o["horas"] * 100
    o["razon_fc"] = np.where(o["fc_resto"] > 0, o["fc_seca"] / o["fc_resto"], np.nan)
    o["lluvia_seca"] /= 100
    o["lluvia_resto"] /= 100
    return o.reset_index()


cols_a = ["unidad", "anio", "embalse", "sistema_geom_A", "sistema_geom_B", "cap_mw", "bosque2000_pct_cuenca", "def_acum_pct"]
base = a[a["obs_principal"].eq(1)][cols_a].copy()
base["conservacion"] = base["bosque2000_pct_cuenca"] * (1 - base["def_acum_pct"] / 100)

filas, datos = [], []
for var, dm in [("todos los meses", mm), ("sin meses sin registro", mm[mm["mes_sin_registro"].eq(0)])]:
    d = base.merge(por_anio(dm), on=["unidad", "anio"], how="inner")
    d = d[d["meses_secos"].eq(4) | (var != "todos los meses")]
    d = d[d["meses_secos"].ge(1)]
    datos.append(d.assign(variante=var))
    for tipo, e in [("filo (H2)", 0), ("embalse (contraste)", 1)]:
        dd = d[d["embalse"].eq(e)]
        for y, ny in [("pct_horas_seca", "% de horas con generación en época seca (principal)"),
                      ("razon_fc", "FC seca / FC resto del año (secundaria)")]:
            for cl in ["sistema_geom_A", "unidad"]:
                filas += estimar(dd, y, ["conservacion", "lluvia_seca", "lluvia_resto"],
                                 {"conservación (% de la cuenca con bosque)": {"conservacion": 1.0}},
                                 cluster=cl, etiqueta={"tipo": tipo, "variable": ny, "variante": var,
                                                       "errores": f"por {cl}"})
res = pd.DataFrame(filas)
guardar(res, "t7_06_h2_dentro", "T7 · H2 exploratoria · Diseño dentro de cada unidad",
        "Efectos fijos de unidad y año; lluvia de los meses secos y del resto del año (cientos de mm). Coeficiente: "
        "cambio en la variable por cada punto más de la cuenca con bosque. Signo esperado: positivo en filo. "
        "Hipótesis propuesta después de ver resultados (registro de cambios, 20-nov).",
        ["tipo", "variable", "variante", "errores", "estimado", "ee", "p_conv", "p_wcb", "N", "unidades", "G"])
dat = pd.concat(datos)
dat.to_csv(ROOT / "07_salidas" / "tablas" / "t7_06_h2_datos.csv", index=False)

# diseño entre unidades (descriptivo)
fe = []
d = dat[dat["variante"].eq("todos los meses") & dat["embalse"].eq(0)]
u = d.groupby("unidad").agg(pct_horas_seca=("pct_horas_seca", "mean"), razon_fc=("razon_fc", "mean"),
                            conservacion=("conservacion", "mean"), lluvia_seca=("lluvia_seca", "mean"),
                            cap_mw=("cap_mw", "mean"), anios=("anio", "size")).reset_index()
u["ln_cap"] = np.log(u["cap_mw"])
for y in ["pct_horas_seca", "razon_fc"]:
    uu = u.dropna(subset=[y])
    r = sm.OLS(uu[y], sm.add_constant(uu[["conservacion", "lluvia_seca", "ln_cap"]])).fit(cov_type="HC1")
    rho, prho = stats.spearmanr(uu["conservacion"], uu[y])
    fe.append({"variable": y, "n_unidades": len(uu), "coef_conservacion": r.params["conservacion"],
               "ee": r.bse["conservacion"], "p": r.pvalues["conservacion"], "spearman_rho": rho, "p_spearman": prho})
guardar(pd.DataFrame(fe), "t7_06_h2_entre", "T7 · H2 exploratoria · Diseño entre unidades (descriptivo)",
        "Una fila por unidad a filo (promedios de sus años). MCO con errores HC1: y ~ conservación + lluvia seca + "
        "ln(capacidad). Con 12 unidades es solo descriptivo: la conservación se mezcla con todo lo que distingue a "
        "una central de otra.")
guardar(u, "t7_06_h2_unidades", "T7 · H2 · Promedios por unidad a filo", "")
print(res[["tipo", "variable", "variante", "errores", "estimado", "ee", "p_conv", "p_wcb", "N", "G"]].round(4).to_string())
print(pd.DataFrame(fe).round(4).to_string())
print(u.round(2).to_string())
print(val.to_string())
