"""
T7 · Tesis 2.0 · utilidades comunes de estimación.

Especificación fijada en la sección 4.5 del plan (etiqueta `pre-estimacion`, commit b9a6f68,
y registro de cambios del 19-nov-2026: se estima con pyfixest y se entrega el equivalente en R).

  FC_it = b1·D_it + b2·(D_it × Embalse_i) + b3·Lluvia_it + c1·TrasvGuarino_it + c2·TrasvManso_it
          + mu_i + lambda_t + e_it

- FC en puntos porcentuales (fc × 100). Lluvia en miles de mm. Flujo en hectáreas: miles de ha.
- Errores agrupados por `sistema_geom_A` (10 sistemas). p-valor convencional: CRV1 de pyfixest
  con t de G − 1 grados de libertad.
- Wild cluster *restricted* bootstrap (WCR, impone la nula), pesos de Webb, 9.999 réplicas,
  p-valor simétrico de dos colas. Algoritmo de Roodman, MacKinnon, Nielsen y Webb (2019,
  "Fast and wild", Stata Journal), el mismo de `boottest` y `fwildclusterboot`. Se programa aquí
  porque `wildboottest` 0.3.2 falla con identificadores de grupo de texto. Los efectos fijos
  entran como variables indicadoras, de modo que el modelo bootstrap es exactamente el estimado.
- b1 + b2 = 0: una sola restricción, así que F = t². Se reporta con CRV1 y con WCR.

Correr desde 03_tesis: python3 03_codigo/05_estimacion/01_modelo_principal.py, etc.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf
from scipy import stats

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]          # 03_tesis
PANEL = ROOT / "02_datos" / "panel"
TAB = ROOT / "07_salidas" / "tablas"
FIG = ROOT / "07_salidas" / "figuras"
TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

B_REPS = 9999
SEMILLA = 20261119
CLUSTER = "sistema_geom_A"
FE_ANUAL = "unidad + anio"
FE_MENSUAL = "unidad^mes + anio^mes"     # estacionalidad propia de cada unidad y choques de cada mes
MIEL = "MIEL I"

# medida -> (columna del panel, etiqueta, divisor de escala)
MEDIDAS = {
    "acum_pct": ("def_acum_pct", "Acumulado (% del bosque 2000)", 1.0),
    "flujo_ha": ("def_flujo_ha", "Flujo del año (miles de ha)", 1000.0),
    "flujo_pct": ("def_flujo_pct", "Flujo del año (% del bosque 2000)", 1.0),
}
SUFIJOS = ["", "_l1", "_l2", "_l3", "_f1", "_f2", "_f3"]
CONTROLES = ["lluvia", "trasv_guarino", "trasv_manso"]
CONTROLES_MES = ["lluvia_mes", "trasv_guarino", "trasv_manso"]

# Observaciones esperadas (conteo_observaciones.csv de T6 y TEMAS_por_chat.md, T6)
ESPERADO = {
    "principal": 524, "con_parciales": 538, "sin_nino": 385, "placebo_f1_f3": 450,
    "caudales": 349, "mensual_todos": 6366, "mensual_seca": 2114,
}


# --------------------------------------------------------------------------------------
# Datos
# --------------------------------------------------------------------------------------
def _leer(nombre: str) -> pd.DataFrame:
    """Parquet si se puede leer; si OneDrive lo tiene solo en la nube, el CSV gemelo."""
    try:
        return pd.read_parquet(PANEL / f"{nombre}.parquet")
    except Exception:
        return pd.read_csv(PANEL / f"{nombre}.csv")


def _agregar_medidas(d: pd.DataFrame) -> pd.DataFrame:
    for m, (col, _, esc) in MEDIDAS.items():
        for s in SUFIJOS:
            if col + s in d:
                d[f"D_{m}{s}"] = d[col + s] / esc
                d[f"DE_{m}{s}"] = d[f"D_{m}{s}"] * d["embalse"]
    return d


def cargar_anual() -> pd.DataFrame:
    a = _leer("panel_anual")
    a["fc_pp"] = a["fc"] * 100
    a["fc_horas_pp"] = a["fc_horas_operacion"] * 100
    a["lluvia"] = a["lluvia_mm"] / 1000
    a["trasv_guarino"] = a["miel_trasvase_guarino"]
    a["trasv_manso"] = a["miel_trasvase_manso"]
    a["tendencia"] = a["anio"] - 2000
    a["ln_reg"] = np.log1p(a["regulacion_dias"])
    return _agregar_medidas(a)


def cargar_mensual() -> pd.DataFrame:
    m = _leer("panel_mensual")
    m["fc_pp"] = m["fc"] * 100
    m["lluvia_mes"] = m["lluvia_mm"] / 100      # cientos de mm en el mes
    m["trasv_guarino"] = m["miel_trasvase_guarino"]
    m["trasv_manso"] = m["miel_trasvase_manso"]
    return _agregar_medidas(m)


# --------------------------------------------------------------------------------------
# Muestras (misma lógica que la sección 6 de 03_codigo/04_panel/construir_panel.py)
# --------------------------------------------------------------------------------------
def muestras_anuales(a: pd.DataFrame) -> dict[str, pd.Series]:
    mp = a["muestra_principal"].eq(1)
    pr = a["obs_principal"].eq(1)
    nn = lambda cols: a[cols].notna().all(axis=1)
    return {
        "principal": pr,
        "con_parciales": a["obs_base_acum"].eq(1),
        "sin_miel_2001_2013": pr & ~(a["unidad"].eq(MIEL) & a["anio"].lt(2014)),
        "rezagos_acum": pr & nn(["def_acum_pct_l1", "def_acum_pct_l2", "def_acum_pct_l3"]),
        "rezagos_flujo": pr & nn(["def_flujo_pct_l1", "def_flujo_pct_l2", "def_flujo_pct_l3"]),
        "placebo_f1": pr & a["def_acum_pct_f1"].notna(),
        "placebo_f1_f3": pr & nn(["def_acum_pct_f1", "def_acum_pct_f2", "def_acum_pct_f3"]),
        "sin_nino": pr & a["anio_nino"].eq(0),
        "sin_fc_mayor_1": pr & a["fc_mayor_1"].eq(0),
        "sin_meses_sin_registro": pr & a["anio_con_mes_sin_registro"].eq(0),
        "regulacion": pr & a["regulacion_dias"].notna(),
        "no_anidadas": pr & a["dentro_de"].isna(),
        "caudales": mp & a["usar_prueba_mecanismo"].eq(1) & a["q_anio_completo"].eq(1) & a["def_acum_pct"].notna(),
        "caudales_sin_hueco": mp & a["usar_prueba_mecanismo"].eq(1) & a["q_anio_completo"].eq(1)
                              & a["hueco_caudal_chinchina"].eq(0),
    }


def muestras_mensuales(m: pd.DataFrame) -> dict[str, pd.Series]:
    bm = m["muestra_principal"].eq(1) & m["obs_principal_mes"].eq(1)
    return {
        "mensual_todos": bm,
        "mensual_seca": bm & m["seca_principal"].eq(1),
        "mensual_no_seca": bm & m["seca_principal"].eq(0),
        "mensual_dic_mar": bm & m["seca_nal_dic_mar"].eq(1),
        "mensual_sin_meses_sin_registro": bm & m["mes_sin_registro"].eq(0),
    }


def conteo(df: pd.DataFrame, mask: pd.Series, nombre: str) -> dict:
    s = df[mask]
    return {"muestra": nombre, "obs": len(s), "unidades": s["unidad"].nunique(),
            "unidades_embalse": s.loc[s["embalse"].eq(1), "unidad"].nunique(),
            "unidades_filo": s.loc[s["embalse"].eq(0), "unidad"].nunique(),
            "sistemas_A": s["sistema_geom_A"].nunique(), "sistemas_B": s["sistema_geom_B"].nunique(),
            "esperado_T6": ESPERADO.get(nombre, "")}


# --------------------------------------------------------------------------------------
# Wild cluster restricted bootstrap (WCR) con pesos de Webb
# --------------------------------------------------------------------------------------
_WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])


def _dummies(df: pd.DataFrame, fe: str) -> np.ndarray:
    bloques = []
    for termino in [t.strip() for t in fe.split("+") if t.strip()]:
        partes = [p.strip() for p in termino.split("^")]
        clave = df[partes].astype(str).agg("|".join, axis=1)
        bloques.append(pd.get_dummies(clave, drop_first=len(bloques) > 0).to_numpy(float))
    return np.hstack(bloques)


def wcr(y: np.ndarray, X: np.ndarray, a: np.ndarray, grupos: np.ndarray, reps: int = B_REPS,
        semilla: int = SEMILLA) -> tuple[float, float]:
    """p-valor WCR de H0: a'beta = 0. Devuelve (t sin corrección de muestra pequeña, p)."""
    g, G = pd.factorize(grupos)[0], len(pd.unique(grupos))
    A = np.linalg.pinv(X.T @ X)
    beta = A @ (X.T @ y)
    w = A @ a
    beta_r = beta - w * (a @ beta) / (a @ w)
    u, u_r = y - X @ beta, y - X @ beta_r
    Xw = X @ w
    c_hat = np.bincount(g, weights=Xw * u, minlength=G)
    t0 = (a @ beta) / np.sqrt((c_hat ** 2).sum())
    s = np.bincount(g, weights=Xw * u_r, minlength=G)
    Q = np.zeros((G, X.shape[1]))
    S = np.zeros((X.shape[1], G))
    for k in range(G):
        idx = g == k
        Q[k] = Xw[idx] @ X[idx]
        S[:, k] = X[idx].T @ u_r[idx]
    H = Q @ A @ S
    V = np.random.default_rng(semilla).choice(_WEBB, size=(G, reps))
    num = s @ V
    C = s[:, None] * V - H @ V
    tb = num / np.sqrt((C ** 2).sum(axis=0))
    return float(t0), float(np.mean(np.abs(tb) >= abs(t0) - 1e-12))


# --------------------------------------------------------------------------------------
# Estimación
# --------------------------------------------------------------------------------------
def estimar(df: pd.DataFrame, y: str, regs: list[str], pruebas: dict[str, dict[str, float]],
            fe: str = FE_ANUAL, cluster: str = CLUSTER, boot: bool = True,
            etiqueta: dict | None = None, conjuntas: dict[str, list[str]] | None = None) -> list[dict]:
    """Estima con pyfixest (CRV1) y calcula WCR para cada combinación lineal de `pruebas`.

    pruebas: nombre -> {regresor: peso}. conjuntas: nombre -> lista de regresores (Wald CRV1, F(q, G-1)).
    """
    d = df.dropna(subset=[y] + regs + [cluster]).copy()
    # regresores sin variación en la submuestra (p. ej. trasvases sin Miel I) salen y se anotan
    sin_var = [r for r in regs if d[r].nunique() <= 1]
    regs_ok = [r for r in regs if r not in sin_var]
    fml = f"{y} ~ {' + '.join(regs_ok)} | {fe}"
    fit = pf.feols(fml, data=d, vcov={"CRV1": cluster})
    nombres = list(fit._coefnames)
    b = pd.Series(np.asarray(fit.coef()), index=nombres)
    Vc = pd.DataFrame(np.asarray(fit._vcov), index=nombres, columns=nombres)
    G = d[cluster].nunique()
    base = {"N": int(fit._N), "unidades": d["unidad"].nunique(), "G": G, "y": y,
            "omitidos": ";".join(sorted(set(regs_ok) - set(nombres)) + sin_var)}
    base.update(etiqueta or {})
    if boot:
        X = np.column_stack([d[nombres].to_numpy(float), _dummies(d, fe)])
        yv = d[y].to_numpy(float)
        # control: la estimación con indicadoras reproduce a pyfixest
        bx = np.linalg.lstsq(X, yv, rcond=None)[0][: len(nombres)]
        assert np.allclose(bx, b.values, atol=1e-6 * (1 + np.abs(b.values).max())), "indicadoras ≠ pyfixest"
    filas = []
    for nombre, pesos in pruebas.items():
        if any(k not in nombres for k in pesos):
            filas.append({**base, "termino": nombre, "estimado": np.nan, "ee": np.nan, "t": np.nan,
                          "p_conv": np.nan, "p_wcb": np.nan, "nota": "término omitido"})
            continue
        av = np.array([pesos.get(k, 0.0) for k in nombres])
        est = float(av @ b.values)
        ee = float(np.sqrt(av @ Vc.values @ av))
        t = est / ee
        p_conv = float(2 * stats.t.sf(abs(t), G - 1))
        p_wcb = np.nan
        if boot:
            a_full = np.concatenate([av, np.zeros(X.shape[1] - len(nombres))])
            _, p_wcb = wcr(yv, X, a_full, d[cluster].to_numpy())
        filas.append({**base, "termino": nombre, "estimado": est, "ee": ee, "t": t,
                      "p_conv": p_conv, "p_wcb": p_wcb, "nota": base.get("nota", "")})
    for nombre, terms in (conjuntas or {}).items():
        if any(k not in nombres for k in terms):
            continue
        R = np.array([[1.0 if k == tt else 0.0 for k in nombres] for tt in terms])
        rb = R @ b.values
        W = float(rb @ np.linalg.pinv(R @ Vc.values @ R.T) @ rb) / len(terms)
        filas.append({**base, "termino": nombre, "estimado": W, "ee": np.nan, "t": np.nan,
                      "p_conv": float(stats.f.sf(W, len(terms), G - 1)), "p_wcb": np.nan,
                      "nota": f"Wald conjunta CRV1, F({len(terms)}, {G - 1}); el valor en 'estimado' es F"})
    return filas


def pruebas_basicas(m: str, sufijo: str = "") -> dict[str, dict[str, float]]:
    """b1 (filo), b2 (diferencia embalse) y b1 + b2 (embalse)."""
    D, DE = f"D_{m}{sufijo}", f"DE_{m}{sufijo}"
    return {"b1 (filo)": {D: 1.0}, "b2 (embalse − filo)": {DE: 1.0}, "b1 + b2 (embalse)": {D: 1.0, DE: 1.0}}


def a_markdown(df: pd.DataFrame, cols: list[str] | None = None, dec: int = 3) -> str:
    d = df[cols] if cols else df
    d = d.copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.{dec}f}")
    enc = "| " + " | ".join(map(str, d.columns)) + " |\n|" + "---|" * len(d.columns) + "\n"
    return enc + "\n".join("| " + " | ".join(map(str, r)) + " |" for r in d.to_numpy())


def guardar(df: pd.DataFrame, nombre: str, titulo: str, nota: str = "", cols: list[str] | None = None) -> None:
    df.to_csv(TAB / f"{nombre}.csv", index=False, encoding="utf-8")
    (TAB / f"{nombre}.md").write_text(f"# {titulo}\n\n{nota}\n\n{a_markdown(df, cols)}\n", encoding="utf-8")
