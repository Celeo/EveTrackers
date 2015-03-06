from flask import Flask, redirect, url_for, request, session, render_template, flash
from werkzeug.contrib.fixers import ProxyFix
from flask_oauth import OAuth
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
import requests
import logging
from datetime import datetime, timedelta
from trackers.shared import app_settings, db, socketio, InGameBrowser, api

# flask
app = Flask(__name__)
app.config.from_pyfile('config.cfg')
app.permanent_session_lifetime = timedelta(days=14)
app.wsgi_app = ProxyFix(app.wsgi_app)


# flask-sqlalchemy
db.app = app
db.init_app(app)


# logger
LOGGING_IP = 60
logging.addLevelName(LOGGING_IP, 'IP')
logging.basicConfig(filename='log.txt', level=LOGGING_IP)

# settings
app_settings['ALLIANCE'] = app.config['ALLIANCE']
app_settings['HOME_SYSTEM'] = app.config['HOME_SYSTEM']
app_settings['SYSTEM_RENAMES'] = app.config['SYSTEM_RENAMES']
app_settings['FUEL_KEYS'] = app.config['FUEL_KEYS']
app_settings['ADMINS'] = app.config['ADMINS']
app_settings['LEADERSHIP'] = app.config['LEADERSHIP']
app_settings['APPROVED_CORPORATIONS'] = app.config['APPROVED_CORPORATIONS']
app_settings['BANNED_USERS'] = app.config['BANNED_USERS']

# import blueprints
from trackers.site.app import blueprint as site_tracker
from trackers.op.app import blueprint as op_tracker
from trackers.corp.app import blueprint as corp_tracker
from trackers.fuel.app import blueprint as fuel_tracker
from trackers.war.app import blueprint as war_tracker
from trackers.char.app import blueprint as char_tracker

# flask-admin
from trackers.site.models import *
from trackers.op.models import *
admin = Admin(app, 'Eve Trackers Admin Panel')
# the default flask-admin doesn't have any permissions, so it's visible by anyone
# this extension of ModelView restricts access to only site admins
class MyModelView(ModelView):
    """ Overwrite default view to include access restrictions """
    def is_accessible(self):
        return _name() in app.config['ADMINS']
admin.add_view(MyModelView(Site, db.session))
admin.add_view(MyModelView(SiteSnapshot, db.session))
admin.add_view(MyModelView(Wormhole, db.session))
admin.add_view(MyModelView(WormholeSnapshot, db.session))
admin.add_view(MyModelView(System, db.session))
admin.add_view(MyModelView(WormholeType, db.session))
admin.add_view(MyModelView(Settings, db.session))
admin.add_view(MyModelView(Operation, db.session))
admin.add_view(MyModelView(Player, db.session))
admin.add_view(MyModelView(ApiKey, db.session))
admin.add_view(MyModelView(PlayerAuthName, db.session))
admin.add_view(MyModelView(LogStatement, db.session))


# flask-oauth
oauth = OAuth()
oi_auth = oauth.remote_app('oi_auth',
    consumer_key = app.config['OI_OAUTH_CONSUMER_KEY'],
    consumer_secret = app.config['OI_OAUTH_CONSUMER_SECRET'],
    request_token_params =  {'response_type': 'code', 'scope': 'auth_info'},
    base_url = 'https://oauth.talkinlocal.org/api/v1/',
    request_token_url =  None,
    access_token_method =  'GET',
    access_token_url =  'https://oauth.talkinlocal.org/token',
    authorize_url =  'https://oauth.talkinlocal.org/authorize',
    access_token_params = {'grant_type': 'authorization_code'}
)


@oi_auth.tokengetter
def get_oi_auth_token(token=None):
    """ Return oauth token """
    # required method for flask-oauth
    return session.get('oi_auth_token')


@app.route('/oauthauthorized')
@oi_auth.authorized_handler
def oauth_authorized(resp):
    # required method for flask-oauth - performs the actual remote authorization
    """ Perform the "login validation" after oauth """
    if resp is None:
        flash('You denied the request to sign in', 'danger')
        return redirect(url_for('site_tracker.index'))
    data = requests.get('https://oauth.talkinlocal.org/api/v1/auth_user?access_token=' + resp['access_token']).json()['user']
    if not data['auth_status'] in ['Internal', 'Protected']:
        flash('You do not have sufficient permissions to use this tool. Requires group "Internal", while you have group "{}".'.format(data['auth_status']), 'danger')
        app.logger.log(LOGGING_IP, 'User ' + data['user_id'] + ' was denied access through an accountStatus of ' + data['auth_status'])
        return redirect(url_for('site_tracker.index'))
    session['oi_auth_token'] = resp['access_token']
    session['oi_auth_user'] = data['user_id']
    session['corporation'] = api.eve.CharacterAffiliation(ids=api.eve.CharacterID(names=data['main_character']).characters[0].characterID).characters[0].corporationName
    session.permanent = True
    flash('You were signed in as {}'.format(data['user_id']), 'info')
    app.logger.log(LOGGING_IP, 'User ' + session['oi_auth_user'] + ' has logged in under IP ' + request.environ['REMOTE_ADDR'])
    return redirect(url_for('site_tracker.index'))


@app.route('/login')
def login_page():
    """ View: Start oauth authorization """
    # actual url that someone goes to to have flask-oauth attempt to log them in
    return oi_auth.authorize(callback='http://tracker.talkinlocal.org/oauthauthorized')


@app.route('/logout')
def logout_page():
    """ View: Delete the session cookie and redirect """
    # login information is stored in the session
    # to log a user out of the site, dump the session cookies
    session.clear()
    return redirect(url_for('no_access'))


@app.route('/root_login', methods=['GET', 'POST'])
def root_login():
    """ View: Administrator login, bypassing the OAUTH login method """
    # this method is used when debugging locally or when oauth is unaccessible
    if request.method == 'POST':
        if (request.form['username'], request.form['password']) == app.config['ROOT_LOGIN']:
            session['oi_auth_token'] = 'root_login_page'
            session['oi_auth_user'] = app.config['ROOT_LOGIN'][0]
            session['corporation'] = app_settings['APPROVED_CORPORATIONS'][0]
            session.permanent = True
            flash('You used the root login page to log into the trackers as {}'.format(app.config['ROOT_LOGIN'][0]), 'info')
            return redirect(url_for('site_tracker.index'))
    return render_template('root_login.html')


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


def _can_access():
    """ Returns if the user can access the resources at that page """
    # checks first for the diplayname of the view (from their session contnents) and their stored corporation
    name = _name()
    if name == 'None':
        flash('You are not logged in', 'danger')
        return False
    eveigb = InGameBrowser(request)
    session_corp = session['corporation'] if 'corporation' in session else None
    ingame_corp = eveigb['Eve-Corpname'] if eveigb.is_valid() else None
    if not session_corp in app_settings['APPROVED_CORPORATIONS'] and not ingame_corp in app_settings['APPROVED_CORPORATIONS']:
        # protection against corporations leaving the alliance - we can force logouts of any user in a corporation not in the settings
        flash('You are in a corporation that does not have access to this tool', 'danger')
        session.clear()
        return False
    return True


@app.context_processor
def _prerender():
    """ Add variables to all templates """
    displayname = _name()
    valid_user = not displayname == 'None'
    return dict(displayname=displayname, valid_user=valid_user, now=datetime.utcnow(), igb=InGameBrowser(request))


@app.before_request
def _preprocess():
    """ Reroute the user to the login prompt page if not logged in """
    # for any page in the app that isn't a static file or involved in logging in, only allow access to valid users
    if request.path.startswith('/static/'):
        return
    app.logger.log(LOGGING_IP, 'User "' + _name() + '" viewing page "' + request.path + '" with IP ' + request.environ['REMOTE_ADDR'])
    if request.path in ['/noaccess', '/login', '/oauthauthorized', '/root_login']:
        return
    if not _can_access():
        return redirect(url_for('no_access'))


@app.template_filter('date')
def _date(s):
    """ Template filter: format date objects """
    return s.strftime('%m/%d @ %H:%M')


@app.template_filter('count')
def _count(l):
    """ Template filter: returns length of attached list """
    return len(l)


@app.template_filter('formatcommas')
def _format_commas(n):
    """ Template filter: adds thousand's separator commas to large numbers """
    if '.' in str(n):
        return '{:,}'.format(float(n))
    return '{:,}'.format(int(n))


@app.route('/landing')
def landing():
    return render_template('landing.html')


@app.route('/noaccess')
def no_access():
    # the catch-all invalid user notice page
    if _can_access():
        flash('Your are already logged in', 'info')
        return redirect(url_for('site_tracker.index'))
    return render_template('no_access.html')


@app.route('/update_approved_corporations')
def update_approved_corporations():
    # this method updates the valid corporations for the filtering by corporation security feature
    if not _name() in app_settings['ADMINS']:
        flash('You do not have permission to visit this page', 'danger')
        return redirect(url_for('no_access'))
    app_settings['APPROVED_CORPORATIONS'] = ''
    alliances = api.eve.AllianceList().alliances
    corporation_ids = []
    for alliance in alliances:
        if alliance.name == app_settings['ALLIANCE']:
            for corporation in alliance.memberCorporations:
                corporation_ids.append(corporation.corporationID)
    corporations = api.eve.CharacterName(ids=corporation_ids).characters
    app_settings['APPROVED_CORPORATIONS'] = [str(corporation.name) for corporation in corporations]
    return 'Done'


socketio.app = app
socketio.init_app(app)

app.register_blueprint(site_tracker)
app.register_blueprint(op_tracker, url_prefix='/operations')
app.register_blueprint(corp_tracker, url_prefix='/corp')
app.register_blueprint(fuel_tracker, url_prefix='/fuel')
app.register_blueprint(war_tracker, url_prefix='/war')
app.register_blueprint(char_tracker, url_prefix='/char')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
