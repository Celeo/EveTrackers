from flask import Blueprint, render_template, request, redirect, url_for, session
from trackers.shared import InGameBrowser, socketio
from datetime import datetime
import eveapi


# flask
blueprint = Blueprint('char_tracker', __name__, template_folder='templates/char', static_folder='static')

# eveapi
api = eveapi.EVEAPIConnection()

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


@blueprint.context_processor
def _prerender():
    """ Add variables to all templates """
    return dict(displayname=_name(), now=datetime.utcnow(), eveigb=InGameBrowser(request))


@blueprint.route('/')
def index():
    """ View: index page """
    return render_template('char/index.html', page='home')


@socketio.on('optracker event', namespace='/char')
def websocket_message(message):
    """
    Listener: Normal event
    """
    pass


def _message_clients(data):
    """ Sends data to all connected websocket clients """
    socketio.emit('chartracker response', data, namespace='/char')


@socketio.on('connect', namespace='/char')
def websocket_connect():
    """ Listener: Socket connection made """
    pass


@socketio.on('disconnect', namespace='/char')
def websocket_disconnect():
    """ Listener: Socket connection disconnected """
    pass
