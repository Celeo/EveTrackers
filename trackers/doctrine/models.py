from trackers.shared import db
from datetime import datetime


class AuthKeyPair(db.Model):
    
    __tablename__ = 'doctrinetracker_authkeypair'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    keyid = db.Column(db.Integer)
    vcode = db.Column(db.String(50))
    added = db.Column(db.DateTime)

    def __init__(self, name, keyid, vcode):
        self.name = name
        self.keyid = keyid
        self.vcode = vcode
        self.added = datetime.utcnow()

    def __repr__(self):
        return '<AuthKeyPair-{}>'.format(self.name)


class FittingItem(db.Model):

    __tablename__ = 'doctrinetracker_fittingitem'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<FittingItem-{}>'.format(self.name)


class Fitting(db.Model):

    __tablename__ = 'doctrinetracker_fitting'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    # TODO setup many-to-many with FittingItem

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Fitting-{}>'.format(self.name)
