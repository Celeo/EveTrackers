from flask import Flask, redirect, url_for, request, session, render_template, flash
from flask_oauth import OAuth
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
import requests
from datetime import datetime
from shared import *

# flask
app = Flask(__name__)
app.config.from_pyfile('config.cfg')


# flask-sqlalchemy
db.app = app
db.init_app(app)


# settings
app_settings['ALLIANCE'] = app.config['ALLIANCE']
app_settings['HOME_SYSTEM'] = app.config['HOME_SYSTEM']
app_settings['SYSTEM_RENAMES'] = app.config['SYSTEM_RENAMES']
app_settings['NOTIFICATION_KEYS'] = app.config['NOTIFICATION_KEYS']
app_settings['KILLMAIL_KEYS'] = app.config['KILLMAIL_KEYS']
app_settings['ADMINS'] = app.config['ADMINS']

# import blueprints
from trackers.site.app import blueprint as site
from trackers.op.app import blueprint as op
from trackers.corp.app import blueprint as corp
from trackers.fuel.app import blueprint as fuel
from trackers.war.app import blueprint as war

# flask-admin
from trackers.site.models import *
from trackers.op.models import *
admin = Admin(app, 'Eve Trackers Admin Panel')
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
    return session.get('oi_auth_token')


@app.route('/oauthauthorized')
@oi_auth.authorized_handler
def oauth_authorized(resp):
    """ Perform the "login validation" after oauth """
    if resp is None:
        flash('You denied the request to sign in', 'danger')
        return redirect(url_for('site_tracker.index'))
    data = requests.get('https://oauth.talkinlocal.org/api/v1/auth_user?access_token=' + resp['access_token']).json()['user']
    if not data['auth_status'] in ['Internal', 'Protected']:
        flash('You do not have sufficient permissions to use this tool. Requires group "Internal", while you have group "{}".'.format(data['auth_status']), 'danger')
        return redirect(url_for('site_tracker.index'))
    session['oi_auth_token'] = resp['access_token']
    session['oi_auth_user'] = data['user_id']
    session.permanent = True
    flash('You were signed in as {}'.format(data['user_id']), 'info')
    return redirect(url_for('site_tracker.index'))


@app.route('/login')
def login_page():
    """ View: Start oauth authorization """
    return oi_auth.authorize(callback='http://tracker.talkinlocal.org/oauthauthorized')


@app.route('/logout')
def logout_page():
    """ View: Delete the session cookie and redirect """
    session.clear()
    return redirect(url_for('no_access'))


@app.route('/root_login', methods=['GET', 'POST'])
def root_login():
    """ View: Administrator login, bypassing the OAUTH login method """
    if request.method == 'POST':
        if (request.form['username'], request.form['password']) == app.config['ROOT_LOGIN']:
            session['oi_auth_token'] = 'root_login_page'
            session['oi_auth_user'] = app.config['ROOT_LOGIN'][0]
            session.permanent = True
            flash('You used the root login page to log into the trackers as {}'.format(app.config['ROOT_LOGIN'][0]), 'info')
            return redirect(url_for('site_tracker.index'))
    return render_template('root_login.html')


def _name():
    """ Returns the name of the user """
    if 'oi_auth_user' in session:
        return session['oi_auth_user']
    eveigb = InGameBrowser(request)
    if eveigb.is_valid():
        return eveigb['Eve-Charname']
    return 'None'


def _can_access():
    """ Returns if the user can access the resources at that page """
    return not _name() == 'None'


@app.context_processor
def _prerender():
    """ Add variables to all templates """
    displayname = _name()
    valid_user = not displayname == 'None'
    return dict(displayname=displayname, valid_user=valid_user, now=datetime.utcnow())


@app.before_request
def _preprocess():
    """ Reroute the user to the login prompt page if not logged in """
    print('Full path: ' + request.path)
    if request.path.startswith('/static/'):
        return
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
    return '{:,}'.format(int(n))


@app.route('/noaccess')
def no_access():
    return render_template('no_access.html')


socketio.app = app
socketio.init_app(app)

app.register_blueprint(site)
app.register_blueprint(op, url_prefix='/operations')
app.register_blueprint(corp, url_prefix='/corp')
app.register_blueprint(fuel, url_prefix='/fuel')
app.register_blueprint(war, url_prefix='/war')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
