# Predicciones, métricas y navegación

La página Predicciones y modelos contiene V7, V8, la tabla comparativa, los selectores de período y modelo, el resumen de filtros activos y un mensaje de estado. Las visualizaciones usan la evaluación histórica de abril de 2021 a junio de 2026, con 63 meses por modelo y entrenamiento hasta marzo de 2021. No hay nuevas predicciones ni intervalos de incertidumbre en las fuentes.

## V7: observado frente a estimado

Equivale a las líneas de observado y estimado del Laboratorio 10. La línea permite seguir ambas series en orden mensual y reconocer períodos en los que se separan. El observado es azul continuo, y el estimado naranja discontinuo, con nombres además del color. El título incluye «evaluación histórica, no pronóstico».

El eje es `Calendario[year_month]`, ordenado cronológicamente. El selector de modelo empieza en LSTM catch22 y admite un modelo a la vez para esta gráfica. Si se limpia la selección, el observado sigue disponible, pero el estimado queda en blanco y el mensaje pide elegir un modelo; no se suman estimaciones de modelos distintos.

```dax
Observado histórico = SUM(Observados[observed])

Estimado histórico =
IF(HASONEVALUE(Modelos[model_id]), SUM(Predicciones[estimate]), BLANK())
```

El observado proviene de la tabla de 63 meses únicos, relacionada únicamente con Calendario. Un filtro de Modelos no puede multiplicarlo ni cambiar su valor. `Predicciones[observed]` continúa oculta y no se usa en estas medidas. Al seleccionar un mes de V7, V8 se filtra al mismo período.

## V8: error mensual por modelo

Equivale a las barras de errores mensuales del Laboratorio 10. Una barra sobre cero indica sobreestimación y una bajo cero subestimación. Se mantienen las unidades de visitantes y el signo `estimado − observado`.

En Dash se veía el error del modelo elegido. Aquí se presentan tres paneles pequeños, uno por modelo, con la misma escala y barras naranjas. El cambio permite comparar los tres sin asignar un color diferente a cada modelo ni sumar sus errores. El selector de modelo de V7 tiene una interacción `NoFilter` sobre V8. Los selectores de años y meses sí afectan sus tres paneles.

```dax
Error mensual =
VAR Estimado = SUM(Predicciones[estimate])
VAR Observado = SUM(Observados[observed])
RETURN
    IF(
        HASONEVALUE(Modelos[model_id])
            && NOT ISBLANK(Estimado)
            && NOT ISBLANK(Observado),
        Estimado - Observado,
        BLANK()
    )
```

Cada panel aporta un único modelo al contexto de la medida. Los meses sin datos no se convierten en ceros. La selección de V8 no modifica V7, para evitar intersectar el modelo de un panel con el modelo elegido arriba. La relación V7 → V8 sí está definida como filtrado de datos.

## Tabla de métricas

La tabla muestra MAE, RMSE y MAPE de los tres modelos. No cuenta entre las ocho visualizaciones. Son comparables porque usan la misma serie nacional y los mismos 63 meses; no son una evaluación nueva calculada con los meses visibles de V7.

```dax
MAE de evaluación = CALCULATE(MAX(Metricas[mae]), REMOVEFILTERS(Calendario))
RMSE de evaluación = CALCULATE(MAX(Metricas[rmse]), REMOVEFILTERS(Calendario))
MAPE de evaluación = CALCULATE(MAX(Metricas[mape]), REMOVEFILTERS(Calendario))
```

Cada fila se filtra por `Modelos[model_label]`. La tabla no recibe el selector de V7, el período ni las selecciones de las gráficas. `mape` usa el formato `0.0" %"`, porque el CSV ya guarda 29,1615, no 0,291615.

MAE explica el tamaño medio del error en visitantes. RMSE también usa visitantes, pero pesa más los errores grandes. MAPE expresa el error absoluto medio en porcentaje del observado. La explicación aclara que un menor valor es mejor y no garantiza el desempeño futuro.

| Modelo | MAE mostrado | RMSE mostrado | MAPE mostrado | Error de diciembre de 2025 |
|---|---:|---:|---:|---:|
| LSTM catch22, ventana 24 | 55.256 | 67.735 | 29,2 % | −142.131 |
| Prophet | 132.304 | 139.549 | 60,9 % | −205.733 |
| ARIMA(1,1,1) | 154.873 | 169.524 | 59,3 % | −275.896 |

Los valores se redondean únicamente para mostrarlos. El observado exacto de diciembre de 2025 es 365573.0218067979. La lectura del modelo importado y el recálculo independiente están en [validacion_modelos_pbix.json](validacion_modelos_pbix.json).

## Controles y contexto

Las tres páginas de análisis comparten los grupos de segmentadores `PeriodoAnio` y `PeriodoMes`. Los mercados se sincronizan entre Llegadas y mercados y Temporadas y hospedaje. En esta última, el mercado no filtra V5, V6 ni el mensaje de hospedaje: son indicadores nacionales. `Llegadas con hospedaje` devuelve blanco cuando no hay habitaciones disponibles, para impedir puntos falsos con cero ocupación fuera de 2022–2024:

```dax
Llegadas con hospedaje =
IF(NOT ISBLANK(SUM(Hospedaje[rooms_available])), SUM(Llegadas[arrivals]), BLANK())
```

Cada página tiene una tarjeta con años, meses y mercados o modelo activos. Cuando se seleccionan muchos valores, muestra su cantidad para mantener el texto legible. Los nombres y fórmulas de estas tarjetas y de los mensajes están en `reportExtensions.json`.

Los mensajes cubren llegadas sin registros, hospedaje fuera de 2022–2024, predicciones fuera de abril de 2021 a junio de 2026 y ausencia de un modelo único. No sustituyen datos faltantes por cero. La tabla mantiene su cobertura completa, expresada en el título y en la explicación.

## Navegación y lectura

Las cinco páginas principales tienen botones en el mismo orden y posición. El botón de la página activa tiene fondo azul y texto blanco; los otros tienen fondo blanco. La página de detalle permanece oculta en la navegación ordinaria, se abre por región y tiene un botón Volver. V1 conserva la jerarquía con bajar y subir de nivel.

Los seis marcadores de Restablecer vista incluyen el estado de todos los visuales y de los controles sincronizados. Limpian períodos, mercados, filtros y selecciones entre gráficas, recuperan el nivel anual de V1 y el modelo inicial LSTM. Conservan la página actual; el marcador del detalle vuelve a Llegadas y mercados.

Inicio relaciona cada pregunta con la página adecuada y explica cómo explorar. Sobre los datos incluye la procedencia, coberturas, glosario, alcance nacional, falta de intervalos, diferencias entre llegadas y huéspedes, el cero de Guatemala desde 2023 y las observaciones de ocupación publicadas por INGUAT. Los textos distinguen observado, interpretado y estimado, sin atribuir causas a una asociación visual.

## Ubicación y comprobación

Las medidas específicas del informe están en `powerbi/observatorio_turismo.Report/definition/reportExtensions.json`, conforme al [esquema de extensiones de Microsoft](https://github.com/microsoft/json-schemas/blob/main/fabric/item/report/definition/reportExtension/1.0.0/schema.json). Los visuales las referencian con `SourceRef.Schema = extension`. Las tres medidas anteriores de llegadas, peso regional y ocupación también quedaron reflejadas en el modelo editable para que el `.pbip` no tenga referencias incompletas.

El `.pbix` contiene la misma definición PBIR que la carpeta del informe. [comprobaciones_finales.dax](../../powerbi/comprobaciones_finales.dax) incluye `DEFINE MEASURE` y consultas para comprobar las fórmulas en Desktop. El 7 de noviembre de 2026 esas consultas se ejecutaron en Desktop contra el modelo del informe y dieron los valores esperados: observado de diciembre de 2025 igual con uno o con todos los modelos, errores de −142.131, −205.733 y −275.896, MAPE de 29,2 %, 60,9 % y 59,3 %, mensajes sin datos y participación de El Salvador de 73,8 %. Las capturas del informe en Desktop están en [capturas/](capturas/).
