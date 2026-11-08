# Revisión del informe

Se incorporaron predicciones, errores, métricas, navegación, filtros y textos al archivo `powerbi/observatorio_turismo.pbix` y se sincronizó su definición con el proyecto editable. También se recuperó V3: la matriz había sido reemplazada por V6 en el archivo recibido. No se corrigieron ni modificaron datos o resultados de los modelos.

## Evidencia obtenida

| Aspecto | Resultado comprobado |
|---|---|
| Ocho visualizaciones | V1 a V8 presentes, con matriz y dispersión en archivos distintos. |
| Enlaces | V1 → V2, V3 → V5 y V7 → V8 por filtrado, ejercidos en Desktop. |
| Jerarquía temporal | V1 conserva año, trimestre y mes y los controles de bajar y subir. |
| Detalle | Región como parámetro de drillthrough desde V4; en Desktop conservó 2025, mostró la participación por país y Volver regresó a Llegadas y mercados. |
| Resumen | Tarjetas de total, máximo mensual y mes del máximo para resolver la primera tarea sin depender del nivel de V1. |
| Controles | Año y mes sincronizados entre las tres páginas de análisis; mercado aplicado solo a las llegadas. |
| Contexto y limpieza | Tarjeta de filtros en las seis páginas y seis marcadores; Restablecer vista limpió años, selecciones entre gráficas y el modelo. |
| Mensajes | Con 2025, Temporadas y hospedaje muestra el aviso de falta de hospedaje sin ceros; sin modelo elegido, V7 deja en blanco el estimado y pide elegir uno. |
| Predicciones | V7 no suma estimaciones de modelos distintos; V8 y la tabla conservan la comparación de los tres modelos. |
| Observado | 63 filas únicas en el modelo importado; ninguna medida del informe suma Predicciones[observed]. |
| Métricas | MAE, RMSE y MAPE recalculados desde las 189 predicciones del propio `.pbix`, coincidentes con los CSV. |
| Estructura | Referencias válidas, sin objetos fuera del lienzo ni superpuestos; la definición de la carpeta coincide con la guardada en el `.pbix`. |
| Datos | El modelo guardado por Desktop se auditó contra los CSV: llegadas y predicciones coinciden y las métricas se recalculan igual. |
| Pruebas de código | 320 pruebas del repositorio aprobadas en Windows. |

Las comprobaciones estructurales se repiten con `python scripts/verificar_informe_powerbi.py`. Los resultados están en [revision_informe.json](revision_informe.json). La auditoría del modelo importado se repite con `python scripts/auditar_modelo_powerbi.py`, usando PBIXRay 0.15.5, y se guarda en [validacion_modelos_pbix.json](validacion_modelos_pbix.json). La verificación exige que el modelo del `.pbix` sea el mismo que registró la auditoría.

## Alcance de la comprobación

El 7 de noviembre de 2026 el informe se abrió en Power BI Desktop 2.159.1231.0 (64 bits) en Windows 11. Abrió sin errores. Las consultas de [comprobaciones.dax](../../powerbi/comprobaciones.dax) y [comprobaciones_finales.dax](../../powerbi/comprobaciones_finales.dax) se ejecutaron contra el modelo abierto y todas coincidieron con [resultados_esperados.md](resultados_esperados.md): total de 46.711.912,89, máximo de diciembre de 2019 con 449.114, llegadas de 2024 y 2025, observado de diciembre de 2025 igual con uno o con todos los modelos, métricas y errores de los tres modelos, peso de América Central y participación de El Salvador. Después de las correcciones, el parámetro `pCarpetaDatos`, que conservaba la ruta personal del equipo donde se cargaron los datos el 5 de noviembre, se cambió a `C:/Lab12/Laboratorio-10-Dashboard/data` y se ejecutó Actualizar. Las ocho tablas se recargaron sin errores desde los CSV del repositorio y las consultas de comprobación dieron los mismos valores.

Se recorrieron las seis páginas y se ejercieron los enlaces, el detalle, los segmentadores, los mensajes sin datos y Restablecer vista. El recorrido encontró problemas de presentación que se corrigieron antes de guardar:

- Los botones de navegación, Restablecer vista y Volver se mostraban vacíos, porque el texto y el relleno no tenían activada su visibilidad general. Se activaron y el botón de la página activa quedó en azul con texto blanco.
- Las tarjetas de total y máximo mostraban unidades abreviadas («47 mill.»); ahora muestran la cifra completa. La medida Llegadas del archivo tenía formato sin separador de miles y se le dio el formato `#,0`, el mismo de `model.bim`.
- V8 tenía tres paneles demasiado bajos para leer sus barras y usaba el azul de lo observado. Ahora ocupa el ancho de la página, sus paneles se leen y usa el naranja de lo estimado; la tabla de métricas y su glosario pasaron debajo.
- La gráfica de años del detalle asignaba un color por país, incluido el naranja reservado a lo estimado. Ahora usa un panel por mercado en azul, igual que V4.
- Títulos, subtítulos y notas que no cabían en su cuadro se ajustaron. V3 rotula «Año» y «Mes» y el eje de V6 dice «Llegadas».

Después de las correcciones se restableció la vista en todas las páginas, se dejó abierta Inicio y el archivo se guardó desde Desktop. Al guardar, Desktop reescribe la definición del informe y el modelo importado aunque los datos no cambien; por eso la carpeta `observatorio_turismo.Report/` se sincronizó con lo guardado y el modelo se volvió a auditar. Queda una observación menor sin cambiar: la información sobre herramientas de las barras del detalle rotula el país con el nombre de la columna, «origin».
