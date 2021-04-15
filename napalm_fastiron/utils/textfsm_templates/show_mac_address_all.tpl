Value Macaddress (\S+)
Value Port (\S+)
Value Type (\S+)
Value Index (\d+)
Value VLAN (\d+)
Value Action (\S+)

Start
  ^${Macaddress}\s+${Port}\s+${Type}\s+${Index}\s+${VLAN}\s+${Action} -> Record