# Resultados de las pruebas

Las tres pruebas de [protocolo_pruebas.md](protocolo_pruebas.md) se ejecutaron el 7 de noviembre de 2026 en un mismo equipo Windows, con los mismos CSV de `data/` y las mismas selecciones en las dos versiones: el tablero de Plotly Dash del tag `lab10-final` (commit `29a091d`) y `powerbi/observatorio_turismo.pbix` guardado en Power BI Desktop ese mismo día. Los valores esperados están en [resultados_esperados.md](resultados_esperados.md).

## Entorno

| Elemento | Valor |
|---|---|
| Equipo | Alienware m15 R3, Intel Core i7-10750H a 2,60 GHz, 16 GB de memoria |
| Sistema operativo | Windows 11 Home Single Language, versión 26H2 (compilación 26300) |
| Navegador para Dash | Google Chrome 156.0.8078.80 |
| Power BI Desktop | 2.159.1231.0 (64 bits), instalado desde Microsoft Store |
| Python para Dash | 3.12.10, con las dependencias de `requirements.txt` de `lab10-final` |

El detalle está en [entorno_pruebas.json](entorno_pruebas.json).

Experiencia previa de quien ejecutó las pruebas: ninguna con Plotly Dash ni con Power BI antes del curso.

## Cómo se registró cada dato

El resultado de cada prueba se leyó en la interfaz de cada versión y se guardó una captura en [capturas/](capturas/). Los clics se cuentan sobre la ruta mínima que describe el protocolo, con la regla del protocolo: cada selección, cambio de página, despliegue de un control o botón pulsado cuenta como un clic. Pasar el cursor para leer un valor no cuenta. Antes de cada prueba se volvió a la vista inicial: recargar la página en Dash y Restablecer vista en Power BI.

Las pruebas se realizaron con una persona habituada a programar, pero que no había usado Plotly Dash ni Power BI antes del curso. Los tiempos de las tablas son aproximados.

## Prueba 1: mes con más llegadas en 2025

Pregunta: en 2025, con todos los mercados, ¿cuál fue el mes con más llegadas y cuántas hubo? Esperado: diciembre de 2025, con 365.573 llegadas.

| Versión | Resultado obtenido | ¿Coincide? | Pasos | Clics | Tiempo aproximado (s) | Dificultades |
|---|---|---|---|---|---|---|
| Dash | Diciembre de 2025, 365.573; llegadas del periodo 3.352.289 | Sí | Desde: Enero de 2025; Hasta: Diciembre de 2025; leer la tarjeta Mes con más llegadas | 4 | 35 | Las listas de Desde y Hasta tienen 210 meses; conviene escribir en su buscador para llegar a 2025. |
| Power BI | diciembre 2025, 365,573; llegadas del período 3,352,289 | Sí | Ir a Llegadas y mercados; desplegar Años; elegir 2025; leer las tarjetas Mes con más llegadas y Máximo mensual | 3 | 25 | La lista de años obliga a desplazarse hasta 2025. En el nivel anual V1 muestra un solo punto; el mes se lee en la tarjeta o bajando a mes. |

Capturas: `capturas/dash_prueba1.png` y `capturas/powerbi_prueba1.png`.

## Prueba 2: región, país y regreso

Pregunta: en 2025, ¿qué región aportó más llegadas y, dentro de ella, qué país aportó más y con qué participación? Después, volver a todas las regiones. Esperado: América Central, 2.143.694 (63,9 %); El Salvador, 1.582.845 (73,8 % de la región); al regresar se ven las cinco regiones.

| Versión | Resultado obtenido | ¿Coincide? | Pasos | Clics | Tiempo aproximado (s) | Dificultades |
|---|---|---|---|---|---|---|
| Dash | América Central, 2.143.694 (63,9 % en el peso regional); El Salvador, 1.582.845 · 73,8 %; al pulsar Todos los mercados vuelven las cinco regiones | Sí | Periodo enero a diciembre de 2025; clic en el panel de América Central; leer Llegadas por mercado de origen; pulsar ← Todos los mercados | 6 | 60 | El panel de América Central está al final de la pestaña y hay que desplazarse para verlo. |
| Power BI | América Central es la región de mayor peso en V4 (2.143.694 llegadas y 63,9 % con la misma medida en la vista de consultas DAX); en el detalle, El Salvador 1,582,845 y 73.8 % de la región; Volver regresa a Llegadas y mercados con 2025 conservado | Sí | Ir a Llegadas y mercados; elegir 2025; clic derecho sobre América Central en V4; Obtener detalles; Detalle de región; pasar el cursor por El Salvador; Volver | 7 | 75 | El detalle solo se descubre con clic derecho. En Desktop el botón Volver requiere Ctrl + clic. La información sobre herramientas rotula el país como «origin». |

Guatemala aparece con cero desde 2023 en las dos versiones porque así viene en la fuente.

Capturas: `capturas/dash_prueba2.png`, `capturas/powerbi_prueba2_region.png` y `capturas/powerbi_prueba2.png`.

## Prueba 3: modelo con menor MAPE y su error en diciembre de 2025

Pregunta: en la evaluación de abril de 2021 a junio de 2026, ¿qué modelo tiene el menor MAPE y cuál es su error en diciembre de 2025? Esperado: LSTM catch22 (ventana 24), 29,2 %; error −142.131; observado 365.573 con cualquier modelo.

| Versión | Resultado obtenido | ¿Coincide? | Pasos | Clics | Tiempo aproximado (s) | Dificultades |
|---|---|---|---|---|---|---|
| Dash | LSTM catch22 (ventana 24), MAPE 29,16 en la tabla y 29,2 % en la tarjeta; diciembre de 2025: observado 365.573, estimado 223.442, error −142.131 | Sí | Pestaña Predicciones y modelos; leer la tabla Comparación de los tres modelos; LSTM ya está elegido; pasar el cursor por diciembre de 2025 en el gráfico de errores | 1 | 40 | La tabla muestra el MAPE con dos decimales y la tarjeta con uno. |
| Power BI | LSTM catch22 (ventana 24), 29.2 %; error de diciembre de 2025 −142,131; observado 365,573 con uno y con todos los modelos | Sí | Ir a Predicciones y modelos; leer la tabla de métricas; LSTM ya está elegido; clic en diciembre de 2025 en V7; pasar el cursor por la barra de LSTM en V8 | 2 | 50 | El eje mensual de V8 es categórico y no muestra los 63 meses a la vez; seleccionar el mes en V7 es la forma directa de llegar a diciembre de 2025. |

Capturas: `capturas/dash_prueba3.png`, `capturas/dash_prueba3_tabla.png`, `capturas/powerbi_prueba3_v7.png` y `capturas/powerbi_prueba3.png`.

## Verificación de indicadores entre versiones

| Indicador | Filtros | Dash | Power BI | Esperado |
|---|---|---|---|---|
| Llegadas de 2024 | Enero a diciembre de 2024, todos los mercados | 3.274.436 | 3.274.436 (3274435,995 sin redondear) | 3.274.436 |
| MAPE LSTM catch22 (ventana 24) | Evaluación completa | 29,2 % (tabla: 29,16) | 29.2 % | 29,2 % |
| MAPE Prophet | Evaluación completa | 60,9 % (tabla: 60,89) | 60.9 % | 60,9 % |
| MAPE ARIMA(1,1,1) | Evaluación completa | 59,3 % (tabla: 59,30) | 59.3 % | 59,3 % |
| Observado de diciembre de 2025 | Cualquier modelo | 365.573 | 365.573 con uno y con todos los modelos | 365.573 |

No hay diferencias de valor. Las únicas diferencias son de presentación: Dash usa punto de miles y coma decimal, y Power BI usa la configuración regional del modelo, con coma de miles y punto decimal; la tabla de Dash muestra el MAPE con dos decimales. En Power BI las llegadas de 2024 se obtuvieron con la misma medida que alimenta las tarjetas, ejecutada en la vista de consultas DAX.

## Rendimiento

Todas las mediciones son del mismo equipo.

| Medición | Dash (`lab10-final`) | Power BI Desktop |
|---|---|---|
| Apertura | Desde `python app.py` hasta que la página responde: 4,79 s, 2,59 s y 2,07 s (mediana 2,59 s); hasta servir el layout: mediana 2,70 s | Desde abrir el `.pbix` hasta que la página Inicio queda completa y estable: 32,2 s, 18,2 s y 18,0 s; la ventana principal aparece a los 13,6 s, 12,4 s y 12,1 s |
| Respuesta al filtro de 2025 | Mediana 62 ms en 10 repeticiones (callbacks de la serie y de mercados) | 478 ms desde el primer hasta el último de los 21 visuales actualizados; el más lento fue V4, con 442 ms; la consulta DAX más larga, 27 ms |
| Cambio de vista | Pestaña Predicciones y modelos: mediana 87 ms en 10 repeticiones | Página Temporadas y hospedaje: 484 ms para 19 visuales; el más lento fue V5, con 375 ms |
| Tamaño | Código y CSV de la carpeta del tablero | `.pbix` final de 297.159 bytes |

En Dash los tiempos son de las solicitudes al servidor local y no incluyen el dibujo de las figuras en el navegador; se repiten con `python scripts/medir_rendimiento_dash.py` y están en [rendimiento_dash.json](rendimiento_dash.json). En Power BI la apertura se midió con un script que registra cuándo la ventana del informe deja de cambiar, cerrando Desktop antes de cada repetición; la primera apertura incluye la carga inicial del programa. El filtro y el cambio de página se midieron con el Analizador de rendimiento de Desktop, exportado en [rendimiento_powerbi.json](rendimiento_powerbi.json). No se midió el tiempo de Actualizar en Power BI.

## Control adicional del servidor de Dash

Las tres tareas también se ejecutaron contra los callbacks HTTP del servidor `lab10-final`, sin la interfaz. Los tres resultados coinciden con los esperados, el resumen de 2024 devolvió «3.274.436» y la consulta de hospedaje para 2025 devolvió el mensaje de falta de cobertura sin imputar ceros. Ocho solicitudes repetidas del callback temporal tuvieron una mediana de 34,4 ms. Los resultados y las figuras recibidas están en [evidencia_http/](evidencia_http/); se repiten iniciando la referencia en el puerto 8051 y ejecutando:

```bash
python scripts/pruebas_http_lab12.py --url http://127.0.0.1:8051
```
