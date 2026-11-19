"""
T7 · 03 · Análisis individuales (4.3, punto 9). Definiciones fijadas antes de ver resultados:

 a) Regresión por unidad, cada medida por separado: FC (pp) ~ D + lluvia + ONI + tendencia lineal
    (+ trasvases en Miel I), MCO con errores Newey-West de 2 rezagos. Se estima si quedan al menos
    3 grados de libertad. Resumen por tipo (filo / embalse): unidades estimadas, cuántas con signo
    negativo, cuántas negativas con p < 0,05, mediana, y promedio ponderado por precisión (inverso de
    la varianza) con su error, sobre las unidades con 10 años o más y también sobre todas las estimadas.
 b) Influencia: modelo principal quitando una unidad a la vez y un sistema A a la vez (b1 y b1 + b2,
    CRV1 y WCR).
 c) Errores alternativos: agrupados por unidad (26) y por sistema B (14), CRV1 y WCR de Webb.

Salidas: t7_03_por_unidad, t7_03_por_unidad_resumen, t7_03_influencia, t7_03_errores_alternativos.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm

from t7_comun import (CONTROLES, MEDIDAS, MIEL, cargar_anual, estimar, guardar, muestras_anuales,
                      pruebas_basicas)

a = cargar_anual()
MA = muestras_anuales(a)
p = a[MA["principal"]].copy()

# a) por unidad ----------------------------------------------------------------------------
filas = []
for u, d in p.groupby("unidad"):
    for m in MEDIDAS:
        X = [f"D_{m}", "lluvia", "oni", "tendencia"] + (["trasv_guarino", "trasv_manso"] if u == MIEL else [])
        dd = d.dropna(subset=["fc_pp"] + X)
        X = [x for x in X if dd[x].nunique() > 1]
        fila = {"unidad": u, "embalse": int(d["embalse"].iloc[0]), "tipo": "embalse" if d["embalse"].iloc[0] == 1 else "filo",
                "medida": m, "n": len(dd), "anio_ini": int(dd["anio"].min()), "anio_fin": int(dd["anio"].max())}
        if len(dd) - (len(X) + 1) < 3 or f"D_{m}" not in X:
            filas.append({**fila, "nota": "no estimable (menos de 3 gl)"})
            continue
        r = sm.OLS(dd["fc_pp"], sm.add_constant(dd[X])).fit(cov_type="HAC", cov_kwds={"maxlags": 2, "use_correction": True},
                                                          use_t=True)
        filas.append({**fila, "b": r.params[f"D_{m}"], "ee": r.bse[f"D_{m}"], "p": r.pvalues[f"D_{m}"], "nota": ""})
pu = pd.DataFrame(filas)
guardar(pu, "t7_03_por_unidad", "T7 · 4.3.9 Regresión por unidad",
        "FC (pp) ~ D + lluvia + ONI + tendencia (+ trasvases en Miel I); MCO, Newey-West 2 rezagos.")

res = []
for m in MEDIDAS:
    for tipo in ["filo", "embalse"]:
        for corte, cond in [("≥ 10 años", pu["n"] >= 10), ("todas las estimadas", pu["n"] > 0)]:
            d = pu[pu["medida"].eq(m) & pu["tipo"].eq(tipo) & cond & pu["b"].notna()]
            w = 1 / d["ee"] ** 2
            pm = (w * d["b"]).sum() / w.sum()
            se = 1 / np.sqrt(w.sum())
            from scipy import stats
            res.append({"medida": m, "tipo": tipo, "unidades": corte, "n_unidades": len(d),
                        "negativas": int((d["b"] < 0).sum()), "negativas_p<0,05": int(((d["b"] < 0) & (d["p"] < 0.05)).sum()),
                        "positivas_p<0,05": int(((d["b"] > 0) & (d["p"] < 0.05)).sum()),
                        "mediana": d["b"].median(), "prom_ponderado": pm, "ee_prom": se,
                        "p_prom": 2 * stats.norm.sf(abs(pm / se))})
guardar(pd.DataFrame(res), "t7_03_por_unidad_resumen", "T7 · 4.3.9 Resumen de las regresiones por unidad",
        "Promedio ponderado por precisión (inverso de la varianza). Su error supone independencia entre unidades, "
        "que no se cumple en cuencas anidadas: es un resumen descriptivo, no reemplaza al panel.")

# b) influencia -----------------------------------------------------------------------------
f = []
for tipo, col in [("sin la unidad", "unidad"), ("sin el sistema A", "sistema_geom_A")]:
    for v in sorted(p[col].unique()):
        mask = MA["principal"] & a[col].ne(v)
        for m in MEDIDAS:
            pr = pruebas_basicas(m)
            pr.pop("b2 (embalse − filo)")
            f += estimar(a[mask], "fc_pp", [f"D_{m}", f"DE_{m}"] + CONTROLES, pr,
                         etiqueta={"medida": m, "variante": tipo, "excluido": v})
inf = pd.DataFrame(f)
guardar(inf, "t7_03_influencia", "T7 · 4.3.9 Influencia: quitar una unidad o un sistema a la vez",
        "Modelo principal. Al quitar un sistema quedan 9 grupos.",
        ["variante", "excluido", "medida", "termino", "estimado", "ee", "p_conv", "p_wcb", "N", "unidades", "G", "omitidos"])

# c) errores alternativos ----------------------------------------------------------------------
f = []
for cl, nom in [("sistema_geom_A", "sistema A (principal)"), ("unidad", "unidad"), ("sistema_geom_B", "sistema B")]:
    for m in MEDIDAS:
        f += estimar(a[MA["principal"]], "fc_pp", [f"D_{m}", f"DE_{m}"] + CONTROLES, pruebas_basicas(m),
                     cluster=cl, etiqueta={"medida": m, "variante": f"agrupados por {nom}"})
guardar(pd.DataFrame(f), "t7_03_errores_alternativos", "T7 · 4.3.9 Errores alternativos",
        "Mismos coeficientes que el modelo principal; cambian los errores. WCR de Webb con el grupo indicado.",
        ["variante", "medida", "termino", "estimado", "ee", "p_conv", "p_wcb", "N", "G"])
print(pd.DataFrame(res).round(3).to_string())
print(inf.groupby(["medida", "termino", "variante"])["estimado"].describe().round(3).to_string())
print(pd.DataFrame(f)[["variante", "medida", "termino", "estimado", "p_conv", "p_wcb", "G"]].round(4).to_string())
