from __future__ import annotations

from sqlalchemy import text

from .models import db


CURRENT_SCHEMA_VERSION = 6


def migrate_database() -> None:
    engine = db.engine
    _ensure_meta_table()

    with engine.begin() as conn:
        version = _read_schema_version(conn)
        if version is None:
            # For legacy databases (without db_meta), start from v1 and run
            # all idempotent migration steps to backfill compatibility data.
            version = 1
            _write_schema_version(conn, version)

    while version < CURRENT_SCHEMA_VERSION:
        if version == 1:
            _migrate_v1_to_v2()
        elif version == 2:
            _migrate_v2_to_v3()
        elif version == 3:
            _migrate_v3_to_v4()
        elif version == 4:
            _migrate_v4_to_v5()
        elif version == 5:
            _migrate_v5_to_v6()
        version += 1


def _ensure_meta_table() -> None:
    with db.engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS db_meta (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                )
                """
            )
        )


def _read_schema_version(conn) -> int | None:
    row = conn.execute(text("SELECT value FROM db_meta WHERE key = 'schema_version'")).fetchone()
    if not row:
        return None
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return None


def _write_schema_version(conn, version: int) -> None:
    conn.execute(
        text(
            """
            INSERT INTO db_meta(key, value) VALUES ('schema_version', :version)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """
        ),
        {"version": str(version)},
    )


def _migrate_v1_to_v2() -> None:
    with db.engine.begin() as conn:
        _grant_existing_credentials_all_phonebooks(conn)
        _write_schema_version(conn, 2)


def _migrate_v2_to_v3() -> None:
    with db.engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO phonebook_settings (phonebook_id, category)
                SELECT p.id, 'private'
                FROM phonebooks p
                LEFT JOIN phonebook_settings s ON s.phonebook_id = p.id
                WHERE s.id IS NULL
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE phonebook_settings
                SET category = 'private'
                WHERE category NOT IN ('private', 'business')
                """
            )
        )
        _grant_existing_credentials_all_phonebooks(conn)
        _write_schema_version(conn, 3)


def _migrate_v3_to_v4() -> None:
    with db.engine.begin() as conn:
        # Reserved compatibility step for previously released schema version 4.
        _write_schema_version(conn, 4)


def _migrate_v4_to_v5() -> None:
    with db.engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS sync_profiles (
                  id INTEGER PRIMARY KEY,
                  name VARCHAR(120) NOT NULL,
                  phonebook_id INTEGER NOT NULL,
                  phone_host VARCHAR(255) NOT NULL,
                  web_username VARCHAR(80) NOT NULL,
                  web_password_enc TEXT NOT NULL,
                  verify_tls BOOLEAN NOT NULL DEFAULT 0,
                  interval_minutes INTEGER NOT NULL DEFAULT 60,
                  enabled BOOLEAN NOT NULL DEFAULT 1,
                  last_run_at DATETIME,
                  last_status VARCHAR(20),
                  last_message VARCHAR(255),
                  next_run_at DATETIME,
                  created_at DATETIME NOT NULL,
                  updated_at DATETIME NOT NULL,
                  FOREIGN KEY(phonebook_id) REFERENCES phonebooks(id) ON DELETE CASCADE
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_phonebook_host
                ON sync_profiles(phonebook_id, phone_host)
                """
            )
        )
        _write_schema_version(conn, 5)


def _migrate_v5_to_v6() -> None:
    with db.engine.begin() as conn:
        if not _has_column(conn, "contact_entries", "ring"):
            conn.execute(text("ALTER TABLE contact_entries ADD COLUMN ring VARCHAR(80)"))
        if not _has_column(conn, "contact_entries", "photo"):
            conn.execute(text("ALTER TABLE contact_entries ADD COLUMN photo VARCHAR(120)"))
        _write_schema_version(conn, 6)


def _grant_existing_credentials_all_phonebooks(conn) -> None:
    row = conn.execute(text("SELECT COUNT(*) FROM access_credential_phonebooks")).fetchone()
    permission_count = int(row[0]) if row else 0
    if permission_count > 0:
        return

    conn.execute(
        text(
            """
            INSERT OR IGNORE INTO access_credential_phonebooks (credential_id, phonebook_id)
            SELECT c.id, p.id
            FROM access_credentials c
            CROSS JOIN phonebooks p
            """
        )
    )


def _has_column(conn, table_name: str, column_name: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(str(row[1]) == column_name for row in rows)
