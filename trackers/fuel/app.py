from flask import Blueprint, render_template, session, url_for, redirect
from datetime import datetime
import eveapi
from shared import app_settings


# flask
blueprint = Blueprint('fuel_tracker', __name__, template_folder='templates/fuel', static_folder='static')

# eveapi
api = eveapi.EVEAPIConnection()
pairs = app_settings['NOTIFICATION_KEYS']


class Tower:
    def __init__(self):
        self.owner = ''
        self.name = ''
        self.location = ''
        self.offline = ''
        self.offset = -1
    def update(self, owner, name, location, offline, offset):
        self.owner = owner
        self.name = name
        self.location = location
        self.offline = offline
        self.offset = offset
    def readout(self):
        return 'Tower named %s in %s owned by %s goes offline %s, which is %s days from now.' % \
            (self.name, self.location, self.owner, self.offline, self.offset)


class Corp:
    def __init__(self, keyid, vCode):
        self.keyid = keyid
        self.vCode = vCode
        self.last_updated = None
        self.towers = []
    def update(self):
        now = datetime.utcnow()
        auth = api.auth(keyID=self.keyid, vCode=self.vCode)
        events = auth.char.UpcomingCalendarEvents()
        self.towers = []
        for event in events.upcomingEvents:
            tower = Tower()
            if not 'will run out of fuel and go offline' in event.eventText:
                continue
            print 'Parsing tower belonging to', event.ownerName
            tower.owner = event.ownerName
            d = datetime.fromtimestamp(event.eventDate)
            try:
                tower.name = event.eventText.split('<b>Name</b>: ')[1].split('<br />')[0]
                tower.location = event.eventText.split('<b>Location</b>: ')[1].split('<br />')[0].split('/')[2].strip()
            except:
                tower.name = '-unknown-'
                tower.location = '-unknown-'
            tower.offline = d.strftime('%Y-%m-%d %H:%M:%S')
            tower.offset = str((d - now).days)
            self.towers.append(tower)
        self.last_updated = now
    def try_update(self):
        if self.needs_update:
            self.update()
    @property
    def needs_update(self):
        return not self.last_updated or (datetime.utcnow() - self.last_updated).seconds > 7200
    def readout(self):
        ret = ''
        for tower in self.towers:
            ret += tower.readout() + '\n'
        return ret


corps = []
for p in pairs:
    corps.append(Corp(keyid=p[0], vCode=p[1]))


def _name():
    """ Returns the name of the user """
    if 'oi_auth_user' in session:
        return session['oi_auth_user']
    return 'None'


@blueprint.context_processor
def _prerender():
    """ Add variables to all templates """
    return dict(displayname=_name(), now=datetime.utcnow())


@blueprint.route('/')
def index():
    """ View: index page """
    now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    message = []
    for c in corps:
        c.try_update()
        message.append(c.readout())
    return render_template('fuel/index.html', message=message, now_str=now_str)


@blueprint.route('/update')
def force_update():
    for c in corps:
        c.update()
    return redirect(url_for('.index'))
