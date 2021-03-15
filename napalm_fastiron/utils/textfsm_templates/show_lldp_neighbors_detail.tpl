Value Filldown Port (\S+)
Value RemoteChassisId (\S+)
Value RemotePortId (\S+)
Value RemotePortDescription (\S+)
Value Required RemoteSystemName (\S+)
Value RemoteSystemDescription (.*)
Value RemoteSystemCapab (.*)
Value RemoteSystemCapabEnabled (.*)

Start
  ^Local port: ${Port}
  ^\s+Neighbor: ${RemoteChassisId},
  ^\s+\+ Port ID \(interface name\): ${RemotePortId}
  ^\s+\+ System name\s+: ${RemoteSystemName}
  ^\s+\+ Port description\s+: ${RemotePortDescription}
  ^\s+\+ System description\s+: ${RemoteSystemDescription}
  ^\s+\+ System capabilities : ${RemoteSystemCapab}
  ^\s+ Enabled capabilities: ${RemoteSystemCapabEnabled}
  ^$$ -> Record
