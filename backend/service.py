from __future__ import annotations

from pathlib import Path

from backend.database import get_connection, init_db


class PlateRecordService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path
        init_db(self.db_path) if self.db_path else init_db()

    def _connect(self):
        return get_connection(self.db_path) if self.db_path else get_connection()

    def list_records(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, plate_number, owner_name, car_model, notes, created_at
                FROM plate_records
                ORDER BY id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def search_by_plate(self, plate_query: str) -> list[dict]:
        query = plate_query.strip()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, plate_number, owner_name, car_model, notes, created_at
                FROM plate_records
                WHERE plate_number LIKE ?
                ORDER BY id DESC
                """,
                (f"%{query}%",),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_record(
        self, plate_number: str, owner_name: str, car_model: str, notes: str = ""
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO plate_records (plate_number, owner_name, car_model, notes)
                VALUES (?, ?, ?, ?)
                """,
                (plate_number.strip(), owner_name.strip(), car_model.strip(), notes.strip()),
            )
            connection.commit()

    def update_record(
        self,
        record_id: int,
        plate_number: str,
        owner_name: str,
        car_model: str,
        notes: str = "",
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE plate_records
                SET plate_number = ?, owner_name = ?, car_model = ?, notes = ?
                WHERE id = ?
                """,
                (
                    plate_number.strip(),
                    owner_name.strip(),
                    car_model.strip(),
                    notes.strip(),
                    record_id,
                ),
            )
            connection.commit()
        return cursor.rowcount > 0

    def delete_record(self, record_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM plate_records WHERE id = ?",
                (record_id,),
            )
            connection.commit()
        return cursor.rowcount > 0

