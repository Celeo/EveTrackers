from trackers.shared import db


class Killmail(db.Model):

    __tablename__ = 'wartracker_killmail'

    id = db.Column(db.Integer, primary_key=True)
    kill_id = db.Column(db.Integer)
    hashcode = db.Column(db.String(50))
    date = db.Column(db.DateTime)
    system = db.Column(db.String(30))
    victim = db.Column(db.String(200))
    attacker_count = db.Column(db.Integer)

    def __init__(self, kill_id, hashcode, date, system, victim, attacker_count):
        self.kill_id = kill_id
        self.hashcode = hashcode
        self.date = date
        self.system = system
        self.victim = victim
        self.attacker_count = attacker_count

    def __repr__(self):
        return '<Killmail {} {}>'.format(self.kill_id, self.hashcode)
