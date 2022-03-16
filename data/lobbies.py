import sqlalchemy
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase
from flask_login import UserMixin


class Lobby(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'Lobbies'

    id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)

    p1 = sqlalchemy.Column(sqlalchemy.Integer)
    p2 = sqlalchemy.Column(sqlalchemy.Integer)
