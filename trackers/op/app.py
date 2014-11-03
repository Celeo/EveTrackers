from flask import Blueprint, render_template, request, redirect, url_for, session
from trackers.shared import InGameBrowser, socketio
from .models import *
from datetime import datetime
from collections import Counter
import eveapi


# flask
blueprint = Blueprint('op_tracker', __name__, template_folder='templates/op', static_folder='static')

# eveapi
api = eveapi.EVEAPIConnection()


def _name():
    """ Returns the name of the user """
    if 'oi_auth_user' in session:
        return session['oi_auth_user']
    eveigb = InGameBrowser(request)
    if eveigb.is_valid():
        return eveigb['Eve-Charname']
    return 'None'


def _is_bursar():
    """ Returns if the user is a bursar """
    name = _name()
    pan = PlayerAuthName.query.filter_by(username=name).first()
    if not pan:
        pan = PlayerAuthName(username=name)
        result = api.eve.CharacterID(names=name.replace('_', ' '))
        try:
            char_name = result.characters[0].characterName
            char_id = result.characters[0].characterID
            result = api.eve.CharacterAffiliation(ids=char_id)
            corp = result.characters[0].corporationName
            pan.character_name = char_name
            pan.corp = corp
        except:
            pass
        db.session.add(pan)
        db.session.commit()
    return pan.bursar


@blueprint.context_processor
def _prerender():
    """ Add variables to all templates """
    return dict(displayname=_name(), now=datetime.utcnow(), bursar=_is_bursar())


@blueprint.route('/')
def index():
    """ View: index page """
    operations = [op for op in Operation.query.filter_by(state='Not started').order_by('-id').all()]
    operations.extend(op for op in Operation.query.filter_by(state='In progress').order_by('-id').all())
    operations.extend(op for op in Operation.query.filter_by(state='Loot Collected').order_by('-id').all())
    operations.extend(op for op in Operation.query.filter_by(state='Loot Sold').order_by('-id').all())
    operations.extend(op for op in Operation.query.filter_by(state='Paid').order_by('-id').all())
    now = datetime.utcnow()
    for operation in Operation.query.filter_by(locked=False):
        if (now - operation.date).total_seconds() / 3600 >= 6:
            operation.locked = True
            db.session.commit()
    return render_template('op/index.html', page='home', operations=operations, apikeys=ApiKey.query.count())


@blueprint.route('/op/<op_id>', methods=['GET', 'POST'])
def op(op_id):
    """ View: operation page """
    operation = Operation.query.filter_by(id=op_id).first_or_404()
    total_shares = 0
    for player in Player.query.filter_by(operation_id=op_id).all():
        total_shares += player.sites
    return render_template('op/op.html', op=operation, total_shares=total_shares)


@blueprint.route('/op/<op_id>/players')
def players(op_id):
    """ AJAX View: return list of players in the operation """
    operation = Operation.query.filter_by(id=op_id).first_or_404()
    total_shares = 0
    for player in Player.query.filter_by(operation_id=op_id).all():
        total_shares += player.sites
    return render_template('op/players.html', op=operation, total_shares=total_shares)


@blueprint.route('/playernames', methods=['POST'])
def player_names():
    """ AJAX View: return list of player names in the operation as select options """
    if not _is_bursar():
        return redirect(url_for('.index'))
    ret = ''
    for player in Operation.query.filter_by(id=int(int(request.form['op'].split(' ')[0]))).first_or_404().get_players():
        ret += '<option>{}</option>'.format(player.name)
    return ret


@blueprint.route('/playeropdata', methods=['POST'])
def player_op_data():
    """ AJAX View: return information about a player in an operation """
    if not _is_bursar():
        return redirect(url_for('.index'))
    operation = Operation.query.filter_by(id=int(request.form['op'].split(' ')[0])).first_or_404()
    player = Player.query.filter_by(operation_id=operation.id, name=request.form['player']).first_or_404()
    return render_template('op/player_op_data.html', player=player)


@blueprint.route('/payoutplayerlist/<op_id>')
def payout_player_list(op_id):
    """ AJAX View: return a list of players in an operation in a table """
    if not _is_bursar():
        return redirect(url_for('.index'))
    return render_template('op/payout_playerlist.html', operation=Operation.query.filter_by(id=op_id).first_or_404(),
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
    return render_template('op/addop.html', page='addop')


@blueprint.route('/payouts', methods=['GET', 'POST'])
def payouts():
    """ View: manage tracking of payment to players """
    if not _is_bursar():
        return redirect(url_for('.index'))
    if request.method == 'POST':
        if 'name' in request.form:
            player = Player.query.filter_by(id=int(request.form['name'])).first()
            player.complete = player.paid >= player.get_share()
            db.session.commit()
            return player.get_share_formatted() + '-' + str(player.complete)
        if 'player' in request.form:
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
    players = Player.query.order_by('-operation_id').order_by('complete').all()
    names = ['{}-{}'.format(pl.operation.id, pl.name) for pl in players]
    return render_template('op/payouts.html', page='payout', players=players, names=names,
        api_enabled=ApiKey.query.count() > 0, apikeys=ApiKey.query.all(),
        operations=Operation.query.order_by('-id').all())


@blueprint.route('/apiupddate', methods=['POST'])
def api_update():
    """ AJAX View: Update players paid from the api keys """
    if not _is_bursar():
        return redirect(url_for('.index'))
    keypair = ApiKey.query.filter_by(id=request.form['id'].split(' ')[0][1]).first()
    auth = api.auth(keyID=keypair.key, vCode=keypair.code)
    wallet = auth.corp.WalletJournal(accountKey=keypair.wallet)
    count = 0
    for entry in wallet.entries:
        if entry.refTypeID == 37:
            receiver, amount, reason = entry.ownerName2, entry.amount, entry.reason.split(' ')[1].strip()
            try:
                players = Player.query.filter_by(name=receiver, api_paid=0).all()
                for pl in players:
                    if pl.operation.key in reason:
                        isk = int(str(amount).split('.')[0]) * -1
                        pl.api_paid = isk
                        pl.paid = isk
                        if pl.get_share() <= isk:
                            pl.complete = True
                        count += 1
            except:
                pass
    db.session.commit()
    return count


@blueprint.route('/review')
def review():
    """ View: show metrics about player participation """
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
            isk_per_player[player.name] += player.paid + player.api_paid
    alliance_tax = 0
    for operation in Operation.query.all():
        total_isk_all += operation.loot
        alliance_tax += operation.get_alliance_share()
    graph = []
    for player, amount in isk_per_player.most_common()[:20]:
        graph.append('{ y: ' + str(amount ) + ', indexLabel: "' + player + '" },')
    return render_template('op/review.html', page='review', isk_per_player=isk_per_player.most_common(),
        srp=srp, brg=brg, graph=graph, total_isk_all=total_isk_all, alliance_tax=alliance_tax)


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
    op_id = int(message['op_id'])
    operation = Operation.query.filter_by(id=op_id).first_or_404()
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
    if message['command'] == 'lootprice':
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
            player = Player(operation_id=op_id, name=message['name'])
            db.session.add(player)
            db.session.commit()
            _log('Added {} to op {}'.format(message['name'], op_id))
        else:
            _log('Tried to add duplicate player {} to {}'.format(message['name'], op_id))
            return
    if message['command'] in ['increment', 'decrement']:
        player = Player.query.filter_by(id=message['player_id']).first()
        if not player:
            return
        step = float(message['step'])
        if message['command'] == 'increment':
            player.sites += step
        else:
            if player.sites - step >= 0.0:
                player.sites -= step
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
    socketio.emit('optracker response', data, namespace='/op')


@socketio.on('connect', namespace='/op')
def websocket_connect():
    """ Listener: Socket connection made """
    pass


@socketio.on('disconnect', namespace='/op')
def websocket_disconnect():
    """ Listener: Socket connection disconnected """
    pass
