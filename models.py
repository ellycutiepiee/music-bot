from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.String(20), primary_key=True)  # Discord ID
    username = db.Column(db.String(100))
    avatar_url = db.Column(db.String(255))
    history = db.relationship('SongHistory', backref='user', lazy=True)

class SongHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20), db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    platform = db.Column(db.String(50))  # youtube, soundcloud, spotify, etc.
    played_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'title': self.title,
            'url': self.url,
            'platform': self.platform,
            'played_at': self.played_at.strftime('%Y-%m-%d %H:%M:%S')
        }
