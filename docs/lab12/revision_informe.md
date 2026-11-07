# Revisión del informe

Se incorporaron predicciones, errores, métricas, navegación, filtros y textos al archivo `powerbi/observatorio_turismo.pbix` y se sincronizó su definición con el proyecto editable. También se recuperó V3: la matriz había sido reemplazada por V6 en el archivo recibido. No se corrigieron ni modificaron datos o resultados de los modelos.

## Evidencia obtenida

| Aspecto | Resultado comprobado |
|---|---|
| Ocho visualizaciones | V1 a V8 presentes, con matriz y dispersión en archivos distintos. |
| Enlaces | Definidos V1 → V2, V3 → V5 y V7 → V8 por filtrado. |
| Jerarquía temporal | V1 conserva año, trimestre y mes y los controles de bajar y subir. |
| Detalle | Región como parámetro de drillthrough, página oculta y botón de regreso. |
| Controles | Año y mes sincronizados entre las tres páginas de análisis; mercado aplicado solo a las llegadas. |
| Contexto y limpieza | Tarjeta de filtros en las seis páginas y seis marcadores con todos los estados. |
| Predicciones | V7 no suma estimaciones de modelos distintos; V8 y la tabla conservan la comparación de los tres modelos. |
| Observado | 63 filas únicas en el modelo importado; ninguna medida del informe suma Predicciones[observed]. |
| Métricas | MAE, RMSE y MAPE recalculados desde las 189 predicciones del propio `.pbix`, coincidentes con los CSV. |
| Estructura | 112 archivos de definición PBIR conformes a los esquemas oficiales consultados. Referencias válidas, sin objetos fuera del lienzo ni superpuestos. |
| Datos | DataModel idéntico al commit recibido `a52f372`; el caché se puede leer y las llegadas y predicciones coinciden con los CSV. |
| Pruebas de código | 45 pruebas de fuentes, modelos, preparación y estructura del informe aprobadas. |

Las comprobaciones estructurales se repiten con `python scripts/verificar_informe_powerbi.py`. Los resultados están en [revision_informe.json](revision_informe.json). La auditoría opcional del caché se repite con `python scripts/auditar_modelo_powerbi.py`, usando PBIXRay 0.15.5, y se guarda en [validacion_modelos_pbix.json](validacion_modelos_pbix.json).

La revisión de distribución también comprobó los límites de los objetos y estimó el espacio de los textos a su tamaño declarado. Los esquemas de distribución usados para esa inspección no son capturas de Power BI ni se presentan como evidencia de ejecución.

## Alcance de la comprobación

Los cambios se prepararon en macOS. No hubo una sesión de Power BI Desktop disponible para abrir esta edición, ejecutar las doce medidas de informe, revisar su apariencia real o guardar el archivo desde Desktop. La versión `2.159.1231.0 (64 bits)` corresponde a la versión documentada antes de estos cambios. La conformidad del JSON y la lectura de DataModel no prueban que todas las interacciones se ejecuten correctamente en Desktop.

En Windows falta comprobar esta edición con Actualizar y [comprobaciones_finales.dax](../../powerbi/comprobaciones_finales.dax), recorrer las seis páginas y ejercer los enlaces, el detalle, los segmentadores y cada marcador. Es necesario abrir y guardar el `.pbix` desde Desktop después de esa revisión. Las tres pruebas comparativas, sus tiempos y sus capturas se obtienen con el [protocolo existente](protocolo_pruebas.md); no se han inventado mediciones ni capturas.

Para las ediciones externas se conserva el contenido importado del modelo y se reconstruye el contenedor con `scripts/empaquetar_powerbi.py`. Las referencias guardadas en `SecurityBindings` dejan de corresponder al informe editado; el empaquetado retira esa entrada desactualizada y Desktop la vuelve a generar al guardar. La comprobación pendiente de apertura se mantiene explícita.
