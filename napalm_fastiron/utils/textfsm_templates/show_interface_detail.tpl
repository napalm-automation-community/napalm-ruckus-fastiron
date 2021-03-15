Value Interface (\S+)
Value Link (up|down|disabled|empty)
Value Mac (\S+)
Value Name (.*)
Value IPAddress (\S+)
Value MTU (\d+)

Start
  ^${Interface} is ${Link},
  ^\s+Hardware is .*, address is ${Mac}
  ^\s+Port name is ${Name}
  ^\s+Internet address is ${IPAddress}, IP MTU ${MTU} bytes -> Record