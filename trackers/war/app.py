from flask import Blueprint, render_template, redirect, url_for, request
import requests, json
from datetime import datetime
from lxml import etree
from trackers.shared import db
from .models import *


# flask
blueprint = Blueprint('war_tracker', __name__, template_folder='templates/war', static_folder='static')


@blueprint.route('/')
def index():
    """ View: Index page """
    return render_template('war/index.html', kills=Killmail.query.all())


@blueprint.route('/<kill_id>/<hashcode>')
def kill(kill_id, hashcode):
    """ View: Killmail page """
    return render_template('war/kill.html', kill_id=kill_id, hashcode=hashcode)


@blueprint.route('/kill_info/<kill_id>/<hashcode>')
def kill_info(kill_id, hashcode):
    # get data from CREST
    js = json.loads(requests.get('http://public-crest.eveonline.com/killmails/{}/{}/'.format(kill_id, hashcode)).text)

    # sanity check
    if ('message' in js and js['message'] == 'Invalid killmail ID or hash'):
        return 'Invalid killmail ID or hash'

    # local storage of id/hash
    if Killmail.query.filter_by(kill_id=kill_id, hashcode=hashcode).count() == 0:
        date = datetime.strptime(js['killTime'], '%Y.%m.%d %H:%M:%S')
        db.session.add(Killmail(kill_id, hashcode, date, js['solarSystem']['name'], js['victim']['character']['name'], js['attackerCount']))
        db.session.commit()

    # calculate all needed price data and group items
    items, item_ids, ship_cost, total_destroyed = {}, {}, 0.0, 0.0
    for item in js['victim']['items']:
        if not item['itemType']['name'] in items:
            item['quantityDropped'] = item['quantityDropped'] if 'quantityDropped' in item else 0
            item['quantityDestroyed'] = item['quantityDestroyed'] if 'quantityDestroyed' in item else 0
            items[item['itemType']['name']] = item
        else:
            items[item['itemType']['name']]['quantityDropped'] += item['quantityDropped'] if 'quantityDropped' in item else 0
            items[item['itemType']['name']]['quantityDestroyed'] += item['quantityDestroyed'] if 'quantityDestroyed' in item else 0
    for item in items.values():
        item_ids[item['itemType']['id']] = item['itemType']['name']
    tree = etree.fromstring(str(requests.get('http://eve-central.com/api/marketstat?usesystem=30000142' + ''.join(['&typeid={}'.format(item_id) for item_id in item_ids.keys() + [js['victim']['shipType']['id']]])).text))
    for item in tree.find('marketstat').getchildren():
        if int(item.attrib['id']) == int(js['victim']['shipType']['id']):
            ship_cost = float(item.find('sell/avg').text)
            total_destroyed += ship_cost
            pass
        else:
            items[item_ids[int(item.attrib['id'])]]['pricePer'] = float(item.find('sell/avg').text)
    total_dropped, total_destroyed = 0.0, 0.0
    for item in items.values():
        total_dropped += float(item['quantityDropped']) * float(item['pricePer'])
        total_destroyed += float(item['quantityDestroyed']) * float(item['pricePer'])

    # fix for missing data
    for attacker in js['attackers']:
        if not 'character' in attacker:
            attacker['character'] = { 'name': '?' }
            if 'faction' in attacker:
                attacker['corporation'] = attacker['faction']
            attacker['weaponType'] = { 'name': '?' }
        if not 'shipType' in attacker:
            attacker['shipType'] = { 'name': '?' }
        if not 'weaponType' in attacker:
            attacker['weaponType'] = { 'name': '?' }

    # inject modified JSON into the original, overwriting the previous data
    js['victim']['shipType']['pricePer'] = ship_cost
    js['totalDropped'], js['totalDestroyed'] = total_dropped, total_destroyed
    js['victim']['items'] = items.values()
    return render_template('war/kill_info.html', js=js)


@blueprint.route('/uriconvert')
def uri_convert():
    uri = request.args.get('uri', None)
    if not uri: return redirect(url_for('.index'))
    return redirect(url_for('.kill', kill_id=uri.split('/')[4], hashcode=uri.split('/')[5]))
