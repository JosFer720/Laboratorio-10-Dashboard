# Observatorio de turismo sostenible

Tablero interactivo para consultar indicadores de turismo receptor en Guatemala. Usa datos mensuales del Instituto Guatemalteco de Turismo (INGUAT) para 2022, 2023 y 2024: las llegadas de visitantes no residentes y la ocupación hotelera.

## Requisitos

- Python 3.11 o posterior.
- Acceso a una terminal.

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

## Ejecución

Desde la raíz del proyecto:

```bash
python app.py
```

El tablero estará disponible en `http://127.0.0.1:8050`.

La ruta del CSV puede cambiarse con la variable de entorno `TOURISM_DATA_PATH`. El archivo `.env.example` muestra las variables disponibles; deben establecerse en la terminal antes de iniciar la aplicación.
