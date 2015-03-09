from flask import Blueprint, render_template, session, redirect, url_for, request
from datetime import datetime
from trackers.shared import app_settings


# flask
blueprint = Blueprint('doctrine_tracker', __name__, template_folder='templates/doctrine', static_folder='static')


def _name():
    """ Returns the name of the user """
    if 'oi_auth_user' in session:
        return session['oi_auth_user']
    return 'None'


@blueprint.context_processor
def _prerender():
    """ Add variables to all templates """
    return dict(displayname=_name(), now=datetime.utcnow())


@blueprint.before_request
def _check_fleet_commander():
    """ Ensure that users are fleet commanders """
    if request.path == url_for('.not_fleet_commander'):
        return
    if not _name() in app_settings['FLEET_COMMANDERS']:
        return redirect(url_for('.not_fleet_commander'))


@blueprint.route('/not_fleet_commander')
def not_fleet_commander():
    return render_template('doctrine/not_fleet_commander.html')


@blueprint.route('/')
def index():
    """ View: index page """
    return render_template('doctrine/index.html', page='home')
