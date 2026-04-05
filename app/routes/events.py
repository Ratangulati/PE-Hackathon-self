import json

from flask import Blueprint, jsonify, request
from peewee import IntegrityError
from playhouse.shortcuts import model_to_dict

from app.models.event import Event

events_bp = Blueprint("events", __name__)


def _event_to_dict(event):
    d = model_to_dict(event, recurse=False)
    d["url_id"]  = event.url_id_id
    d["user_id"] = event.user_id_id
    # Parse details back to dict if it was stored as JSON string
    if d.get("details") and isinstance(d["details"], str):
        try:
            d["details"] = json.loads(d["details"])
        except (ValueError, TypeError):
            pass
    return d


@events_bp.route("/events")
def list_events():
    """GET /events — filterable by ?url_id=, ?user_id=, ?event_type="""
    query = Event.select().order_by(Event.id)

    url_id = request.args.get("url_id")
    if url_id is not None:
        try:
            query = query.where(Event.url_id == int(url_id))
        except (TypeError, ValueError):
            return jsonify({"error": "validation failed", "details": ["'url_id' must be an integer"]}), 400

    user_id = request.args.get("user_id")
    if user_id is not None:
        try:
            query = query.where(Event.user_id == int(user_id))
        except (TypeError, ValueError):
            return jsonify({"error": "validation failed", "details": ["'user_id' must be an integer"]}), 400

    event_type = request.args.get("event_type")
    if event_type is not None:
        query = query.where(Event.event_type == event_type)

    return jsonify([_event_to_dict(e) for e in query]), 200


@events_bp.route("/events", methods=["POST"])
def create_event():
    """POST /events — log a new event."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "invalid or missing JSON body"}), 400

    errors = []
    event_type = data.get("event_type")
    if not event_type or not isinstance(event_type, str):
        errors.append("'event_type' is required")

    if errors:
        return jsonify({"error": "validation failed", "details": errors}), 400

    details = data.get("details")
    if details is not None and not isinstance(details, str):
        details = json.dumps(details)

    event = Event.create(
        url_id=data.get("url_id"),
        user_id=data.get("user_id"),
        event_type=event_type.strip(),
        details=details,
    )

    return jsonify(_event_to_dict(event)), 201