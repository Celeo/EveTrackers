from flask import Flask, redirect, url_for, request, session, render_template
from flask_oauth import OAuth
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
import requests
from datetime import datetime
from shared import *
from trackers.landing.app import blueprint as landing
from trackers.site.app import blueprint as site
from trackers.op.app import blueprint as op
from trackers.corp.app import blueprint as corp
from trackers.fuel.app import blueprint as fuel

# flask
app = Flask(__name__)
app.config.from_pyfile('config.cfg')

# flask-sqlalchemy
db.app = app
db.init_app(app)

# settings
ALLIANCE = app.config['ALLIANCE']
HOME_SYSTEM = app.config['HOME_SYSTEM']
SYSTEM_RENAMES = app.config['SYSTEM_RENAMES']
ADMINS = app.config['ADMINS']

# flask-admin
from trackers.site.models import *
from trackers.op.models import *
admin = Admin(app, 'Op Tracker Admin Panel')
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
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        flash('You denied the request to sign in', 'danger')
        return redirect(next_url)
    data = requests.get('https://oauth.talkinlocal.org/api/v1/auth_user?access_token=' + resp['access_token']).json()['user']
    if not data['auth_status'] == 'Internal':
        flash('You do not have sufficient permissions to use this tool', 'danger')
        return redirect('login')
    session['oi_auth_token'] = resp['access_token']
    session['oi_auth_user'] = data['user_id']
    session.permanent = True
    flash('You were signed in as {}'.format(data['user_id']), 'info')
    return redirect(next_url)


@app.route('/login')
def login_page():
    """ View: Start oauth authorization """
    return oi_auth.authorize(callback='http://tracker.talkinlocal.org/oauthauthorized')


@app.route('/logout')
def logout_page():
    """ View: Delete the session cookie and redirect """
    session.clear()
    return redirect(url_for('no_access'))


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
    if request.path in ['/noaccess', '/login', '/oauthauthorized', '/landing']:
        return
    if not _can_access():
        return redirect(url_for('no_access'))


@app.template_filter('date')
def _date(s):
    """ Template filter: format date objects """
    return s.strftime('%m/%d @ %H:%M')


@app.route('/noaccess')
def no_access():
    return render_template('no_access.html')


socketio.app = app
socketio.init_app(app)

app.register_blueprint(landing)
app.register_blueprint(site)
app.register_blueprint(op, url_prefix='/operations')
app.register_blueprint(corp, url_prefix='/corp')
app.register_blueprint(fuel, url_prefix='/fuel')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
