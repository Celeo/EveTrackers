from flask import Blueprint, render_template, session, redirect, url_for, flash
from datetime import datetime
import eveapi
from trackers.shared import app_settings
from trackers.site.models import System


# flask
blueprint = Blueprint('fuel_tracker', __name__, template_folder='templates/fuel', static_folder='static')

# eveapi
api = eveapi.EVEAPIConnection()
pairs = app_settings['FUEL_KEYS']
tower_status = {
    0: 'Unanchored',
    1: 'Offline',
    2: 'Onlining',
    3: 'Reinforced',
    4: 'Online'
}
fuel_types = {
    4247: 'Amarr Fuel Blocks',
    4051: 'Caldari Fuel Blocks',
    4312: 'Gallente Fuel Blocks',
    4246: 'Minmatar Fuel Blocks',
    16275: 'Strontium Clathrates'
}
tower_types = {
    12235: 'Amarr Control Tower',
    20059: 'Amarr Control Tower Medium',
    20060: 'Amarr Control Tower Small',
    17777: 'Amarr Starbase Control Tower',
    23761: 'Amarr Starbase Control Tower_LCO',
    29469: 'Amarr Starbase Control Tower Tough',
    26732: 'Amarr Starbase Control Tower_Tough_Good Loot',
    27539: 'Angel Control Tower',
    27607: 'Angel Control Tower Medium',
    27610: 'Angel Control Tower Small',
    27530: 'Blood Control Tower',
    27589: 'Blood Control Tower Medium',
    27592: 'Blood Control Tower Small',
    16213: 'Caldari Control Tower',
    20061: 'Caldari Control Tower Medium',
    20062: 'Caldari Control Tower Small',
    17778: 'Caldari Starbase Control Tower',
    29507: 'Caldari Starbase Control Tower_LCO',
    26734: 'Caldari Starbase Control Tower_Tough_Good Loot',
    27532: 'Dark Blood Control Tower',
    27591: 'Dark Blood Control Tower Medium',
    27594: 'Dark Blood Control Tower Small',
    27540: 'Domination Control Tower',
    27609: 'Domination Control Tower Medium',
    27612: 'Domination Control Tower Small',
    27535: 'Dread Guristas Control Tower',
    27597: 'Dread Guristas Control Tower Medium',
    27600: 'Dread Guristas Control Tower Small',
    12236: 'Gallente Control Tower',
    20063: 'Gallente Control Tower Medium',
    20064: 'Gallente Control Tower Small',
    17779: 'Gallente Starbase Control Tower',
    29460: 'Gallente Starbase Control Tower_LCO',
    32194: 'Gallente Starbase Control Tower Tough',
    26737: 'Gallente Starbase Control Tower_Tough_Good Loot',
    27533: 'Guristas Control Tower',
    27595: 'Guristas Control Tower Medium',
    27598: 'Guristas Control Tower Small',
    19505: 'Guristas Starbase Control Tower',
    20326: 'Guristas Starbase Control Tower',
    25991: 'Guristas Starbase Control Tower_Tough',
    25375: 'LCO Guristas Control Tower',
    3059: 'LCO Sansha Starbase Control Tower',
    3591: 'LCS Angel Control Tower',
    22719: "Minas Iksan's Control Tower",
    16214: 'Minmatar Control Tower',
    20065: 'Minmatar Control Tower Medium',
    20066: 'Minmatar Control Tower Small',
    17780: 'Minmatar Starbase Control Tower',
    22709: 'Minmatar Starbase Control Tower',
    26729: 'Minmatar Starbase Control Tower_Tough_Good Loot',
    27290: 'Minmatar Starbase Control Tower_Tough_Good Loot_testing',
    16286: 'QA Control Tower',
    4361: 'QA Fuel Control Tower',
    27780: 'Sansha Control Tower',
    27782: 'Sansha Control Tower Medium',
    27784: 'Sansha Control Tower Small',
    3499: 'Sansha Starbase Control Tower',
    27536: 'Serpentis Control Tower',
    27601: 'Serpentis Control Tower Medium',
    27604: 'Serpentis Control Tower Small',
    27538: 'Shadow Control Tower',
    27603: 'Shadow Control Tower Medium',
    27606: 'Shadow Control Tower Small',
    3495: 'Shield Transfer Control Tower',
    22156: 'Sispur Estate Control Tower',
    17821: 'Slaver Rig Control Tower',
    27786: 'True Sansha Control Tower',
    27788: 'True Sansha Control Tower Medium',
    27790: 'True Sansha Control Tower Small',
}


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
    if not _name() in app_settings['LEADERSHIP']:
        flash('You cannot view this page', 'danger')
        return redirect(url_for('site_tracker.index'))
    info = []
    for pair in pairs:
        auth = api.auth(keyID=pair[0], vCode=pair[1])
        poses = []
        for pos_basic in auth.corp.StarbaseList().starbases:
            pos_details = auth.corp.StarbaseDetail(itemID=pos_basic.itemID)
            key_details = auth.account.Characters()
            data = {
                'Owner': key_details.characters[0].corporationName,
                'API Tower ID': pos_basic.itemID,
                'Tower Item Type ID': pos_basic.typeID,
                'Tower Item Type Name': tower_types[pos_basic.typeID],
                'State': tower_status[pos_basic.state],
                'Location System ID': System.query.filter_by(map_id=pos_basic.locationID).first().name,
                'Location Moon ID': pos_basic.moonID,
                'Fuel': { fuel_types[fuel.typeID]: fuel.quantity for fuel in pos_details.fuel },
                'Allow corp access': bool(pos_details.generalSettings.allowCorporationMembers),
                'Allow alliance access': bool(pos_details.generalSettings.allowAllianceMembers),
                'Use Alliance Standings': 'Yes' if not pos_details.combatSettings.useStandingsFrom == '0' else 'No',
                'Attack if standing lower than': float(pos_details.combatSettings.onStandingDrop.standing) / 100.0,
                'Attack if security status lower than': pos_details.combatSettings.onStatusDrop.standing if not pos_details.combatSettings.onStatusDrop.enabled == '0' else 'Disabled',
                'Attack if other security status is dropping': bool(pos_details.combatSettings.onAggression),
                'Attack if at war': bool(pos_details.combatSettings.onCorporationWar),
            }
            poses.append(data)
        info.extend(poses)
    return render_template('fuel/index.html', info=info)
