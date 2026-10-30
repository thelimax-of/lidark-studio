from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from . import models  # noqa: F401  (registra as tabelas)
from .config import DB_PATH

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False, "timeout": 30},
)


@event.listens_for(engine, "connect")
def _pragmas(dbapi_conn, _rec) -> None:
    """Ajustes de velocidade por conexão (WAL + sync NORMAL é seguro contra queda de energia no modo WAL)."""
    cur = dbapi_conn.cursor()
    for p in ("journal_mode=WAL", "synchronous=NORMAL", "temp_store=MEMORY", "mmap_size=268435456",
              "cache_size=-32000", "busy_timeout=30000"):
        try:
            cur.execute(f"PRAGMA {p}")
        except Exception:  # noqa: BLE001 — banco ocupado num instante: segue com o padrão
            pass
    cur.close()


# Índices das consultas quentes (painel, métricas, fila). IF NOT EXISTS: roda a cada início sem custo.
INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_ms_pub_captured ON metricsnapshot (publication_id, captured_at)",
    "CREATE INDEX IF NOT EXISTS ix_ms_channel_platform_captured ON metricsnapshot (channel_id, platform, captured_at)",
    "CREATE INDEX IF NOT EXISTS ix_publication_video ON publication (video_id)",
    "CREATE INDEX IF NOT EXISTS ix_publication_channel_status ON publication (channel_id, status)",
    "CREATE INDEX IF NOT EXISTS ix_video_script ON video (script_id)",
    "CREATE INDEX IF NOT EXISTS ix_script_idea ON script (idea_id)",
    "CREATE INDEX IF NOT EXISTS ix_script_channel_created ON script (channel_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_idea_channel_status_created ON idea (channel_id, status, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_job_status_id ON job (status, id)",
    "CREATE INDEX IF NOT EXISTS ix_job_kind_status ON job (kind, status)",
    "CREATE INDEX IF NOT EXISTS ix_account_channel_platform ON account (channel_id, platform)",
    "CREATE INDEX IF NOT EXISTS ix_insight_channel_created ON insight (channel_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_comment_channel_status_pub ON comment (channel_id, status, published_at)",
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        _auto_migrate(conn)
        ensure_indexes(conn)


def ensure_indexes(conn) -> None:
    for ddl in INDEXES:
        try:
            conn.exec_driver_sql(ddl)
        except Exception as e:  # noqa: BLE001 — tabela ainda não existe etc.: não impede o servidor de subir
            import logging
            logging.getLogger("lidark.db").warning("índice não criado (%s): %s", ddl.split(" ON ")[0][-40:], e)
    try:
        conn.exec_driver_sql("PRAGMA optimize")
    except Exception:  # noqa: BLE001
        pass


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
