from __future__ import annotations

from pathlib import Path

from backend.database import get_connection, init_db


class AuthService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path
        init_db(self.db_path) if self.db_path else init_db()

    def _connect(self):
        return get_connection(self.db_path) if self.db_path else get_connection()

    def register_user(
        self,
        account_type: str,
        name: str,
        identifier: str,
        username: str,
        password: str,
    ) -> tuple[bool, str]:
        with self._connect() as connection:
            exists = connection.execute(
                """
                SELECT id
                FROM users
                WHERE account_type = ? AND username = ?
                """,
                (account_type.strip(), username.strip()),
            ).fetchone()
            if exists:
                return False, "این نام کاربری قبلا ثبت شده است."

            connection.execute(
                """
                INSERT INTO users (account_type, name, identifier, username, password)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    account_type.strip(),
                    name.strip(),
                    identifier.strip(),
                    username.strip(),
                    password,
                ),
            )
            connection.commit()
        return True, "ثبت نام با موفقیت انجام شد."

    def authenticate_user(
        self,
        account_type: str,
        username: str,
        password: str,
    ) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, account_type, name, identifier, username
                FROM users
                WHERE account_type = ? AND username = ? AND password = ?
                """,
                (account_type.strip(), username.strip(), password),
            ).fetchone()
        return dict(row) if row else None
