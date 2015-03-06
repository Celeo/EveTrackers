from flask import Blueprint, render_template, session, redirect, url_for, request
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


@blueprint.before_request
def _check_corporation():
    """ Ensure that users have their corpraotion data in their session """
    if request.path == url_for('.no_corp_info'):
        return
    if not 'corporation' in session or not session['corporation'] \
        or not 'corporation_roles' in session or not session['corporation_roles']:
        return redirect(url_for('.no_corp_info'))


@blueprint.route('/nocorpinfo')
def no_corp_info():
    return render_template('corp/no_corp_info.html')


@blueprint.route('/')
def index():
    """ View: index page """
    return render_template('corp/index.html', page='home')
