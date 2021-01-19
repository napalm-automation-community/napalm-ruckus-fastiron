Value Port (\S+)
Value Link (Up|Down|Disabled|Empty|Disable)
Value PortState (\S+)
Value Dupl (\S+)
Value Speed (\S+)
Value Trunk (\S+)
Value Tag (Yes|No|N/A)
Value Pvid (\S+)
Value Pri (\S+)
Value Mac (\S+)
Value Name (.*)

Start
  ^${Port}\s+${Link}\s+${PortState}\s+${Dupl}\s+${Speed}\s+${Trunk}\s+${Tag}\s+${Pvid}\s+${Pri}\s+${Mac}(\s+)?(${Name})? -> Record

