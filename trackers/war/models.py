from trackers.shared import db


class Killmail(db.Model):

    # Add victim name, date, system, and attacker count here
    
    __tablename__ = 'wartracker_killmail'

    id = db.Column(db.Integer, primary_key=True)
    kill_id = db.Column(db.Integer)
    hashcode = db.Column(db.String(50))

    def __init__(self, kill_id, hashcode):
        self.kill_id = kill_id
        self.hashcode = hashcode

    def __repr__(self):
        return '<Killmail {} {}>'.format(self.kill_id, self.hashcode)
