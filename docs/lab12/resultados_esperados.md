# Resultados esperados

Valores calculados con `python scripts/resultados_esperados.py` a partir de los CSV de `data/`, con las mismas reglas de agregación del tablero en Dash. Sirven para comprobar que el informe de Power BI muestra lo mismo. Las cifras de llegadas conservan decimales en la fuente; aquí se redondean a enteros solo para leerlas.

## Indicadores generales

| Indicador | Filtros | Valor esperado |
|---|---|---|
| Llegadas del período completo | Enero de 2009 a junio de 2026, todos los mercados | 46.711.913 |
| Mes con más llegadas | Período completo, todos los mercados | Diciembre de 2019: 449.114 |
| Meses con información | Período completo, todos los mercados | 210 |
| Llegadas de 2024 | Enero a diciembre de 2024, todos los mercados | 3.274.436 |
| Llegadas de 2025 | Enero a diciembre de 2025, todos los mercados | 3.352.289 |
| Ocupación hotelera de 2022 a 2024 | Habitaciones ocupadas entre disponibles | 61,4 % |

## Prueba 1: mes con más llegadas en 2025

Con el período de enero a diciembre de 2025 y todos los mercados, el mes con más llegadas es diciembre de 2025, con 365.573 llegadas, y el de menos es septiembre de 2025, con 218.070. El total del año es 3.352.289.

| Mes | Llegadas |
|---|---|
| Enero de 2025 | 289.544 |
| Febrero de 2025 | 254.429 |
| Marzo de 2025 | 278.538 |
| Abril de 2025 | 300.288 |
| Mayo de 2025 | 247.982 |
| Junio de 2025 | 254.190 |
| Julio de 2025 | 283.389 |
| Agosto de 2025 | 293.781 |
| Septiembre de 2025 | 218.070 |
| Octubre de 2025 | 255.921 |
| Noviembre de 2025 | 310.586 |
| Diciembre de 2025 | 365.573 |

## Prueba 2: de las regiones a los países de América Central en 2025

Llegadas de 2025 por región:

| Región | Llegadas | Participación |
|---|---|---|
| América Central | 2.143.694 | 63,9 % |
| América del Norte | 839.380 | 25,0 % |
| Europa | 176.262 | 5,3 % |
| América del Sur | 132.352 | 3,9 % |
| Resto del mundo | 60.601 | 1,8 % |

Al bajar a los países de América Central, el que más aporta es El Salvador, con 1.582.845 llegadas, el 73,8 % de la región:

| Origen | Llegadas | Participación en la región |
|---|---|---|
| El Salvador | 1.582.845 | 73,8 % |
| Honduras | 273.040 | 12,7 % |
| Resto de América Central | 198.686 | 9,3 % |
| Belice | 89.123 | 4,2 % |
| Guatemala | 0 | 0,0 % |

La categoría Guatemala vale cero desde enero de 2023 en la fuente, por eso aparece con cero.

## Prueba 3: desempeño de los tres modelos

Los tres modelos estiman la misma serie mensual de turistas y excursionistas en los mismos 63 meses de evaluación, de abril de 2021 a junio de 2026, con entrenamiento hasta marzo de 2021. Sus métricas son comparables entre sí.

| Modelo | MAE | RMSE | MAPE | Error en diciembre de 2025 (estimado − observado) |
|---|---|---|---|---|
| LSTM catch22 (ventana 24) | 55.256 | 67.735 | 29,2 % | -142.131 |
| Prophet | 132.304 | 139.549 | 60,9 % | -205.733 |
| ARIMA(1,1,1) | 154.873 | 169.524 | 59,3 % | -275.896 |

El modelo con menor MAPE es LSTM catch22 (ventana 24). El valor observado de diciembre de 2025 es 365.573 y debe ser el mismo con cualquier modelo seleccionado: si cambia, el observado se está sumando entre modelos.
