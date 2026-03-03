from __future__ import annotations
from typing import List, Dict, Optional
from datetime import datetime

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    func,
    text,
)
from sqlalchemy.engine import Engine

# reuse engine from your existing DB module
from database.users_table import engine as DB_ENGINE


def create_tables() -> None:
    """
    Create the `compare` table if missing. `output_2_id` is nullable so the
    second output can be attached later.
    """
    metadata = MetaData()
    metadata.reflect(bind=DB_ENGINE)

    if "compare" in metadata.tables:
        print("compare table already exists.")
        return

    compare = Table(
        "compare",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", Integer, ForeignKey("users.user_id"), nullable=False, index=True),
        Column("output_1_id", Integer, ForeignKey("outputs.id"), nullable=False, index=True),
        Column("output_2_id", Integer, ForeignKey("outputs.id"), nullable=True, index=True),
        Column("simulation_name", String(255), nullable=True),
        Column("hospital_id", String(255), nullable=True),
        Column("created", DateTime, server_default=func.now(), nullable=False),
    )

    metadata.create_all(DB_ENGINE, tables=[compare])
    print("compare table created.")


def add_compare(user_id: int, output_1_id: int, output_2_id: Optional[int] = None, simulation_name: Optional[str] = None, hospital_id: Optional[str] = None) -> int:
    """
    Insert a compare row. output_2_id may be None. Returns new compare.id.
    """
    if output_2_id is None:
        sql = text(
            "INSERT INTO compare (user_id, output_1_id, output_2_id, simulation_name, hospital_id) VALUES (:user_id, :o1, NULL, :sim_name, :hosp_id)"
        )
        params = {"user_id": int(user_id), "o1": int(output_1_id), "sim_name": simulation_name, "hosp_id": hospital_id}
    else:
        sql = text(
            "INSERT INTO compare (user_id, output_1_id, output_2_id, simulation_name, hospital_id) VALUES (:user_id, :o1, :o2, :sim_name, :hosp_id)"
        )
        params = {"user_id": int(user_id), "o1": int(output_1_id), "o2": int(output_2_id), "sim_name": simulation_name, "hosp_id": hospital_id}

    with DB_ENGINE.begin() as conn:
        res = conn.execute(sql, params)
        try:
            inserted_id = res.lastrowid
        except Exception:
            inserted_id = int(conn.execute(text("SELECT last_insert_rowid()")).scalar_one())
    return int(inserted_id)


def attach_output_to_compare(compare_id: int, output_2_id: int) -> None:
    """Set output_2_id on an existing compare row."""
    with DB_ENGINE.begin() as conn:
        conn.execute(
            text("UPDATE compare SET output_2_id = :o2 WHERE id = :id"),
            {"o2": int(output_2_id), "id": int(compare_id)},
        )


def update_compare_output_2(compare_id: int, output_2_id: int, user_id: int) -> bool:
    """
    Set output_2_id on an existing compare row, but only if it belongs to the given user.
    Returns True if updated, False if no matching row found.
    """
    with DB_ENGINE.begin() as conn:
        result = conn.execute(
            text("UPDATE compare SET output_2_id = :o2 WHERE id = :id AND user_id = :user_id"),
            {"o2": int(output_2_id), "id": int(compare_id), "user_id": int(user_id)},
        )
        return result.rowcount > 0


def get_user_compares(user_id: int) -> List[Dict]:
    sql = text(
        "SELECT id, user_id, output_1_id, output_2_id, simulation_name, hospital_id, created FROM compare "
        "WHERE user_id = :user_id ORDER BY created DESC"
    )
    with DB_ENGINE.connect() as conn:
        rows = conn.execute(sql, {"user_id": int(user_id)}).mappings().all()
        return [dict(r) for r in rows]


def get_compare_by_id(compare_id: int) -> Optional[Dict]:
    sql = text("SELECT id, user_id, output_1_id, output_2_id, created FROM compare WHERE id = :id LIMIT 1")
    with DB_ENGINE.connect() as conn:
        r = conn.execute(sql, {"id": int(compare_id)}).mappings().first()
        return dict(r) if r else None


if __name__ == "__main__":
    # Run as package from project root so imports resolve:
    # python -m database.compare_table
    create_tables()