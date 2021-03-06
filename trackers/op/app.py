from flask import Blueprint, render_template, request, redirect, url_for, session
from trackers.shared import InGameBrowser, socketio
from .models import *
from datetime import datetime
from collections import Counter
from lxml import etree
import requests


# flask
blueprint = Blueprint('op_tracker', __name__, template_folder='templates/op', static_folder='static')

# data
loot_items = (
    (30018, 'Fused Nanomechanical Engines'),
    (30019, 'Powdered C-540 Graphite'),
    (30021, 'Modified Fluid Router'),
    (30022, 'Heuristic Selfassemblers'),
    (30024, 'Cartesian Temporal Coordinator'),
    (30251, 'Neurovisual Input Matrix'),
    (30252, 'Thermoelectric Catalysts'),
    (30254, 'Electromechanical Hull Sheeting'),
    (30248, 'Emergent Combat Analyzer'),
    (30258, 'Resonance Calibration Matrix'),
    (30259, 'Melted Nanoribbons'),
    (30268, 'Jump Drive Control Nexus'),
    (30269, 'Defensive Control Node'),
    (30270, 'Central System Controller'),
    (30271, 'Emergent Combat Intelligence'),
    (30746, 'Ancient Coordinates Database'),
    (30744, 'Neural Network Analyzer'),
    (30745, 'Sleeper Data Library'),
    (30747, 'Sleeper Drone AI Nexus')
)

tradehubs = {
    'Amarr': {'region': 'Domain', 'region_id': 10000043},
    'Dodixie': {'region': 'Sinq Laison', 'region_id': 10000032},
    'Hek': {'region': 'Metropolis', 'region_id': 10000042},
    'Jita': {'region': 'The Forge', 'region_id': 10000002},
    'Rens': {'region': 'Heimatar', 'region_id': 10000030}
}


def _name():
    """ Returns the name of the user """
    # the user's name on the site
    # either their oauth name, their in-game character's name, or 'None' for users that don't have access
    if 'oi_auth_user' in session:
        return session['oi_auth_user']
    eveigb = InGameBrowser(request)
    if eveigb.is_valid():
        return eveigb['Eve-Charname']
    return 'None'


def _is_bursar():
    """ Returns if the user is a bursar """
    return _name() in app_settings['BURSARS']


def _render_template(template_name, **kwargs):
    """
        Because the in-game browser doesn't process newer technologies,
        we render those requests on the pre-materail deign templates.
    """
    if InGameBrowser(request).is_igb():
        return render_template('{}/old/old_{}'.format(*template_name.split('/')), **kwargs)
    else:
        return render_template(template_name, **kwargs)


@blueprint.context_processor
def _prerender():
    """ Add variables to all templates """
    return dict(displayname=_name(), now=datetime.utcnow(), bursar=_is_bursar(), eveigb=InGameBrowser(request))


@blueprint.route('/')
def index():
    """ View: index page """
    # show all operations to the user, ordering by their status
    operations = [op for op in Operation.query.filter_by(state='Not started').order_by('-id').all()]
    operations.extend(op for op in Operation.query.filter_by(state='In progress').order_by('-id').all())
    operations.extend(op for op in Operation.query.filter_by(state='Loot Collected').order_by('-id').all())
    operations.extend(op for op in Operation.query.filter_by(state='Loot Sold').order_by('-id').all())
    operations.extend(op for op in Operation.query.filter_by(state='Paid').order_by('-id').all())
    now = datetime.utcnow()
    for operation in Operation.query.filter_by(locked=False):
        if (now - operation.last_edited).total_seconds() / 3600 >= 6:
            operation.locked = True
            db.session.commit()
    return _render_template('op/index.html', page='home', operations=operations)


@blueprint.route('/op/<op_id>', methods=['GET', 'POST'])
def op(op_id):
    """ View: operation page """
    # the operation page template is passed the op model and the total shares count initially - other data comes from websockets
    operation = Operation.query.filter_by(id=op_id).first()
    if not operation:
        return _render_template('op/op_not_found.html', op_id=op_id)
    total_shares = 0
    for player in Player.query.filter_by(operation_id=op_id).all():
        total_shares += player.sites
    return _render_template('op/op.html', op=operation, total_shares=total_shares)


@blueprint.route('/op/<op_id>/players')
def players(op_id):
    """ AJAX View: return list of players in the operation """
    operation = Operation.query.filter_by(id=op_id).first_or_404()
    total_shares = 0
    for player in Player.query.filter_by(operation_id=op_id).all():
        total_shares += player.sites
    return _render_template('op/players.html', op=operation, total_shares=total_shares)


@blueprint.route('/playernames', methods=['POST'])
def player_names():
    """ AJAX View: return list of player names in the operation as select options """
    if not _is_bursar():
        return redirect(url_for('.index'))
    ret = ''
    for player in Operation.query.filter_by(id=int(int(request.form['op'].split(' ')[0]))).first_or_404().get_players():
        ret += '<option value="{0}">{0}</option>'.format(player.name)
    return '<select class="form-control width-half">{}</select>'.format(ret)


@blueprint.route('/playeropdata', methods=['POST'])
def player_op_data():
    """ AJAX View: return information about a player in an operation """
    if not _is_bursar():
        return redirect(url_for('.index'))
    operation = Operation.query.filter_by(id=int(request.form['op'].split(' ')[0])).first_or_404()
    player = Player.query.filter_by(operation_id=operation.id, name=request.form['player']).first_or_404()
    return _render_template('op/player_op_data.html', player=player)


@blueprint.route('/payoutplayerlist/<op_id>')
def payout_player_list(op_id):
    """ AJAX View: return a list of players in an operation in a table """
    if not _is_bursar():
        return redirect(url_for('.index'))
    operation = Operation.query.filter_by(id=op_id).first_or_404()
    data = operation.get_payout_data()
    return _render_template('op/payout_playerlist.html', operation=operation, data=data,
        players=Player.query.filter_by(operation_id=op_id).all())


@blueprint.route('/addop', methods=['GET', 'POST'])
def add_op():
    """ View: add a new operation """
    if request.method == 'POST':
        op = Operation(name=request.form['name'], leader=request.form['fc'], location=request.form['location'], 
            description=request.form['description'], state=request.form['state'])
        db.session.add(op)
        db.session.commit()
        return redirect(url_for('.op', op_id=op.id))
    return _render_template('op/addop.html', page='addop')


@blueprint.route('/payouts', methods=['GET', 'POST'])
def payouts():
    """ View: manage tracking of payment to players """
    if not _is_bursar():
        return redirect(url_for('.index'))
    if request.method == 'POST':
        if 'name' in request.form:
            # unused code?
            player = Player.query.filter_by(id=int(request.form['name'])).first()
            player.complete = player.paid >= player.get_share()
            db.session.commit()
            return player.get_share_formatted() + '-' + str(player.complete)
        if 'player' in request.form:
            # paying players for an operation
            name = request.form['player']
            amount = float(request.form['amount']) if 'amount' in request.form and not request.form['amount'] == '' else 0.0
            full = 'payfull' in request.form and request.form['payfull'] and request.form['payfull'] == 'true'
            zero = 'payzero' in request.form and request.form['payzero'] and request.form['payzero'] == 'true'
            if not full and not amount and not zero:
                return 'Not full nor amount nor zero'
            operation = Operation.query.filter_by(id=request.form['operation'].split(' ')[0]).first_or_404()
            player = Player.query.filter_by(name=name, operation_id=operation.id).first_or_404()
            if not operation or not player:
                return ''
            if zero:
                player.complete = False
                player.paid = 0
            elif full:
                player.complete = True
                player.paid = operation.get_share_for(player)
            else:
                player.paid += amount
                player.complete = player.paid >= operation.get_share_for(player)
            db.session.commit()
            return 'Done - {} {} {} {}'.format(zero, full, amount, player.id)
    # send models of players and their operations to the template
    players = Player.query.order_by('-operation_id').order_by('complete').all()
    names = ['{}-{}'.format(pl.operation.id, pl.name) for pl in players if pl and pl.operation]
    return _render_template('op/payouts.html', page='payout', players=players, names=names, operations=Operation.query.order_by('-id').all())


@blueprint.route('/review')
def review():
    """ View: show metrics about player participation """
    # basically the site app's stats page
    isk_per_player = Counter()
    srp = 0
    brg = 0
    total_isk_all = 0
    for player in Player.query.all():
        if 'srp' in player.name.lower():
            srp += player.paid
        elif 'brg' in player.name.lower():
            brg += player.paid
        else:
            isk_per_player[player.name] += player.paid
    alliance_tax = 0
    for operation in Operation.query.all():
        total_isk_all += operation.loot
        alliance_tax += operation.get_alliance_share()
    graph = []
    for player, amount in isk_per_player.most_common()[:20]:
        graph.append('{ y: ' + str(amount ) + ', indexLabel: "' + player + '" },')
    return _render_template('op/review.html', page='review', isk_per_player=isk_per_player.most_common(),
        srp=srp, brg=brg, graph=graph, total_isk_all=total_isk_all, alliance_tax=alliance_tax)


@blueprint.route('/loot')
def loot():
    items = {item_id: {'name': item, 'id': item_id, 'Amarr': 0, 'Dodixie': 0, 'Hek': 0, 'Jita': 0, 'Rens': 0, 'highest': None} for item_id, item in loot_items}
    for tradehub, tradehub_info in tradehubs.items():
        r = requests.get('http://eve-central.com/api/marketstat?regionlimit={}&typeid='.format(tradehub_info['region_id']) + '&typeid='.join(str(item) for item in items))
        tree = etree.fromstring(str(r.text))
        for item in tree.find('marketstat').getchildren():
            items[int(item.attrib['id'])][tradehub] = float(item.find('buy/avg').text)
    for item in items:
        items[item]['highest'] = max(items[item][tradehub] for tradehub in tradehubs)
    return _render_template('op/loot.html', page='loot', items=items)


def _log(message):
    """ Logs a message to the database """
    db.session.add(LogStatement(user=_name(), message=message))
    db.session.commit()


@socketio.on('optracker event', namespace='/op')
def websocket_message(message):
    """
    Listener: Normal event
        If nothing goes wrong in the processing of the command from the client,
        the server will broadcast the command to all connected clients.
        In order to prevent the server from broadcasting the command back,
        use a return in the if case for the command,
            EXCEPT:
        increment and decrement commands don't simply return the source command;
        instead, they return a command with the now-current share count for the player.
    """
    # operation page was moved from AJAX calls to websockets - this is that
    op_id = int(message['op_id'])
    operation = Operation.query.filter_by(id=op_id).first_or_404()
    operation.last_edited = datetime.utcnow()
    if message['command'] == 'remove':
        removed = Player.query.filter_by(id=message['player_id']).first()
        if removed:
            db.session.delete(removed)
            db.session.commit()
            _log('Removed {} from op {}'.format(removed.name, op_id))
    if message['command'] == 'location':
        operation.location = message['location']
        db.session.commit()
        _log('Changed location to {} on op {}'.format(operation.location, op_id))
    if message['command'] == 'lock':
        operation.locked = True if message['info'] == '1' else False
        db.session.commit()
        _log('Set op {} to {}'.format(op_id, 'locked' if operation.locked else 'Unlocked'))
    if message['command'] == 'state':
        operation.state = message['state']
        db.session.commit()
        _log('Set op {} to state {}'.format(op_id, operation.state))
    if message['command'] == 'loot':
        try:
            isk = float(message['loot'].replace(',', ''))
            operation.loot = isk
            db.session.commit()
            _log('Set loot on op {} to {}'.format(op_id, isk))
        except:
            return
    if message['command'] == 'tax':
        try:
            operation.tax = float(message['tax'])
            db.session.commit()
            _log('Set tax for op {} to {}'.format(op_id, operation.tax))
        except:
            return
    if message['command'] == 'rename':
        operation.name = message['name']
        db.session.commit()
        _log('Renamed op {} to {}'.format(op_id, operation.name))
    if message['command'] == 'leader':
        operation.leader = message['leader']
        db.session.commit()
        _log('Set leader for op {} to {}'.format(op_id, operation.leader))
    if message['command'] == 'description':
        operation.description = message['description']
        db.session.commit()
        _log('Set description for op {} to {}'.format(op_id, operation.description))
    if message['command'] == 'add':
        if Player.query.filter_by(name=message['name'], operation_id=op_id).count() == 0:
            player = Player(operation_id=op_id, name=message['name'], corporation=message['corporation'])
            db.session.add(player)
            db.session.commit()
            _log('Added {} to op {}'.format(message['name'], op_id))
        else:
            _log('Tried to add duplicate player {} to {}'.format(message['name'], op_id))
            return
    if message['command'] == 'holes':
        player = Player.query.filter_by(id=message['player_id']).first()
        if not player:
            return
        if message['did'] == '1' and player.sites % 2 != 0:
            player.sites += 0.5
        elif message['did'] == '0' and player.sites % 2 == 0:
            player.sites -= 0.5
        db.session.commit()
        _log('Set holes for {} to {} on op {}'.format(player.name, player.sites % 2 != 0, op_id))
    if message['command'] in ['increment', 'decrement']:
        player = Player.query.filter_by(id=message['player_id']).first()
        if not player:
            return
        if message['command'] == 'increment':
            player.sites += 1
        else:
            if player.sites - 1 >= 0.0:
                player.sites -= 1
        db.session.commit()
        _log('Set count for {} to {} on op {}'.format(player.name, player.sites, op_id))
        new_message = message.copy()
        new_message['share'] = player.sites
        total_shares = 0
        for player in Player.query.filter_by(operation_id=op_id).all():
            total_shares += player.sites
        new_message['total_shares'] = total_shares
        _message_clients(new_message)
        return
    _message_clients(message)


def _message_clients(data):
    """ Sends data to all connected websocket clients """
    socketio.emit('optracker response', data, namespace='/op')


@socketio.on('connect', namespace='/op')
def websocket_connect():
    """ Listener: Socket connection made """
    pass


@socketio.on('disconnect', namespace='/op')
def websocket_disconnect():
    """ Listener: Socket connection disconnected """
    pass
