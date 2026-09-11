
import json
from napalm import get_network_driver
driver = get_network_driver('ios')
iosv = driver('17.1.1.2', 'david', 'cisco')
iosv.open()

ios_output = iosv.get_facts()
print (json.dumps(ios_output, indent=4)) 

ios_output2 = iosv.get_bgp_neighbors()
print ios_output2

