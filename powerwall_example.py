# Example of using CamTesla to access a Tesla Powerwall

import camtesla
import json
import time

# The Server object represents the API connection, authenticated via the
# stored access token
s = camtesla.ServerOAuth2()

# 's.products' represents the '/products' URL within the API
# Calling it like this executes a GET request and returns the result.
# (Strictly, it decodes the returned JSON and returns the 'response'
# component as Python values)
products = s.products()

# Access to a Powerwall is via an energy_site_id that we can
# extract from the list of products
energy_site_ids = [p['energy_site_id'] for p in products]

# Check that we only have one energy site, which is usual for a domestic setting
assert len(energy_site_ids)==1, "Expecting one energy site but we have %d" % (len(energy_sites))

# Use the energy_site_id to create an object to access a powerwall
powerwall = s.energy_sites[energy_site_ids[0]]
info = powerwall.site_info()
print("Powerwall firmware version: %s" % (info["version"]))
print("Battery count: %d" % (info["battery_count"]))
print("Operating mode: %s" % (info["default_real_mode"]))
print("Backup reserve: %3.1f%%" % (float(info["backup_reserve_percent"])))

status = powerwall.live_status()
# Print all of the data returned:
print(json.dumps(status, indent=4))

# Example extracting some fields of the status:
print("Total pack capacity: %3.2f kWh" % (float(status["total_pack_energy"])/1000.0))
print("Energy in pack: %3.2f kWh" % (float(status["energy_left"])/1000.0))


def get_mode(powerwall):
    info = powerwall.site_info()
    print("Current operating mode: %s" % (info["default_real_mode"]))
    print("Current backup reserve: %3.1f%%" % (float(info["backup_reserve_percent"])))
    print()
    return info

def change_mode(powerwall, mode, backup_percent):
    print("Changing the mode to %s and the backup reserve to %3.1f" % (mode, backup_percent))
    powerwall.backup(backup_reserve_percent=backup_percent)
    powerwall.operation(default_real_mode=mode)


original_mode = get_mode(powerwall)
modeswap = {'backup' : 'self_consumption',
            'self_consumption' : 'backup',
            'autonomous' : 'backup'}
new_mode = modeswap[original_mode['default_real_mode']]
new_backup_percent = (original_mode['backup_reserve_percent']+5) % 101

change_mode(powerwall, new_mode, new_backup_percent)

# Allow time for Powerwall to respond and status to update on the Tesla phone app
print("Waiting 30s so that changes can be observed on Tesla phone app, etc.")
time.sleep(30)

mode = get_mode(powerwall)

change_mode(powerwall, original_mode['default_real_mode'], original_mode['backup_reserve_percent'])

time.sleep(10)

mode = get_mode(powerwall)
