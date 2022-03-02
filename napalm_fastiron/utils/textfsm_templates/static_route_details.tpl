Value Prefix (\S+)
Value NextHop (\S+)
Value Name (\S+)

Start
  ^ip route ${Prefix} ${NextHop}(?: name ${Name})? -> Record