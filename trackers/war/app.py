from flask import Blueprint, render_template
import requests, json
from lxml import etree
from trackers.shared import db
from .models import *


# flask
blueprint = Blueprint('war_tracker', __name__, template_folder='templates/war', static_folder='static')


@blueprint.route('/')
def index():
    """ View: Index page """
    return render_template('war/index.html', kills=Killmail.query.all())


@blueprint.route('/<kill_id>,<hashcode>')
def kill(kill_id, hashcode):
    """ View: Killmail page """
    js = json.loads(requests.get('http://public-crest.eveonline.com/killmails/{}/{}/'.format(kill_id, hashcode)).text)
    if ('message' in js and js['message'] == 'Invalid killmail ID or hash'):
        return 'Invalid killmail ID or hash'
    if Killmail.query.filter_by(kill_id=kill_id, hashcode=hashcode).count() == 0:
        db.session.add(Killmail(kill_id, hashcode))
        db.session.commit()
    item_count = len(js['victim']['items'])
    return render_template('war/kill.html', kill_id=kill_id, hashcode=hashcode, js=js, item_count=item_count)


@blueprint.route('/cost/<item_id>/<qty>')
def item_cost(item_id, qty):
    """ AJAX View: Item cost """
    return str('{:,}'.format(float(etree.fromstring(str(requests.get('http://eve-central.com/api/marketstat?typeid={}&usesystem=30000142'.format(item_id)).text)).find('marketstat/type/buy/avg').text) * float(qty)))
