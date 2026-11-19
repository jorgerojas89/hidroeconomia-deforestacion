# T7 · Resumen de la estimación (19-nov-2026)

Especificación de 4.5 sin cambios. 524 unidad-año, 26 unidades (14 embalse, 12 filo), 10 sistemas A; efectos fijos de unidad y año, lluvia y trasvases de Miel I. FC en puntos porcentuales. p: convencional (CRV1, t con 9 gl) / *wild cluster bootstrap* (Webb, 9.999 réplicas).

## Cada medida frente al criterio de 4.5

| Medida | b1 filo (EE) | p conv / WCB | b1 + b2 embalse | p F conv / WCB | ¿Cumple? |
|---|---|---|---|---|---|
| Acumulado, % del bosque 2000 | −1,07 (0,42) | 0,032 / 0,294 | 0,35 | 0,78 / 0,78 | Con p convencional sí; con bootstrap no |
| Flujo del año, miles de ha | +3,30 (10,3) | 0,76 / 0,93 | 0,92 | 0,61 / 0,68 | No (b1 positivo y nulo) |
| Flujo del año, % del bosque | −0,38 (6,8) | 0,96 / 0,95 | −1,53 | 0,89 / 0,87 | No |

Las dos medidas no coinciden. El acumulado apunta en la dirección de la hipótesis: un punto más de bosque perdido baja el FC de las centrales a filo en 1,07 puntos, y en las de embalse no hay efecto (b1 + b2 ≈ 0). Pero solo es significativo con el p convencional. Con el bootstrap, que es el p fiable con 10 grupos, p = 0,29. La diferencia se explica porque las 12 centrales a filo están en 5 sistemas, 6 de ellas en el de Ituango: b1 se identifica con muy pocos grupos. El flujo anual, en hectáreas o en %, no muestra ningún efecto.

## Qué pruebas lo sostienen y cuáles no (medida acumulada, b1 filo)

**Lo sostienen (mismo signo y tamaño parecido; ninguna con bootstrap < 0,05):**
- Rezagos (4.3.2): suma de t a t−3 = −1,07 (0,023 / 0,30). En el acumulado los rezagos casi coinciden con el valor del año.
- Época seca propia (4.3.3): −1,13 (0,034 / 0,30); dic–mar −0,97 (0,06 / 0,41).
- Placebo (4.3.4): los adelantos no son significativos (Wald 0,64).
- Sin El Niño (4.3.5): −0,93 (0,095 / 0,36).
- Muestra (4.3.8): con años parciales −1,12; sin Miel I 2001–2013 −1,09; regulación continua −1,10 y la interacción con días de regulación es positiva (0,34; p 0,14 / 0,23), como predice la hipótesis.
- Influencia (4.3.9): el signo nunca cambia al quitar una unidad o un sistema (rango −3,15 a −0,43).

**No lo sostienen:**
- El efecto no se concentra en los meses secos: la diferencia seca − no seca en filo es −0,11 (0,31 / 0,11). En los meses no secos es igual (−1,15).
- Caudales (4.3.6), la prueba del mecanismo: el CV diario no sube con la deforestación (acumulado −0,008; 0,12 / 0,27, signo contrario al esperado) y el caudal base no cambia. Solo 216 unidad-año con serie diaria, 8 sistemas.
- Muestra: sin FC > 1, −0,54 (0,08 / 0,25); sin años con meses sin registro, −0,72 (0,29 / 0,81); solo cuencas no anidadas, −1,68 (0,17 / 0,86); cascada agrupada por sistema, −0,43 (0,86 / 0,88).
- Influencia: el p convencional pasa de 0,05 al quitar Caracolí, Pajarito, Río Grande, Riofrío, Sonsón, o los sistemas Ituango o Porce III. Sin Río Grande b1 cae a −0,43.
- Errores alternativos: por unidad 0,21 / 0,24; por sistema B 0,038 / 0,38.
- Regresión por unidad: en filo, 7 de 12 negativas, 2 negativas significativas (La Herradura, La Vuelta) y 2 positivas significativas (Amoyá, Sonsón); promedio ponderado −0,27 (p 0,78). En embalse el promedio es positivo (+1,9; p 0,03).
- Flujo, placebo: con el flujo en %, los adelantos sí son conjuntamente significativos (Wald 0,002 convencional; suma 0,12 / 0,057). Es una señal de factor omitido en esa medida.

**Pendiente:** fuente alterna SMByC (4.3.7), sin datos.

## Lectura

Con la especificación fijada, la hipótesis no se confirma con el estándar de inferencia que se fijó para 10 grupos. La medida acumulada da la dirección y el tamaño esperados y es estable en la mayoría de las pruebas. Pero no pasa el bootstrap, no se concentra en la época seca y la prueba de caudales no la respalda. El flujo anual no muestra efecto. Es un resultado publicable como "efecto acumulado de signo esperado, impreciso con 26 unidades", que gana potencia si el IGAC pasa más cuencas a "ok".
