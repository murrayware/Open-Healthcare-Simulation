# inputs_table.py
# Adds an `inputs` table to db.db for storing simulation input settings/configurations.
from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    Integer,
    String,
    ForeignKey,
    Text,
    DateTime,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

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

# inputs table
class Input(Base):
    __tablename__ = "inputs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    hospital_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    settings_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    simulation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)  # Groups inputs for same simulation
    simulation_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Original simulation name
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=True, index=True)
    is_first_run: Mapped[bool] = mapped_column(Integer, default=False, nullable=False)

def create_inputs_table():
    """Create the inputs table if it doesn't exist."""
    Base.metadata.create_all(engine, tables=[Input.__table__])

# helpers
from sqlalchemy.orm import Session

def add_input(user_id: int, hospital_id: str, settings_json: dict, run_id: Optional[str] = None, simulation_id: Optional[str] = None, simulation_name: Optional[str] = None, is_first_run: bool = False) -> int:
    """Add a new input record and return its ID."""
    with Session(engine) as s:
        inp = Input(
            user_id=int(user_id) if user_id else None,
            hospital_id=hospital_id,
            settings_json=settings_json,
            run_id=run_id,
            simulation_id=simulation_id,
            simulation_name=simulation_name,
            is_first_run=is_first_run
        )
        s.add(inp)
        s.commit()
        s.refresh(inp)
        return int(inp.id)

def get_input_by_id(input_id: int) -> Optional[Input]:
    """Get a single input by its ID."""
    with Session(engine) as s:
        return s.get(Input, int(input_id))

def get_inputs_by_run_id(run_id: str) -> list[Input]:
    """Get all inputs with a specific run_id."""
    with Session(engine) as s:
        return s.query(Input).filter_by(run_id=run_id).all()

def get_first_input_by_simulation_id(simulation_id: str) -> Optional[Input]:
    """Get the first input (is_first_run=True) for a specific simulation_id."""
    with Session(engine) as s:
        return s.query(Input).filter_by(simulation_id=simulation_id, is_first_run=True).first()

if __name__ == "__main__":
    # Create the table
    create_inputs_table()
    print("inputs table created successfully!")
