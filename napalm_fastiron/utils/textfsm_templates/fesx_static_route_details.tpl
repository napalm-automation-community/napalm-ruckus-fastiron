Value Prefix (\S+)
Value Subnet (\S+)
Value NextHop (\S+)
Value Name (\S+)

Start
  ^ip route ${Prefix} ${Subnet} ${NextHop}(?: name ${Name})? -> Record