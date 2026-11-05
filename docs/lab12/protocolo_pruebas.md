# Protocolo de comparación entre Dash y Power BI

Este protocolo define cómo se comparan las dos versiones del tablero: la de Plotly Dash, identificada con el tag `lab10-final`, y el informe `powerbi/observatorio_turismo.pbix`. Ambas usan los mismos CSV de `data/`. Los valores correctos de cada prueba están en `resultados_esperados.md`.

## Criterios de comparación

Cada criterio se evalúa con evidencia de las dos versiones: una medición, una captura, un archivo del repositorio o una fuente documental con su enlace y fecha de consulta.

| Criterio | Qué se observa | Evidencia que se recoge |
|---|---|---|
| Facilidad de aprendizaje | Conocimientos previos necesarios y dificultades al empezar. | Experiencia previa declarada de cada integrante y dificultades anotadas en las pruebas. |
| Tiempo de desarrollo | Horas efectivas para llegar a las ocho visualizaciones con sus interacciones. | Registro de tiempo por sesión y fechas de los commits. |
| Preparación y actualización de datos | Cómo se transforman los CSV y qué hay que hacer cuando cambian. | Funciones de carga en `src/tourism_dashboard/data.py` frente a los pasos de Power Query; tiempo de actualizar los datos. |
| Integración de resultados de modelos | Cómo se cargan predicciones y métricas sin duplicar el observado. | Validaciones de carga en Dash frente a relaciones y medidas DAX; valor observado de diciembre de 2025 con cada modelo. |
| Interacción y navegación | Enlaces entre gráficos, niveles de detalle, selección de vistas y regreso a la vista inicial. | Pasos y clics de las tres pruebas. |
| Personalización | Control sobre colores, fuentes, textos, mensajes sin datos y controles. | Tema de Power BI frente a la hoja de estilos de Dash; elementos que no se pudieron reproducir. |
| Rendimiento | Tiempo de apertura, de respuesta a un filtro y de cambio de vista. | Mediciones en el mismo equipo para ambas versiones; tamaño del archivo .pbix. |
| Colaboración y control de versiones | Cómo trabaja el equipo en paralelo y cómo se revisan los cambios. | Historial de git: diferencias legibles en el código de Dash frente a un archivo binario en Power BI. |
| Requisitos para compartir o desplegar | Qué necesita otra persona para consultar el tablero y cuánto cuesta. | Documentación oficial de licencias, sistemas operativos y alojamiento, con fecha de consulta. |

## Condiciones de las pruebas

- Las dos versiones se prueban en el mismo equipo Windows, con los mismos datos y las mismas selecciones. Se anota el equipo, el sistema operativo, el navegador usado para Dash y la versión de Power BI Desktop.
- Quien ejecuta las pruebas declara su experiencia previa con cada herramienta. Las diferencias de experiencia o de entorno se reportan y no se atribuyen por sí solas a la herramienta.
- Antes de cada prueba se abre la vista inicial: en Dash se recarga la página; en Power BI se usa el botón para restablecer la vista.
- El tiempo se mide con cronómetro desde que se empieza a buscar la respuesta hasta que se lee el valor final. Un clic es cada selección, cambio de página, despliegue de un control o botón pulsado; escribir en un campo cuenta como un clic.
- Para cada prueba se anota: resultado obtenido, si coincide con el esperado, pasos seguidos, número de clics, tiempo y dificultades. Se toma una captura del resultado.

## Prueba 1: responder una pregunta de gestión con filtros

Pregunta de gestión: ¿en qué momentos del año llegan más y menos visitantes?

Pregunta concreta: en 2025, con todos los mercados, ¿cuál fue el mes con más llegadas y cuántas hubo?

Resultado esperado: diciembre de 2025, con 365.573 llegadas.

Pasos en Dash (`lab10-final`):

1. En la pestaña Llegadas y mercados, en Periodo, elegir Desde: Enero de 2025.
2. Elegir Hasta: Diciembre de 2025.
3. Confirmar que Mercado de origen dice Todos los mercados y que Detalle temporal está en Mes.
4. Leer la tarjeta Mes con más llegadas.

Pasos en Power BI:

1. En la página Llegadas y mercados, en el segmentador de período, elegir el año 2025.
2. Confirmar que el segmentador de mercado no tiene selección.
3. Leer el mes más alto en V1 o en la tarjeta de mes con más llegadas.

## Prueba 2: pasar de una vista general al detalle y regresar

Pregunta de gestión: ¿de qué países o regiones vienen los visitantes?

Pregunta concreta: en 2025, ¿qué región aportó más llegadas y, dentro de ella, qué país aportó más y con qué participación? Después, volver a la vista de todas las regiones.

Resultado esperado: América Central, con 2.143.694 llegadas (63,9 %). Dentro de ella, El Salvador, con 1.582.845 llegadas (73,8 % de la región). Al regresar se ven otra vez las cinco regiones.

Pasos en Dash (`lab10-final`):

1. Con el período de enero a diciembre de 2025, ir a Peso de cada mercado en el tiempo.
2. Hacer clic en el panel de América Central. El filtro de mercado pasa a América Central y las gráficas muestran sus países.
3. Leer en Llegadas por mercado de origen el país con más llegadas y su participación.
4. Pulsar ← Todos los mercados y confirmar que vuelven las cinco regiones.

Pasos en Power BI:

1. Con 2025 en el segmentador de período, identificar la región con más llegadas.
2. Abrir el detalle de América Central (clic derecho y Obtener detalles, o bajar de nivel en la jerarquía región y país).
3. Leer el país con más llegadas y su participación dentro de la región.
4. Pulsar el botón de regreso o subir de nivel, y confirmar que vuelven las cinco regiones.

## Prueba 3: consultar las predicciones y comparar los tres modelos

Preguntas de gestión: ¿cuántos visitantes se esperan y con qué margen de error?, y ¿qué tan confiable es cada modelo?

Pregunta concreta: en la evaluación de abril de 2021 a junio de 2026, ¿qué modelo tiene el menor MAPE y cuál es su error en diciembre de 2025 (estimado menos observado)?

Resultado esperado: LSTM catch22 (ventana 24), con un MAPE de 29,2 %, frente a 60,9 % de Prophet y 59,3 % de ARIMA(1,1,1). Su error en diciembre de 2025 es −142.131 (estimó menos de lo observado). El valor observado de diciembre de 2025 es 365.573 con cualquier modelo.

Pasos en Dash (`lab10-final`):

1. Ir a la pestaña Predicciones y modelos.
2. Leer el MAPE de los tres modelos en la tabla Comparación de los tres modelos e identificar el menor.
3. Elegir ese modelo en el selector Modelo.
4. En ¿En qué meses se equivoca el modelo?, pasar el cursor por diciembre de 2025 y leer el error.

Pasos en Power BI:

1. Ir a la página Predicciones y modelos.
2. Leer el MAPE de los tres modelos en la tabla de métricas e identificar el menor.
3. Elegir ese modelo en el segmentador de modelo.
4. En V8, pasar el cursor por diciembre de 2025 y leer el error. Comprobar en V7 que el observado de ese mes es 365.573.

## Verificación de indicadores entre versiones

Con los mismos filtros y las mismas reglas de agregación, se comparan al menos estos dos indicadores. Cualquier diferencia se documenta y se explica.

| Indicador | Filtros | Valor esperado |
|---|---|---|
| Llegadas de 2024 | Enero a diciembre de 2024, todos los mercados | 3.274.436 |
| MAPE de cada modelo | Evaluación de abril de 2021 a junio de 2026 | LSTM 29,2 %, Prophet 60,9 %, ARIMA(1,1,1) 59,3 % |

## Registro de resultados

Los resultados se guardan en `resultados_pruebas.md` con esta tabla por prueba, y las capturas en `capturas/`.

| Versión | Resultado obtenido | ¿Coincide con el esperado? | Pasos seguidos | Clics | Tiempo (s) | Dificultades |
|---|---|---|---|---|---|---|
| Dash | | | | | | |
| Power BI | | | | | | |

Además se anota el entorno: equipo, sistema operativo, navegador, versión de Power BI Desktop y experiencia previa de quien ejecuta las pruebas.
