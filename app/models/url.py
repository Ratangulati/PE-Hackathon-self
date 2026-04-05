import random
import string

from peewee import BooleanField, CharField, ForeignKeyField, TextField

from app.database import BaseModel
from app.models.user import User


def _generate_short_code(length=8):
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


class Url(BaseModel):
    original_url = TextField()
    title        = CharField(null=True)
    short_code   = CharField(unique=True)
    is_active    = BooleanField(default=True)
    user_id      = ForeignKeyField(User, backref="urls", column_name="user_id", null=True)

    @classmethod
    def generate_unique_short_code(cls):
        for _ in range(10):
            code = _generate_short_code()
            if not cls.select().where(cls.short_code == code).exists():
                return code
        raise RuntimeError("Could not generate unique short code")