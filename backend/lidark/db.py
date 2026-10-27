from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from . import models  # noqa: F401  (registra as tabelas)
from .config import DB_PATH

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False, "timeout": 30},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        _auto_migrate(conn)


def _auto_migrate(conn) -> None:
    """Adiciona colunas novas dos modelos em tabelas já existentes (migração leve)."""
    for table in SQLModel.metadata.sorted_tables:
        existing = {r[1] for r in conn.exec_driver_sql(f"PRAGMA table_info('{table.name}')")}
        for col in table.columns:
            if col.name in existing:
                continue
            ddl = col.type.compile(dialect=engine.dialect)
            default = "''" if ddl.upper().startswith(("VARCHAR", "TEXT")) else "0" if ddl.upper() in (
                "INTEGER", "FLOAT", "BOOLEAN") else "NULL"
            if ddl.upper() == "JSON":
                default = "'{}'"
            conn.exec_driver_sql(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {ddl} DEFAULT {default}")


@contextmanager
def session() -> Iterator[Session]:
    with Session(engine, expire_on_commit=False) as s:
        yield s


def get_session() -> Iterator[Session]:
    """Dependência do FastAPI."""
    with Session(engine, expire_on_commit=False) as s:
        yield s
