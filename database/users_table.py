# users_table.py
# Creates a minimal `users` table in db.db and provides simple helpers & CLI.
from __future__ import annotations
import argparse
import base64
import os
import hmac
import datetime as dt
from typing import Optional

from sqlalchemy import create_engine, String, Integer, DateTime, func, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

# DB file next to this module
DB_PATH = os.path.join(os.path.dirname(__file__), "db.db")
DB_URL = f"sqlite:///{DB_PATH}"

# ----------------- SQLAlchemy base & model -----------------
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email:    Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

engine = create_engine(DB_URL, echo=False, future=True)

# ----------------- Password hashing (PBKDF2-HMAC-SHA256) -----------------
import hashlib

PBKDF2_ALGO = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 200_000
SALT_BYTES = 16
DKLEN = 32  # 256-bit derived key

def hash_password(plaintext: str) -> str:
    if not isinstance(plaintext, str) or plaintext == "":
        raise ValueError("Password cannot be empty.")
    salt = os.urandom(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", plaintext.encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=DKLEN)
    return f"{PBKDF2_ALGO}${PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"

def verify_password(plaintext: str, stored: str) -> bool:
    try:
        algo, iters_str, salt_b64, hash_b64 = stored.split("$", 3)
        assert algo == PBKDF2_ALGO
        iterations = int(iters_str)
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(hash_b64.encode())
        dk = hashlib.pbkdf2_hmac("sha256", plaintext.encode("utf-8"), salt, iterations, dklen=len(expected))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False

# ----------------- CRUD helpers -----------------
def create_tables() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(engine)

def create_user(username: Optional[str], email: str, password_plaintext: str) -> int:
    """
    Create a new user. Returns the new user_id.
    Raises ValueError if email already exists or invalid input.
    """
    if not email or not password_plaintext:
        raise ValueError("email and password required")
    with Session(engine) as s:
        # check email unique
        if s.query(User).filter_by(email=email).first():
            raise ValueError("Email already exists.")
        u = User(username=username, email=email, password_hash=hash_password(password_plaintext))
        s.add(u)
        s.commit()
        s.refresh(u)
        return int(u.user_id)

def get_user_by_email(email: str) -> Optional[User]:
    with Session(engine) as s:
        return s.query(User).filter_by(email=email).first()

def get_user_by_id(user_id: int) -> Optional[User]:
    with Session(engine) as s:
        return s.query(User).filter_by(user_id=int(user_id)).first()

def verify_user_by_email(email: str, password_plaintext: str) -> bool:
    u = get_user_by_email(email)
    if not u:
        return False
    return verify_password(password_plaintext, u.password_hash)

def list_users() -> list[tuple[int, str]]:
    with Session(engine) as s:
        return [(int(u.user_id), u.email) for u in s.query(User).all()]

# ----------------- CLI -----------------
def main():
    parser = argparse.ArgumentParser(description="Users table utility")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Create the users table if it doesn't exist")

    p_add = sub.add_parser("add", help="Add a new user")
    p_add.add_argument("--username", required=False)
    p_add.add_argument("--email", required=True)
    p_add.add_argument("--password", required=True)

    p_check = sub.add_parser("check", help="Verify an email/password")
    p_check.add_argument("--email", required=True)
    p_check.add_argument("--password", required=True)

    sub.add_parser("list", help="List users (id, email)")

    args = parser.parse_args()

    if args.cmd == "init":
        create_tables()
        print("Users table is ready.")
    elif args.cmd == "add":
        create_tables()
        try:
            uid = create_user(args.username, args.email, args.password)
            print(f"Created user id={uid}.")
        except ValueError as e:
            print(f"Error: {e}")
    elif args.cmd == "check":
        create_tables()
        ok = verify_user_by_email(args.email, args.password)
        print("OK" if ok else "FAIL")
    elif args.cmd == "list":
        create_tables()
        for uid, e in list_users():
            print(f"{uid}\t{e}")

if __name__ == "__main__":
    main()
