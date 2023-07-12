Value Filldown,Required Interface (\S+)
Value Filldown,Required InterfaceNum (\S+)
Value VrfName (\S+)
Value Ipv4address (\S+)
Value Ipv6address (\S+)
Value Netmask (\S+)
Value InterfaceAcl (\S+)

Start
  ^interface ${Interface} ${InterfaceNum}
  ^\s+vrf forwarding ${VrfName} -> Record
  ^\s+ip address ${Ipv4address} ${Netmask} -> Record
  ^\s+ipv6 address ${Ipv6address} -> Record
  ^\s+ip access-group ${InterfaceAcl} in -> Record
  ^! -> Clearall
