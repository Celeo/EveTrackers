from flask import Blueprint, render_template, session
from datetime import datetime


# flask
blueprint = Blueprint('corp_tracker', __name__, template_folder='templates/corp', static_folder='static')


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
    return render_template('corp/index.html', page='home')
