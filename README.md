# Observatorio de turismo sostenible

Tablero interactivo para consultar indicadores de turismo receptor en Guatemala. La base inicial contiene las llegadas mensuales de visitantes no residentes publicadas por el Instituto Guatemalteco de Turismo (INGUAT) para 2022, 2023 y 2024.

## Requisitos

- Python 3.11 o posterior.
- Acceso a una terminal.

## Instalacion

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

## Ejecucion

Desde la raiz del proyecto:

```bash
python app.py
```

El tablero estara disponible en `http://127.0.0.1:8050`.

La ruta del CSV puede cambiarse con la variable de entorno `TOURISM_DATA_PATH`. El archivo `.env.example` muestra las variables disponibles; deben establecerse en la terminal antes de iniciar la aplicacion.
