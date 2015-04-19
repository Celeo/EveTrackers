import csv

from trackers.app import db

from trackers.site.models import *
from trackers.op.models import *
from trackers.war.models import *


f = open('export.csv', 'wb')
writer = csv.writer(f)

# =====================
# Site
# =====================

writer.writerow(('Site',))

for site in Site.query.all():
    writer.writerow((site.creator, site.date, site.scanid, site.name, site.type_, site.system, site.opened, site.closed, site.notes))

for sitesnap in SiteSnapshot.query.all():
    writer.writerow((sitesnap.site_id, sitesnap.snapper, sitesnap.changed, sitesnap.date))

for wormhole in Wormhole.query.all():
    writer.writerow((wormhole.creator, wormhole.date, wormhole.scanid, wormhole.o_scanid, wormhole.start, wormhole.end, wormhole.status, wormhole.opened, wormhole.closed, wormhole.mass_taken, wormhole.tiny, wormhole.notes))

for wormholesnap in WormholeSnapshot.query.all():
    writer.writerow((wormholesnap.wormhole_id, wormholesnap.snapper, wormholesnap.changed, wormholesnap.date))

for settings in Settings.query.all():
    writer.writerow((settings.user, settings.edits_in_new_tabs, settings.store_multiple, settings.auto_expand_graph, settings.edits_made, settings.dont_show_nn_banner))

for system in System.query.all():
    writer.writerow((system.name, system.map_id, system.class_, system.security_level, system.note, system.jumps_amarr, system.jumps_dodixie, system.jumps_hek, system.jumps_jita, system.jumps_rens, system.static, system.effect, system.is_stub, system.dscan, system.dscan_date))

for wormholetype in WormholeType.query.all():
    writer.writerow((wormholetype.name, wormholetype.start, wormholetype.end, wormholetype.duration, wormholetype.mass_per_jump, wormholetype.mass_total))

for pasteupdated in PasteUpdated.query.all():
    writer.writerow((pasteupdated.user, pasteupdated.date))

for shipmass in ShipMass.query.all():
    writer.writerow((shipmass.ship, shipmass.mass))

# =====================
# Operations
# =====================

writer.writerow(('Operations',))

for operation in Operation.query.all():
    writer.writerow((operation.name, operation.date, operation.state, operation.leader, operation.location, operation.description, operation.last_edited, operation.loot, operation.key, operation.locked, operation.tax))

for player in Player.query.all():
    writer.writerow((player.operation_id, player.name, player.sites, player.paid, player.api_paid, player.complete))

# ignoring LogStatement

# =====================
# War
# =====================

writer.writerow(('War',))

for killmail in Killmail.query.all():
    writer.writerow((killmail.kill_id, killmail.hashcode, killmail.date, killmail.system, killmail.victim, killmail.attacker_count))
