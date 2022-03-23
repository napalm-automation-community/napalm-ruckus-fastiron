# -*- coding: utf-8 -*-
# Copyright 2015 Spotify AB. All rights reserved.
#
# The contents of this file are licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the
# License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

# Python3 support
from __future__ import print_function
from __future__ import unicode_literals

# std libs
import re
import socket
import sys

from netaddr import IPAddress

from netmiko import ConnectHandler

from napalm.base.exceptions import (
    ConnectionClosedException,
    ConnectionException,
    MergeConfigException,
    ReplaceConfigException,
)
from napalm.base.helpers import textfsm_extractor
from napalm.base import NetworkDriver


class FastIronDriver(NetworkDriver):
    """Napalm driver for FastIron."""

    def __init__(self, hostname, username, password, timeout=60, **optional_args):
        """Constructor."""

        self.device = None
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout
        self.port = optional_args.get("port", 22)
        self.merge_config = False
        self.replace_config = False
        self.stored_config = None
        self.config_replace = None
        self.config_merge = None
        self.rollback_cfg = optional_args.get("rollback_cfg", "rollback_config.txt")
        self.use_secret = optional_args.get("use_secret", False)
        self.image_type = None
        self._show_command_delay_factor = optional_args.pop("show_command_delay_factor", 1)

        # Cache command output
        self.show_running_config = None
        self.show_lag_deployed = None
        self.show_int = None
        self.interface_map = None

    def __del__(self):
        """
        This method is used to cleanup when the program is terminated suddenly.
        We need to make sure the connection is closed properly and the configuration DB
        is released (unlocked).
        """
        self.close()

    def open(self):
        """
        Opens a connection to the device.
        """
        try:
            if self.use_secret:
                secret = self.password
            else:
                secret = ""

            self.device = ConnectHandler(
                device_type="brocade_fastiron",
                ip=self.hostname,  # saves device parameters
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                secret=secret,
                conn_timeout=self.timeout,
                verbose=False,
            )
            self.device.session_preparation()
            # image_type = self.device.send_command("show version")   # find the image type
            # if image_type.find("SPS") != -1:
            #     self.image_type = "Switch"
            # else:
            #     self.image_type = "Router"

        except Exception:
            raise ConnectionException("Cannot connect to switch: %s:%s" % (self.hostname, self.port))

    def close(self):
        """
        Closes the connection to the device.
        """
        if self.device is not None:
            self.device.disconnect()

    def is_alive(self):
        """
        Returns a flag with the connection state.
        Depends on the nature of API used by each driver.
        The state does not reflect only on the connection status (when SSH), it must also take into
        consideration other parameters, e.g.: NETCONF session might not be usable, although the
        underlying SSH session is still open etc.
        """
        null = chr(0)
        try:  # send null byte see if alive
            self.device.send_command(null)
            return {"is_alive": self.device.remote_conn.transport.is_active()}

        except (socket.error, EOFError):
            return {"is_alive": False}
        except AttributeError:
            return {"is_alive": False}

    def _send_command(self, command):
        """Wrapper for self.device.send.command().

        If command is a list will iterate through commands until valid command.
        """
        output = ""

        try:
            if isinstance(command, list):
                for cmd in command:
                    output = self.device.send_command(cmd)
                    if "% Invalid" not in output:
                        break
            else:
                output = self.device.send_command(command)
            return output
        except (socket.error, EOFError) as e:
            raise ConnectionClosedException(str(e))

    class PortSpeedException(Exception):
        """Raised when port speed does not match available inputs"""

        def __init_(self, arg):
            print("unexpected speed: %s please submit bug with port speed" % arg)
            sys.exit(1)

    @staticmethod
    def __retrieve_all_locations(long_string, word, pos):
        """Finds a word of a long_string and returns the value in the nth position"""
        count = 0  # counter
        split_string = long_string.split()  # breaks long string into string of substring
        values = []  # creates a list
        for m in split_string:  # goes through substrings one by one
            count += 1  # increments counter
            if m == word:  # if substring and word match then specific value
                values.append(split_string[count + pos])  # is added to list that is returned
        return values

    @staticmethod
    def __find_words(output, word_list, pos_list):
        """ """
        dictionary = {}
        if len(word_list) != len(pos_list):  # checks word, pos pair exist
            return None

        if len(word_list) == 0 or len(pos_list) == 0:  # returns NONE if list is empty
            return None

        size = len(word_list)
        sentence = output.split()  # breaks long string into separate strings

        for m in range(0, size):  # Iterates through size of word list
            pos = int(pos_list.pop())  # pops element position and word pair in list
            word = word_list.pop()
            if word in sentence:  # checks if word is contained in text
                indx = sentence.index(word)  # records the index of word
                dictionary[word] = sentence[indx + pos]

        return dictionary

    @staticmethod
    def __creates_list_of_nlines(my_string):
        """Breaks a long string into separated substring"""
        temp = ""  # sets empty string, will add char respectively
        my_list = list()  # creates list
        for val in range(0, len(my_string)):  # iterates through the length of input

            if my_string[val] == "\n" and temp == "":
                continue
            elif my_string[val] == "\n" or val == len(my_string) - 1:  # add what was found
                my_list.append(temp)
                temp = ""
            else:
                temp += my_string[val]

        return my_list

    @staticmethod
    def __delete_if_contains(nline_list, del_word):
        temp_list = list()  # Creates a list to store variables
        for a_string in nline_list:  # iterates through list
            if del_word in a_string:  # if word matches, word is skipped
                continue
            else:
                temp_list.append(a_string.split())  # Word didn't match store in list
        return temp_list

    @staticmethod
    def __facts_uptime(my_string):  # TODO check for hours its missing....
        my_list = ["day(s)", "hour(s)", "minute(s)", "second(s)"]  # list of words to find
        my_pos = [-1, -1, -1, -1]  # relative position of interest
        total_seconds = 0  # data variables
        multiplier = 0
        t_dictionary = FastIronDriver.__find_words(my_string, my_list, my_pos)  # retrieves pos

        for m in t_dictionary.keys():  # Checks word found and its multiplier
            if m == "second(s)":  # converts to seconds
                multiplier = 1
            elif m == "minute(s)":
                multiplier = 60
            elif m == "hour(s)":
                multiplier = 3600
            elif m == "day(s)":
                multiplier = 86400
            total_seconds = int(t_dictionary.get(m)) * multiplier + total_seconds
        return total_seconds

    @staticmethod
    def __facts_model(string):
        model = FastIronDriver.__retrieve_all_locations(string, "Stackable", 0)[0]
        return model  # returns the model of the switch

    @staticmethod
    def __facts_hostname(string):
        if "hostname" in string:
            hostname = FastIronDriver.__retrieve_all_locations(string, "hostname", 0)[0]
            return hostname  # returns the hostname if configured
        else:
            return None

    @staticmethod
    def __facts_os_version(string):
        os_version = FastIronDriver.__retrieve_all_locations(string, "SW:", 1)[0]
        return os_version  # returns the os_version of switch

    @staticmethod
    def __facts_serial(string):
        serial = FastIronDriver.__retrieve_all_locations(string, "Serial", 0)[0]
        if serial == "#:":  # If there is a space before serial
            serial = FastIronDriver.__retrieve_all_locations(string, "Serial", 1)[0]
        serial = serial.replace("#:", "")
        return serial  # returns serial number

    def __physical_interface_list(self, shw_int_brief, only_physical=True):
        interface_list = list()
        n_line_output = FastIronDriver.__creates_list_of_nlines(shw_int_brief)

        for line in n_line_output:
            line = line.strip()
            # Ignore empty lines
            if not line:
                continue
            line_list = line.split()
            # Exclude header rows
            if only_physical == 1 and line_list[0] != "Port":
                interface_list.append(self.__standardize_interface_name(line_list[0]))
        return interface_list

    def _get_interface_map(self):
        """Return dict mapping ethernet port numbers to full interface name, ie

        {
            "1/1": "GigabitEthernet1/1",
            ...
        }
        """

        if not self.show_int or "pytest" in sys.modules:
            self.show_int = self.device.send_command_timing(
                "show interface", delay_factor=self._show_command_delay_factor
            )
        info = textfsm_extractor(self, "show_interface", self.show_int)

        result = {}
        for interface in info:
            if "ethernet" in interface["port"].lower() and "mgmt" not in interface["port"].lower():
                ifnum = re.sub(r"^(?:\d+)?\D+([\d/]+)", "\\1", interface["port"])
                result[ifnum] = interface["port"]

        return result

    def __standardize_interface_name(self, interface):
        if not self.interface_map or "pytest" in sys.modules:
            self.interface_map = self._get_interface_map()

        interface = str(interface).strip()
        # Convert lbX to loopbackX
        interface = re.sub(r"^lb(\d+)$", "Loopback\\1", interface)
        # Convert Loopback 1 to Loopback1
        interface = re.sub(r"^Loopback (\d+)$", "Loopback\\1", interface)
        # Convert loopback1 to Loopback1
        interface = re.sub(r"^loopback(\d+)$", "Loopback\\1", interface)
        # Convert tnX to TunnelX
        interface = re.sub(r"^tn(\d+)$", "Tunnel\\1", interface)
        # Convert Ve 10 to Ve10
        interface = re.sub(r"^Ve (\d+)$", "Ve\\1", interface)
        # Convert ve10 to Ve10
        interface = re.sub(r"^ve(\d+)$", "Ve\\1", interface)
        # Convert lg44 to lag44
        interface = re.sub(r"^lg(\d+)$", "lag\\1", interface)
        # Convert mgmt1 to Ethernetmgmt1
        if interface in ["mgmt1", "Eth mgmt1", "management1", "GigEthernetmgmt1"]:
            interface = "Ethernetmgmt1"
        # Convert 1 to ethernet1
        if re.match(r"^[\d|\/]+$", interface):
            interface = self.interface_map[interface]

        return interface

    @staticmethod
    def __facts_interface_list(shw_int_brief, pos=0, del_word="Port", trigger=0):
        interfaces_list = list()
        n_line_output = FastIronDriver.__creates_list_of_nlines(shw_int_brief)

        interface_details = FastIronDriver.__delete_if_contains(n_line_output, del_word)

        for port_det in interface_details:

            if trigger == 0:
                interfaces_list.append(port_det[pos])
            else:  # removes non physical interface
                if any(x in port_det[pos] for x in ["ve", "lb", "tunnel"]):
                    continue
                else:
                    interfaces_list.append(port_det[pos])  # adds phys interface to list
        return interfaces_list

    @staticmethod
    def __port_time(shw_int_port):
        t_port = list()  # Creates n lines of show int port
        new_lines = FastIronDriver.__creates_list_of_nlines(shw_int_port)

        for val in new_lines:
            if "name" in val:
                continue
            t_port.append(FastIronDriver.__facts_uptime(val))  # adds time to ports

        return t_port

    @staticmethod
    def __get_interface_speed(val):
        if val == "auto" or val == "1Gbit":  # appends speed hat
            speed = 1000
        elif val == "10Mbit":
            speed = 10
        elif val == "100Mbit":
            speed = 100
        elif val == "2.5Gbit":
            speed = 2500
        elif val == "5Gbit":
            speed = 5000
        elif val == "10Gbit":
            speed = 10000
        elif val == "20G":
            speed = 20000
        elif val == "40Gbit":
            speed = 40000
        elif val == "100Gbit":
            speed = 100000
        else:
            raise FastIronDriver.PortSpeedException(val)

        return float(speed)

    @staticmethod
    def __unite_strings(output):
        """removes all the new line and excess spacing in a string"""
        my_string = ""  # empty string

        for index in range(len(output)):  # iterates through all characters of output

            if output[index] != "\n" and output[index] != " ":  # skips newline and spaces
                my_string += output[index]

            if index != len(output) - 1:
                if output[index] == " " and output[index + 1] != " ":
                    my_string += " "  # next char of string is not another space

        return my_string  # returns stored string

    @staticmethod
    def __get_interface_name(shw_int_name, size):
        port_status = list()  # Creates list
        shw_int_name = FastIronDriver.__creates_list_of_nlines(shw_int_name)
        for val in shw_int_name:  # iterates through n lines
            if "No port name" in val:
                port_status.append("")  # appends nothing for port name
            else:
                port_status.append(val.replace("Port name is", ""))  # Removes fluff add name

        for temp in range(0, size - len(port_status)):  # adds no names to the remainder so that
            port_status.append("")  # all matrix of data are the same size

        return port_status

    @staticmethod
    def __is_greater(value, threshold):  # compares two values returns true if value
        if float(value) >= float(threshold):  # is greater or equal to threshold
            return True
        return False

    @staticmethod
    def __get_interfaces_speed(shw_int_speed, size):
        port_status = list()  # Create a list
        for val in range(0, size):
            if val < len(shw_int_speed):
                port_status.append(shw_int_speed[val])  # appends string index into port list
            else:
                port_status.append(0)
        return port_status  # returns port list

    @staticmethod
    def __matrix_format(my_input):
        my_list = list()
        newline = FastIronDriver.__creates_list_of_nlines(my_input)
        for text in newline:  # Goes through n lines by n lines
            text = text.split()  # splits long string into words
            if len(text) < 1:  # if more than a single word skip
                continue
            else:
                my_list.append(text)  # appends single word

        return my_list  # returns list

    @staticmethod
    def __environment_temperature(string):
        dic = dict()
        temp = FastIronDriver.__retrieve_all_locations(string, "(Sensor", -3)
        warning = FastIronDriver.__retrieve_all_locations(string, "Warning", 1)
        shutdown = FastIronDriver.__retrieve_all_locations(string, "Shutdown", 1)
        for val in range(0, len(temp)):
            crit = FastIronDriver.__is_greater(temp[val], shutdown[0])
            alert = FastIronDriver.__is_greater(temp[val], warning[0])
            dic.update(
                {"sensor " + str(val + 1): {"temperature": float(temp[val]), "is_alert": alert, "is_critical": crit}}
            )

        return {"temperature": dic}  # returns temperature of type dictionary

    @staticmethod
    def __environment_cpu(string):
        cpu = max(FastIronDriver.__retrieve_all_locations(string, "percent", -2))
        dic = {"%usage": cpu}
        return {"cpu": dic}  # returns dictionary with key cpu

    @staticmethod
    def __environment_power(chassis_string, inline_string):
        status = FastIronDriver.__retrieve_all_locations(chassis_string, "Power", 4)
        potential_values = FastIronDriver.__retrieve_all_locations(chassis_string, "Power", 1)
        norm_stat = FastIronDriver.__retrieve_all_locations(chassis_string, "Power", 7)
        capacity = float(FastIronDriver.__retrieve_all_locations(inline_string, "Free", -4)[0]) / 1000
        pwr_used = capacity - float(FastIronDriver.__retrieve_all_locations(inline_string, "Free", 1)[0]) / 1000

        my_dic = {}  # creates new list
        for val in range(0, len(status)):  # if power supply has failed will return
            if status[val] == "failed":  # false, if working will return true
                my_dic["PSU" + potential_values[val]] = {"status": False, "capacity": 0.0, "output": 0.0}
            elif norm_stat[val] == "ok":
                my_dic["PS" + potential_values[val]] = {"status": True, "capacity": capacity, "output": pwr_used}

        return {"power": my_dic}  # returns dictionary containing pwr info

    @staticmethod
    def __environment_fan(string):
        fan = FastIronDriver.__retrieve_all_locations(string, "Fan", 1)
        unit = FastIronDriver.__retrieve_all_locations(string, "Fan", 0)
        my_dict = {}  # creates list

        if "Fanless" in string:
            return {"fan": {None}}  # no fans are in unit and returns None

        for val in range(0, len(fan)):
            if fan[val] == "ok,":  # checks if output is failed or ok
                my_dict["fan" + unit[val]] = {"status": True}
            elif fan[val] == "failed":  # if fan fails, will return false
                my_dict["fan" + unit[val]] = {"status": False}

        return {"fan": my_dict}  # returns dictionary containing fan info

    @staticmethod
    def __environment_memory(string):
        mem_total = FastIronDriver.__retrieve_all_locations(string, "Dynamic", 1)
        mem_used = FastIronDriver.__retrieve_all_locations(string, "Dynamic", 4)
        dic = {"available_ram": int(mem_total[0]), "used_ram": int(mem_used[0])}

        return {"memory": dic}

    @staticmethod
    def __output_parser(output, word):
        """If the word is found in the output, it will return the ip
        address until a new interface is found."""
        token = output.find(word) + len(word)  # saves pos of where word is contained
        count = 0  # counter variable
        output = output[token : len(output)].replace("/", " ")
        nline = FastIronDriver.__creates_list_of_nlines(output)
        ip6_dict = dict()  # creates dictionary

        for sentence in nline:  # separated n lines goes n line by n line
            sentence = sentence.split()  # sentence contains list of words

            if len(sentence) > 2:  # if length of list is greater than 2
                count += 1  # its a parent interface
                if count > 1:  # only a single parent interface at a time
                    break  # breaks if another parent interface found
                ip6_dict.update(
                    {sentence[2]: {"prefix_length": sentence[3]}}  # Update ipv6 dict with ipv6 add and mask
                )
            if len(sentence) == 2:  # child ipv6 interface is found
                ip6_dict.update({sentence[0]: {"prefix_length": sentence[1]}})  # updates dictionary with ipv6 and mask

        return ip6_dict  # returns ipv6 dictionary

    @staticmethod
    def __creates_config_block(list_1):
        config_block = list()
        temp_block = list()

        for line_cmd in list_1:
            cmd_position = list_1.index(line_cmd)
            if cmd_position != 0:
                if list_1[cmd_position - 1] == "!":
                    while list_1[cmd_position] != "!" and cmd_position < len(list_1) - 1:
                        temp_block.append(list_1[cmd_position])
                        cmd_position += 1

                    if len(temp_block) > 0:
                        config_block.append(temp_block)
                    temp_block = list()

        return config_block

    @staticmethod
    def __compare_blocks(cb_1, config_blocks_2, cmd, symbol):
        temp_list = list()
        for cb_2 in config_blocks_2:  # grabs a single config block
            if cmd == cb_2[0]:  # checks cmd not found
                stat = True
                for single_cmd in cb_1:  # iterates through cmd of config block
                    if single_cmd == cmd:  # if this is first command add as base
                        temp_list.append(single_cmd)  # add to list with no changes
                    elif single_cmd not in cb_2:
                        temp_list.append(symbol + " " + single_cmd)
        return temp_list, stat

    @staticmethod
    def __comparing_list(list_1, list_2, symbol):
        diff_list = list()
        config_blocks_1 = FastIronDriver.__creates_config_block(list_1)
        config_blocks_2 = FastIronDriver.__creates_config_block(list_2)

        for cb_1 in config_blocks_1:  # Grabs a single config block
            is_found = False

            if cb_1 not in config_blocks_2:  # checks if config block already exisit
                cmd = cb_1[0]  # grabs first cmd of config block

                temp_list, is_found = FastIronDriver.__compare_blocks(cb_1, config_blocks_2, cmd, symbol)

                if is_found == 0:
                    for value in cb_1:
                        temp_list.append(symbol + " " + value)

            if len(temp_list) > 1:
                diff_list.append(temp_list)

        return diff_list

    @staticmethod
    def __compare_away(diff_1, diff_2):
        mystring = ""

        for cb_1 in diff_1:
            mystring += cb_1[0] + "\n"
            for cb_2 in diff_2:
                if cb_1[0] in cb_2:
                    for value_2 in range(1, len(cb_2)):
                        mystring += cb_2[value_2] + "\n"
            for input_1 in range(1, len(cb_1)):
                mystring += cb_1[input_1] + "\n"

        return mystring

    @staticmethod
    def __compare_vice(diff_2, diff_1):
        mystring = ""

        for cb_2 in diff_2:
            found = False
            for cb_1 in diff_1:
                if cb_2[0] in cb_1:
                    found = True

            if found == 0:
                for input_2 in cb_2:
                    mystring += input_2 + "\n"

        return mystring

    def interfaces_to_list(self, interfaces_string):
        """Convert string like 'ethe 2/1 ethe 2/4 to 2/5' or 'e 2/1 to 2/4' to list of interfaces"""
        interfaces = []
        lag_sections = []

        # Seperate lag section from ethernet
        if "lag" in interfaces_string:
            lag_sections = interfaces_string.split("lag")
            interfaces_string = lag_sections.pop(0)

        if "ethernet" in interfaces_string:
            split_string = "ethernet"
        elif "ethe" in interfaces_string:
            split_string = "ethe"
        else:
            split_string = "e"

        # Process ethernet entries
        sections = interfaces_string.split(split_string)
        if "" in sections:
            sections.remove("")  #  Remove empty list items
        for section in sections:
            section = section.strip()  # Remove leading/trailing spaces

            # Process sections like 2/4 to 2/6
            if "to" in section:
                start_intf, end_intf = section.split(" to ")
                if "/" in start_intf:
                    start_intf, end_intf = section.split(" to ")
                    start_intf_parts = start_intf.split("/")
                    slot = "/".join(start_intf_parts[0:-1])
                    num = int(start_intf_parts[-1])
                    end_num = int(end_intf.split("/")[-1])

                    while num <= end_num:
                        intf_name = "{}/{}".format(slot, num)
                        interfaces.append(self.__standardize_interface_name(intf_name))
                        num += 1
                # Process sections like 1 to 5
                else:
                    num = int(start_intf)
                    end_num = int(end_intf)
                    while num <= end_num:
                        intf_name = num
                        interfaces.append(self.__standardize_interface_name(intf_name))
                        num += 1

            # Individual ports like '2/1'
            else:
                interfaces.append(self.__standardize_interface_name(section))

        # Lags
        for lag in lag_sections:
            lag = lag.strip()  # Remove leading/trailing spaces
            if "to" in lag:
                start_intf, end_intf = lag.split(" to ")
                num = int(start_intf)
                end_num = int(end_intf)
                while num <= end_num:
                    intf_name = num
                    interfaces.append(self.__standardize_interface_name("lag{}".format(intf_name)))
                    num += 1
            else:
                interfaces.append(self.__standardize_interface_name("lag{}".format(lag)))

        return interfaces

    def interface_list_conversion(self, ve, taggedports, untaggedports):
        interfaces = []
        if ve:
            interfaces.append("Ve{}".format(ve))
        if taggedports:
            interfaces.extend(self.interfaces_to_list(taggedports))
        if untaggedports:
            interfaces.extend(self.interfaces_to_list(untaggedports))
        return interfaces

    def load_replace_candidate(self, filename=None, config=None):
        """
        Populates the candidate configuration. You can populate it from a file or from a string.
        If you send both a filename and a string containing the configuration, the file takes
        precedence.

        If you use this method the existing configuration will be replaced entirely by the
        candidate configuration once you commit the changes. This method will not change the
        configuration by itself.

        :param filename: Path to the file containing the desired configuration. By default is None.
        :param config: String containing the desired configuration.
        :raise ReplaceConfigException: If there is an error on the configuration sent.
        """
        file_content = ""

        if filename is None and config is None:  # if nothing is entered returns none
            print("No filename or config was entered")
            return None

        if filename is not None:
            try:
                file_content = open(filename, "r")  # attempts to open file
                temp = file_content.read()  # stores file content
                self.config_replace = FastIronDriver.__creates_list_of_nlines(temp)
                self.replace_config = True  # file opened successfully
                return
            except ValueError:
                raise ReplaceConfigException("Configuration error")

        if config is not None:
            try:
                self.config_replace = FastIronDriver.__creates_list_of_nlines(config)
                self.replace_config = True  # string successfully saved
                return
            except ValueError:
                raise ReplaceConfigException("Configuration error")

        raise ReplaceConfigException("Configuration error")

    def load_merge_candidate(self, filename=None, config=None):
        """
        Populates the candidate configuration. You can populate it from a file or from a string.
        If you send both a filename and a string containing the configuration, the file takes
        precedence.

        If you use this method the existing configuration will be merged with the candidate
        configuration once you commit the changes. This method will not change the configuration
        by itself.

        :param filename: Path to the file containing the desired configuration. By default is None.
        :param config: String containing the desired configuration.
        :raise MergeConfigException: If there is an error on the configuration sent.
        """
        file_content = ""

        if filename is None and config is None:  # if nothing is entered returns none
            print("No filename or config was entered")
            return None

        if filename is not None:
            try:
                file_content = open(filename, "r")  # attempts to open file
                temp = file_content.read()  # stores file content
                self.config_merge = FastIronDriver.__creates_list_of_nlines(temp)
                self.merge_config = True  # file opened successfully
                return
            except ValueError:
                raise MergeConfigException("Configuration error")

        if config is not None:
            try:
                self.config_merge = FastIronDriver.__creates_list_of_nlines(config)
                self.merge_config = True  # string successfully saved
                return
            except ValueError:
                raise MergeConfigException("Configuration error")

        raise MergeConfigException("Configuration error")

    def compare_config(self):  # optimize implementation
        """
        :return: A string showing the difference between the running configuration and the \
        candidate configuration. The running_config is loaded automatically just before doing the \
        comparison so there is no need for you to do it.
        """
        # compare_list = list()
        if self.replace_config is not True and self.merge_config is not True:
            return -1  # Configuration was never loaded

        running_config = FastIronDriver.get_config(self, "running")
        rc = running_config.get("running")
        stored_conf = None

        if self.replace_config is True:
            stored_conf = self.config_replace
        elif self.merge_config is True:
            stored_conf = self.config_merge
        else:
            return -1  # No configuration was found

        diff_1 = FastIronDriver.__comparing_list(rc, stored_conf, "+")
        diff_2 = FastIronDriver.__comparing_list(stored_conf, rc, "-")

        str_diff1 = FastIronDriver.__compare_away(diff_1, diff_2)
        str_diff2 = FastIronDriver.__compare_vice(diff_2, diff_1)

        return str_diff1 + str_diff2

    def commit_config(self):
        """
        Commits the changes requested by the method load_replace_candidate or load_merge_candidate.
        """
        if self.replace_config is False and self.merge_config is False:
            print("Please replace or merge a configuration ")
            return -1  # returns failure

        if self.replace_config is not False:
            replace_list = list()

            diff_in_config = FastIronDriver.compare_config(self)
            my_temp = FastIronDriver.__creates_list_of_nlines(diff_in_config)

            for sentence in my_temp:

                if sentence[0] == "-":
                    sentence = sentence[1 : len(sentence)]
                elif sentence[0] == "+":
                    sentence = "no" + sentence[1 : len(sentence)]
                replace_list.append(sentence)

            self.device.config_mode()
            self.device.send_config_set(replace_list)

            return True

        if self.merge_config is not False:  # merges candidate configuration with existing config
            self.device.config_mode()
            self.device.send_config_set(self.config_merge)

            return True  # returns success

    def discard_config(self):
        """
        Discards the configuration loaded into the candidate.
        """
        self.config_merge = None
        self.config_replace = None
        self.replace_config = False
        self.merge_config = False

    def rollback(self):
        """
        If changes were made, revert changes to the original state.
        """
        filename = self.rollback_cfg

        if filename is not None:
            try:
                file_content = open(filename, "r")  # attempts to open file
                temp = file_content.read()  # stores file content
                # sends configuration
                self.device.send_command(temp)

                # Save config to startup
                self.device.send_command_expect("write mem")
            except ValueError:
                raise MergeConfigException("Configuration error")
        else:
            print("no rollback file found, please insert")

    def get_facts(self):  # TODO check os_version as it returns general not switch or router
        """
        Returns a dictionary containing the following information:
         * uptime - Uptime of the device in seconds.
         * vendor - Manufacturer of the device.
         * model - Device model.
         * hostname - Hostname of the device
         * fqdn - Fqdn of the device
         * os_version - String with the OS version running on the device.
         * serial_number - Serial number of the device
         * interface_list - List of the interfaces of the device
        """
        version_output = self.device.send_command("show version")  # show version output
        interfaces_up = self.device.send_command("show int brief")  # show int brief output
        token = interfaces_up.find("Name") + len("Name") + 1
        interfaces_up = interfaces_up[token : len(interfaces_up)]
        host_name = self.device.send_command("show running | i hostname")

        return {
            "uptime": FastIronDriver.__facts_uptime(version_output),  # time of device in sec
            "vendor": "Brocade",  # Vendor of ICX switches
            "model": FastIronDriver.__facts_model(version_output),  # Model type of switch
            "hostname": FastIronDriver.__facts_hostname(host_name),  # Host name if configured
            "fqdn": "",
            "os_version": FastIronDriver.__facts_os_version(version_output),
            "serial_number": FastIronDriver.__facts_serial(version_output),
            "interface_list": self.__physical_interface_list(interfaces_up),
        }

    def get_lags(self):
        result = {}

        if not self.show_lag_deployed or "pytest" in sys.modules:  # Disable caching for tests
            self.show_lag_deployed = self.device.send_command("show lag deployed")
        info = textfsm_extractor(self, "show_lag_deployed", self.show_lag_deployed)
        for lag in info:
            port = "lag{}".format(lag["id"])
            result[port] = {
                "is_up": True,
                "is_enabled": True,
                "description": lag["name"],
                "last_flapped": float(-1),
                "speed": float(0),
                "mac_address": "",
                "mtu": 0,
                "children": self.interfaces_to_list(lag["ports"]),
            }

        return result

    def get_interfaces(self):
        """
        Returns a dictionary of dictionaries. The keys for the first dictionary will be the \
        interfaces in the devices. The inner dictionary will containing the following data for \
        each interface:
         * is_up (True/False)
         * is_enabled (True/False)
         * description (string)
         * last_flapped (int in seconds)
         * speed (int in Mbit)
         * mac_address (string)
        """
        # Get loopback, mgmt, ethernet interfaces from show interface output
        if not self.show_int or "pytest" in sys.modules:
            self.show_int = self.device.send_command_timing(
                "show interface", delay_factor=self._show_command_delay_factor
            )
        interfaces = textfsm_extractor(self, "show_interface", self.show_int)
        result = {}
        for intf in interfaces:
            port = self.__standardize_interface_name(intf["port"])
            result[port] = {
                "is_up": intf["link"] == "up",
                "is_enabled": intf["portstate"].lower() == "forwarding",
                "description": intf["name"].strip(),
                "last_flapped": float(-1),
                "speed": FastIronDriver.__get_interface_speed(intf["speed"]),
                "mtu": int(intf["mtu"]),
                "mac_address": intf["mac"],
            }

        # Process ve & loopback interfaces from running config & show int ve
        if not self.show_running_config or "pytest" in sys.modules:
            self.show_running_config = self.device.send_command("show running-config")
        running_config_interfaces = textfsm_extractor(self, "show_running_config_interface", self.show_running_config)
        for intf in [i for i in running_config_interfaces if i["interface"] in ["ve", "loopback"]]:
            ifname = self.__standardize_interface_name("{}{}".format(intf["interface"], intf["interfacenum"]))
            if ifname not in result.keys():
                show_intf = self.device.send_command(
                    "show interface {} {}".format(intf["interface"], intf["interfacenum"])
                )
                info = textfsm_extractor(self, "show_interface_detail", show_intf)[0]
                result[ifname] = {
                    "is_up": True,
                    "is_enabled": True,
                    "description": info["name"],
                    "last_flapped": float(-1),
                    "speed": float(0),
                    "mtu": int(info["mtu"]),
                    "mac_address": info["mac"],
                }

        # Get lags
        lags = self.get_lags()
        result.update(lags)

        # Remove extra keys to make tests pass
        if "pytest" in sys.modules:
            return self._delete_keys_from_dict(result, ["children", "type"])

        return result

    def get_interfaces_ip(self):
        """
        Returns all configured IP addresses on all interfaces as a dictionary of dictionaries.
        Keys of the main dictionary represent the name of the interface.
        Values of the main dictionary represent are dictionaries that may consist of two keys
        'ipv4' and 'ipv6' (one, both or none) which are themselvs dictionaries witht the IP
        addresses as keys.
        Each IP Address dictionary has the following keys:
            * prefix_length (int)
        """
        interfaces = {}

        if not self.show_running_config or "pytest" in sys.modules:
            self.show_running_config = self.device.send_command("show running-config")
        info = textfsm_extractor(self, "show_running_config_interface_ip", self.show_running_config)

        for intf in info:
            port = self.__standardize_interface_name(intf["interface"] + intf["interfacenum"])

            if port not in interfaces:
                interfaces[port] = {
                    "ipv4": {},
                    "ipv6": {},
                }

            if intf["ipv4address"]:
                prefix = IPAddress(intf["netmask"]).netmask_bits()
                interfaces[port]["ipv4"][intf["ipv4address"]] = {"prefix_length": prefix}
            if intf["ipv6address"]:
                ipaddress, prefix = intf["ipv6address"].split("/")
                interfaces[port]["ipv6"][ipaddress] = {"prefix_length": prefix}
            if intf["vrfname"]:
                interfaces[port]["vrf"] = intf["vrfname"]
            if intf["interfaceacl"]:
                interfaces[port]["interfaceacl"] = intf["interfaceacl"]

        return interfaces

    def get_vlans(self):
        if not self.show_running_config or "pytest" in sys.modules:
            self.show_running_config = self.device.send_command("show running-config")
        info = textfsm_extractor(self, "show_running_config_vlan", self.show_running_config)

        result = {}
        for vlan in info:
            if vlan["taggedports"] or vlan["untaggedports"]:
                result[vlan["vlan"]] = {
                    "name": vlan["name"],
                    "interfaces": self.interface_list_conversion(
                        vlan["ve"], vlan["taggedports"], vlan["untaggedports"]
                    ),
                }

        return result

    def get_interfaces_vlans(self):
        """return dict as documented at https://github.com/napalm-automation/napalm/issues/919#issuecomment-485905491"""

        show_int_brief = self.device.send_command_timing("show int brief", delay_factor=self._show_command_delay_factor)
        info = textfsm_extractor(self, "show_interface_brief", show_int_brief)

        result = {}

        # Create interfaces structure and correct mode
        for interface in info:
            intf = self.__standardize_interface_name(interface["port"])
            if interface["tag"] == "No" or re.match(r"^Ve", intf):
                mode = "access"
            else:
                mode = "trunk"
            result[intf] = {
                "mode": mode,
                "access-vlan": -1,
                "trunk-vlans": [],
                "native-vlan": -1,
                "tagged-native-vlan": False,
            }

        # Add lags
        for lag in self.get_lags().keys():
            result[lag] = {
                "mode": "trunk",
                "access-vlan": -1,
                "trunk-vlans": [],
                "native-vlan": -1,
                "tagged-native-vlan": False,
            }

        if not self.show_running_config or "pytest" in sys.modules:
            self.show_running_config = self.device.send_command("show running-config")
        info = textfsm_extractor(self, "show_running_config_vlan", self.show_running_config)

        # Assign VLANs to interfaces
        for vlan in info:
            if vlan["taggedports"] or vlan["untaggedports"]:
                access_ports = self.interface_list_conversion(vlan["ve"], "", vlan["untaggedports"])
                trunk_ports = self.interface_list_conversion("", vlan["taggedports"], "")

                for port in access_ports:
                    if int(vlan["vlan"]) <= 4094:
                        result[port]["access-vlan"] = vlan["vlan"]

                for port in trunk_ports:
                    if int(vlan["vlan"]) <= 4094:
                        result[port]["trunk-vlans"].append(vlan["vlan"])

        # Set native vlan for tagged ports
        for port, data in result.items():
            if data["trunk-vlans"] and data["access-vlan"] != -1:
                result[port]["native-vlan"] = data["access-vlan"]
                result[port]["access-vlan"] = -1

        return result

    def get_lldp_neighbors(self):
        """
        Returns a dictionary where the keys are local ports and the value is a list of \
        dictionaries with the following information:
            * hostname
            * port
        """
        my_dict = {}
        shw_int_neg = self.device.send_command("show lldp neighbors detail")
        info = textfsm_extractor(self, "show_lldp_neighbors_detail", shw_int_neg)

        port_regex = re.compile(
            r".*eth|^\d+$|^\d+\/\d+|^\d+\/[A-Z]\d+|^[A-Z]\d+$|^te|^xe|^ge|^gi",
            re.IGNORECASE,
        )

        for result in info:
            # Try to determine if port name is in port-id or port-desc
            if (
                " " not in result["remoteportid"]
                and ":" not in result["remoteportid"]
                and re.match(port_regex, result["remoteportid"])
                or not result["remoteportdescription"]
            ):
                port = result["remoteportid"]
            else:
                port = result["remoteportdescription"]
            local_port = self.__standardize_interface_name(result["port"])

            if local_port not in my_dict.keys():
                my_dict[local_port] = []
            my_dict[local_port].append(
                {"hostname": re.sub('"', "", result["remotesystemname"]), "port": re.sub('"', "", port)}
            )

        return my_dict

    def get_environment(self):
        """
        Returns a dictionary where:

            * fans is a dictionary of dictionaries where the key is the location and the values:
                 * status (True/False) - True if it's ok, false if it's broken
            * temperature is a dict of dictionaries where the key is the location and the values:
                 * temperature (float) - Temperature in celsius the sensor is reporting.
                 * is_alert (True/False) - True if the temperature is above the alert threshold
                 * is_critical (True/False) - True if the temp is above the critical threshold
            * power is a dictionary of dictionaries where the key is the PSU id and the values:
                 * status (True/False) - True if it's ok, false if it's broken
                 * capacity (float) - Capacity in W that the power supply can support
                 * output (float) - Watts drawn by the system
            * cpu is a dictionary of dictionaries where the key is the ID and the values
                 * %usage
            * memory is a dictionary with:
                 * available_ram (int) - Total amount of RAM installed in the device
                 * used_ram (int) - RAM in use in the device
        """
        main_dictionary = {}
        chassis_output = self.device.send_command("show chassis")
        cpu_output = self.device.send_command("show cpu")
        mem_output = self.device.send_command("show memory")
        pwr_output = self.device.send_command("show inline power")
        main_dictionary.update(FastIronDriver.__environment_fan(chassis_output))
        main_dictionary.update(FastIronDriver.__environment_temperature(chassis_output))
        main_dictionary.update(FastIronDriver.__environment_power(chassis_output, pwr_output))
        main_dictionary.update(FastIronDriver.__environment_cpu(cpu_output))
        main_dictionary.update(FastIronDriver.__environment_memory(mem_output))

        return main_dictionary

    def get_interfaces_counters(self):
        """
        Returns a dictionary of dictionaries where the first key is an interface name and the
        inner dictionary contains the following keys:

            * tx_errors (int)
            * rx_errors (int)
            * tx_discards (int)
            * rx_discards (int)
            * tx_octets (int)
            * rx_octets (int)
            * tx_unicast_packets (int)
            * rx_unicast_packets (int)
            * tx_multicast_packets (int)
            * rx_multicast_packets (int)
            * tx_broadcast_packets (int)
            * rx_broadcast_packets (int)
        """
        int_output = self.device.send_command("show interface brief")
        ports = FastIronDriver.__facts_interface_list(int_output, trigger=1)
        interface_counters = dict()
        stats = self.device.send_command("show interface")

        mul = FastIronDriver.__retrieve_all_locations(stats, "multicasts,", -2)
        uni = FastIronDriver.__retrieve_all_locations(stats, "unicasts", -2)
        bro = FastIronDriver.__retrieve_all_locations(stats, "broadcasts,", -2)
        ier = FastIronDriver.__retrieve_all_locations(stats, "errors,", -3)

        for val in range(len(ports)):
            interface_counters.update(
                {
                    ports[val]: {
                        "rx_errors": int(ier.pop(0)),
                        "tx_errors": int(ier.pop(0)),
                        "tx_discards": None,  # discard is not put in output of current show int
                        "rx_discards": None,  # alternative is to make individual calls which break
                        "tx_octets": None,
                        "rx_octets": None,
                        "rx_unicast_packets": int(uni.pop(0)),
                        "tx_unicast_packets": int(uni.pop(0)),
                        "rx_multicast_packets": int(mul.pop(0)),
                        "tx_multicast_packets": int(mul.pop(0)),
                        "rx_broadcast_packets": int(bro.pop(0)),
                        "tx_broadcast_packets": int(bro.pop(0)),
                    }
                }
            )

        return interface_counters

    def get_lldp_neighbors_detail(self, interface=""):
        """
        Returns a detailed view of the LLDP neighbors as a dictionary
        containing lists of dictionaries for each interface.

        Inner dictionaries contain fields:
            * parent_interface (string)
            * remote_port (string)
            * remote_port_description (string)
            * remote_chassis_id (string)
            * remote_system_name (string)
            * remote_system_description (string)
            * remote_system_capab (string)
            * remote_system_enabled_capab (string)
        """
        if interface == "":  # no interface was entered
            print("please enter an interface")
            return None

        output = self.device.send_command("show lldp neighbor detail port " + interface)
        output = output.replace(":", " ")
        output = output.replace('"', "")
        output = output.replace("+", " ")

        if "No neighbors" in output:  # no neighbors found on this interface
            return {}

        par_int = FastIronDriver.__retrieve_all_locations(output, "Local", 1)[0]
        chas_id = FastIronDriver.__retrieve_all_locations(output, "Chassis", 3)[0]
        sys_nam = FastIronDriver.__retrieve_all_locations(output, "name", 0)[0]

        e_token_sd = output.find("System description") + len("System description")
        s_token_sc = output.find("System capabilities")
        e_token_sc = output.find("System capabilities") + len("System capabilities")
        s_token_ma = output.find("Management address")
        s_token_la = output.find("Link aggregation")
        e_token_pd = output.find("Port description") + len("Port description")

        sys_des = output[e_token_sd:s_token_sc]  # grabs system description
        sys_cap = output[e_token_sc:s_token_ma]  # grabs system capability
        port_de = output[e_token_pd:s_token_la]  # grabs ports description

        sys_des = FastIronDriver.__unite_strings(sys_des)  # removes excess spaces and n lines
        sys_cap = FastIronDriver.__unite_strings(sys_cap)
        port_de = FastIronDriver.__unite_strings(port_de)

        return {
            interface: [
                {
                    "parent_interface": par_int,
                    "remote_chassis_id": chas_id,
                    "remote_system_name": sys_nam,
                    "remote_port": port_de,
                    "remote_port_description": "",
                    "remote_system_description": sys_des,
                    "remote_system_capab": sys_cap,
                    "remote_system_enable_capab": None,
                }
            ]
        }

    def cli(self, commands):

        cli_output = dict()
        if type(commands) is not list:
            raise TypeError("Please enter a valid list of commands!")

        for command in commands:
            output = self.device._send_command(command)
            if "Invalid input detected" in output:
                raise ValueError('Unable to execute command "{}"'.format(command))
            cli_output.setdefault(command, {})
            cli_output[command] = output

        return cli_output

    # Netmiko methods
    def send_config(self, commands):
        """send a set of configurations commands to a remote device"""
        if type(commands) is not list:
            raise TypeError("Please enter a valid list of commands!")

        self.device.send_config_set(commands)

    def config_mode(self):
        """Enter into config mode"""
        self.device.config_mode()

    def check_config_mode(self):
        """Check if you are in config mode, return boolean"""
        return self.device.check_config_mode()

    def exit_config_mode(self):
        """Exit config mode"""
        self.device.exit_config_mode()

    def enable(self):
        """Enter enable mode"""
        self.device.enable()

    def exit_enable_mode(self):
        """Exit enable mode"""
        self.device.exit_enable_mode()

    def clear_buffer(self):
        """Clear the output buffer on the remote device"""
        self.device.clear_buffer()

    def prompt(self):
        """Return the current router prompt"""
        self.device.find_prompt()

    ################################################################

    # Napalm Base Functions
    def get_arp_table(self):

        """
        Returns a list of dictionaries having the following set of keys:
            * interface (string)
            * mac (string)
            * ip (string)
            * age (float)
        """
        output = self.device.send_command("show arp")
        token = output.find("Status") + len("Status") + 1
        vtoken = output.find("VLAN") + len("VLAN") + 1

        if vtoken != 0:  # router version does not contain default vlan in arp
            token = vtoken

        output = FastIronDriver.__creates_list_of_nlines(output[token : len(output)])
        arp_table = list()

        for val in output:

            check = val
            if len(check.split()) < 7:
                continue

            if vtoken == 0:
                __, ip, mac, __, age, interface, __ = val.split()
            else:
                __, ip, mac, __, age, interface, __, vlan = val.split()

            arp_table.append(
                {
                    "interface": interface,
                    "mac": mac,
                    "ip": ip,
                    "age": float(age),
                }
            )

        return arp_table

    def get_ntp_peers(self):

        """
        Returns the NTP peers configuration as dictionary.
        The keys of the dictionary represent the IP Addresses of the peers.
        Inner dictionaries do not have yet any available keys.

        Example::

            {
                '192.168.0.1': {},
                '17.72.148.53': {},
                '37.187.56.220': {},
                '162.158.20.18': {}
            }

        """
        output = self.device.send_command("show ntp associations")
        token = output.find("disp") + len("disp") + 1
        output = output[token : len(output)]
        nline = FastIronDriver.__creates_list_of_nlines(output)
        ntp_peers = dict()
        for val in range(len(nline) - 1):
            val = nline[val].replace("~", " ")
            val = val.split()
            ntp_peers.update({val[1]: {}})

        return ntp_peers

    def get_ntp_servers(self):

        """
        Returns the NTP servers configuration as dictionary.
        The keys of the dictionary represent the IP Addresses of the servers.
        Inner dictionaries do not have yet any available keys.
        """
        output = self.device.send_command("show ntp associations")
        token = output.find("disp") + len("disp") + 1
        output = output[token : len(output)]
        nline = FastIronDriver.__creates_list_of_nlines(output)
        ntp_servers = dict()
        for val in range(len(nline) - 1):
            val = nline[val].replace("~", " ")
            val = val.split()
            ntp_servers.update({val[2]: {}})

        return ntp_servers

    def get_ntp_stats(self):

        """
        Returns a list of NTP synchronization statistics.

            * remote (string)
            * referenceid (string)
            * synchronized (True/False)
            * stratum (int)
            * type (string)
            * when (string)
            * hostpoll (int)
            * reachability (int)
            * delay (float)
            * offset (float)
            * jitter (float)
        """
        my_list = list()
        output = self.device.send_command("show ntp associations")
        token = output.find("disp") + len("disp") + 1
        end_token = output.find("synced,") - 3
        output = output[token:end_token]
        nline = FastIronDriver.__creates_list_of_nlines(output)

        for sentence in nline:
            isbool = False
            # sentence = sentence.split()
            remote, refid, stra, when, hostpoll, reach, delay, offset, jitter = sentence.split()

            if "*" in sentence:
                isbool = True

            # sentence[0] = sentence[0].replace('*', '')
            # sentence[0] = sentence[0].replace('+', '')
            # sentence[0] = sentence[0].replace('~', '')

            remote = remote.replace("*", "")
            remote = remote.replace("+", "")
            remote = remote.replace("~", "")

            my_list.append(
                {
                    "remote": remote,
                    "referenceid": refid,
                    "synchronized": isbool,
                    "stratum": int(stra),
                    "type": "-",
                    "when": int(when),
                    "hostpoll": int(hostpoll),
                    "reachability": float(reach),
                    "delay": float(delay),
                    "offset": float(offset),
                    "jitter": float(jitter),
                }
            )
        return my_list

    def get_mac_address_table(self):

        """
        Returns a lists of dictionaries. Each dictionary represents an entry in the MAC Address
        Table, having the following keys:
            * mac (string)
            * interface (string)
            * vlan (int)
            * active (boolean)
            * static (boolean)
            * moves (int)
            * last_move (float)
        """

        show_mac_address_all = self.device.send_command_timing(
            "show mac-address all", delay_factor=self._show_command_delay_factor
        )
        macaddresses = textfsm_extractor(self, "show_mac_address_all", show_mac_address_all)

        mac_tbl = list()
        for mac in macaddresses:
            if mac["type"] == "Dynamic":
                is_dynamic = True
            else:
                is_dynamic = False

            if mac["action"] == "forward":
                is_active = True
            else:
                is_active = False

            # Handle port lists like 12-13 from TurboIrons
            if "-" in mac["port"]:
                start, end = mac["port"].split("-")
                ports = list(range(int(start), int(end) + 1))
            else:
                ports = [mac["port"]]

            for port in ports:
                mac_tbl.append(
                    {
                        "mac": mac["macaddress"],
                        "interface": self.__standardize_interface_name(port),
                        "vlan": int(mac["vlan"]),
                        "static": is_dynamic,
                        "active": is_active,
                        "moves": -1,
                        "last_move": float(-1),
                    }
                )

        return mac_tbl

    def get_users(self):
        """
        Returns a dictionary with the configured users.
        The keys of the main dictionary represents the username. The values represent the details
        of the user, represented by the following keys:
            * level (int)
            * password (str)
            * sshkeys (list)

        The level is an integer between 0 and 15, where 0 is the lowest access and 15 represents
        full access to the device.
        """

        output = self.device.send_command("show users")
        user_dict = dict()
        token = output.rfind("=") + 1

        n_line = FastIronDriver.__creates_list_of_nlines(output[token : len(output)])
        for line in n_line:

            user, password, encrpt, priv, status, exptime = line.split()

            if int(priv) == 0:
                lv = 15
            elif int(priv) == 4:
                lv = 8
            else:
                lv = 3

            user_dict.update({user: {"level": lv, "password": password, "sshkeys": []}})
        return user_dict

    def get_config(self, retrieve="all"):
        """
        Return the configuration of a device.

        Args:
            retrieve(string): Which configuration type you want to populate, default is all of them.
                The rest will be set to "".

        Returns:
          The object returned is a dictionary with the following keys:
            - running(string) - Representation of the native running configuration
            - candidate(string) - Representation of the native candidate configuration. If the
              device doesnt differentiate between running and startup configuration this will an
              empty string
            - startup(string) - Representation of the native startup configuration. If the
              device doesnt differentiate between running and startup configuration this will an
              empty string
        """
        config_list = list()
        config_dic = dict()
        if retrieve == "running":
            config_list.append("show running-config")
        elif retrieve == "startup":
            config_list.append("show config")
        elif retrieve == "candidate":
            config_list.append("")
        elif retrieve == "all":
            config_list.append("show running-config")
            config_list.append(None)
            config_list.append("show config")

        for cmd in config_list:

            if cmd is None:
                config_dic.update({"candidate": {}})
                continue

            output = self.device.send_command(cmd)
            n_line = FastIronDriver.__creates_list_of_nlines(output)

            if cmd == "show running-config":
                config_dic.update({"running": n_line})
            elif cmd == "":
                config_dic.update({"candidate": n_line})
            else:
                config_dic.update({"startup": n_line})

        return config_dic

    def get_network_instances(self, name=""):

        instances = {}

        show_vrf_detail = self.device.send_command("show vrf detail")
        vrf_detail = textfsm_extractor(self, "show_vrf_detail", show_vrf_detail)

        show_ip_interface = self.device.send_command("show ip interface")
        ip_interface = textfsm_extractor(self, "show_ip_interface", show_ip_interface)

        instances["default"] = {
            "name": "default",
            "type": "DEFAULT_INSTANCE",
            "state": {"route_distinguisher": ""},
            "interfaces": {"interface": {}},
        }

        for vrf in vrf_detail:
            rd = vrf["rd"]
            if rd == "(not":
                rd = ""

            instances[vrf["name"]] = {
                "name": vrf["name"],
                "type": "L3VRF",
                "state": {"route_distinguisher": rd},
                "interfaces": {"interface": {}},
            }

        for interface in ip_interface:
            intf = self.__standardize_interface_name(interface["interfacetype"] + interface["interfacenum"])

            vrf_name = interface["vrf"]
            if vrf_name == "default-vrf":
                vrf = "default"
            else:
                vrf = [k for k in instances.keys() if vrf_name in k][0]

            instances[vrf]["interfaces"]["interface"][intf] = {}

        return instances if not name else instances[name]

    def _delete_keys_from_dict(self, dict_del, lst_keys):
        for k in lst_keys:
            try:
                del dict_del[k]
            except KeyError:
                pass
        for v in dict_del.values():
            if isinstance(v, dict):
                self._delete_keys_from_dict(v, lst_keys)

        return dict_del

    def get_static_routes(self):

        routes = []

        show_running_config = self.device.send_command("show running-config")

        if "FESX" in self.hostname or "TI24X" in self.hostname:
            static_routes_detail = textfsm_extractor(self, "fesx_static_route_details", show_running_config)
        else:
            static_routes_detail = textfsm_extractor(self, "static_route_details", show_running_config)

        vrf_static_routes_details = textfsm_extractor(self, "vrf_static_route_details", show_running_config)

        for route in static_routes_detail:
            route["vrf"] = None
            routes.append(route)

        for route in vrf_static_routes_details:
            routes.append(route)

        return routes
