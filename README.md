# napalm-ruckus-fastiron
NAPALM driver for Ruckus FastIron

  _____            _                ______        _   _                 
 |  __ \          | |              |  ____|      | | (_)                
 | |__) |   _  ___| | ___   _ ___  | |__ __ _ ___| |_ _ _ __ ___  _ __  
 |  _  / | | |/ __| |/ / | | / __| |  __/ _` / __| __| | '__/ _ \| '_ \ 
 | | \ \ |_| | (__|   <| |_| \__ \ | | | (_| \__ \ |_| | | | (_) | | | |
 |_|  \_\__,_|\___|_|\_\\__,_|___/ |_|  \__,_|___/\__|_|_|  \___/|_| |_|


NAPALM (Network Automation and Programmability Abstraction Layer with Multivendor support) is a Python library that implements a set of functions to interact with different router vendor devices using a unified API.
Welcome To The Ruckus FastIron Driver for Napalm. 


Current methods supported
=======
IsAlilve()
get_facts()
get_interfaces()
get_lldp_neighbors()
get_environment()
get_ntp_peers()
get_ntp_servers()
get_arp_table()
get_interfaces_counters()
get_mac_address_table()
get_users()
get_ntp_stats()
get_config()
get_interfaces_ip()
get_lldp_neighbors_detail()
load_replace_candidate()
load_merge_candidate()
compare_config()
commit_config()
rollback()

Currently Testing not implement
=======
load_template()
get_network_instance()
get_bgp_congfig()
get_bgp_neighbors_detail()
get_route_to()
get_snmp information()
ping()
tracerroute()
get_optics()


Authors
=======
 * Jesús Mendez ([mendezj@staticoverride.us](mailto:mendezj@staticoverride.us))
