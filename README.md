[![PyPI](https://img.shields.io/pypi/v/napalm-ruckus-fastiron.svg)](https://pypi.python.org/pypi/napalm-ruckus-fastiron)
[![PyPI](https://img.shields.io/pypi/dm/napalm-ruckus-fastiron.svg)](https://pypi.python.org/pypi/napalm-ruckus-fastiron)
[![Build Status](https://travis-ci.org/Static0verride/napalm-ruckus-fastiron.svg?branch=master)](https://travis-ci.org/Static0verride/napalm-ruckus-fastiron)
[![Coverage Status](https://coveralls.io/repos/github/napalm-automation/napalm-napalm-ruckus-fastiron/badge.svg?branch=master)](https://coveralls.io/github/napalm-automation/napalm-napalm-ruckus-fastiron)


# napalm-ruckus-fastiron
- version 1.0.21

NAPALM (Network Automation and Programmability Abstraction Layer with Multivendor support) is a Python library that implements a set of functions to interact with different router vendor devices using a unified API.

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
- get_arp_table()
- get_config()
- get_environment()
- get_facts()
- get_interfaces()
- get_interfaces_counters()
- get_interfaces_ip()
- get_lldp_neighbors()
- get_lldp_neighbors_detail()
- get_mac_address_table()
- get_network_instance()
- get_ntp_peers()
- get_ntp_servers()
- get_ntp_stats()
- get_users()
- IsAlive()

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

Roapmapped
=======
- get_ipv6_neighbors_table

Requirements
=======
- Netmiko v2.0.2
- FastIron v8.0.30

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
