"""
Tesis 2.0 · T2 · Descarga el listado vigente de recursos de generación de XM
y la capacidad efectiva neta por recurso.

Uso (en el Mac, desde la carpeta 03_tesis):
    python3 -m pip install pydataxm pandas openpyxl requests
    python3 03_codigo/00_tabla_maestra/descargar_listado_xm.py

Escribe en 02_datos/crudos/xm_listado/:
    ListadoRecursos_AAAAMMDD.csv        todos los recursos (código, nombre, tipo, fuente, fecha de operación, estado)
    ListadoRecursos_hidro_AAAAMMDD.csv  solo los de fuente agua
    CapEfecNeta_Recurso_AAAAMMDD.csv    capacidad efectiva neta por recurso (último día con dato)
    columnas_descargadas.txt            nombres de columnas, para ajustar el cruce si XM los cambia

Después vuelve a correr construir_tabla_maestra.py: si encuentra el listado,
llena los códigos XM que faltan por coincidencia de nombre.
"""
import sys, json
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[2]          # .../03_tesis
OUT = BASE / "02_datos" / "crudos" / "xm_listado"
OUT.mkdir(parents=True, exist_ok=True)
HOY = date.today()
TAG = HOY.strftime("%Y%m%d")
API = "https://servapibi.xm.com.co"


def con_pydataxm(metric, entity, ini, fin):
    from pydataxm.pydataxm import ReadDB
    return ReadDB().request_data(metric, entity, ini, fin)


def con_requests(metric, entity, ini, fin):
    """Respaldo sin pydataxm: llamada directa a la API pública de XM."""
    import requests
    ruta = "/lists" if metric.startswith("Listado") else "/daily"
    body = {"MetricId": metric, "StartDate": ini.isoformat(),
            "EndDate": fin.isoformat(), "Entity": entity, "Filter": []}
    r = requests.post(API + ruta, json=body, timeout=120)
    r.raise_for_status()
    items = r.json().get("Items", [])
    filas = []
    for it in items:
        for clave in ("ListEntities", "DailyEntities", "HourlyEntities"):
            for e in it.get(clave, []) or []:
                fila = {"Date": it.get("Date")}
                fila.update({f"Values_{k}": v for k, v in (e.get("Values") or {}).items()})
                filas.append(fila)
    return pd.DataFrame(filas)


def bajar(metric, entity, ini, fin):
    try:
        df = con_pydataxm(metric, entity, ini, fin)
        if df is not None and len(df):
            print(f"  {metric}: {len(df)} filas (pydataxm)")
            return df
    except Exception as e:
        print(f"  pydataxm falló para {metric}: {e}. Pruebo directo con la API…")
    df = con_requests(metric, entity, ini, fin)
    print(f"  {metric}: {len(df)} filas (API directa)")
    return df


def main():
    cols = {}
    print("1/2 Listado de recursos…")
    lst = bajar("ListadoRecursos", "Sistema", HOY - timedelta(days=3), HOY - timedelta(days=1))
    if lst.empty:
        sys.exit("XM no devolvió el listado. Revisa conexión o intenta más tarde.")
    lst = lst.drop_duplicates(subset=[c for c in lst.columns if c.lower() != "date"])
    lst.to_csv(OUT / f"ListadoRecursos_{TAG}.csv", index=False, encoding="utf-8-sig")
    cols["ListadoRecursos"] = list(lst.columns)
    fuente = next((c for c in lst.columns if "enersource" in c.lower() or "fuente" in c.lower()), None)
    tipo = next((c for c in lst.columns if c.lower().endswith("_type")), None)
    if fuente:
        hid = lst[lst[fuente].astype(str).str.upper().str.contains("AGUA|HIDR")]
    elif tipo:
        hid = lst[lst[tipo].astype(str).str.upper().str.contains("HIDR")]
    else:
        hid = lst
    hid.to_csv(OUT / f"ListadoRecursos_hidro_{TAG}.csv", index=False, encoding="utf-8-sig")
    print(f"  hidráulicos: {len(hid)}")

    print("2/2 Capacidad efectiva neta por recurso…")
    cap = pd.DataFrame()
    for atras in (2, 5, 10, 20):           # XM publica con rezago; busco el último día con dato
        d = HOY - timedelta(days=atras)
        try:
            cap = bajar("CapEfecNeta", "Recurso", d, d)
        except Exception as e:
            print(f"  sin dato para {d}: {e}")
        if len(cap):
            break
    if len(cap):
        cap.to_csv(OUT / f"CapEfecNeta_Recurso_{TAG}.csv", index=False, encoding="utf-8-sig")
        cols["CapEfecNeta"] = list(cap.columns)
    (OUT / "columnas_descargadas.txt").write_text(json.dumps(cols, indent=2, ensure_ascii=False))
    print(f"Listo. Archivos en {OUT}")


if __name__ == "__main__":
    main()
