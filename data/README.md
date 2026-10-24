# Turistas y excursionistas en Guatemala

`arrivals_migration_2009_2026.csv` contiene la serie mensual de turistas y excursionistas entre enero de 2009 y junio de 2026. Cada fila representa un mes y conserva cantidades decimales cuando la fuente contiene estimaciones expandidas.

## Fuente

La exportación se deriva de `Base_Migracion_2009-2026jun.xlsx`, la misma base preparada y validada en el repositorio [Laboratorio-1-Series-de-Tiempo](https://github.com/JosFer720/Laboratorio-1-Series-de-Tiempo): el Laboratorio 1 corresponde a `main` y el Laboratorio 2 a la rama `Lab2`. La fuente combina registros del Instituto Guatemalteco de Migración con estimaciones de flujos terrestres de INGUAT.

## Transformación

- Se conservaron únicamente las filas cuyo `Tipo de Viajero` es `Turista` o `Excursionista`.
- Los meses se normalizaron como fechas ISO (`YYYY-MM-01`).
- Canadá, Estados Unidos, México, Belice, El Salvador, Honduras y Guatemala se conservaron como países individuales.
- Las demás procedencias se agruparon en Resto de América Central, América del Sur, Europa y Resto del mundo usando `Agrupación Residencia` y `Región dos`.
- No se imputaron ni redondearon valores.

## Columnas

| Columna | Descripción |
|---|---|
| `date` | Mes de observación. |
| `canada` | Residentes de Canadá. |
| `united_states` | Residentes de Estados Unidos. |
| `mexico` | Residentes de México. |
| `belize` | Residentes de Belice. |
| `el_salvador` | Residentes de El Salvador. |
| `honduras` | Residentes de Honduras. |
| `rest_of_central_america` | Resto de residentes de América Central. |
| `south_america` | Agregado de América del Sur. |
| `europe` | Agregado de Europa. |
| `rest_of_world` | Agregado del resto del mundo. |
| `guatemala` | Viajeros con residencia agrupada en Guatemala. |
| `reported_total` | Total mensual de turistas y excursionistas; se incluye para auditoría. |

## Validación

La exportación contiene 210 meses consecutivos. Para cada mes, la suma de las once categorías coincide con `reported_total` y con `S0_total.csv` de los laboratorios de series de tiempo dentro de una tolerancia de `1e-6`.

Desde enero de 2023 la base de los laboratorios registra cero viajeros en la categoría `guatemala`; hasta diciembre de 2022 la categoría tenía valores positivos, con 1,410,620 viajeros en 2022. El dato se conserva sin ajustes. Por eso, a partir de 2023 los demás orígenes de América Central concentran una parte mayor del total, y ese cambio no debe interpretarse por sí solo como una variación real de los mercados.

# Resultados de modelos para S0

`model_predictions_s0.csv` y `model_metrics_s0.csv` conservan resultados ya generados para `S0_total`; no vuelven a entrenar modelos. Los tres modelos comparten el mismo tramo de entrenamiento, de enero de 2009 a marzo de 2021, y el mismo tramo de evaluación, de abril de 2021 a junio de 2026.

## Procedencia

| Modelo | Artefactos fuente | Commit fuente |
|---|---|---|
| `lstm-catch22-contexto-w24` | `data/processed/resultados/lstm_catch22_s0.csv` y `data/processed/resultados/pronostico_lstm_catch22_s0.csv`, Laboratorio 2 | `f2155dcc34bc9abae93797fb5ec3ceb962833f38` |
| `prophet` | `data/processed/resultados/metricas_s0_s5.csv` y `data/processed/resultados/pronosticos_s0_s5.csv`, Laboratorio 1 | `534cfd5fc7586122632dab4c28aaddb6587c281d` |
| `arima-1-1-1` | `data/processed/resultados/metricas_s0_s5.csv` y `data/processed/resultados/pronosticos_s0_s5.csv`, Laboratorio 1 | `534cfd5fc7586122632dab4c28aaddb6587c281d` |

Para los modelos clásicos se conservaron solamente las filas de `S0_total`. Cada modelo aporta 63 estimaciones mensuales y los valores observados son idénticos entre los tres. Los artefactos fuente no incluyen intervalos de predicción, por lo que la exportación tampoco los incorpora.

## Columnas de predicciones

| Columna | Descripción |
|---|---|
| `date` | Mes evaluado, en formato `YYYY-MM-01`. |
| `model_id` | Identificador estable del modelo. |
| `model_label` | Etiqueta legible del modelo. |
| `observed` | Valor observado de `S0_total`. |
| `estimate` | Estimación del modelo para el mes. |

## Columnas de métricas

| Columna | Descripción |
|---|---|
| `model_id` | Identificador estable del modelo. |
| `model_label` | Etiqueta legible del modelo. |
| `source_lab` | Laboratorio que produjo el artefacto. |
| `source_commit` | Commit completo del artefacto fuente. |
| `mae`, `rmse`, `mape` | Métricas calculadas sobre los 63 meses de evaluación. |
| `aic`, `bic` | Criterios de información cuando el modelo fuente los reporta. |
| `train_end` | Último mes del entrenamiento. |
| `evaluation_start`, `evaluation_end` | Límites inclusivos de la evaluación. |

# Ocupación hotelera en Guatemala

`hotel_occupancy_inguat_2022_2024.csv` contiene la ocupación hotelera mensual de Guatemala entre enero de 2022 y diciembre de 2024. Cada fila representa un mes.

## Fuente

Instituto Guatemalteco de Turismo (INGUAT), Departamento de Investigación y Análisis de Mercados. Tabla "Habitaciones disponibles, habitaciones ocupadas e índice de ocupación hotelera" de los boletines anuales de ocupación hotelera:

- [Boletín ocupación hotelera enero a diciembre 2022](https://inguat.gob.gt/es/recursos/boletin-ocupacion-hotelera-enero-a-diciembre-2022/), página 4.
- [Boletín ocupación hotelera enero a diciembre 2023](https://inguat.gob.gt/es/recursos/boletin-ocupacion-hotelera-enero-a-diciembre-2023/), página 5.
- [Boletín ocupación hotelera enero a diciembre 2024](https://inguat.gob.gt/es/recursos/boletin-ocupacion-hotelera-enero-a-diciembre-2024/), página 5.

El índice de los boletines de cada año está en el [archivo de ocupación hotelera de INGUAT](https://inguat.gob.gt/es/recursos/informacion-estadistica/ocupacion-hotelera/).

## Transformación

- Los meses se normalizaron como fechas ISO (`YYYY-MM-01`).
- Las habitaciones disponibles y ocupadas se transcribieron sin cambios.
- `reported_occupancy_pct` es el índice publicado en el boletín del mismo año, en porcentaje entero.

## Columnas

| Columna | Descripción |
|---|---|
| `date` | Mes de observación. |
| `rooms_available` | Habitaciones-noche disponibles en hoteles durante el mes. |
| `rooms_occupied` | Habitaciones-noche ocupadas durante el mes, por huéspedes residentes y no residentes. |
| `reported_occupancy_pct` | Índice de ocupación hotelera publicado por INGUAT (%). |

## Validación y observaciones

- La suma de los doce meses coincide con el total anual publicado en los tres años: 2022 (9,142,615 disponibles y 4,586,817 ocupadas), 2023 (9,367,587 y 5,760,943) y 2024 (9,453,493 y 6,819,342).
- En los 36 meses, ocupadas entre disponibles, redondeado a entero, coincide con el índice publicado.
- El boletín 2024 muestra enero de 2023 con 63 %, mientras que el boletín 2023 lo publica con 62 %. El valor exacto es 62.5 %, así que la diferencia es de redondeo; se conserva el del boletín 2023.
- Noviembre de 2023 tiene un índice de 41 %, muy por debajo de los meses vecinos. Es el valor oficial y se conserva sin ajustes.
- La ocupación incluye huéspedes de establecimientos hoteleros y tiene un alcance distinto al de la serie migratoria de turistas y excursionistas.
