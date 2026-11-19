"""
Tesis 2.0 · T2 · Historia de capacidad efectiva neta por recurso (XM), 2000-hoy,
y registro de cambios (repotenciaciones, ampliaciones, retiros) con su fecha.

Uso (en el Mac, desde 03_tesis):
    python3 -m pip install pydataxm pandas openpyxl requests
    python3 03_codigo/00_tabla_maestra/descargar_capacidad_historica_xm.py            # solo capacidad
    python3 03_codigo/00_tabla_maestra/descargar_capacidad_historica_xm.py --gen-max  # + máximo horario de generación por año

Salidas:
    02_datos/crudos/xm_capacidad/CapEfecNeta_Recurso_AAAA.csv   (una por año, sin tocar)
    02_datos/tabla_maestra/cambios_capacidad_xm.csv             recurso, fecha, MW antes, MW después
    02_datos/tabla_maestra/capacidad_anual_xm.csv               recurso × año: capacidad promedio del año (la que pide la sección 4.5)
    02_datos/tabla_maestra/gen_max_horaria_anual_xm.csv         (con --gen-max) recurso × año: máximo MWh en una hora

Si XM no tiene CapEfecNeta para los primeros años, el script lo dice y el máximo
horario de generación (--gen-max) sirve como capacidad observada para esos años.
Se puede interrumpir y volver a correr: no repite años ya descargados.
"""
import sys
from datetime import date
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
RAW = BASE / "02_datos" / "crudos" / "xm_capacidad"
OUT = BASE / "02_datos" / "tabla_maestra"
RAW.mkdir(parents=True, exist_ok=True)
HOY = date.today()
ANIOS = range(2000, HOY.year + 1)


def api():
    from pydataxm.pydataxm import ReadDB
    return ReadDB()


def bajar_anio(x, metric, entity, anio):
    ini, fin = date(anio, 1, 1), min(date(anio, 12, 31), HOY)
    try:
        df = x.request_data(metric, entity, ini, fin)
    except Exception as e:
        print(f"  {metric} {anio}: error {e}")
        return pd.DataFrame()
    return df if df is not None else pd.DataFrame()


def col(df, *claves):
    for c in df.columns:
        if any(k in c.lower() for k in claves):
            return c
    raise KeyError(f"No encuentro columna {claves} en {list(df.columns)}")


def main():
    x = api()
    partes = []
    for a in ANIOS:
        f = RAW / f"CapEfecNeta_Recurso_{a}.csv"
        if not f.exists():
            print(f"CapEfecNeta {a}…")
            df = bajar_anio(x, "CapEfecNeta", "Recurso", a)
            if df.empty:
                print(f"  sin datos para {a}")
                continue
            df.to_csv(f, index=False, encoding="utf-8-sig")
        partes.append(pd.read_csv(f))
    if not partes:
        sys.exit("XM no devolvió capacidad. Revisa conexión.")
    cap = pd.concat(partes, ignore_index=True)
    cfecha, ccod, cval = col(cap, "date"), col(cap, "code"), col(cap, "value")
    cap[cfecha] = pd.to_datetime(cap[cfecha]).dt.date
    cap = cap[[cfecha, ccod, cval]].rename(columns={cfecha: "fecha", ccod: "codigo", cval: "valor"})
    # XM reporta en kW o MW según la métrica; se normaliza a MW
    if cap.valor.max() > 50000:
        cap["valor"] = cap.valor / 1000
    cap = cap.sort_values(["codigo", "fecha"]).drop_duplicates(["codigo", "fecha"])
    print(f"Capacidad: {cap.fecha.min()} a {cap.fecha.max()}, {cap.codigo.nunique()} recursos")
    if cap.fecha.min() > date(2001, 1, 1):
        print(f"OJO: XM solo tiene capacidad desde {cap.fecha.min()}. Para antes, usa --gen-max.")

    # registro de cambios
    cap["antes"] = cap.groupby("codigo").valor.shift()
    ch = cap[cap.antes.notna() & (cap.valor.round(3) != cap.antes.round(3))].copy()
    primeros = cap.groupby("codigo").first().reset_index().assign(antes=None)
    ch = pd.concat([primeros, ch]).sort_values(["codigo", "fecha"])
    ch["tipo"] = ch.apply(lambda r: "primer registro" if pd.isna(r.antes) else
                          ("aumento" if r.valor > r.antes else "reducción"), axis=1)
    ch = ch.rename(columns={"antes": "mw_antes", "valor": "mw_despues"})
    ch[["codigo", "fecha", "mw_antes", "mw_despues", "tipo"]].to_csv(
        OUT / "cambios_capacidad_xm.csv", index=False, encoding="utf-8-sig")

    cap["anio"] = pd.to_datetime(cap.fecha).dt.year
    cap.groupby(["codigo", "anio"]).valor.mean().round(3).unstack().to_csv(
        OUT / "capacidad_anual_xm.csv", encoding="utf-8-sig")
    print(f"Cambios registrados: {(ch.tipo != 'primer registro').sum()}")

    if "--gen-max" in sys.argv:
        filas = []
        for a in ANIOS:
            f = RAW / f"GenMaxHora_{a}.csv"
            if not f.exists():
                print(f"Generación horaria {a}…")
                g = bajar_anio(x, "Gene", "Recurso", a)
                if g.empty:
                    continue
                horas = [c for c in g.columns if "hour" in c.lower()]
                gc = col(g, "code")
                g["max_h"] = g[horas].max(axis=1)
                m = g.groupby(gc).max_h.max().reset_index().rename(columns={gc: "codigo"})
                m["anio"] = a
                m.to_csv(f, index=False)
            filas.append(pd.read_csv(f))
        if filas:
            gm = pd.concat(filas)
            if gm.max_h.max() > 50000:
                gm["max_h"] = gm.max_h / 1000          # kWh -> MWh
            gm.pivot(index="codigo", columns="anio", values="max_h").round(3).to_csv(
                OUT / "gen_max_horaria_anual_xm.csv", encoding="utf-8-sig")
    print("Listo.")


if __name__ == "__main__":
    main()
