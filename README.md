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

El código de salida indica el resultado: `0` si terminó, `2` si un control crítico detuvo la ejecución y `3` si la configuración, un archivo o una hoja de las fuentes no se pudo leer. Cuando un control crítico falla, el reporte queda escrito y los resultados anteriores no se reemplazan. Una ejecución con advertencias, como los meses sin cobertura, continúa y las deja anotadas en el reporte.

### Configuración

Los períodos, los parámetros, los umbrales de calidad y los nombres de los archivos están en `config/pipeline.yaml`. Estas variables de entorno tienen prioridad sobre el archivo:

| Variable | Uso |
|---|---|
| `INGUAT_DATA_DIR` | Carpeta con los archivos de datos institucionales (obligatoria). |
| `PIPELINE_CONFIG` | Ruta de otro archivo de configuración. |
| `PIPELINE_OUTPUT_DIR` | Carpeta donde se guardan los resultados (por defecto `output`). |

El procedimiento no tiene componentes aleatorios. La semilla (`parameters.seed`) solo se usa para generar los datos sintéticos.

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
