from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from trackers.shared import db, InGameBrowser, socketio, app_settings
from .models import *
from datetime import datetime
from collections import Counter
from sqlalchemy import and_, or_
import requests
import re
import json

# flask
blueprint = Blueprint('site_tracker', __name__, template_folder='templates/site', static_folder='static')


last_system = {}
active_users = []


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
    settings = _get_settings(_name())
    displayname = _name()
    valid_user = not displayname == 'None'
    return dict(displayname=displayname, valid_user=valid_user, homesystem=app_settings['HOME_SYSTEM'], eveigb=InGameBrowser(request),
        now=datetime.utcnow(), settings_nt=settings.edits_in_new_tabs, settings_sm=settings.store_multiple, settings_aeg=settings.auto_expand_graph)


def _get_settings(username):
    """ Return the settings for a user """
    settings = None
    settings = Settings.query.filter_by(user=username).first()
    if not settings:
        settings = Settings(user=username)
        db.session.add(settings)
        db.session.commit()
    return settings


@blueprint.route('/', methods=['GET', 'POST'])
def index():
    """ View: index page """
    if request.method == 'POST':
        if 'graph_new_wormhole' in request.form:
            # the canvas graph has a small wormhole quick-add form that can be used to add wormholes
            w = Wormhole(creator=_name(), scanid=request.form['scanid'].upper() if request.form['scanid'] else '?',
                start=request.form['start'], end=request.form['end'], opened=True)
            if not _check_existing(_name(), 'wormhole', w):
                db.session.add(w)
                db.session.commit()
                _notify_change('tables')
                _add_edit_counter(request, session)
                flash('Wormhole added', 'info')
        # the tables under the graph each have a row at the end of the current data for adding another of that model
        elif request.form['data_type'] == 'wormhole':
            w = Wormhole(creator=_name(), scanid=request.form['scanid'].upper() if request.form['scanid'] else '?',
                start=request.form['start'], end=request.form['end'],
                status=request.form['status'], o_scanid=request.form['o_scanid'].upper(), opened=True)
            if not _check_existing(_name(), 'wormhole', w):
                db.session.add(w)
                db.session.commit()
                _notify_change('tables')
                _add_edit_counter(request, session)
                flash('Wormhole added', 'info')
        elif request.form['data_type'] == 'site':
            s = Site(creator=_name(), scanid=request.form['scanid'].upper() if request.form['scanid'] else '?',
                name=request.form['name'], type_=request.form['type'],
                system=app_settings['HOME_SYSTEM'], opened='opened' in request.form)
            if not _check_existing(_name(), 'site', s):
                db.session.add(s)
                db.session.commit()
                _notify_change('tables')
                _add_edit_counter(request, session)
                flash('Site added', 'info')
        return redirect(url_for('.index'))
    now = datetime.utcnow()
    last_edit = _get_last_update()
    return render_template('site/index.html', homepage=True, 
        last_update_diff=_get_time_diff_formatted(last_edit['time'].replace(tzinfo=None), now) if last_edit['time'] else '-never-',
        last_update_user=last_edit['user'])


@blueprint.route('/tables')
def tables():
    """ AJAX View: Return the tables of sites and wormholes for the index page """
    # the tables of current data are loaded via AJAX so they can be refreshed without reloading the entire index page
    sites = Site.query.filter_by(closed=False)
    wormholes = Wormhole.query.filter_by(closed=False)
    elapsed_timers = _get_elapsed_timers()
    return render_template('site/tables.html', sites=sites, wormholes=wormholes, elapsed_timers=elapsed_timers)


def _get_last_update():
    """ Returns a dict of info for the last time a user made an edit """
    # internal method for getting the time of and user who made the last edit to the database
    site = Site.query.order_by('-id').first()
    sitesnap = SiteSnapshot.query.order_by('-id').first()
    wormhole = Wormhole.query.order_by('-id').first()
    wormholesnap = WormholeSnapshot.query.order_by('-id').first()
    dates = []
    if site: dates.append(site.date)
    if sitesnap: dates.append(sitesnap.date)
    if wormhole: dates.append(wormhole.date)
    if wormholesnap: dates.append(wormholesnap.date)
    try:
        date = sorted(dates)[-1]
    except:
        return {'time': None, 'user': '-no one-'}
    if site and site.date == date: return {'time': date, 'user': site.creator}
    if sitesnap and sitesnap.date == date: return {'time': date, 'user': sitesnap.snapper}
    if wormhole and wormhole.date == date: return {'time': date, 'user': wormhole.creator}
    if wormholesnap and wormholesnap.date == date: return {'time': date, 'user': wormholesnap.snapper}
    return {'time': None, 'user': '-no one-'}


def _get_elapsed_timers():
    """ Return countdown timers for wormholes on the index page's tables """
    # internal method for returning the incremental timers shown on the tables on the index page
    ret = {}
    now = datetime.utcnow()
    changed = False
    for wormhole in Wormhole.query.filter_by(opened=True, closed=False).all():
        diff = (now - wormhole.date)
        days = diff.days
        m, s = divmod(diff.seconds, 60)
        h, m = divmod(m, 60)
        if days > 0 and h > 0:
            wormhole.closed = True
            snap = WormholeSnapshot(wormhole_id=wormhole.id, snapper='__server__', changed='<b>Closed</b>: False -> True')
            wormhole.snapshots.append(snap)
            changed = True
        h += days * 24
        passed = '{}:{}:{}'.format(h, m, s)
        ret[wormhole.id] = passed
    if changed:
        db.session.commit()
        _notify_change('tables')
    return ret


def _get_time_diff_formatted(old, recent):
    """ Formats the difference between two datetime objects """
    diff = recent - old
    days = diff.days
    m, s = divmod(diff.seconds, 60)
    h, m = divmod(m, 60)
    return '{} days, {} hours, {} minutes, and {} seconds'.format(days, h, m, s)


def _add_edit_counter(request, session):
    """ Adds an update count to the user """
    settings = Settings.query.filter_by(user=_name()).first()
    settings.edits_made = settings.edits_made + 1
    db.session.commit()


@blueprint.route('/add', methods=['GET', 'POST'])
def add():
    """ Add sites and wormholes to the database """
    if request.method == 'POST':
        if request.form['model_type'] == 'site':
            # user clicked submit on the site form
            # as long as that exact site doesn't exist, add the user's submission to the database
            data = [request.form[key] for key in ['scanid', 'name', 'type', 'system', 'notes']]
            opened = 'opened' in request.form
            closed = 'closed' in request.form
            s = Site(creator=_name(), scanid=data[0].upper(), name=data[1], type_=data[2], system=data[3], opened=opened, closed=closed, notes=data[4])
            if not _check_existing(_name(), 'site', s):
                db.session.add(s)
                db.session.commit()
                _notify_change('tables')
                _add_edit_counter(request, session)
                flash('Site added', 'info')
        else:
            # like the site code above, but wormholes
            data = [request.form[key] for key in ['scanid', 'start', 'end', 'status', 'o_scanid', 'notes']]
            opened = 'opened' in request.form
            closed = 'closed' in request.form
            w = Wormhole(creator=_name(), scanid=data[0].upper(), start=data[1], end=data[2], status=data[3], o_scanid=data[4], opened=opened, closed=closed, notes=data[5])
            if not _check_existing(_name(), 'wormhole', w):
                db.session.add(w)
                db.session.commit()
                _notify_change('tables')
                _add_edit_counter(request, session)
                flash('Wormholed added', 'info')
        if _get_settings(_name()).store_multiple:
            # based on the user's settings, they're either redirected to the index page to see their contribution or back to the add page for more entry
            return redirect(url_for('.add') + '?model_type={}'.format(request.form['model_type']))
        else:
            return redirect(url_for('.index'))
    # the paste page generates links to this add page with available data parsed from scanned pastes - this handles those values from the URL into the forms
    model_type = request.args.get('model_type', 'site')
    g_scanid = request.args.get('scanid', None)
    g_system = request.args.get('system', None)
    g_type = request.args.get('type', None)
    g_name = request.args.get('name', None)
    g_start = request.args.get('start', None)
    g_end = request.args.get('end', None)
    return render_template('site/add.html', model_type=model_type, g_scanid=g_scanid, g_system=g_system, g_type=g_type, g_name=g_name, g_start=g_start, g_end=g_end)


@blueprint.route('/site/<id>/close')
def close_site(id):
    """ View: close specified site and redirect to the index page """
    site = Site.query.filter_by(id=id).first_or_404()
    if not site.closed:
        site.closed = True
        snap = SiteSnapshot(site.id, _name(), '<b>Closed</b>: False -> True')
        site.snapshots.append(snap)
        db.session.commit()
        _notify_change('tables')
        _add_edit_counter(request, session)
        flash('Site closed', 'info')
    return redirect(url_for('.index'))


@blueprint.route('/site/<id>/open')
def open_site(id):
    """ View: open the specified site and redirect to the index page """
    site = Site.query.filter_by(id=id).first_or_404()
    if not site.opened:
        site.opened = True
        snap = SiteSnapshot(site.id, _name(), '<b>Opened</b>: False -> True')
        site.snapshots.append(snap)
        db.session.commit()
        _notify_change('tables')
        _add_edit_counter(request, session)
        flash('Site opened', 'info')
    return redirect(url_for('.index'))


@blueprint.route('/site/<id>', methods=['GET', 'POST'])
def site(id):
    """ View: show the user an edit form for the site and accept edits """
    site = Site.query.filter_by(id=id).first_or_404()
    admin = _name() in app_settings['ADMINS']
    if request.method == 'POST':
        if 'admin_delete' in request.form and admin:
            # this app allows site admins to immediately delete models from the database instead of the usual "close"
            db.session.delete(site)
            db.session.commit()
            _notify_change('tables')
            flash('Site deleted from database', 'warning')
            return redirect(url_for('.index'))
        if _edit_site(site, request, session):
            flash('Site edited', 'info')
            return redirect(url_for('.site', id=id))
    return render_template('site/editsite.html', site=site, admin=admin)


def _edit_site(site, request, session, in_line=False):
    """ Performs an edit on a site """
    # the previous version of the model and the data from the edit are compared and all differences are noted
    changes = []
    if not site.scanid == request.form['scanid'].upper():
        changes.append('<b>Scanid</b>: {} -> {}'.format(site.scanid, request.form['scanid'].upper()))
        site.scanid = request.form['scanid'].upper()
    if not site.name == request.form['name']:
        changes.append('<b>Name</b>: {} -> {}'.format(site.name, request.form['name']))
        site.name = request.form['name']
    if not in_line:
        if not site.system == request.form['system']:
            changes.append('<b>System</b>: {} -> {}'.format(site.system, request.form['system']))
            site.system = request.form['system']
        if not site.notes == request.form['notes']:
            changes.append('<b>Notes</b>: {} -> {}'.format(site.notes, request.form['notes']))
            site.notes = request.form['notes']
        opened = 'opened' in request.form
        if not opened == site.opened:
            changes.append('<b>Opened</b>: {} -> {}'.format(site.opened, 'opened' in request.form))
            site.opened = 'opened' in request.form
        closed = 'closed' in request.form
        if not site.closed == closed:
            changes.append('<b>Closed</b>: {} -> {}'.format(site.closed, 'closed' in request.form))
            site.closed = 'closed' in request.form
    if len(changes) > 0:
        # as long as the user changed something on the model, we generate a snapshot for their action
        snap = SiteSnapshot(site_id=site.id, snapper=_name(), changed=''.join(c + ', ' for c in changes)[:-2])
        site.snapshots.append(snap)
        db.session.commit()
        _notify_change('tables')
        _add_edit_counter(request, session)
    return changes


def _check_existing(user, model_type, model):
    """
        Checks if an existing model matching already exists for closing from the index page
        If it does, then that model is opened if closed and this method returns True
        If no matching models exist, this method returns False
    """
    existing_models = []
    if model_type == 'site':
        existing_models = Site.query.filter_by(name=model.name, scanid=model.scanid, type_=model.type_, system=model.system).all()
    else:
        existing_models = Wormhole.query.filter_by(scanid=model.scanid, start=model.start, end=model.end).all()
        existing_models.extend(w for w in Wormhole.query.filter_by(scanid=model.scanid, start=model.end, end=model.start).all())
    if len(existing_models) == 0:
        return False
    to_reopen = [model for model in existing_models if model.closed]
    if len(to_reopen) == 0:
        flash('There are {} matching {}{} in the database and {} open'.format(len(existing_models), model_type, \
            's' if len(existing_models) > 0 else '', 'are all' if len(existing_models) > 0 else 'is'), 'danger')
        return True
    reopen = to_reopen[-1]
    reopen.closed = False
    snap = None
    if model_type == 'site':
        snap = SiteSnapshot(site_id=model.id, snapper=user, changed='<b>Closed</b>: True -> False')
    else:
        snap = WormholeSnapshot(wormhole_id=model.id, snapper=user, changed='<b>Closed</b>: True -> False')
    model.snapshots.append(snap)
    db.session.commit()
    flash('There are {} matching {}{} in the database and id #{} has been reopened'.format(len(existing_models), model_type, \
        's' if len(existing_models) > 0 else '', reopen.id), 'danger')
    return True


@blueprint.route('/wormhole/<id>/open')
def open_wormhole(id):
    """ View: open the specified wormhole and return to the index page """
    wormhole = Wormhole.query.filter_by(id=id).first_or_404()
    if not wormhole.opened:
        wormhole.opened = True
        snap = WormholeSnapshot(wormhole.id, _name(), '<b>Opened</b>: False -> True')
        wormhole.snapshots.append(snap)
        db.session.commit()
        _notify_change('tables')
        _add_edit_counter(request, session)
        flash('Wormhole opened', 'info')
    return redirect(url_for('.index'))


@blueprint.route('/wormhole/<id>/close')
def close_wormhole(id):
    """ View: close the specified wormhole and redirect to the index page """
    wormhole = Wormhole.query.filter_by(id=id).first_or_404()
    if not wormhole.closed:
        wormhole.closed = True
        snap = WormholeSnapshot(wormhole.id, _name(), '<b>Closed</b>: False -> True')
        wormhole.snapshots.append(snap)
        if (app_settings['HOME_SYSTEM'] in [wormhole.start, wormhole.end]):
            _close_chain(_name(), wormhole)
        db.session.commit()
        _notify_change('tables')
        _add_edit_counter(request, session)
        flash('Wormhole closed', 'info')
    return redirect(url_for('.index'))


@blueprint.route('/wormhole/<id>', methods=['GET', 'POST'])
def wormhole(id):
    """ View: show the user an edit form for the wormhole and accept edits """
    wormhole = Wormhole.query.filter_by(id=id).first_or_404()
    admin = _name() in app_settings['ADMINS']
    if request.method == 'POST':
        # this app allows site admins to immediately delete models from the database instead of the usual "close"
        if 'admin_delete' in request.form and admin:
            db.session.delete(wormhole)
            db.session.commit()
            _notify_change('tables')
            flash('Wormhole deleted from database', 'warning')
            return redirect(url_for('.index'))
        if _edit_wormhole(wormhole, request, session):
            flash('Wormhole edited', 'info')
            return redirect(url_for('.wormhole', id=id))
    return render_template('site/editwormhole.html', wormhole=wormhole, admin=admin)


def _edit_wormhole(wormhole, request, session, in_line=False):
    """ Performs an edit on a wormhole """
    changes = []
    # the previous version of the model and the data from the edit are compared and all differences are noted
    originally_open = not wormhole.closed
    if not wormhole.scanid == request.form['scanid'].upper():
        changes.append('<b>Scanid</b>: {} -> {}'.format(wormhole.scanid, request.form['scanid'].upper()))
        wormhole.scanid = request.form['scanid'].upper()
    if not wormhole.start == request.form['start']:
        changes.append('<b>Start</b>: {} -> {}'.format(wormhole.start, request.form['start']))
        wormhole.start = request.form['start']
    if not wormhole.end == request.form['end']:
        changes.append('<b>End</b>: {} -> {}'.format(wormhole.end, request.form['end']))
        wormhole.end = request.form['end']
    if not wormhole.status == request.form['status']:
        changes.append('<b>Status</b>: {} -> {}'.format(wormhole.status, request.form['status']))
        wormhole.status = request.form['status']
    if not wormhole.o_scanid == request.form['o_scanid'].upper():
        changes.append('<b>O_Scanid</b>: {} -> {}'.format(wormhole.o_scanid, request.form['o_scanid'].upper()))
        wormhole.o_scanid = request.form['o_scanid'].upper()
    if not in_line:
        if not wormhole.notes == request.form['notes']:
            changes.append('<b>Notes</b>: {} -> {}'.format(wormhole.notes, request.form['notes']))
            wormhole.notes = request.form['notes']
        opened = 'opened' in request.form
        if not opened == wormhole.opened:
            changes.append('<b>Opened</b>: {} -> {}'.format(wormhole.opened, opened))
            wormhole.opened = opened
        closed = 'closed' in request.form
        if not closed == wormhole.closed:
            changes.append('<b>Closed</b>: {} -> {}'.format(wormhole.closed, closed))
            wormhole.closed = closed
        tiny = 'tiny' in request.form
        if not tiny == wormhole.tiny:
            changes.append('<b>Tiny</b>: {} -> {}'.format(wormhole.tiny, tiny))
            wormhole.tiny = tiny
    if len(changes) > 0:
        # as long as the user changed something on the model, we generate a snapshot for their action
        snap = WormholeSnapshot(wormhole_id=wormhole.id, snapper=_name(), changed=''.join(c + ', ' for c in changes)[:-2])
        wormhole.snapshots.append(snap)
        if (app_settings['HOME_SYSTEM'] in [wormhole.start, wormhole.end]) and wormhole.closed and originally_open:
            _close_chain(_name(), wormhole)
        db.session.commit()
        _notify_change('tables')
        _add_edit_counter(request, session)
    return changes


def _close_chain(user, wormhole):
    """
        Closes all wormholes connected to the system recursively.
        * For performance, this method does not commit changes to the database.
    """
    # this is the method called to collapse an entire chain of wormholes when someone closes a wormhole
    connected = []
    if not str(app_settings['HOME_SYSTEM']) == wormhole.start:
        connected = [w for w in Wormhole.query.filter_by(start=wormhole.start, opened=True, closed=False).all()]
        connected.extend([w for w in Wormhole.query.filter_by(end=wormhole.start, opened=True, closed=False).all() if not w in connected])
    if not str(app_settings['HOME_SYSTEM']) == wormhole.end:
        connected.extend([w for w in Wormhole.query.filter_by(start=wormhole.end, opened=True, closed=False).all() if not w in connected])
        connected.extend([w for w in Wormhole.query.filter_by(end=wormhole.end, opened=True, closed=False).all() if not w in connected])
    if not connected:
        return
    snap = WormholeSnapshot(wormhole.id, user, '<b>Closed</b>: False -> True')
    wormhole.closed = True
    wormhole.snapshots.append(snap)
    for conn in connected:
        _close_chain(user, conn)


@blueprint.route('/paste', methods=['GET', 'POST'])
def paste():
    """ View: show the user the paste form and accept pastes """
    class PasteData:
        def __init__(self, scanid='', name='', type_='', is_anom=False, is_wormhole=False, is_signature=False):
            self.scanid = scanid
            self.name = name
            self.type_ = type_
            self.is_anom = is_anom
            self.is_wormhole = is_wormhole
            self.is_signature = is_signature
        @property
        def model_type(self):
            return 'wormhole' if self.is_wormhole else 'site'
    def get_all_data(line):
        p = PasteData()
        p.scanid = re.findall(r'\w{3}-\d{3}', line)[0]
        p.is_anom = 'Anomaly' in line
        p.is_wormhole = 'Wormhole' in line
        p.is_signature = not p.is_anom and not p.is_wormhole
        if not p.is_wormhole and '100.00%' in line:
            for e in [e for e in line.split() if not e in ['Cosmic', 'Site', 'AU', 'Anomaly', 'Signature'] and not re.match(r'\d+', e) and not e == p.scanid]:
                if e in ['Combat', 'Gas', 'Ore', 'Data', 'Relic']:
                    p.type_ = e
                    continue
                else:
                    p.name += e + ' '
            p.name = p.name[:-1]
        p.scanid = p.scanid.split('-')[0]
        return p

    if request.method == 'POST':
        if not 'pastedata' in request.form or not 'system' in request.form or request.form['pastedata'].strip() == '' or request.form['system'].strip() == '':
            flash('You cannot leave the system nor the paste empty', 'danger')
            return render_template('site/pastescan.html')
        _add_edit_counter(request, session)
        db.session.add(PasteUpdated(_name()))
        db.session.commit()
        # this method returns the data for the 3 tables on the paste results page
        present = []
        findnew = []
        notfound = []
        current = datetime.utcnow()
        paste = request.form['pastedata']
        system = request.form['system']
        notfound.extend(Site.query.filter_by(system=system, closed=False).all())
        notfound.extend([w for w in Wormhole.query.filter_by(start=system, closed=False).all() if (current - w.date).days < 3])
        notfound.extend([w for w in Wormhole.query.filter_by(end=system, closed=False).all() if (current - w.date).days < 3])
        for line in paste.split('\n'):
            try:
                if not line or not line.strip(): continue
                line = line.strip()
                found = False
                newP = get_all_data(line)
                if Site.query.filter_by(scanid=newP.scanid, system=system, closed=False).count() > 0:
                    site = Site.query.filter_by(scanid=newP.scanid, system=system, closed=False).first()
                    if site in notfound:
                        notfound.remove(site)
                    found = True
                    present.append(site)
                elif Wormhole.query.filter(and_(Wormhole.closed==False, or_(Wormhole.scanid==newP.scanid, Wormhole.o_scanid==newP.scanid))).count() > 0:
                    wormhole = Wormhole.query.filter(and_(Wormhole.closed==False, or_(Wormhole.scanid==newP.scanid, Wormhole.o_scanid==newP.scanid))).first()
                    if (wormhole.start == system or wormhole.end == system):
                        if wormhole in notfound:
                            notfound.remove(wormhole)
                        found = True
                        present.append(wormhole)
                if not found:
                    findnew.append(newP)
            except:
                flash('Unknown error with line "{}"'.format(line), 'danger')
        return render_template('site/pastescan.html', raw=paste, present=present, notfound=notfound, findnew=findnew, system=system)
    return render_template('site/pastescan.html')


@blueprint.route('/graph')
def graph():
    """ View: return JSON for the graphing feature """
    # this is all of the data crunching for the JSON output read by the canvas graphing JavaScript
    def get_system_name(system):
        if system in app_settings['SYSTEM_RENAMES']:
            return app_settings['SYSTEM_RENAMES'][system]
        return system
    def get_player_count_in_system(system):
        count = 0
        for entry in last_system.values():
            if entry['current'] == system:
                count += 1
        return count
    def append_connection(connections, wh):
        for c in connections:
            if c['name'] == get_system_name(wh.start):
                c['connections'].append({
                    'name': get_system_name(wh.end),
                    'proper_name': wh.end,
                    'class': format_class(wh.end, wh.end_class, wh.end_sec),
                    'connections': [],
                    'id': wh.id,
                    'mass': wh.get_type_js(),
                    'count': get_player_count_in_system(wh.end),
                })
                return True
            if c['name'] == get_system_name(wh.end):
                c['connections'].append({
                    'name': get_system_name(wh.start),
                    'proper_name': wh.start,
                    'class': format_class(wh.start, wh.start_class, wh.start_sec),
                    'connections': [],
                    'id': wh.id,
                    'mass': wh.get_type_js(),
                    'count': get_player_count_in_system(wh.start),
                })
                return True
            if append_connection(c['connections'], wh):
                return True
        return False
    def format_class(system, clazz, security):
        if System.is_wspace(system):
            return clazz
        if re.match(r'^C\d$', system):
            return clazz
        if '?' in system:
            return 'nullsec'
        security = float(security)
        if security >= 0.45:
            return 'highsec'
        elif security > 0.0:
            return 'lowsec'
        else:
            return 'nullsec'
    class GraphWormhole(object):
        def __init__(self, id=0, start='', end='', status='', start_class='', start_sec='', end_clazz='', end_sec=''):
            self.id = id
            self.start = start
            self.end = end
            self.status = status
            self.start_class = start_class
            self.start_sec = start_sec
            self.end_clazz = end_clazz
            self.end_sec = end_sec
        def get_type_js(self):
            if self.status in ['Undecayed', 'Fresh']:
                return 'good'
            elif self.status in ['< 50% mass']:
                return 'half'
            elif self.status in ['VoC', 'EoL', 'VoC and EoL']:
                return 'critical'
            elif self.status == 'Unknown':
                return 'unknown'
            return 'gone'

    wormholes = []
    for wormhole in Wormhole.query.filter_by(opened=True, closed=False):
        g = GraphWormhole(id=wormhole.id, start=wormhole.start, end=wormhole.end, status=wormhole.status)
        s_s = System.query.filter_by(name=wormhole.start).first()
        s_e = System.query.filter_by(name=wormhole.end).first()
        if s_s:
            g.start_class = s_s.class_
            g.start_sec = s_s.security_level
        else:
            g.start_class = 0
            g.start_sec = 0
        if s_e:
            g.end_class = s_e.class_
            g.end_sec = s_e.security_level
        else:
            g.end_class = 0
            g.end_sec = 0
        wormholes.append(g)

    chains = []
    for wh in wormholes:
        if wh.start == app_settings['HOME_SYSTEM']:
            chain = {
                'name': get_system_name(wh.start),
                'proper_name': wh.start,
                'class': format_class(wh.start, wh.start_class, wh.start_sec),
                'connections': [],
                'id': wh.id,
                'count': get_player_count_in_system(wh.start),
            }
            chains.append(chain)
            break

    while wormholes:
        while True:
            changed = False
            for i, wh in enumerate(wormholes):
                if append_connection(chains, wh):
                    wormholes.pop(i)
                    changed = True
            if not changed or not wormholes:
                break
        if wormholes:
            wh = wormholes[0]
            chains.append({
                'name': get_system_name(wh.start),
                'proper_name': wh.start,
                'class': format_class(wh.start, wh.start_class, wh.start_sec),
                'connections': [],
                'id': wh.id,
                'count': get_player_count_in_system(wh.start),
            })
    return json.dumps(chains)


@blueprint.route('/systemlanding')
def system_landing():
    """ View: show all systems with open models """
    # also known as the universe page or systems page - it shows all of "active" systems
    systems = []
    def append(system):
        # if system is a stub system, don't append
        obj = System.query.filter_by(name=system).first()
        if obj and not obj.is_stub and not obj in systems:
            systems.append(obj)
    for w in Wormhole.query.filter_by(opened=True, closed=False).all():
        append(w.start)
        append(w.end)
    for s in Site.query.filter_by(closed=False).all():
        append(s.system)
    return render_template('site/systemlanding.html', systems=systems)


@blueprint.route('/system/<system>/apiinfo')
def system_api_info(system):
    """ AJAX View: return information from the EVE API about a system """
    # returns information about a system for its calling page
    system_data = _get_system_information(system)
    region = system_data['region']
    constellation = system_data['constellation']
    faction = system_data['faction']
    pirates = system_data['pirates']
    activityjumps = system_data['jumps']
    return render_template('site/systemapiinfo.html', region=region, constellation=constellation,
        faction=faction, pirates=pirates, jumps1=activityjumps[0], jumps24=activityjumps[1])

def _get_system_information(system):
    """ Return information about a system """
    data = {
        'region': 'region',
        'constellation': 'constellation',
        'faction': 'faction',
        'jumps': [-1, -1],
        'npckills': [0, 0],
        'shipkills': [0, 0],
        'podkills': [0, 0],
        'pirates': 'pirates',
        'statics': 'statics'
    }
    # website lines
    contents = [line.strip() for line in requests.get('http://evemaps.dotlan.net/system/' + system).text.split('\n') if line and not line == '']
    # recent kills
    kills = []
    for line in contents:
        if re.match(r'^<td align="right">\d+</td>$', line):
            kills.append(re.search(r'\d+', line).group(0))
        if len(kills) == 6:
            break
    data['shipkills'] = [kills[0], kills[1]]
    data['npckills'] = [kills[2], kills[3]]
    data['podkills'] = [kills[4], kills[5]]
    # faction
    for line in contents:
        if '<td colspan="3">' in line:
            data['faction'] = line.split('>')[1].split('<')[0]
            break
    # region
    for line in contents:
        if '/region/' in line:
            data['region'] = re.search(r'/region/\w+', line).group(0).split('/')[2].replace('_', ' ')
            break
    # constellation
    next = False
    for line in contents:
        if next:
            data['constellation'] = re.search(r'/universe/\w+', line).group(0).split('/')[2].replace('_', ' ')
            break
        if '<td><b>Constellation</b></td>' in line:
            next = True
    # pirates
    for line in contents:
        if '<td nowrap="nowrap" colspan="2">' in line:
            data['pirates'] = line.split('>')[1].split('<')[0]
    # jumps
    for line in contents:
        if '<td width="5%" align="right">' in line:
            if data['jumps'][0] == -1:
                data['jumps'][0] = line.split('>')[1].split('<')[0]
            else:
                data['jumps'][1] = line.split('>')[1].split('<')[0]
                break
    # wormhole statics
    systemObject = System.query.filter_by(name=system).first()
    s = ''
    if ',' in systemObject.static:
        for static in systemObject.static.split(','):
            s += static.replace(':', ' to ') + '\n'
        s = s[:-1]
    else:
        s = systemObject.static.replace(':', ' to ')
    data['statics'] = s
    return data


@blueprint.route('/system/<system>/closestchainsystem')
def closest_chain_system(system):
    """ AJAX View: return the closest chain system to this system """
    chain_systems = [w.start for w in Wormhole.query.filter_by(opened=True, closed=False)]
    chain_systems.extend([w.end for w in Wormhole.query.filter_by(opened=True, closed=False)])
    is_in_chain = system in chain_systems
    closest_chain = None
    closest_jumps = 5000
    additional = []
    if not is_in_chain:
        for chain in chain_systems:
            if System.is_wspace(chain):
                continue
            jumps = _get_jumps_between(chain, system)
            if jumps == -1:
                continue
            additional.append([chain, jumps])
            if jumps < closest_jumps:
                closest_jumps = jumps
                closest_chain = chain
    for add in additional:
        if add[0] == closest_chain:
            additional.pop(additional.index(add))
    return render_template('site/closestchainsystem.html', is_in_chain=is_in_chain, closest_chain=closest_chain, closest_jumps=closest_jumps, additional=additional)


@blueprint.route('/system/<system>/tradehubjumps')
def get_tradehub_jumps(system):
    """ AJAX View: return the number of jumps to each of the tradehubs from this system """
    # this method will first attempt to fetch the desired information from the database
    # if the data isn't yet stored, it will get the information, store it, and then return it
    systemObject = None
    systemObject = System.query.filter_by(name=system).first()
    if not systemObject:
        return ''
    amarr = -1
    dodixie = -1
    hek = -1
    jita = -1
    rens = -1
    if not systemObject.jumps_amarr == -1:
        amarr = systemObject.jumps_amarr
        dodixie = systemObject.jumps_dodixie
        hek = systemObject.jumps_hek
        jita = systemObject.jumps_jita
        rens = systemObject.jumps_rens
    else:
        for hub in ['Jita', 'Rens', 'Dodixie', 'Amarr', 'Hek']:
            distance = _get_jumps_between(system, hub)
            if systemObject:
                if hub == 'Amarr':
                    systemObject.jumps_amarr = distance
                    amarr = distance
                elif hub == 'Dodixie':
                    systemObject.jumps_dodixie = distance
                    dodixie = distance
                elif hub == 'Hek':
                    systemObject.jumps_hek = distance
                    hek = distance
                elif hub == 'Jita':
                    systemObject.jumps_jita = distance
                    jita = distance
                elif hub == 'Rens':
                    systemObject.jumps_rens = distance
                    rens = distance
        db.session.commit()
    return render_template('site/tradehubjumps.html', system=system, amarr=amarr, dodixie=dodixie, hek=hek, jita=jita, rens=rens)


def _get_jumps_between(start, end):
    """ AJAX View: Returns the number of jumps between the two systems """
    if start == end:
        return 0
    page = requests.get('http://api.eve-central.com/api/route/from/{}/to/{}'.format(start, end)).text
    if 'An internal error occurred' in page:
        return -1
    else:
        return len(json.loads(page))


@blueprint.route('/system/<system>/kills')
def system_kills(system):
    """ AJAX View: return the number of recent kills in the system """
    if System.is_wspace(system):
        return ''
    if System.query.filter_by(name=system).count() == 0:
        return ''
    data = _get_system_information(system)
    return render_template('site/systemkills.html', npc1=data['npckills'][0], npc24=data['npckills'][1],
            ship1=data['shipkills'][0], ship24=data['shipkills'][1],
            pod1=data['podkills'][0], pod24=data['podkills'][1])


@blueprint.route('/system/<system>')
def system(system):
    """ View: show information about the specified system """
    # the sites and wormholes are initially sent to the template to be rendered, the other information is loaded via AJAX
    systemObject = System.query.filter_by(name=system).first()
    if not systemObject:
        return render_template('site/systemnotfound.html', system=system)
    openwormholes = []
    openwormholes.extend([w for w in Wormhole.query.filter_by(start=system, opened=True, closed=False).all()])
    openwormholes.extend([w for w in Wormhole.query.filter_by(end=system, opened=True, closed=True).all()])
    opensites = Site.query.filter_by(system=system, opened=True, closed=False).all()
    closedwormholes = []
    closedwormholes.extend([w for w in Wormhole.query.filter_by(start=system, opened=True, closed=True).all()])
    closedwormholes.extend([w for w in Wormhole.query.filter_by(end=system, opened=True, closed=True).all()])
    unopenedsites = Site.query.filter_by(system=system, opened=False, closed=False).all()
    return render_template('site/system.html', systemObject=systemObject, class_=systemObject.class_ if System.is_wspace(system) else None,
        security=systemObject.security_level if not System.is_wspace(system) else None, kspace=not System.is_wspace(system),
        rename=app_settings['SYSTEM_RENAMES'][system] if system in app_settings['SYSTEM_RENAMES'] else None,
        openwormholes=openwormholes, opensites=opensites, closedwormholes=closedwormholes, unopenedsites=unopenedsites)


@blueprint.route('/mastertable')
def mastertable():
    """ View: show all sites and wormholes in the database """
    return render_template('site/mastertable.html', sites=Site.query.all(), wormholes=Wormhole.query.all())


@blueprint.route('/massclose', methods=['GET', 'POST'])
def mass_close():
    """ View: quickly close multiple wormholes """
    if request.method == 'POST':
        _add_edit_counter(request, session)
        for i in request.form.keys():
            wormhole = Wormhole.query.filter_by(id=i).first()
            snap = WormholeSnapshot(wormhole_id=wormhole.id, snapper=_name(), changed='<b>Closed</b>: False -> True')
            wormhole.snapshots.append(snap)
            wormhole.closed = True
            if (app_settings['HOME_SYSTEM'] in [wormhole.start, wormhole.end]):
                _close_chain(_name(), wormhole)
        db.session.commit()
        return redirect(url_for('.mass_close'))
    return render_template('site/massclose.html', wormholes=Wormhole.query.filter_by(closed=False).all())


@blueprint.route('/inlineeditsite/<id>', methods=['POST'])
def inline_edit_site(id):
    """ AJAX View: make edits to the site from POST data """
    # this is used by the index page's table editing
    site = Site.query.filter_by(id=id).first_or_404()
    if _edit_site(site, request, session, True):
        return 'Site edited'
    return 'Error occurred in editing the site'


@blueprint.route('/inlineeditwormhole/<id>', methods=['POST'])
def inline_edit_wormhole(id):
    """ AJAX View: make edits to the wormholes from POST data """
    # this is used by the index page's table editing
    wormhole = Wormhole.query.filter_by(id=id).first_or_404()
    if _edit_wormhole(wormhole, request, session, True):
        return 'Wormhole edited'
    return 'Error occurred in editing the wormhole'


def _get_chain_systems():
    """ Returns all systems directly in the chain """
    chain_systems = [w.start for w in Wormhole.query.filter_by(opened=True, closed=False).all()]
    chain_systems.extend([w.end for w in Wormhole.query.filter_by(opened=True, closed=False).all()])
    return chain_systems


@blueprint.route('/ingameplayersystem')
def in_game_player_system():
    """ AJAX View: log an in-game player's current system """
    eveigb = InGameBrowser(request)
    if not eveigb.is_igb():
        return 'Not using the in-game browser'

    # get this user's current system and ship via the Eve IGB
    current = eveigb['Eve-Solarsystemname']
    ship = eveigb['Eve-Shiptypename']
    shipname = eveigb['Eve-Shipname']

    # check if this user has just started using this page
    display_name = _name()
    has_data = False
    for d in last_system:
        if d == display_name:
            has_data = True
            break
    if not has_data:
        last_system[display_name] = {}
        last_system[display_name]['current'] = current
        last_system[display_name]['time'] = datetime.utcnow()
        last_system[display_name]['ship'] = ship
        last_system[display_name]['shipname'] = shipname
        _notify_change('locations:' + _get_player_locations())
        return 'Tracking starting, with current system = ' + current
    last = last_system[display_name]['current']

    #  update last_system with current timestamp
    last_system[display_name]['time'] = datetime.utcnow()

    # check if this user has not moved since the last AJAX call
    if last == current and last_system[display_name]['ship'] == ship and last_system[display_name]['shipname'] == shipname:
        return 'No change. `{}` `{}` `{}`'.format(last_system[display_name]['current'], last_system[display_name]['ship'], last_system[display_name]['shipname'])

    # update last_system with current data
    last_system[display_name]['current'] = current
    last_system[display_name]['ship'] = ship
    last_system[display_name]['shipname'] = shipname

    # notify index page viewers of the change(s)
    _notify_change('locations:' + _get_player_locations())

    # check if this user has moved in at last 1 w-space system this jump
    if not System.is_wspace(last) and not System.is_wspace(current):
        return 'Both your last system and your current system are k-space.'

    # check if a wormhole for this user's movement already exists
    for wormhole in Wormhole.objects.filter(opened=True, closed=False):
        if (wormhole.start == current and wormhole.destination == last) or (wormhole.start == last and wormhole.destination == current):
            return "Wormhole from {} to {} already exists." .format(last, current)

    # add a new wormhole
    wormhole = Wormhole(creator=display_name, start=last, end=current, opened=True)
    db.session.add(wormhole)
    db.session.commit()
    return 'New wormhole from {} to {} created'.format(wormhole.start, wormhole.destination)


def _get_player_locations():
    """ Return a list of all players in space """
    # used by the index page to load in-game players into the area underneath the chain graph
    players = []
    remove = []
    ret = ''
    if len(last_system) > 0:
        for entry in last_system:
            time_ = last_system[entry]['time']
            if (datetime.utcnow() - time_).seconds > 60:
                remove.append(entry)
            else:
                players.append("{} ({} '{}') in {}, &nbsp;".format(entry, last_system[entry]['ship'], last_system[entry]['shipname'], last_system[entry]['current']))
        for r in remove:
            last_system.pop(r)
        if len(players) > 0:
            players[-1] = players[-1][:-8]
        ret += ''.join(r for r in players) if players else 'No players in space'
    if _name() in app_settings['ADMINS'] and active_users > 0:
        ret += ' | '
        ret += ''.join(user + ' [online], ' for user in set(active_users))[:-2]
    return ret


@blueprint.route('/changelog')
def changelog():
    """ View: changelog """
    return render_template('site/changelog.html')


@blueprint.route('/stats')
def stats():
    """ View: usage stats """
    # show a bunch of stats that users can brag about
    # the JSON data is used for a JavaScript chart on that page
    num_sites = Site.query.count()
    num_wormholes = Wormhole.query.count()
    num_edits = SiteSnapshot.query.count() + WormholeSnapshot.query.count()
    num_pastes = PasteUpdated.query.count()
    con = Counter()
    for s in Site.query.all():
        con[s.creator] += 1
    for w in Wormhole.query.all():
        con[w.creator] += 1
    for s in SiteSnapshot.query.all():
        con[s.snapper] += 1
    for w in WormholeSnapshot.query.all():
        con[w.snapper] += 1
    num_contributors = len(con)
    con_list = []
    con = sorted(list(con.items()), key=lambda kv: kv[1])
    for s in Settings.query.all():
        if s.edits_made > 0:
            con_list.append([s.user, s.edits_made])
    con_list = list(reversed(sorted(con_list, key=lambda kv: kv[1])))
    graph = []
    for player, count in con_list[:30]:
        graph.append('{ y: ' + str(count) + ', label: "' + player + '" },')
    return render_template('site/stats.html', num_sites=num_sites, num_wormholes=num_wormholes, num_pastes=num_pastes,
        num_edits=num_edits, num_contributors=num_contributors, all_contributors=con_list, graph=graph)


@blueprint.route('/settings', methods=['GET', 'POST'])
def settings():
    """ View: change settings for the user """
    # the page for editing a users's settings that are used in a couple places around the app
    if request.method == 'POST':
        s = _get_settings(_name())
        s.edits_in_new_tabs = 'nt' in request.form
        s.store_multiple = 'sm' in request.form
        s.auto_expand_graph = 'aeg' in request.form
        db.session.commit()
        return redirect(url_for('.settings'))
    return render_template('site/settings.html')


@blueprint.route('/api/<path>/')
def api_views(path):
    """ View: current data JSON dumps """
    # current unused; redirect to the index page
    return redirect(url_for('.index'))


def _notify_change(changed):
    """ Broadcast change to all connected clients """
    # used to send messages to clients on the app's index page
    socketio.emit('sitetracker response', { 'data': 'update_' + changed }, namespace='/site')


@socketio.on('sitetracker event', namespace='/site')
def websocket_message(message):
    """ Listener: Normal event """
    # when the index page loads, it sends this request to the backend to get in-game locations
    if message['data'] == 'player_locations':
        _notify_change('locations:' + _get_player_locations())


@socketio.on('connect', namespace='/site')
def websocket_connect():
    """ Listener: Socket connection made """
    # users can have multiple tabs open - add duplicates to the 
    # list but only notify first unique additions
    name = _name()
    if name == 'None':
        return
    notify = not name in active_users
    active_users.append(name)
    if notify:
        _notify_change('locations:' + _get_player_locations())


@socketio.on('disconnect', namespace='/site')
def websocket_disconnect():
    """ Listener: Socket connection disconnected """
    # only remove the first instance in case the user has multiple tabs open, 
    # and notify if the user is completely removed from the list
    name = _name()
    active_users.remove(name)
    if not name in active_users:
        _notify_change('locations:' + _get_player_locations())


@blueprint.route('/kick/<user>')
def kick_user(user):
    """ View: kicks a user on the index page (admin only) """
    # uses the websockets to redirect a user to the logout page which dumps their session and forces 
    # them to log back into the app which fetches current data from OAuth (use case: they wouldn't be allowed back in)
    if not _name() in app_settings['ADMINS']:
        return redirect(url_for('.index'))
    socketio.emit('sitetracker response', { 'data': 'kick:' + user }, namespace='/site')
    flash('User kicked', 'info')
    return redirect(url_for('.index'))
