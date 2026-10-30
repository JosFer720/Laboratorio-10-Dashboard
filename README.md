# Observatorio de turismo sostenible

Este proyecto tiene dos partes:

- Un tablero interactivo para consultar turistas y excursionistas en Guatemala entre enero de 2009 y junio de 2026, comparar tres modelos sobre su evaluación histórica y explorar la ocupación hotelera de 2022 a 2024.
- Un pipeline que lee las fuentes institucionales de movilidad y de flujo migratorio, valida los datos con seis controles de calidad y estima los visitantes únicos de los meses sin cobertura en cada subdestino.

El alcance de la estimación está en `docs/alcance.md` y el diagrama del flujo en `docs/flujo.md`.

## Requisitos

- Python 3.11 o posterior.
- Acceso a una terminal.
- Para el pipeline, los archivos de datos institucionales `BD_moviidad_mensual.xlsx` y `Base_Migracion_2009-2026jun.xlsx`, o datos sintéticos para probarlo.

## Instalación

En Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

En macOS o Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Pipeline de estimación

### Datos

Los datos institucionales son confidenciales: no se guardan en el repositorio. Deben estar en una carpeta propia y el pipeline la lee de la variable de entorno `INGUAT_DATA_DIR`, que se define en la terminal antes de ejecutarlo (en `.env.example` está la lista de variables).

En Windows PowerShell:

```powershell
$env:INGUAT_DATA_DIR = "C:\ruta\a\Datos Inguat"
```

En macOS o Linux:

```bash
export INGUAT_DATA_DIR="/ruta/a/Datos Inguat"
```

Para probar el pipeline sin datos institucionales se pueden generar datos sintéticos con la misma estructura. No representan cifras reales:

```bash
python scripts/generate_synthetic_data.py datos_sinteticos
```

Después se apunta `INGUAT_DATA_DIR` a esa carpeta. El script acepta `--problem` para introducir un problema conocido (`missing_column`, `duplicate_row`, `zero_denominator`, `negative_visitors`, `invalid_date` o `missing_values`) y comprobar que los controles lo detectan.

### Ejecución

Con `INGUAT_DATA_DIR` definida, desde la raíz del proyecto:

```bash
python run_pipeline.py
```

El comando lee las fuentes, ejecuta los controles de calidad, prepara las series, estima los meses sin cobertura y guarda los resultados en la carpeta `output/`. Con los datos reales tarda alrededor de medio minuto.

| Archivo en `output/` | Contenido |
|---|---|
| `estimates.csv` | Estimaciones por subdestino y mes, rotuladas como estimación. |
| `reparto_factors.csv` | Factor de reparto de cada subdestino y meses de ajuste usados. |
| `national_entries.csv` | Entradas nacionales de los meses de ajuste y de los meses estimados. |
| `coverage.csv` | Qué fuente tiene datos en cada mes de la ventana de trabajo. |
| `reports/quality_<ejecución>.json` | Resultado de los seis controles de cada ejecución. |

El código de salida indica el resultado: `0` si terminó y la versión se aprobó y publicó, `2` si un control crítico detuvo la ejecución, `3` si la configuración, un archivo o una hoja de las fuentes no se pudo leer, y `4` si la ejecución terminó pero la regla de aceptación rechazó la versión. Cuando un control crítico falla, el reporte queda escrito y los resultados anteriores no se reemplazan. Una ejecución con advertencias, como los meses sin cobertura, continúa y las deja anotadas en el reporte.

### Configuración

Los períodos, los parámetros, los umbrales de calidad y los nombres de los archivos están en `config/pipeline.yaml`. Estas variables de entorno tienen prioridad sobre el archivo:

| Variable | Uso |
|---|---|
| `INGUAT_DATA_DIR` | Carpeta con los archivos de datos institucionales (obligatoria). |
| `PIPELINE_CONFIG` | Ruta de otro archivo de configuración. |
| `PIPELINE_OUTPUT_DIR` | Carpeta donde se guardan los resultados (por defecto `output`). |
| `PIPELINE_VERSIONS_DIR` | Carpeta del almacén de versiones aprobadas (por defecto `output/versions`). |

El procedimiento no tiene componentes aleatorios. La semilla (`parameters.seed`) solo se usa para generar los datos sintéticos.

### Registro y reproducibilidad

Cada ejecución se registra en MLflow con el commit de Git, las huellas de las fuentes, los períodos, parámetros, seis controles y artefactos de configuración y resultados. Las ejecuciones detenidas por un control crítico quedan con estado `FAILED` y su causa, sin métricas de evaluación inventadas.

El almacén local queda por defecto en `output/mlflow/`. Puede cambiarse con `MLFLOW_TRACKING_URI`, y el nombre del experimento con `MLFLOW_EXPERIMENT_NAME`.

Para comprobar que dos ejecuciones con los mismos datos y configuración producen resultados equivalentes:

```bash
python scripts/check_reproducibility.py
```

La comparación cubre los CSV de resultados y de evaluación, ignora únicamente el identificador y la fecha variables de cada corrida y usa la tolerancia `tracking.reproducibility_tolerance` de la configuración. El procedimiento actual es determinista, por lo que la diferencia esperada es cero.

Para consultar estados, métricas, parámetros y artefactos registrados:

```bash
python scripts/query_mlflow.py --limit 20
```

Las métricas de la evaluación temporal (`evaluation.*`) se registran en cada ejecución que llega a evaluar; una corrida que se detiene antes no contiene métricas. La comprobación de reproducibilidad nunca publica versiones.

### Evaluación, aprobación y versiones

Cada ejecución oculta los meses de evaluación (marzo a junio de 2026), uno por uno y en orden, y los estima solo con la movilidad de los meses anteriores. Compara el factor de reparto con dos referencias sencillas, el último valor observado y el promedio de los meses anteriores, con MAE, RMSE y MAPE. El MAPE excluye los observados iguales a cero y los cuenta aparte. Enero y febrero de 2026 no se evalúan porque no tienen valores observados.

La regla de aceptación está en la sección `acceptance` de `config/pipeline.yaml`: ningún control crítico en falla, estimaciones completas, positivas y finitas, al menos cuatro meses evaluados con todos los subdestinos y un MAPE que no supere `max_mape`. El veredicto y sus razones quedan en `output/reports/acceptance_<ejecución>.json` y en MLflow.

Solo una versión aprobada se publica. Cada una queda en su carpeta dentro del almacén de versiones, con sus estimaciones, la evaluación, la configuración efectiva y un `metadata.json` con la ejecución, la fecha, la versión del procedimiento, la métrica de validación y los períodos evaluados. `current.json` apunta a la versión vigente y `history.jsonl` registra cada publicación y restauración. Si una ejecución falla o se rechaza, la versión vigente no cambia.

Para listar las versiones aprobadas y ver cuál está vigente:

```bash
python scripts/restore_version.py
```

Para volver vigente una versión anterior:

```bash
python scripts/restore_version.py --version <identificador>
```

## Tablero

Desde la raíz del proyecto:

```bash
python app.py
```

El tablero estará disponible en `http://127.0.0.1:8050`.

Las rutas de los CSV del tablero pueden cambiarse con las variables de entorno mostradas en `.env.example`; deben establecerse en la terminal antes de iniciar la aplicación.

## Pruebas

```bash
python -m pytest
```

Las pruebas usan datos sintéticos y no necesitan los datos institucionales.
