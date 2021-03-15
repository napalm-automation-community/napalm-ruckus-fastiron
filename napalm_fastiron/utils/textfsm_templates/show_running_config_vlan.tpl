Value Vlan (\d+)
Value Name (\S+)
Value Ve (\S+)
Value TaggedPorts (.*)
Value UntaggedPorts (.*)

Start
  ^vlan ${Vlan}(?: name )?${Name}?
  ^\s+tagged ${TaggedPorts}
  ^\s+(?:no )?untagged ${UntaggedPorts}
  ^\s+router-interface ve ${Ve}
  ^! -> Record