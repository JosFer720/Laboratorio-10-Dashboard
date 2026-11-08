# Capturas de las pruebas

Capturas de las dos interfaces tomadas en el mismo equipo Windows durante las pruebas de [resultados_pruebas.md](../resultados_pruebas.md). Las de Power BI están recortadas al lienzo del informe.

| Archivo | Versión | Contenido |
|---|---|---|
| `dash_prueba1.png` | Dash | Periodo de enero a diciembre de 2025: 3.352.289 llegadas y diciembre de 2025 con 365.573. |
| `powerbi_prueba1.png` | Power BI | Llegadas y mercados con 2025: tarjetas de total, máximo mensual y mes del máximo. |
| `dash_prueba2.png` | Dash | América Central elegida desde el peso regional: El Salvador con 1.582.845 y 73,8 %. |
| `powerbi_prueba2_region.png` | Power BI | V4 con 2025, antes de abrir el detalle de América Central. |
| `powerbi_prueba2.png` | Power BI | Detalle de América Central con 2025 conservado: El Salvador con 1,582,845 y 73.8 % de la región. |
| `dash_prueba3.png` | Dash | Error de LSTM en diciembre de 2025: observado 365.573, estimado 223.442, error −142.131. |
| `dash_prueba3_tabla.png` | Dash | Comparación de los tres modelos con MAE, RMSE y MAPE. |
| `powerbi_prueba3_v7.png` | Power BI | V7 con LSTM, observado y estimado de 2025. |
| `powerbi_prueba3.png` | Power BI | V8 filtrada a diciembre de 2025 desde V7, con el error de LSTM (−142,131), y la tabla de métricas. |

Las cuatro imágenes `dash_*_exportacion.png` son figuras exportadas de las respuestas del servidor Dash en el control HTTP (`../evidencia_http/`), con títulos de contexto agregados. No son capturas de la interfaz.
