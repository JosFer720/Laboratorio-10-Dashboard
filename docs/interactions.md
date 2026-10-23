# Exploración de llegadas

La aplicación se construye con `create_app(data_path, model_predictions_path, model_metrics_path)` y conserva los DataFrames validados en la configuración del servidor. Los callbacks los consultan sin modificarlos. `layout.py` define los componentes, `figures.py` construye las gráficas, `exploration.py` y `models.py` contienen helpers puros, y `callbacks.py` conecta las interacciones.

## Componentes

| Identificador | Propiedad | Uso |
|---|---|---|
| `arrivals-timeline` | `figure`, `clickData`, `selectedData` | Serie de llegadas observadas y selección de periodos. |
| `period-start` | `value` | Primer mes incluido, como `YYYY-MM-01`. |
| `period-end` | `value` | Último mes incluido, como `YYYY-MM-01`; es inclusivo. |
| `origin-filter` | `value` | Mercado de origen. |
| `time-detail` | `value` | `month`, `quarter` o `year`. |
| `clear-selection` | `n_clicks` | Restablece la selección al periodo completo del filtro. |
| `v1-selection` | `data` | Meses y mercado efectivos para otra visualización. |
| `market-breakdown` | `children` | Contenedor de la gráfica de mercados. |
| `market-chart` | `figure` | Barras de llegadas por mercado de origen para la selección. |
| `market-caption` | `children` | Mercado y periodo que muestra la gráfica de mercados. |
| `model-selector` | `value` | Identificador del modelo que se desea consultar. |
| `v7-model-selection` | `data` | Estado compartido mínimo del modelo elegido. |
| `model-evaluation-chart` | `figure` | Observado frente a estimado en la evaluación histórica. |
| `main-tabs` | `active_tab` | `arrivals`, `seasons`, `models` o `data`. |

Los mercados admiten `all`, `region:<origin_region>` y `origin:<origin>`, con los valores presentes en el DataFrame. `market_options()` genera las opciones y distingue país y agregado. Una región suma sus categorías existentes; no agrega nuevamente un subtotal. Los paneles permanecen montados al cambiar de pestaña. Los filtros conservan sus valores y se desactivan cuando no hay una gráfica que los utilice en la vista elegida.

## Selección compartida

`v1-selection` es un `dcc.Store` en memoria, independiente para cada sesión del navegador. Su contrato tiene cuatro campos:

```json
{
  "dates": ["2024-01-01", "2024-03-01"],
  "market": "all",
  "granularity": "month",
  "is_selected": true
}
```

`dates` contiene meses observados, únicos, ordenados y dentro de los filtros globales. Siempre usa fechas del primer día del mes, incluso al seleccionar un trimestre o un año. No debe sustituirse esta lista por un intervalo entre mínimo y máximo: una selección puede contener enero y marzo sin incluir febrero.

`market` conserva el valor del filtro de origen. `granularity` indica el nivel de detalle que produjo la selección. `is_selected` es `true` cuando hay puntos seleccionados y `false` cuando se usa el periodo completo del filtro. Al abrir o recargar la página, limpiar la selección, deseleccionar los puntos o cambiar un filtro global, se exponen todos los meses disponibles del filtro con `is_selected: false`. Si no hay filas, `dates` es `[]`; esto permite mostrar un mensaje sin intentar calcular participaciones sobre un total inexistente.

Cada punto de la serie incluye `customdata = [period_key, label, months]`. Las claves son `2024-07` para un mes, `2024Q3` para un trimestre y `2024` para un año. El callback acepta clics y selecciones de puntos, verifica esas claves contra las fechas filtradas y descarta selecciones vacías o antiguas. El zoom cambia la vista, pero no el estado compartido. La selección no se guarda en variables globales ni en el servidor.

## Consumir la selección

Una gráfica de mercados puede escuchar `Input("v1-selection", "data")` y recuperar las filas con `apply_selection(arrivals, selection)`, disponible en `tourism_dashboard.exploration`. Esa función aplica los meses exactos y el mercado indicado. Un contrato ausente o sin fechas devuelve un DataFrame vacío.

`market-chart` escucha `v1-selection`, recupera las filas con `apply_selection` y las suma por `origin` con `aggregate_markets`. Cada barra muestra las llegadas y la participación de un origen dentro de la selección. Si la selección no tiene meses, la gráfica muestra un mensaje que sugiere ampliar el periodo, elegir todos los mercados o limpiar la selección.

## Selección de modelo y V7

`v7-model-selection` es un `dcc.Store` en memoria cuyo contrato contiene únicamente el identificador validado:

```json
{"model": "lstm-catch22-contexto-w24"}
```

El selector ofrece LSTM catch22, Prophet y ARIMA(1,1,1). Un valor ajeno a los artefactos se transforma en `{"model": null}` y la vista muestra un estado vacío; nunca se guarda el DataFrame completo en el navegador. Este estado queda disponible para V8.

`model-evaluation-chart` escucha el store y compara los valores observados con los estimados entre abril de 2021 y junio de 2026. Es una evaluación histórica, no un pronóstico futuro. Las tarjetas muestran MAE, RMSE y MAPE del modelo elegido. No se dibuja una banda de confianza porque los artefactos originales no incluyen intervalos.

## Agregación y datos ausentes

El detalle temporal suma llegadas de los meses disponibles. Los trimestres y años recortados por el periodo no se completan ni se extrapolan: el texto de la gráfica lo aclara y el recuadro del cursor muestra cuántos meses contiene cada punto. Los periodos ausentes interrumpen la línea y no se reemplazan por ceros. Las cifras conservan los valores decimales de las estimaciones expandidas y sus categorías mensuales coinciden con `reported_total`.

## Recursos locales

Dash sirve los recursos desde `src/tourism_dashboard/assets`. Inter Variable 4.1 procede de [Inter](https://rsms.me/inter/) y conserva la licencia SIL Open Font License en `fonts/OFL.txt`. La hoja de Bootstrap 5.3.6 corresponde a la que proporciona `dash-bootstrap-components`; está almacenada localmente con su licencia MIT en `vendor/BOOTSTRAP-LICENSE.txt`. El archivo de idioma español corresponde a Plotly.js 3.7.0 y procede de su distribución oficial. Los recursos de estilos, tipografía e idioma se cargan desde la aplicación.
