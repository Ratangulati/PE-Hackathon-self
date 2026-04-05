import json

from flask import Blueprint, jsonify, request
from peewee import IntegrityError
from playhouse.shortcuts import model_to_dict

from app.models.url import Url

urls_bp = Blueprint("urls", __name__)


def _url_to_dict(url):
    d = model_to_dict(url, recurse=False)
    # Expose user_id as a plain int, not a nested object
    d["user_id"] = url.user_id_id  # peewee stores FK as user_id_id internally
    return d


@urls_bp.route("/urls")
def list_urls():
    """GET /urls — list urls, filterable by ?user_id= and ?is_active="""
    query = Url.select().order_by(Url.id)

    user_id = request.args.get("user_id")
    if user_id is not None:
        try:
            query = query.where(Url.user_id == int(user_id))
        except (TypeError, ValueError):
            return jsonify({"error": "validation failed", "details": ["'user_id' must be an integer"]}), 400

    is_active = request.args.get("is_active")
    if is_active is not None:
        if is_active.lower() == "true":
            query = query.where(Url.is_active == True)
        elif is_active.lower() == "false":
            query = query.where(Url.is_active == False)
        else:
            return jsonify({"error": "validation failed", "details": ["'is_active' must be true or false"]}), 400

    return jsonify([_url_to_dict(u) for u in query]), 200


@urls_bp.route("/urls/<int:url_id>")
def get_url(url_id):
    """GET /urls/<id>"""
    url = Url.get_or_none(Url.id == url_id)
    if url is None:
        return jsonify({"error": "url not found"}), 404
    return jsonify(_url_to_dict(url)), 200


@urls_bp.route("/urls", methods=["POST"])
def create_url():
    """POST /urls — create a shortened URL."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "invalid or missing JSON body"}), 400

    errors = []
    original_url = data.get("original_url")
    if not original_url or not isinstance(original_url, str) or not original_url.strip():
        errors.append("'original_url' is required")

    if errors:
        return jsonify({"error": "validation failed", "details": errors}), 400

    short_code = data.get("short_code") or Url.generate_unique_short_code()

    try:
        url = Url.create(
            original_url=original_url.strip(),
            title=data.get("title"),
            short_code=short_code,
            is_active=data.get("is_active", True),
            user_id=data.get("user_id"),
        )
    except IntegrityError:
        return jsonify({"error": "short_code already exists"}), 409

    return jsonify(_url_to_dict(url)), 201


@urls_bp.route("/urls/<int:url_id>", methods=["PUT"])
def update_url(url_id):
    """PUT /urls/<id> — update title, is_active, or original_url."""
    url = Url.get_or_none(Url.id == url_id)
    if url is None:
        return jsonify({"error": "url not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "validation failed", "details": ["request body must not be empty"]}), 400

    if "original_url" in data:
        url.original_url = data["original_url"]
    if "title" in data:
        url.title = data["title"]
    if "is_active" in data:
        url.is_active = bool(data["is_active"])
    if "short_code" in data:
        url.short_code = data["short_code"]

    try:
        url.save()
    except IntegrityError:
        return jsonify({"error": "short_code already exists"}), 409

    return jsonify(_url_to_dict(url)), 200


@urls_bp.route("/urls/<int:url_id>", methods=["DELETE"])
def delete_url(url_id):
    """DELETE /urls/<id>"""
    url = Url.get_or_none(Url.id == url_id)
    if url is None:
        return jsonify({"error": "url not found"}), 404

    url.delete_instance()
    return jsonify({"deleted": True, "id": url_id}), 200


@urls_bp.route("/<string:short_code>")
def redirect_short_code(short_code):
    """GET /<short_code> — redirect to original URL."""
    url = Url.get_or_none(Url.short_code == short_code, Url.is_active == True)
    if url is None:
        return jsonify({"error": "url not found or inactive"}), 404

    return jsonify({"original_url": url.original_url}), 302