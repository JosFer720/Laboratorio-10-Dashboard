# Observatorio de turismo sostenible

Tablero interactivo para consultar turistas y excursionistas en Guatemala entre enero de 2009 y junio de 2026, comparar tres modelos sobre su evaluación histórica y explorar la ocupación hotelera de 2022 a 2024.

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

Las rutas de los CSV pueden cambiarse con las variables de entorno mostradas en `.env.example`; deben establecerse en la terminal antes de iniciar la aplicación.
