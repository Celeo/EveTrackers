from flask import Blueprint, render_template

# flask
blueprint = Blueprint('landing', __name__, template_folder='templates/landing', static_folder='static')


@blueprint.route('/landing')
def index():
    """ View: index page """
    return render_template('landing/index.html')
