Value Filldown Vrf (\S+)
Value Prefix (\S+)
Value NextHop (\S+)
Value Name (\S+)

Start
  ^vrf ${Vrf}
  ^ ip route ${Prefix} ${NextHop}(?: name ${Name})? -> Record
  ^! -> Clearall