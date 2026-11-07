# Revisión del informe

Se incorporaron predicciones, errores, métricas, navegación, filtros y textos al archivo `powerbi/observatorio_turismo.pbix` y se sincronizó su definición con el proyecto editable. También se recuperó V3: la matriz había sido reemplazada por V6 en el archivo recibido. No se corrigieron ni modificaron datos o resultados de los modelos.

## Evidencia obtenida

| Aspecto | Resultado comprobado |
|---|---|
| Ocho visualizaciones | V1 a V8 presentes, con matriz y dispersión en archivos distintos. |
| Enlaces | Definidos V1 → V2, V3 → V5 y V7 → V8 por filtrado. |
| Jerarquía temporal | V1 conserva año, trimestre y mes y los controles de bajar y subir. |
| Detalle | Región como parámetro de drillthrough desde V4, contexto temporal conservado, participación por país y botón de regreso. |
| Resumen | Tarjetas de total, máximo mensual y mes del máximo para resolver la primera tarea sin depender del nivel de V1. |
| Controles | Año y mes sincronizados entre las tres páginas de análisis; mercado aplicado solo a las llegadas. |
| Contexto y limpieza | Tarjeta de filtros en las seis páginas y seis marcadores con todos los estados. |
| Predicciones | V7 no suma estimaciones de modelos distintos; V8 y la tabla conservan la comparación de los tres modelos. |
| Observado | 63 filas únicas en el modelo importado; ninguna medida del informe suma Predicciones[observed]. |
| Métricas | MAE, RMSE y MAPE recalculados desde las 189 predicciones del propio `.pbix`, coincidentes con los CSV. |
| Estructura | 115 archivos de definición PBIR. Validador oficial 0.5.0: cero errores y cero advertencias. Referencias válidas, sin objetos fuera del lienzo ni superpuestos. |
| Datos | DataModel idéntico al commit recibido `a52f372`; el caché se puede leer y las llegadas y predicciones coinciden con los CSV. |
| Pruebas de código | 320 pruebas del repositorio actual y 171 de la referencia Dash aprobadas; tres tareas HTTP correctas. |

Las comprobaciones estructurales se repiten con `python scripts/verificar_informe_powerbi.py`. Los resultados están en [revision_informe.json](revision_informe.json). La auditoría opcional del caché se repite con `python scripts/auditar_modelo_powerbi.py`, usando PBIXRay 0.15.5, y se guarda en [validacion_modelos_pbix.json](validacion_modelos_pbix.json).

La revisión de distribución también comprobó los límites de los objetos y estimó el espacio de los textos a su tamaño declarado. Los esquemas de distribución usados para esa inspección no son capturas de Power BI ni se presentan como evidencia de ejecución.

## Alcance de la comprobación

Los cambios se prepararon en macOS. No hubo una sesión de Power BI Desktop disponible para abrir esta edición, ejecutar las quince medidas de informe, revisar su apariencia real o guardar el archivo desde Desktop. La herramienta oficial devolvió `HOST_UNAVAILABLE` con diagnóstico `UNSUPPORTED_OS` al consultar y abrir Desktop. La versión `2.159.1231.0 (64 bits)` corresponde a la versión documentada antes de estos cambios. La conformidad del JSON y la lectura de DataModel no prueban que todas las interacciones se ejecuten correctamente en Desktop.

En Windows falta comprobar esta edición con Actualizar y [comprobaciones_finales.dax](../../powerbi/comprobaciones_finales.dax), recorrer las seis páginas y ejercer los enlaces, el detalle, los segmentadores y cada marcador. Es necesario abrir y guardar el `.pbix` desde Desktop después de esa revisión. Las tres tareas de Dash se ejecutaron contra el servidor real; sus resultados y las limitaciones de la comparación están en [resultados_pruebas.md](resultados_pruebas.md). Los tiempos de HTTP no se presentan como tiempos de interacción. El [protocolo de interfaz](protocolo_pruebas.md) conserva pendientes sus mediciones y capturas.

La validación oficial detectó y permitió corregir propiedades de texto de segmentadores, referencias del tema, metadatos de los proyectos y un tooltip incompatible. La revisión de las tareas también corrigió el detalle regional para conservar el año y añadió las tarjetas de máximo mensual y la participación dentro de la región. Estos ajustes no cambian los CSV ni el modelo importado.

Para las ediciones externas se conserva el contenido importado del modelo y se reconstruye el contenedor con `scripts/empaquetar_powerbi.py`. Las referencias guardadas en `SecurityBindings` dejan de corresponder al informe editado; el empaquetado retira esa entrada desactualizada y Desktop la vuelve a generar al guardar. La comprobación pendiente de apertura se mantiene explícita.
