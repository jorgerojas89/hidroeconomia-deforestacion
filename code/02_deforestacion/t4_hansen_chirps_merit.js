/**** Tesis 2.0 — T4: deforestación (Hansen GFC v1.12), lluvia (CHIRPS v3) y validación de cuencas (MERIT Hydro)
 * Pegar completo en https://code.earthengine.google.com  y presionar Run.
 * Especificación: PLAN sección 4.5 (bosque = treecover2000 >= 30 %; lluvia CHIRPS promedio de cuenca; cuenca = ATCH IGAC).
 * Salidas (pestaña Tasks → RUN en cada una; quedan en Google Drive, carpeta tesis_T4):
 *   ee_hansen_unidad.csv      una fila por unidad: área, bosque 2000 y pérdida 2001–2024 en ha (formato ancho)
 *   ee_chirps_unidad_mes.csv  una fila por unidad y mes 2000-01 a 2024-12: lluvia media de la cuenca (mm/mes)
 *   ee_chirps_dias_mes.csv    días con imagen CHIRPS por mes (control de huecos)
 *   ee_merit_unidad.csv       área drenada máxima de MERIT dentro de cada cuenca y su ubicación (validación)
 * Los cálculos derivados (acumulado, %, lluvia anual, pruebas) los hace procesar_t4.py. */

// ---------------- 1. PARÁMETROS (editar) ----------------
var ASSET  = 'projects/TU-PROYECTO/assets/atch_unidad_ee';   // ruta que te da Earth Engine al subir el zip
var PRUEBA = true;    // true = solo 3 cuencas y resultados en la consola; false = las 34 y exportación
var UNIDADES_PRUEBA = ['RIO GRANDE', 'AMOYA LA ESPERANZA', 'GUAVIO'];   // chica, mediana filo, embalse
var CARPETA_DRIVE = 'tesis_T4';
var UMBRAL_BOSQUE = 30;      // % de cobertura arbórea en 2000
var ANIO_INI = 2001, ANIO_FIN = 2024;

// ---------------- 2. CUENCAS ----------------
var cuencas = ee.FeatureCollection(ASSET).select(['unidad', 'codigo_xm', 'atch_ha', 'n_proy']);
if (PRUEBA) cuencas = cuencas.filter(ee.Filter.inList('unidad', UNIDADES_PRUEBA));
print('Unidades:', cuencas.size(), cuencas.aggregate_array('unidad'));
Map.centerObject(cuencas, 7);
Map.addLayer(cuencas.style({color: 'blue', fillColor: '00000000'}), {}, 'ATCH IGAC');

// ---------------- 3. HANSEN: bosque 2000 y pérdida anual, a 30 m en la grilla nativa ----------------
var gfc = ee.Image('UMD/hansen/global_forest_change_2024_v1_12');
var bosque = gfc.select('treecover2000').gte(UMBRAL_BOSQUE);
var lossyear = gfc.select('lossyear');            // 1..24 = 2001..2024; 0 = sin pérdida
var ha = ee.Image.pixelArea().divide(1e4);        // área real de cada píxel en ha
var GRILLA_HANSEN = [0.00025, 0, -180, 0, -0.00025, 80];   // misma grilla del producto (sin remuestreo)

var bandas = [ha.rename('area_ha'), ha.multiply(bosque).rename('bosque2000_ha'),
              ha.multiply(bosque).multiply(lossyear.gt(0)).rename('perdida_total_ha'),
              ha.multiply(lossyear.gt(0)).rename('perdida_sin_mascara_ha')];   // robustez: sin umbral de bosque
for (var y = ANIO_INI; y <= ANIO_FIN; y++) {
  bandas.push(ha.multiply(bosque).multiply(lossyear.eq(y - 2000)).rename('perdida_' + y));
}
var imgHansen = ee.Image.cat(bandas);
var hansen = imgHansen.reduceRegions({
  collection: cuencas, reducer: ee.Reducer.sum(),
  crs: 'EPSG:4326', crsTransform: GRILLA_HANSEN, tileScale: 8
});

// ---------------- 4. CHIRPS v3: lluvia mensual promedio de cuenca ----------------
var chirps = ee.ImageCollection('UCSB-CHC/CHIRPS/V3/DAILY_RNL').select('precipitation');
var inicio = ee.Date.fromYMD(2000, 1, 1);
var nMeses = (ANIO_FIN - 2000 + 1) * 12;          // 2000-01 .. 2024-12 (2000 sirve para rezagos)
var idx = ee.List.sequence(0, nMeses - 1);
var mesesImg = ee.ImageCollection.fromImages(idx.map(function (i) {
  var d = inicio.advance(i, 'month');
  return chirps.filterDate(d, d.advance(1, 'month')).sum().rename('p');
}));
var nombres = idx.map(function (i) { return ee.String('p_').cat(inicio.advance(i, 'month').format('YYYY_MM')); });
var imgChirps = mesesImg.toBands().rename(nombres);
// Grilla 10 veces más fina que CHIRPS (0,005°): el promedio queda ponderado por área, incluso en cuencas
// más chicas que un píxel de CHIRPS (Río Grande tiene 16 km²; un píxel de CHIRPS, ~30 km²).
var lluviaAncho = imgChirps.reduceRegions({
  collection: cuencas, reducer: ee.Reducer.mean(),
  crs: 'EPSG:4326', crsTransform: [0.005, 0, -180, 0, -0.005, 50], tileScale: 4
});
// a formato largo: unidad × mes
var lluviaLargo = lluviaAncho.map(function (f) {
  return ee.FeatureCollection(nombres.map(function (n) {
    n = ee.String(n);
    return ee.Feature(null, {
      unidad: f.get('unidad'), codigo_xm: f.get('codigo_xm'),
      anio: ee.Number.parse(n.slice(2, 6)), mes: ee.Number.parse(n.slice(7, 9)),
      lluvia_mm: f.get(n)
    });
  }));
}).flatten();
var diasMes = ee.FeatureCollection(idx.map(function (i) {
  var d = inicio.advance(i, 'month');
  return ee.Feature(null, {anio: d.get('year'), mes: d.get('month'),
    n_imagenes: chirps.filterDate(d, d.advance(1, 'month')).size(),
    dias_mes: d.advance(1, 'month').difference(d, 'day')});
})).map(function (f) { return f.set('completo', ee.Number(f.get('n_imagenes')).eq(f.get('dias_mes'))); });

// ---------------- 5. MERIT Hydro: validación de cuencas sin coordenadas de captación ----------------
// Si la ATCH es una cuenca hidrológica, su píxel de mayor área drenada es la salida y esa área (upa)
// debe parecerse al área de la ATCH. Razón << 1: cuenca con trasvases o varias salidas (p. ej. Miel I).
// Razón >> 1: un río mayor toca el polígono o la delimitación no cierra. Se recorta 300 m hacia adentro
// para que no cuente un río vecino que corre pegado al borde.
var merit = ee.Image('MERIT/Hydro/v1_0_1');
var upaLonLat = merit.select('upa').addBands(ee.Image.pixelLonLat());
var meritRes = cuencas.map(function (f) {
  var g = f.geometry().buffer(-300, 100);
  var r = upaLonLat.reduceRegion({reducer: ee.Reducer.max(3), geometry: g,
    scale: 92.77, maxPixels: 1e10, tileScale: 4});
  var upaHa = ee.Number(r.get('max')).multiply(100);
  return f.setGeometry(null).set({
    upa_max_ha: upaHa, salida_lon: r.get('max1'), salida_lat: r.get('max2'),
    razon_upa_atch: upaHa.divide(f.get('atch_ha'))});
});

// ---------------- 6. PRUEBA o EXPORTACIÓN ----------------
var colsHansen = ['unidad', 'codigo_xm', 'atch_ha', 'area_ha', 'bosque2000_ha', 'perdida_total_ha', 'perdida_sin_mascara_ha'];
for (var y2 = ANIO_INI; y2 <= ANIO_FIN; y2++) colsHansen.push('perdida_' + y2);

if (PRUEBA) {
  print('HANSEN (ha). Revisa: area_ha ≈ atch_ha; perdida_total_ha = suma de perdida_2001..2024', hansen);
  print('CHIRPS, primeros 24 meses de la primera cuenca (mm/mes)', lluviaLargo.limit(24));
  print('CHIRPS: meses con días faltantes (debe ser 0)', diasMes.filter(ee.Filter.eq('completo', 0)).size());
  print('MERIT: razón área drenada / ATCH (cerca de 1 = coherente)', meritRes);
  Map.addLayer(gfc.select('treecover2000').updateMask(bosque).clipToCollection(cuencas), {min: 30, max: 100, palette: ['ccffcc', '006600']}, 'Bosque 2000', false);
  Map.addLayer(lossyear.selfMask().updateMask(bosque).clipToCollection(cuencas), {min: 1, max: 24, palette: ['yellow', 'red']}, 'Pérdida 2001-2024');
  Map.addLayer(merit.select('upa').clipToCollection(cuencas), {min: 0, max: 5000, palette: ['ffffff', '0000ff']}, 'MERIT área drenada', false);
} else {
  Export.table.toDrive({collection: hansen, description: 'ee_hansen_unidad', folder: CARPETA_DRIVE,
    fileFormat: 'CSV', selectors: colsHansen});
  Export.table.toDrive({collection: lluviaLargo, description: 'ee_chirps_unidad_mes', folder: CARPETA_DRIVE,
    fileFormat: 'CSV', selectors: ['unidad', 'codigo_xm', 'anio', 'mes', 'lluvia_mm']});
  Export.table.toDrive({collection: diasMes, description: 'ee_chirps_dias_mes', folder: CARPETA_DRIVE,
    fileFormat: 'CSV', selectors: ['anio', 'mes', 'n_imagenes', 'dias_mes']});
  Export.table.toDrive({collection: meritRes, description: 'ee_merit_unidad', folder: CARPETA_DRIVE,
    fileFormat: 'CSV', selectors: ['unidad', 'codigo_xm', 'atch_ha', 'upa_max_ha', 'razon_upa_atch', 'salida_lon', 'salida_lat']});
  print('Listo: abre la pestaña Tasks (derecha) y presiona RUN en las 4 tareas.');
}
