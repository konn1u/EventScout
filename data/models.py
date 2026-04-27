import datetime
import sqlalchemy
from sqlalchemy import orm
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .db_session import SqlAlchemyBase

participation_table = sqlalchemy.Table(
    'participation', SqlAlchemyBase.metadata,
    sqlalchemy.Column('user_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id')),
    sqlalchemy.Column('event_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('events.id'))
)


class User(SqlAlchemyBase, UserMixin):
    __tablename__ = 'users'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    email = sqlalchemy.Column(sqlalchemy.String, index=True, unique=True, nullable=False)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    owned_events = orm.relationship("Event", back_populates='owner')
    booked_events = orm.relationship("Event", secondary=participation_table, back_populates="participants")

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)


class Event(SqlAlchemyBase):
    __tablename__ = 'events'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.Text)
    address = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    event_date = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
    preview_img = sqlalchemy.Column(sqlalchemy.String, default='default_event.png')

    owner_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    owner = orm.relationship('User', back_populates='owned_events')
    participants = orm.relationship("User", secondary=participation_table, back_populates="booked_events")