from flask import Blueprint, render_template, session
from datetime import datetime
import eveapi
import requests, json
from lxml import etree
from trackers.shared import app_settings


# flask
blueprint = Blueprint('war_tracker', __name__, template_folder='templates/war', static_folder='static')

# eveapi
api = eveapi.EVEAPIConnection()
pairs = app_settings['KILLMAIL_KEYS']


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
    """ View: Index page """
    return render_template('war/index.html')


@blueprint.route('/<kill_id>,<hashcode>')
def kill(kill_id, hashcode):
    """ View: Killmail page """
    js = json.loads(requests.get('http://public-crest.eveonline.com/killmails/{}/{}/'.format(kill_id, hashcode)).text)
    return render_template('war/kill.html', kill_id=kill_id, hashcode=hashcode, js=js)


@blueprint.route('/cost/<item_id>')
def item_cost(item_id):
    """ AJAX View: Item cost """
    return str('{:,}'.format(float(etree.fromstring(str(requests.get('http://eve-central.com/api/marketstat?typeid={}&usesystem=30000142'.format(item_id)).text)).find('marketstat/type/buy/avg').text)))


# update code - needs to be converted to actual DB models instead of loose objects
# api = eveapi.EVEAPIConnection()
# auth = api.auth(keyID=3527924, vCode='S4khsQwmRRVt4MkGg3wHjQ8lxE0sjbTQaZFqeSd5qLOa4hdco7y2qQYn61Wt6Kb0')
# kills = []
# result = auth.corp.KillMails()
# for kill in result.kills:
    # k = Kill(date=kill.killTime)
    # kill.victim = Player(kill.victim.characterID, 'victim', kill.victim.characterName, kill.victim.corporationID,
        # kill.victim.corporationName, kill.victim.allianceID, kill.victim.allianceName,
        # kill.victim.damageTaken, kill.victim.shipTypeID, False)
    # attackers = []
    # for att in kill.attackers:
        # a = Player(att.characterID, 'attacker', att.characterName, att.corporationID,
            # att.corporationName, att.allianceID, att.allianceName,
            # att.damageDone, att.shipTypeID, att.finalBlow)
        # attackers.append(a)
    # k.attackers = attackers
    # kills.append(k)
