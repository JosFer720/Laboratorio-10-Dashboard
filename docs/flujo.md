# Flujo de los datos

El flujo va desde la lectura de las fuentes institucionales hasta la consulta de las estimaciones. Se ejecuta con un solo comando (`python run_pipeline.py`) y no depende de archivos intermedios hechos a mano ni de la memoria de una sesión. El tablero no ejecuta el pipeline: solo lee la versión aprobada vigente, de modo que cambiar un filtro nunca vuelve a calcular nada.

```mermaid
flowchart TD
    S[("Fuentes institucionales<br/>movilidad mensual<br/>flujo migratorio")] --> L["1. Lectura<br/>tablas tal como vienen<br/>huella digital de cada archivo"]
    L --> V{"2. VALIDACIÓN<br/>seis controles de calidad"}
    V -- "falla un control crítico" --> X["Se detiene<br/>queda el reporte de controles<br/>los resultados anteriores no cambian"]
    V -- "correcto o con advertencias" --> P["3. Preparación<br/>entradas nacionales, visitantes por subdestino, cobertura"]
    P --> E["4. Factor de reparto y estimación<br/>meses sin cobertura"]
    E --> EV{{"5. EVALUACIÓN del procedimiento<br/>meses ocultos, solo con meses anteriores<br/>comparación con referencias sencillas"}}
    EV --> AU{"6. AUTORIZACIÓN<br/>regla de aceptación"}
    AU --> A["7. Almacenamiento<br/>carpeta temporal y luego carpeta de salida"]
    A --> R[("Resultados de la ejecución<br/>estimaciones, evaluación y reportes")]
    AU -- "aprobada" --> PV[("Almacén de versiones aprobadas<br/>la nueva versión pasa a ser la vigente")]
    AU -- "rechazada" --> KV["La versión vigente no cambia"]
    PV --> T["Tablero<br/>consulta de la versión vigente"]
    RS["Restauración de una versión anterior"] --> PV
```

La evaluación ocurre en la etapa 5 y la autorización de la publicación en la etapa 6. Una versión rechazada igual deja sus resultados y su reporte en la carpeta de salida para revisarlos, pero no entra al almacén de versiones aprobadas.

## Etapas

| Etapa | Qué hace | Módulo |
|---|---|---|
| 1. Lectura | Lee las seis hojas de movilidad mensual y la hoja de datos del flujo migratorio sin limpiar nada, y calcula la huella digital (SHA-256) de cada archivo. | `tourism_pipeline.ingestion` |
| 2. Validación | Ejecuta los seis controles de calidad y escribe su reporte. | `tourism_pipeline.validation` |
| 3. Preparación | Construye las entradas nacionales por mes, los visitantes por subdestino y mes, y la tabla de cobertura. | `tourism_pipeline.preparation` |
| 4. Estimación | Calcula el factor de reparto de cada subdestino con los meses de ajuste anteriores y estima los meses sin cobertura. | `tourism_pipeline.preparation`, `tourism_pipeline.estimation` |
| 5. Evaluación | Oculta los meses de evaluación uno por uno, los estima solo con meses anteriores y calcula MAE, RMSE y MAPE del procedimiento y de dos referencias sencillas. | `tourism_pipeline.estimation` |
| 6. Autorización | Aplica la regla de aceptación: calidad, integridad de las salidas, cobertura de la evaluación y desempeño. | `tourism_pipeline.publication` |
| 7. Almacenamiento y publicación | Escribe los resultados en una carpeta temporal, los mueve a la carpeta de salida y, si la versión se aprobó, la guarda en el almacén y cambia el puntero a la vigente. | `tourism_pipeline.pipeline`, `tourism_pipeline.publication` |

## Dónde se valida y dónde se detiene

La validación ocurre en la etapa 2, antes de preparar los datos. Cada control tiene dos condiciones, una de advertencia (el flujo continúa y queda anotada en el reporte) y otra de parada (el flujo se detiene).

| Control | Qué verifica | Advertencia cuando | Se detiene cuando |
|---|---|---|---|
| `columns_and_types` | Columnas indispensables y tipos compatibles. | Hay columnas adicionales no esperadas. | Falta una columna indispensable o un tipo es incompatible. |
| `dates_and_coverage` | Fechas válidas y cobertura de los meses necesarios. | Los meses sin cobertura de movilidad configurados están ausentes y se dejan sin dato. | Una fecha es inválida o falta un mes necesario para el ajuste o la estimación. |
| `uniqueness` | Filas únicas según la granularidad de cada fuente. | Los duplicados están solo antes del primer año de migración que se usa. | Hay duplicados en la movilidad o en los años de migración que se usan. |
| `missing_values` | Valores faltantes que impiden estimar frente a los solo descriptivos. | Faltan valores descriptivos, dentro del umbral. | Falta un valor indispensable o los descriptivos superan el umbral. |
| `values_and_denominators` | Conteos finitos y no negativos y denominadores nacionales positivos. | Hay conteos en cero, pero ningún denominador de ajuste es cero. | Un conteo es negativo o no finito, o un denominador de ajuste no es positivo. |
| `methodology` | La serie mensual viene de la base mensual, no se suman subdestinos ni se rellenan con cero los meses sin cobertura. | La movilidad tiene meses fuera de la cobertura configurada. | Se usa la base diaria, se suman subdestinos, se arman totales o se rellenan con cero los meses sin cobertura. |

Cuando se detiene, el pipeline termina con código de salida 2, deja el reporte de controles en `output/reports/` y no toca los resultados anteriores. Los resultados nuevos se escriben primero en una carpeta temporal dentro de la carpeta de salida y solo reemplazan a los anteriores cuando todas las etapas terminaron bien.

## Archivos de salida

| Archivo | Contenido |
|---|---|
| `estimates.csv` | Estimaciones por subdestino y mes, con la ejecución que las generó. |
| `reparto_factors.csv` | Factor de reparto de cada subdestino y meses de ajuste usados. |
| `national_entries.csv` | Entradas nacionales de los meses de ajuste y de los meses estimados. |
| `coverage.csv` | Qué fuente tiene datos en cada mes de la ventana de trabajo. |
| `reports/quality_<ejecución>.json` | Resultado de los seis controles de cada ejecución, también cuando se detiene. |
| `evaluation.csv` | Valor observado y estimaciones del procedimiento y de las dos referencias en cada mes evaluado. |
| `evaluation_by_destination.csv` | MAE, RMSE y MAPE de cada método por subdestino. |
| `reports/acceptance_<ejecución>.json` | Veredicto de la regla de aceptación, sus razones, umbrales y métricas. |
| `versions/<ejecución>/` | Versión aprobada: estimaciones, evaluación, configuración efectiva y `metadata.json`. |
| `versions/current.json` | Puntero a la versión vigente que consulta el tablero. |
| `versions/history.jsonl` | Cada publicación y restauración, con su fecha y la versión anterior. |
| `versions/<ejecución>/observed.csv` | Instantánea de visitantes observados por subdestino y mes que acompaña a las estimaciones aprobadas. |
| `reports/execution_<ejecución>.json` | Inicio, fin, etapas completadas, advertencias, errores, monitoreo y resultado de publicación. También se guarda en MLflow. |

El tablero consulta el puntero vigente cada 30 segundos y al elegir un subdestino. No ejecuta ninguna etapa del procedimiento. Distingue observado en azul continuo de estimado en naranja discontinuo y deja los meses sin observación como sin dato. Si no hay una versión aprobada legible, no muestra estimaciones.

El monitoreo compara el último mes de cada fuente y de los resultados con la cobertura configurada. También compara faltantes, claves duplicadas y cobertura con la ejecución anterior que leyó ambas fuentes, y revisa valores negativos, no finitos o variaciones superiores al umbral frente a la versión vigente. Las alertas de variación requieren revisión y no prueban pérdida de precisión. Solo la evaluación de meses observados comparables produce métricas de error.
