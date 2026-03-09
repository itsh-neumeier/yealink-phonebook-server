from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class Phonebook(db.Model):
    __tablename__ = "phonebooks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    entries = db.relationship(
        "ContactEntry",
        backref="phonebook",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    settings = db.relationship(
        "PhonebookSettings",
        backref="phonebook",
        uselist=False,
        cascade="all, delete-orphan",
    )


class PhonebookSettings(db.Model):
    __tablename__ = "phonebook_settings"

    id = db.Column(db.Integer, primary_key=True)
    phonebook_id = db.Column(
        db.Integer,
        db.ForeignKey("phonebooks.id"),
        nullable=False,
        unique=True,
    )
    category = db.Column(db.String(20), nullable=False, default="private")


class ContactEntry(db.Model):
    __tablename__ = "contact_entries"

    id = db.Column(db.Integer, primary_key=True)
    phonebook_id = db.Column(db.Integer, db.ForeignKey("phonebooks.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    office = db.Column(db.String(40), nullable=True)
    mobile = db.Column(db.String(40), nullable=True)
    other = db.Column(db.String(40), nullable=True)
    line = db.Column(db.String(40), nullable=True)
    ring = db.Column(db.String(40), nullable=True)
    group = db.Column(db.String(120), nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "office IS NOT NULL OR mobile IS NOT NULL OR other IS NOT NULL",
            name="ck_contact_phone_present",
        ),
    )


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class AccessCredential(db.Model):
    __tablename__ = "access_credentials"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
