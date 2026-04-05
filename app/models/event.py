from peewee import CharField, ForeignKeyField, IntegerField

from app.database import BaseModel
from app.models.url import Url
from app.models.user import User


class Event(BaseModel):
    url_id     = ForeignKeyField(Url, backref="events", column_name="url_id", null=True)
    user_id    = ForeignKeyField(User, backref="events", column_name="user_id", null=True)
    event_type = CharField()
    details    = CharField(null=True)  # stored as JSON string