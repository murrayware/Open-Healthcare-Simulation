# outputs_table.py
# Adds an `outputs` table to db.db for storing per-user simulation runs.
from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    create_engine,
    Integer,
    String,
    ForeignKey,
    Text,
    DateTime,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from sqlalchemy.types import TypeDecorator

DB_PATH = os.path.join(os.path.dirname(__file__), "db.db")
DB_URL = f"sqlite:///{DB_PATH}"

# simple JSON column storing text
class JSON(TypeDecorator):
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return json.loads(value)
        except Exception:
            return None

# Import the correct Base, User model, and engine from users_table
from database.users_table import Base, User, engine

# outputs table
class Output(Base):
    __tablename__ = "outputs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    input_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("inputs.id"), nullable=True, index=True)
    configs: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", lazy="joined")

def create_outputs_table():
    """Create only the outputs table if it doesn't exist"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    # Ensure inputs table exists first (for foreign key)
    try:
        from database import inputs_table
        inputs_table.create_inputs_table()
    except Exception:
        pass
    # Create only the Output table, not the users table (users_table.py handles that)
    Output.__table__.create(engine, checkfirst=True)

# helpers
def add_output(user_id: int, configs: dict, results: Optional[dict] = None, input_id: Optional[int] = None) -> int:
    with Session(engine) as s:
        user = s.get(User, int(user_id))
        if not user:
            raise ValueError(f"User id '{user_id}' does not exist.")
        out = Output(user_id=int(user_id), configs=configs, results=results, input_id=input_id)
        s.add(out)
        s.commit()
        s.refresh(out)
        return int(out.id)

def get_user_outputs(user_id: int, limit: Optional[int] = None) -> List[Output]:
    with Session(engine) as s:
        q = s.query(Output).filter_by(user_id=int(user_id)).order_by(Output.created.desc())
        if limit:
            q = q.limit(limit)
        return q.all()


def get_output_by_id(output_id: int) -> Optional[Output]:
    """Get a single output by its ID."""
    with Session(engine) as s:
        return s.get(Output, int(output_id))

# Create the outputs table when this module is imported
create_outputs_table()
