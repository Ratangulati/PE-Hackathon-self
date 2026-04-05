import csv
import io

from flask import Blueprint, jsonify, request
from peewee import IntegrityError
from playhouse.shortcuts import model_to_dict

from app.models.user import User

users_bp = Blueprint("users", __name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _validate_user_payload(data):
    """Return (cleaned_data, errors) for a create/update payload."""
    errors = []

    email    = data.get("email")
    username = data.get("username")

    if email is None:
        errors.append("'email' is required")
    elif not isinstance(email, str) or not email.strip():
        errors.append("'email' must be a non-empty string")
    elif len(email.strip()) > 255:
        errors.append("'email' must be 255 characters or fewer")

    if username is None:
        errors.append("'username' is required")
    elif not isinstance(username, str) or not username.strip():
        errors.append("'username' must be a non-empty string")
    elif len(username.strip()) > 255:
        errors.append("'username' must be 255 characters or fewer")

    cleaned = {}
    if not errors:
        cleaned["email"]    = email.strip()
        cleaned["username"] = username.strip()

    return cleaned, errors


# ── routes ────────────────────────────────────────────────────────────────────

@users_bp.route("/users")
def list_users():
    """GET /users — list all users, with optional ?page=&per_page= pagination."""
    try:
        page     = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "validation failed", "details": ["'page' and 'per_page' must be integers"]}), 400

    query = User.select().order_by(User.id)

    if per_page > 0:
        query = query.paginate(page, per_page)

    return jsonify([model_to_dict(u) for u in query]), 200


@users_bp.route("/users/<int:user_id>")
def get_user(user_id):
    """GET /users/<id> — fetch a single user by primary key."""
    user = User.get_or_none(User.id == user_id)
    if user is None:
        return jsonify({"error": "user not found"}), 404

    return jsonify(model_to_dict(user)), 200


@users_bp.route("/users", methods=["POST"])
def create_user():
    """POST /users — create a new user."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "invalid or missing JSON body"}), 400

    cleaned, errors = _validate_user_payload(data)
    if errors:
        return jsonify({"error": "validation failed", "details": errors}), 400

    try:
        user = User.create(**cleaned)
    except IntegrityError:
        return jsonify({"error": "a user with this email or username already exists"}), 409

    return jsonify(model_to_dict(user)), 201


@users_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    """PUT /users/<id> — update email and/or username."""
    
    user = User.get_or_none(User.id == user_id)
    if user is None:
        return jsonify({"error": "user not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "validation failed", "details": ["request body must not be empty"]}), 400

    errors = []
    if "email" in data:
        if not isinstance(data["email"], str) or not data["email"].strip():
            errors.append("'email' must be a non-empty string")
        elif len(data["email"].strip()) > 255:
            errors.append("'email' must be 255 characters or fewer")
        else:
            user.email = data["email"].strip()

    if "username" in data:
        if not isinstance(data["username"], str) or not data["username"].strip():
            errors.append("'username' must be a non-empty string")
        elif len(data["username"].strip()) > 255:
            errors.append("'username' must be 255 characters or fewer")
        else:
            user.username = data["username"].strip()

    if errors:
        return jsonify({"error": "validation failed", "details": errors}), 400

    try:
        user.save()
    except IntegrityError:
        return jsonify({"error": "a user with this email or username already exists"}), 409

    return jsonify(model_to_dict(user)), 200


@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """DELETE /users/<id> — remove a user."""
    user = User.get_or_none(User.id == user_id)
    if user is None:
        return jsonify({"error": "user not found"}), 404

    user.delete_instance()
    return jsonify({"deleted": True, "id": user_id}), 200


@users_bp.route("/users/bulk", methods=["POST"])
def bulk_load_users():
    """POST /users/bulk — accept a multipart CSV upload and insert all rows.

    Expected form fields:
        file      — the CSV file (columns: email, username)
        row_count — expected number of rows (used for validation / reporting)
    """
    uploaded = request.files.get("file")
    if uploaded is None:
        return jsonify({"error": "validation failed", "details": ["'file' is required"]}), 400

    try:
        expected_count = int(request.form.get("row_count", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "validation failed", "details": ["'row_count' must be an integer"]}), 400

    stream = io.StringIO(uploaded.stream.read().decode("utf-8"))
    reader = csv.DictReader(stream)

    rows   = []
    errors = []

    for i, row in enumerate(reader, start=1):
        email    = (row.get("email")    or "").strip()
        username = (row.get("username") or "").strip()

        if not email or not username:
            errors.append(f"row {i}: 'email' and 'username' are required")
            continue

        rows.append({"email": email, "username": username})

    if errors:
        return jsonify({"error": "validation failed", "details": errors}), 400

    inserted = 0
    skipped  = 0

    with User._meta.database.atomic():
        for chunk_start in range(0, len(rows), 100):
            chunk = rows[chunk_start : chunk_start + 100]
            try:
                User.insert_many(chunk).on_conflict_ignore().execute()
                inserted += len(chunk)
            except IntegrityError:
                skipped += len(chunk)

    return jsonify({
        "imported": inserted,
        "skipped":  skipped,
        "expected": expected_count,
        "total_in_db": User.select().count(),
    }), 201