# Versión de 2019 (sin cambios)

Esta carpeta conserva lo que se publicó en este repositorio para la tesis de 2019. No se edita. El trabajo nuevo va en `code/` y `data/` en la raíz.

La misma versión está congelada en la etiqueta [`v2019`](https://github.com/jorgerojas89/hidroeconomia-deforestacion/tree/v2019).

| Ruta | Contenido | Ruta en 2019 |
|---|---|---|
| `README_2019.md` | README publicado en 2019 | `README.md` |
| `code/01_delimitacion_cuencas.R` | Delimitación de cuencas, versión ordenada (no se volvió a ejecutar) | `code/01_delimitacion_cuencas.R` |
| `code/original_2019/` | Scripts de delimitación tal como se usaron | `code/original_2019/` |
| `data/xm/` | Generación, volumen útil, caudales, precio de bolsa y capacidad, 2000–2018 | `data/xm/` |
| `data/upme/` | Tablas de centrales hidráulicas | `data/upme/` |
| `data/DF.xlsx` | Base de panel usada en la tesis (60 centrales) | No estaba publicada |

## Problemas conocidos de la base de 2019

Se documentan aquí para que nadie use `DF.xlsx` sin advertencia. El detalle está en `PLAN.md`, sección 2.

- Lluvia inválida en 2011, 2012 y 2013 (valores entre 11 y 12 en todas las cuencas).
- Factores de capacidad mayores que 1 (máximo 1,32).
- Algunas cuencas mal delimitadas (por ejemplo, San Carlos con 178 ha).
- Centrales sin generación o sin cuenca por errores de emparejamiento de nombres.
- No se conserva el script que produjo las tablas publicadas.

`DF.xlsx` sirve para comparar variable por variable con la base nueva (2001–2015), no para estimar.
