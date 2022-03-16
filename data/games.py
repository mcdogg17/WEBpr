import sqlalchemy
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase
from flask_login import UserMixin


class Game(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'Games'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    lobby_id = sqlalchemy.Column(sqlalchemy.String)
    players = sqlalchemy.Column(sqlalchemy.String)
    size = sqlalchemy.Column(sqlalchemy.Integer)
