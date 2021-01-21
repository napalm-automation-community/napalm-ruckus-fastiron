Value Name (\S+)
Value Id (\d+)
Value Ports (.*)

Start
  ^=== LAG "${Name}" ID ${Id}
  ^\s+Ports:\s+${Ports} -> Record
