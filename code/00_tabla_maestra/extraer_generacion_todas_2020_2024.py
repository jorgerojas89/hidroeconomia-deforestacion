import pandas as pd, re, sys
from pathlib import Path
D=Path(sys.argv[1]); out=[]
for y in range(2020,2025):
    for f in sorted(D.glob(f"Generacion_(kWh)*{y}*.xls*")):
        crudo=pd.read_excel(f,engine="calamine",header=None,nrows=15)
        fila=next(i for i,r in crudo.iterrows() if str(r.iloc[0]).strip().lower()=="fecha")
        df=pd.read_excel(f,engine="calamine",header=fila)
        df.columns=[str(c).strip() for c in df.columns]
        horas=[c for c in df.columns if re.fullmatch(r"\d{1,2}(\.0+)?",c)]
        get=lambda *ks: next((df[c] for c in df.columns if any(c.lower().startswith(k) for k in ks)), pd.Series([None]*len(df)))
        o=pd.DataFrame({"fecha":pd.to_datetime(df.Fecha).dt.date,"recurso":df.Recurso.astype(str).str.strip(),
          "codigo":get("código recurso","codigo recurso").values,"tipo":get("tipo generación","tipo de gener","tipo gener").astype(str).str.strip().str.upper().values,
          "combustible":get("combustible").values,"agente":get("código agente","codigo agente").values,
          "despacho":get("tipo despacho","tipo de despacho").values,"menor":get("es menor").values,
          "clasificacion":get("clasificación","clasificacion").values,
          "mwh":df[horas].apply(pd.to_numeric,errors="coerce").sum(axis=1,min_count=1).values/1000})
        print(f.name,len(o),len(horas),o.fecha.min(),o.fecha.max(),o.mwh.sum()/1e6,"TWh",flush=True)
        out.append(o)
a=pd.concat(out)
print("dups",a.duplicated(["fecha","recurso"]).sum())
a.to_csv(Path.home()/"work/gen_2020_2024.csv.gz",index=False)
print(a.groupby([pd.to_datetime(a.fecha).dt.year,"tipo"]).mwh.sum().unstack().round(0).to_string())
