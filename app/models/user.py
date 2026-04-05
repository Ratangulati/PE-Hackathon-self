from peewee import CharField
 
from app.database import BaseModel
 
 
class User(BaseModel):
    email = CharField(unique=True)
    username = CharField(unique=True)