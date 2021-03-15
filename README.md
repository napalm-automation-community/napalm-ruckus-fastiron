# Napalm Brocade Fastiron

Current methods supported
=======

Configuration Support Matrix
-----------------------------------
- load_replace_candidate()
- load_merge_candidate()
- compare_config()
- rollback()

Getters Support Matrix
-----------------------------------
- get_facts()
- get_interfaces()
- get_interfaces_ip()
- get_interfaces_vlans()
- get_lldp_neighbors()
- get_lldp_neighbors_detail()
- get_vlans()


Imported from Ruckus Fastiron, not tested
-----------------------------------
- get_arp_table()
- get_config()
- get_environment()
- IsAlive()
- get_interfaces_counters()
- get_mac_address_table()
- get_network_instance()
- get_ntp_peers()
- get_ntp_servers()
- get_ntp_stats()
- get_users()

Currently Testing [not publicly available]
=======
- load_template()
- get_optics()
- get_bgp_congfig()
- get_bgp_neighbors()
- get_bgp_neighbors_detail()
- get_route_to()
- get_snmp information()
- ping()
- tracerroute()

Requirements
=======
- Netmiko v2.0.2

Netmiko methods
=======
- send_config()
- config_mode()
- check_config_mode()
- exit_config_mode()
- enable()
- exit_enable()
- clear_buffer()
- prompt()

Authors
=======
 * Jesús Mendez ([mendezj@staticoverride.us](mailto:mendezj@staticoverride.us))
 * Johan van den Dorpe
