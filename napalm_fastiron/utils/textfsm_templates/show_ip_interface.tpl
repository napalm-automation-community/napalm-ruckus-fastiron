Value Interfacetype (\w+)
Value Interfacenum (\d+)
Value Ipaddress (\S+)
Value OK (YES|NO)
Value Method (\S+)
Value Status (up|down)
Value Protocol (up|down)
Value Vrf (\S+)

Start
  ^${Interfacetype} ${Interfacenum}\s+${Ipaddress}\s+${OK}\s+${Method}\s+${Status}\s+${Protocol}\s+${Vrf} -> Record
