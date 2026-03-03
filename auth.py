# auth.py
import os
import datetime as dt
from functools import wraps

from flask import Blueprint, current_app, jsonify, request, g
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

# use the shared users_table helpers
from database.users_table import (
    create_tables,
    create_user,
    get_user_by_email,
    get_user_by_id,
    verify_user_by_email,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# ---------------- JWT helpers ----------------
def _secret():
    secret = current_app.config.get("SECRET_KEY") or os.environ.get("FLASK_SECRET")
    if not secret:
        raise RuntimeError("SECRET_KEY / FLASK_SECRET not set")
    return secret

def _make_token(user_id, hours=8):
    now = dt.datetime.utcnow()
    payload = {
        "sub": str(int(user_id)),   # <-- make subject a string
        "iat": now,
        "exp": now + dt.timedelta(hours=hours),
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")

def _decode(token):
    return jwt.decode(token, _secret(), algorithms=["HS256"])

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        current_app.logger.debug("Authorization header: %s", auth_header)
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = _decode(token)
        except jwt.ExpiredSignatureError as e:
            current_app.logger.warning("Token expired: %s", e)
            return jsonify({"error": "Token expired"}), 401
        except Exception as e:
            current_app.logger.exception("Token decode failed: %s", e)
            # also log server secret to ensure it's set (avoid printing secret in production)
            current_app.logger.debug("SECRET_KEY present: %s", bool(current_app.config.get("SECRET_KEY")))
            return jsonify({"error": "Invalid token"}), 401
        g.user_id = payload["sub"]
        return fn(*args, **kwargs)
    return wrapper

# ---------------- Routes ----------------
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip() or None  # map to username in users_table

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400

    try:
        uid = create_user(name, email, password)
    except ValueError as e:
        return jsonify({"error": str(e)}), 409

    token = _make_token(uid)
    return jsonify({"token": token, "user": {"id": uid, "email": email, "name": name}}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "invalid credentials"}), 401

    # user.password_hash is stored by users_table
    from database.users_table import verify_password  # local import to keep top-level small
    if not verify_password(password, user.password_hash):
        return jsonify({"error": "invalid credentials"}), 401

    token = _make_token(user.user_id)
    return jsonify({"token": token, "user": {"id": user.user_id, "email": user.email, "name": user.username}}), 200

@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    user = get_user_by_id(g.user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify({
        "id": user.user_id,
        "email": user.email,
        "name": user.username,
        "created_at": user.created.isoformat() if user.created is not None else None,
    }), 200

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    # For JWTs, "logout" is client-side (discard token). Endpoint exists for symmetry.
    return jsonify({"ok": True}), 200

def init_auth(app):
    # ensure all database tables exist
    with app.app_context():
        create_tables()  # creates users table
        # Create outputs table before compare table (due to foreign key dependencies)
        from database import outputs_table
        outputs_table.create_outputs_table()
        # Create compare table (depends on users and outputs tables)
        from database import compare_table
        compare_table.create_tables()
        # Create and seed hospital templates table
        from database import csv_template
        csv_template.ensure_db()
        # Import hospital data if the table is empty
        try:
            from sqlalchemy import text
            with csv_template.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM default_hosps"))
                count = result.scalar()
                if count == 0:
                    csv_template.import_from_csv()
                    print(f"Imported hospital data from CSV files")
        except Exception as e:
            print(f"Warning: Could not import hospital data: {e}")
