# Modelo de datos del informe en Power BI

La definición del modelo está preparada en `powerbi/observatorio_turismo.SemanticModel/model.bim`. Las consultas Power Query, las tablas, las relaciones, las jerarquías y las medidas existentes del modelo forman parte del proyecto `powerbi/observatorio_turismo.pbip`. El informe editable está sincronizado con las seis páginas del `.pbix` y conserva el tema de colores existente.

El modelo se preparó primero como proyecto y después se actualizó y guardó en Power BI Desktop 2.159.1231.0 en Windows, en `powerbi/observatorio_turismo.pbix`. La sintaxis M y los metadatos del informe se comprobaron por separado, y la carga, las relaciones y las consultas DAX se comprobaron en Desktop, como se detalla al final. El procedimiento completo está en [el README de Power BI](../../powerbi/README.md).

## Fuentes y parámetro

Se conservan los cuatro CSV de `data/` tal como estaban en `29a091d26d8a9efec62e4ea292a3b5240fddee17`, el commit al que apunta `lab10-final`. El verificador compara el contenido completo de cada archivo contra ese commit y registra SHA-256 en [validacion_fuentes.json](validacion_fuentes.json). No se usan fuentes ni resultados del pipeline del Laboratorio 11 y no se construyen modelos nuevos.

`pCarpetaDatos` es un parámetro obligatorio de texto con la carpeta que contiene los cuatro CSV. `fnLeerCsv` une esa carpeta al nombre de cada archivo, lee UTF-8 con separador coma y comillas CSV, promueve encabezados y exige las columnas esperadas. Todas las lecturas pasan por esa función. Las conversiones numéricas usan `en-US`, porque los CSV tienen punto decimal; las fechas ISO se convierten al tipo fecha sin cambiar el día ni el mes.

El parámetro queda vacío en Git. `python scripts/preparar_powerbi.py` verifica las fuentes y copia el proyecto a `powerbi/local/`, con la ruta del equipo. Esa copia y las carpetas `.pbi/` están excluidas de Git. No sobrescribe una copia existente. En Desktop el parámetro se cambia en Transformar datos > Administrar parámetros.

## Pasos de Power Query

Las expresiones auxiliares del modelo no cargan tablas adicionales. `fnValidarMeses` exige las fechas mensuales completas del período de referencia y rechaza faltantes, fechas repetidas y meses fuera de cobertura. `fnNumeroValido` rechaza valores nulos, negativos o no finitos.

1. `CatalogoOrigenes` conserva las once claves, las etiquetas, las cinco regiones y el nivel de agregación de `ORIGIN_METADATA` en el Laboratorio 10. Canadá, Estados Unidos y México pertenecen a América del Norte. Belice, El Salvador, Honduras, Resto de América Central y Guatemala pertenecen a América Central. América del Sur, Europa y Resto del mundo son agregados; no se presentan como países individuales. La región se consulta desde la dimensión `Origenes` mediante la clave original.
2. `LlegadasFuente` lee `arrivals_migration_2009_2026.csv`, convierte `date` a fecha y las once categorías y `reported_total` a número decimal. Verifica 210 meses desde enero de 2009 y que la suma de categorías coincida con el total publicado, con tolerancia absoluta de `1e-6`. Los valores no se redondean, imputan ni corrigen.
3. La partición `Llegadas` selecciona `date` y las once categorías. Excluye `reported_total` antes de anular la dinamización con `Table.Unpivot`, para impedir que el total se cuente como un mercado adicional. El resultado contiene `date`, `origin_key` y `arrivals`, con una fila por mes y origen. La región y el nombre legible se obtienen de `Origenes`.
4. `OcupacionFuente` lee `hotel_occupancy_inguat_2022_2024.csv`, convierte fechas y comprueba los 36 meses de 2022 a 2024. Verifica que las habitaciones sean números enteros no negativos, que las disponibles sean positivas, que las ocupadas no las superen y que el índice publicado esté entre 0 y 100. Solo después convierte los conteos a entero. Conserva el índice publicado, incluido noviembre de 2023. La tasa agregada debe calcularse como habitaciones ocupadas divididas entre disponibles; no se suman porcentajes mensuales.
5. `MetricasFuente` lee `model_metrics_s0.csv`. Conserva `model_id`, etiquetas, laboratorio y commit de procedencia, y convierte las fechas y métricas. Solo los campos vacíos `aic` y `bic` pasan a nulo, porque esos modelos no los reportan; no se convierten en cero. Exige una fila para cada uno de los tres identificadores originales, entrenamiento hasta marzo de 2021 y evaluación de abril de 2021 a junio de 2026. `mape` ya viene en unidades porcentuales: 29,1615 se muestra como 29,2 %, sin multiplicarlo por cien.
6. `PrediccionesFuente` lee `model_predictions_s0.csv`. Conserva las fechas e identificadores originales, comprueba que `(date, model_id)` sea único, que haya 63 meses por modelo, que las etiquetas coincidan con las métricas y que observado y estimado sean números finitos no negativos. Antes de producir las tablas comprueba que los tres observados de cada mes sean iguales y que coincidan con el total nacional de llegadas con tolerancia de `1e-6`.
7. `Observados` selecciona únicamente `date` y `observed` de las predicciones ya comprobadas y elimina las repeticiones idénticas. Así quedan 63 filas, una por mes, sin identificador de modelo. `Predicciones` conserva las 189 filas originales. No se elige arbitrariamente el observado de un modelo ni se usa un promedio para esconder discrepancias.
8. `Modelos` selecciona las claves y etiquetas de las tres filas de métricas. `Calendario` crea fechas diarias continuas desde el 1 de enero de 2009 hasta el 31 de diciembre de 2026, con años completos, y agrega año, trimestre, mes y año-mes. Se marca como tabla de fechas mediante `dataCategory: Time` y clave única `date`. La jerarquía es Año > Trimestre > Mes; los nombres de mes se ordenan por su número. Los meses sin hechos, incluido julio a diciembre de 2026, no representan valores observados ni predicciones nuevas.

## Tablas y grano

Los conteos son los esperados a partir de las fuentes verificadas. En Desktop se cargaron las ocho tablas.

| Tabla | Una fila representa | Filas esperadas | Clave |
|---|---|---:|---|
| Calendario | Un día de los años completos 2009 a 2026 | 6.574 | date |
| Origenes | Un mercado con su región y nivel | 11 | origin_key |
| Modelos | Un modelo ya evaluado | 3 | model_id |
| Llegadas | Un mes y un mercado | 2.310 | date + origin_key |
| Hospedaje | Un mes de ocupación nacional | 36 | date |
| Predicciones | Un mes y un modelo | 189 | date + model_id |
| Metricas | El resultado completo de evaluación de un modelo | 3 | model_id |
| Observados | Un mes nacional del período evaluado | 63 | date |

`arrivals`, `observed`, `estimate` y las métricas usan número decimal de doble precisión; no se usa moneda ni decimal fijo de cuatro posiciones. El formato visual no altera los valores. No hay relación de mercados con hospedaje, predicciones o métricas, porque esas fuentes solo tienen alcance nacional.

## Relaciones

Las siete relaciones están definidas como activas, de uno a muchos y con filtro en una sola dirección, desde la dimensión hacia la tabla de hechos. No hay relaciones directas entre tablas de hechos, relaciones muchos a muchos ni filtros bidireccionales.

| Lado uno | Lado muchos | Dirección del filtro |
|---|---|---|
| Calendario[date] | Llegadas[date] | Calendario → Llegadas |
| Calendario[date] | Hospedaje[date] | Calendario → Hospedaje |
| Calendario[date] | Predicciones[date] | Calendario → Predicciones |
| Calendario[date] | Observados[date] | Calendario → Observados |
| Origenes[origin_key] | Llegadas[origin_key] | Origenes → Llegadas |
| Modelos[model_id] | Predicciones[model_id] | Modelos → Predicciones |
| Modelos[model_id] | Metricas[model_id] | Modelos → Metricas |

`Metricas` no se relaciona con el calendario: MAE, RMSE y MAPE corresponden al período completo de evaluación y no cambian al seleccionar un mes. Las fechas de entrenamiento y evaluación son metadatos de procedencia. Para las visualizaciones temporales se usan los campos de `Calendario`, y para mercados y modelos se usan sus dimensiones.

## Observado sin duplicación

Las predicciones repiten el observado una vez por modelo. Sumar esa columna daría tres veces el total cuando están seleccionados los tres modelos. Por eso `Predicciones[observed]` queda oculta y con agregación predeterminada `none`; el informe debe usar la medida `Observado evaluado` de la tabla separada `Observados`:

```dax
Observado evaluado = SUM(Observados[observed])
```

Esa tabla solo recibe filtros del calendario. Elegir uno, dos o tres modelos no cambia el observado. Tampoco responde al origen: representa el total nacional de la evaluación, y no debe interpretarse como la predicción de un país. Las estimaciones también son nacionales; la página de modelos debe dejar claro ese alcance y no usar un filtro de origen para atribuirles cifras por mercado. Las medidas para las visualizaciones de llegadas se agregan sobre `Llegadas[arrivals]`, sin unir físicamente las tablas.

## Comprobaciones realizadas y pendientes

`python scripts/verificar_powerbi.py --output docs/lab12/validacion_fuentes.json` comprueba la identidad de los cuatro CSV con el commit de referencia, la cobertura, las claves, la clasificación de orígenes, las siete relaciones y la igualdad del observado entre modelos. Recalcula MAE, RMSE y MAPE con tolerancia absoluta de `1e-6` y relativa de `1e-10`. También se regeneraron los resultados esperados con el script existente y no hubo diferencias.

| Control sobre las fuentes | Resultado |
|---|---|
| Llegadas del período completo, sin redondear | 46711912.886517508050438 |
| Total mostrado con cero decimales | 46.711.913 |
| Máximo histórico | Diciembre de 2019, 449.114 al mostrar cero decimales |
| Llegadas de 2024 | 3.274.436 al mostrar cero decimales |
| Llegadas de 2025 | 3.352.289 al mostrar cero decimales |
| Observado nacional de diciembre de 2025 | 365573.0218067979 |
| Meses del observado sin duplicar | 63 |
| MAPE LSTM, Prophet y ARIMA | 29,2 %, 60,9 % y 59,3 % |

Las 17 expresiones y particiones M pasaron el analizador de sintaxis `@microsoft/powerquery-parser` 4.0.1. Los siete archivos JSON con esquema del proyecto y del informe pasaron los esquemas oficiales de Microsoft. Estas comprobaciones no ejecutan el motor M ni certifican la deserialización del modelo TMSL en Desktop.

En Desktop se ejecutó Actualizar y las consultas de [comprobaciones.dax](../../powerbi/comprobaciones.dax). El total histórico fue 46711912.89, el máximo fue diciembre de 2019 con 449114.07 y el observado de diciembre de 2025 fue 365573.0218067979 con uno y con todos los modelos. Los indicadores coinciden con [resultados_esperados.md](resultados_esperados.md); las diferencias de representación binaria se comparan con tolerancia, nunca redondeando la fuente.

La revisión posterior de predicciones y navegación conserva el contenido binario de `DataModel` sin cambios. Las doce medidas nuevas pertenecen al informe, en `definition/reportExtensions.json`, y no alteran las tablas ni las relaciones. La auditoría del caché del `.pbix` confirma 189 predicciones, 63 observados mensuales y las métricas esperadas; las fórmulas nuevas y los visuales aún requieren ejecución en Desktop. Véanse [predicciones_y_navegacion.md](predicciones_y_navegacion.md) y [revision_informe.md](revision_informe.md).
