from flask import Blueprint, render_template, redirect, url_for, session, flash
from datetime import datetime
import eveapi


# flask
blueprint = Blueprint('fuel_tracker', __name__, template_folder='templates/fuel', static_folder='static')

# eveapi
api = eveapi.EVEAPIConnection()


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
    """ View: index page """
    return render_template('fuel/index.html', page='home')
