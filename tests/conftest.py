from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@event.listens_for(Engine, "connect")
def _relax_sqlite_durability(dbapi_connection, connection_record) -> None:
    """Acelera la base de MLflow en las pruebas.

    Cada escritura de SQLite espera a que el disco confirme el commit. En algunos
    discos eso toma cientos de milisegundos y una sola ejecución del pipeline
    llega a tardar casi un minuto. Las bases de las pruebas son temporales, así
    que no necesitan esa garantía de durabilidad.
    """
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA synchronous=OFF")
        cursor.execute("PRAGMA journal_mode=MEMORY")
        cursor.close()
