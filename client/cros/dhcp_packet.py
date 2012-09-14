# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Tools for serializing and deserializing DHCP packets.

DhcpPacket is a class that represents a single DHCP packet and contains some
logic to create and parse binary strings containing on the wire DHCP packets.

While you could call the constructor explicitly, most users should use the
static factories to construct packets with reasonable default values in most of
the fields, even if those values are zeros.

For example:

packet = dhcp_packet.create_offer_packet(transaction_id,
                                         hwmac_addr,
                                         offer_ip,
                                         server_ip)
socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Sending to the broadcast address needs special permissions.
socket.sendto(response_packet.to_binary_string(),
              ("255.255.255.255", 68))

Note that if you make changes, make sure that the tests in the bottom of this
file still pass.
"""

import collections
import logging
import random
import socket
import struct


def CreatePacketPieceClass(super_class, field_format):
    class PacketPiece(super_class):
        @staticmethod
        def pack(value):
            return struct.pack(field_format, value)

        @staticmethod
        def unpack(byte_string):
            return struct.unpack(field_format, byte_string)[0]
    return PacketPiece

"""
Represents an option in a DHCP packet.  Options may or may not be present in any
given packet, depending on the configurations of the client and the server.
Using namedtuples as super classes gets us the comparison operators we want to
use these Options in dictionaries as keys.  Below, we'll subclass Option to
reflect that different kinds of options seriallize to on the wire formats in
different ways.

|name|
A human readable name for this option.

|number|
Every DHCP option has a number that goes into the packet to indicate
which particular option is being encoded in the next few bytes.  This
property returns that number for each option.
"""
Option = collections.namedtuple("Option", ["name", "number"])

ByteOption = CreatePacketPieceClass(Option, "!B")

ShortOption = CreatePacketPieceClass(Option, "!H")

IntOption = CreatePacketPieceClass(Option, "!I")

class IpAddressOption(Option):
    @staticmethod
    def pack(value):
        return socket.inet_aton(value)

    @staticmethod
    def unpack(byte_string):
        return socket.inet_ntoa(byte_string)


class IpListOption(Option):
    @staticmethod
    def pack(value):
        return "".join([socket.inet_aton(addr) for addr in value])

    @staticmethod
    def unpack(byte_string):
        return [socket.inet_ntoa(byte_string[idx:idx+4])
                for idx in range(0, len(byte_string), 4)]


class RawOption(Option):
    @staticmethod
    def pack(value):
        return value

    @staticmethod
    def unpack(byte_string):
        return byte_string


class ByteListOption(Option):
    @staticmethod
    def pack(value):
        return "".join(chr(v) for v in value)

    @staticmethod
    def unpack(byte_string):
        return [ord(c) for c in byte_string]

"""
Represents a required field in a DHCP packet.  Similar to Option, we'll
subclass Field to reflect that different fields serialize to on the wire formats
in different ways.

|name|
A human readable name for this field.

|offset|
The |offset| for a field defines the starting byte of the field in the
binary packet string.  |offset| is used during parsing, along with
|size| to extract the byte string of a field.

|size|
Fields in DHCP packets have a fixed size that must be respected.  This
size property is used in parsing to indicate that |self._size| number of
bytes make up this field.
"""
Field = collections.namedtuple("Field", ["name", "offset", "size"])

ByteField = CreatePacketPieceClass(Field, "!B")

ShortField = CreatePacketPieceClass(Field, "!H")

IntField = CreatePacketPieceClass(Field, "!I")

HwAddrField = CreatePacketPieceClass(Field, "!16s")

class IpAddressField(Field):
    @staticmethod
    def pack(value):
        return socket.inet_aton(value)

    @staticmethod
    def unpack(byte_string):
        return socket.inet_ntoa(byte_string)


# This is per RFC 2131.  The wording doesn't seem to say that the packets must
# be this big, but that has been the historic assumption in implementations.
DHCP_MIN_PACKET_SIZE = 300

IPV4_NULL_ADDRESS = "0.0.0.0"

# These are required in every DHCP packet.  Without these fields, the
# packet will not even pass DhcpPacket.is_valid
FIELD_OP = ByteField("op", 0, 1)
FIELD_HWTYPE = ByteField("htype", 1, 1)
FIELD_HWADDR_LEN = ByteField("hlen", 2, 1)
FIELD_RELAY_HOPS = ByteField("hops", 3, 1)
FIELD_TRANSACTION_ID = IntField("xid", 4, 4)
FIELD_TIME_SINCE_START = ShortField("secs", 8, 2)
FIELD_FLAGS = ShortField("flags", 10, 2)
FIELD_CLIENT_IP = IpAddressField("ciaddr", 12, 4)
FIELD_YOUR_IP = IpAddressField("yiaddr", 16, 4)
FIELD_SERVER_IP = IpAddressField("siaddr", 20, 4)
FIELD_GATEWAY_IP = IpAddressField("giaddr", 24, 4)
FIELD_CLIENT_HWADDR = HwAddrField("chaddr", 28, 16)
# For legacy BOOTP reasons, there are 192 octets of 0's that
# come after the chaddr.
FIELD_MAGIC_COOKIE = IntField("magic_cookie", 236, 4)

OPTION_TIME_OFFSET = IntOption("time_offset", 2)
OPTION_ROUTERS = IpListOption("routers", 3)
OPTION_SUBNET_MASK = IpAddressOption("subnet_mask", 1)
OPTION_TIME_SERVERS = IpListOption("time_servers", 4)
OPTION_NAME_SERVERS = IpListOption("name_servers", 5)
OPTION_DNS_SERVERS = IpListOption("dns_servers", 6)
OPTION_LOG_SERVERS = IpListOption("log_servers", 7)
OPTION_COOKIE_SERVERS = IpListOption("cookie_servers", 8)
OPTION_LPR_SERVERS = IpListOption("lpr_servers", 9)
OPTION_IMPRESS_SERVERS = IpListOption("impress_servers", 10)
OPTION_RESOURCE_LOC_SERVERS = IpListOption("resource_loc_servers", 11)
OPTION_HOST_NAME = RawOption("host_name", 12)
OPTION_BOOT_FILE_SIZE = ShortOption("boot_file_size", 13)
OPTION_MERIT_DUMP_FILE = RawOption("merit_dump_file", 14)
OPTION_DOMAIN_NAME = RawOption("domain_name", 15)
OPTION_SWAP_SERVER = IpAddressOption("swap_server", 16)
OPTION_ROOT_PATH = RawOption("root_path", 17)
OPTION_EXTENSIONS = RawOption("extensions", 18)
OPTION_REQUESTED_IP = IpAddressOption("requested_ip", 50)
OPTION_IP_LEASE_TIME = IntOption("ip_lease_time", 51)
OPTION_OPTION_OVERLOAD = ByteOption("option_overload", 52)
OPTION_DHCP_MESSAGE_TYPE = ByteOption("dhcp_message_type", 53)
OPTION_SERVER_ID = IpAddressOption("server_id", 54)
OPTION_PARAMETER_REQUEST_LIST = ByteListOption("parameter_request_list", 55)
OPTION_MESSAGE = RawOption("message", 56)
OPTION_MAX_DHCP_MESSAGE_SIZE = ShortOption("max_dhcp_message_size", 57)
OPTION_RENEWAL_T1_TIME_VALUE = IntOption("renewal_t1_time_value", 58)
OPTION_REBINDING_T2_TIME_VALUE = IntOption("rebinding_t2_time_value", 59)
OPTION_VENDOR_ID = RawOption("vendor_id", 60)
OPTION_CLIENT_ID = RawOption("client_id", 61)
OPTION_TFTP_SERVER_NAME = RawOption("tftp_server_name", 66)
OPTION_BOOTFILE_NAME = RawOption("bootfile_name", 67)
# Unlike every other option, which are tuples like:
# <number, length in bytes, data>, the pad and end options are just
# single bytes "\x00" and "\xff" (without length or data fields).
OPTION_PAD = 0
OPTION_END = 255

# All fields are required.
DHCP_PACKET_FIELDS = [
        FIELD_OP,
        FIELD_HWTYPE,
        FIELD_HWADDR_LEN,
        FIELD_RELAY_HOPS,
        FIELD_TRANSACTION_ID,
        FIELD_TIME_SINCE_START,
        FIELD_FLAGS,
        FIELD_CLIENT_IP,
        FIELD_YOUR_IP,
        FIELD_SERVER_IP,
        FIELD_GATEWAY_IP,
        FIELD_CLIENT_HWADDR,
        FIELD_MAGIC_COOKIE,
        ]

# The op field in an ipv4 packet is either 1 or 2 depending on
# whether the packet is from a server or from a client.
FIELD_VALUE_OP_CLIENT_REQUEST = 1
FIELD_VALUE_OP_SERVER_RESPONSE = 2
# 1 == 10mb ethernet hardware address type (aka MAC).
FIELD_VALUE_HWTYPE_10MB_ETH = 1
# MAC addresses are still 6 bytes long.
FIELD_VALUE_HWADDR_LEN_10MB_ETH = 6
FIELD_VALUE_MAGIC_COOKIE = 0x63825363

OPTIONS_START_OFFSET = 240
# From RFC2132, the valid DHCP message types are:
OPTION_VALUE_DHCP_MESSAGE_TYPE_DISCOVERY = 1
OPTION_VALUE_DHCP_MESSAGE_TYPE_OFFER     = 2
OPTION_VALUE_DHCP_MESSAGE_TYPE_REQUEST   = 3
OPTION_VALUE_DHCP_MESSAGE_TYPE_DECLINE   = 4
OPTION_VALUE_DHCP_MESSAGE_TYPE_ACK       = 5
OPTION_VALUE_DHCP_MESSAGE_TYPE_NAK       = 6
OPTION_VALUE_DHCP_MESSAGE_TYPE_RELEASE   = 7
OPTION_VALUE_DHCP_MESSAGE_TYPE_INFORM    = 8
OPTION_VALUE_DHCP_MESSAGE_TYPE_UNKNOWN   = -1

OPTION_VALUE_PARAMETER_REQUEST_LIST_DEFAULT = [
        OPTION_REQUESTED_IP.number,
        OPTION_IP_LEASE_TIME.number,
        OPTION_SERVER_ID.number,
        OPTION_SUBNET_MASK.number,
        OPTION_ROUTERS.number,
        OPTION_DNS_SERVERS.number,
        OPTION_HOST_NAME.number,
        ]

# These are possible options that may not be in every packet.
# Frequently, the client can include a bunch of options that indicate
# that it would like to receive information about time servers, routers,
# lpr servers, and much more, but the DHCP server can usually ignore
# those requests.
#
# Eventually, each option is encoded as:
#     <option.number, option.size, [array of option.size bytes]>
# Unlike fields, which make up a fixed packet format, options can be in
# any order, except where they cannot.  For instance, option 1 must
# follow option 3 if both are supplied.  For this reason, potential
# options are in this list, and added to the packet in this order every
# time.
#
# size < 0 indicates that this is variable length field of at least
# abs(length) bytes in size.
DHCP_PACKET_OPTIONS = [
        OPTION_TIME_OFFSET,
        OPTION_ROUTERS,
        OPTION_SUBNET_MASK,
        OPTION_TIME_SERVERS,
        OPTION_NAME_SERVERS,
        OPTION_DNS_SERVERS,
        OPTION_LOG_SERVERS,
        OPTION_COOKIE_SERVERS,
        OPTION_LPR_SERVERS,
        OPTION_IMPRESS_SERVERS,
        OPTION_RESOURCE_LOC_SERVERS,
        OPTION_HOST_NAME,
        OPTION_BOOT_FILE_SIZE,
        OPTION_MERIT_DUMP_FILE,
        OPTION_SWAP_SERVER,
        OPTION_DOMAIN_NAME,
        OPTION_ROOT_PATH,
        OPTION_EXTENSIONS,
        OPTION_REQUESTED_IP,
        OPTION_IP_LEASE_TIME,
        OPTION_OPTION_OVERLOAD,
        OPTION_DHCP_MESSAGE_TYPE,
        OPTION_SERVER_ID,
        OPTION_PARAMETER_REQUEST_LIST,
        OPTION_MESSAGE,
        OPTION_MAX_DHCP_MESSAGE_SIZE,
        OPTION_RENEWAL_T1_TIME_VALUE,
        OPTION_REBINDING_T2_TIME_VALUE,
        OPTION_VENDOR_ID,
        OPTION_CLIENT_ID,
        OPTION_TFTP_SERVER_NAME,
        OPTION_BOOTFILE_NAME,
        ]

def get_dhcp_option_by_number(number):
    for option in DHCP_PACKET_OPTIONS:
        if option.number == number:
            return option
    return None

class DhcpPacket(object):
    @staticmethod
    def create_discovery_packet(hwmac_addr):
        """
        Create a discovery packet.

        Fill in fields of a DHCP packet as if it were being sent from
        |hwmac_addr|.  Requests subnet masks, broadcast addresses, router
        addresses, dns addresses, domain search lists, client host name, and NTP
        server addresses.  Note that the offer packet received in response to
        this packet will probably not contain all of that information.
        """
        # MAC addresses are actually only 6 bytes long, however, for whatever
        # reason, DHCP allocated 12 bytes to this field.  Ease the burden on
        # developers and hide this detail.
        while len(hwmac_addr) < 12:
            hwmac_addr += chr(OPTION_PAD)

        packet = DhcpPacket()
        packet.set_field(FIELD_OP, FIELD_VALUE_OP_CLIENT_REQUEST)
        packet.set_field(FIELD_HWTYPE, FIELD_VALUE_HWTYPE_10MB_ETH)
        packet.set_field(FIELD_HWADDR_LEN, FIELD_VALUE_HWADDR_LEN_10MB_ETH)
        packet.set_field(FIELD_RELAY_HOPS, 0)
        packet.set_field(FIELD_TRANSACTION_ID, random.getrandbits(32))
        packet.set_field(FIELD_TIME_SINCE_START, 0)
        packet.set_field(FIELD_FLAGS, 0)
        packet.set_field(FIELD_CLIENT_IP, IPV4_NULL_ADDRESS)
        packet.set_field(FIELD_YOUR_IP, IPV4_NULL_ADDRESS)
        packet.set_field(FIELD_SERVER_IP, IPV4_NULL_ADDRESS)
        packet.set_field(FIELD_GATEWAY_IP, IPV4_NULL_ADDRESS)
        packet.set_field(FIELD_CLIENT_HWADDR, hwmac_addr)
        packet.set_field(FIELD_MAGIC_COOKIE, FIELD_VALUE_MAGIC_COOKIE)
        packet.set_option(OPTION_DHCP_MESSAGE_TYPE,
                          OPTION_VALUE_DHCP_MESSAGE_TYPE_DISCOVERY)
        return packet

    @staticmethod
    def create_offer_packet(transaction_id,
                            hwmac_addr,
                            offer_ip,
                            server_ip):
        """
        Create an offer packet, given some fields that tie the packet to a
        particular offer.
        """
        packet = DhcpPacket()
        packet.set_field(FIELD_OP, FIELD_VALUE_OP_SERVER_RESPONSE)
        packet.set_field(FIELD_HWTYPE, FIELD_VALUE_HWTYPE_10MB_ETH)
        packet.set_field(FIELD_HWADDR_LEN, FIELD_VALUE_HWADDR_LEN_10MB_ETH)
        # This has something to do with relay agents
        packet.set_field(FIELD_RELAY_HOPS, 0)
        packet.set_field(FIELD_TRANSACTION_ID, transaction_id)
        packet.set_field(FIELD_TIME_SINCE_START, 0)
        packet.set_field(FIELD_FLAGS, 0)
        packet.set_field(FIELD_CLIENT_IP, IPV4_NULL_ADDRESS)
        packet.set_field(FIELD_YOUR_IP, offer_ip)
        packet.set_field(FIELD_SERVER_IP, server_ip)
        packet.set_field(FIELD_GATEWAY_IP, IPV4_NULL_ADDRESS)
        packet.set_field(FIELD_CLIENT_HWADDR, hwmac_addr)
        packet.set_field(FIELD_MAGIC_COOKIE, FIELD_VALUE_MAGIC_COOKIE)
        packet.set_option(OPTION_DHCP_MESSAGE_TYPE,
                          OPTION_VALUE_DHCP_MESSAGE_TYPE_OFFER)
        return packet

    @staticmethod
    def create_request_packet(transaction_id,
                              hwmac_addr):
        packet = DhcpPacket()
        packet.set_field(FIELD_OP, FIELD_VALUE_OP_CLIENT_REQUEST)
        packet.set_field(FIELD_HWTYPE, FIELD_VALUE_HWTYPE_10MB_ETH)
        packet.set_field(FIELD_HWADDR_LEN, FIELD_VALUE_HWADDR_LEN_10MB_ETH)
        # This has something to do with relay agents
        packet.set_field(FIELD_RELAY_HOPS, 0)
        packet.set_field(FIELD_TRANSACTION_ID, transaction_id)
        packet.set_field(FIELD_TIME_SINCE_START, 0)
        packet.set_field(FIELD_FLAGS, 0)
        packet.set_field(FIELD_CLIENT_IP, IPV4_NULL_ADDRESS)
        packet.set_field(FIELD_YOUR_IP, IPV4_NULL_ADDRESS)
        packet.set_field(FIELD_SERVER_IP, IPV4_NULL_ADDRESS)
        packet.set_field(FIELD_GATEWAY_IP, IPV4_NULL_ADDRESS)
        packet.set_field(FIELD_CLIENT_HWADDR, hwmac_addr)
        packet.set_field(FIELD_MAGIC_COOKIE, FIELD_VALUE_MAGIC_COOKIE)
        packet.set_option(OPTION_DHCP_MESSAGE_TYPE,
                          OPTION_VALUE_DHCP_MESSAGE_TYPE_REQUEST)
        return packet

    @staticmethod
    def create_acknowledgement_packet(transaction_id,
                                      hwmac_addr,
                                      granted_ip,
                                      server_ip):
        packet = DhcpPacket()
        packet.set_field(FIELD_OP, FIELD_VALUE_OP_SERVER_RESPONSE)
        packet.set_field(FIELD_HWTYPE, FIELD_VALUE_HWTYPE_10MB_ETH)
        packet.set_field(FIELD_HWADDR_LEN, FIELD_VALUE_HWADDR_LEN_10MB_ETH)
        # This has something to do with relay agents
        packet.set_field(FIELD_RELAY_HOPS, 0)
        packet.set_field(FIELD_TRANSACTION_ID, transaction_id)
        packet.set_field(FIELD_TIME_SINCE_START, 0)
        packet.set_field(FIELD_FLAGS, 0)
        packet.set_field(FIELD_CLIENT_IP, IPV4_NULL_ADDRESS)
        packet.set_field(FIELD_YOUR_IP, granted_ip)
        packet.set_field(FIELD_SERVER_IP, server_ip)
        packet.set_field(FIELD_GATEWAY_IP, IPV4_NULL_ADDRESS)
        packet.set_field(FIELD_CLIENT_HWADDR, hwmac_addr)
        packet.set_field(FIELD_MAGIC_COOKIE, FIELD_VALUE_MAGIC_COOKIE)
        packet.set_option(OPTION_DHCP_MESSAGE_TYPE,
                          OPTION_VALUE_DHCP_MESSAGE_TYPE_ACK)
        return packet

    def __init__(self, byte_str=None):
        """
        Create a DhcpPacket, filling in fields from a byte string if given.

        Assumes that the packet starts at offset 0 in the binary string.  This
        includes the fields and options.  Fields are different from options in
        that we bother to decode these into more usable data types like
        integers rather than keeping them as raw byte strings.  Fields are also
        required to exist, unlike options which may not.

        Each option is encoded as a tuple <option number, length, data> where
        option number is a byte indicating the type of option, length indicates
        the number of bytes in the data for option, and data is a length array
        of bytes.  The only exceptions to this rule are the 0 and 255 options,
        which have 0 data length, and no length byte.  These tuples are then
        simply appended to each other.  This encoding is the same as the BOOTP
        vendor extention field encoding.
        """
        super(DhcpPacket, self).__init__()
        self._options = {}
        self._fields = {}
        if byte_str is None:
            return
        if len(byte_str) < OPTIONS_START_OFFSET + 1:
            logging.error("Invalid byte string for packet.")
            return
        for field in DHCP_PACKET_FIELDS:
            self._fields[field] = field.unpack(byte_str[field.offset :
                                                        field.offset +
                                                        field.size])
        offset = OPTIONS_START_OFFSET
        while offset < len(byte_str) and ord(byte_str[offset]) != OPTION_END:
            data_type = ord(byte_str[offset])
            offset += 1
            if data_type == OPTION_PAD:
                continue
            data_length = ord(byte_str[offset])
            offset += 1
            data = byte_str[offset: offset + data_length]
            offset += data_length
            option = get_dhcp_option_by_number(data_type)
            if option is None:
                logging.warning("Unsupported DHCP option found.  "
                                "Option number: %d" % data_type)
                continue
            option_value = option.unpack(data)
            if option == OPTION_PARAMETER_REQUEST_LIST:
                logging.info("Requested options: %s" % str(option_value))
            self._options[option] = option_value

    @property
    def client_hw_address(self):
        return self._fields.get(FIELD_CLIENT_HWADDR)

    @property
    def is_valid(self):
        """
        Checks that we have (at a minimum) values for all the fields, and that
        the magic cookie is set correctly.
        """
        for field in DHCP_PACKET_FIELDS:
            if self._fields.get(field) is None:
                logging.warning("Missing field %s in packet." % field)
                return False
        if self._fields[FIELD_MAGIC_COOKIE] != FIELD_VALUE_MAGIC_COOKIE:
            return False
        return True

    @property
    def message_type(self):
        return self._options.get(OPTION_DHCP_MESSAGE_TYPE,
                                 OPTION_VALUE_DHCP_MESSAGE_TYPE_UNKNOWN)

    @property
    def transaction_id(self):
        return self._fields.get(FIELD_TRANSACTION_ID)

    def get_field(self, field):
        return self._fields.get(field)

    def get_option(self, option):
        return self._options.get(option)

    def set_field(self, field, field_value):
        self._fields[field] = field_value

    def set_option(self, option, option_value):
        self._options[option] = option_value

    def to_binary_string(self):
        if not self.is_valid:
            return None
        # A list of byte strings to be joined into a single string at the end.
        data = []
        offset = 0
        for field in DHCP_PACKET_FIELDS:
            field_data = field.pack(self._fields[field])
            while offset < field.offset:
                # This should only happen when we're padding the fields because
                # we're not filling in legacy BOOTP stuff.
                data.append("\x00")
                offset += 1
            data.append(field_data)
            offset += field.size
        # Last field processed is the magic cookie, so we're ready for options.
        # Have to process options
        for option in DHCP_PACKET_OPTIONS:
            option_value = self._options.get(option)
            if option_value is None:
                continue
            seriallized_value = option.pack(option_value)
            data.append(struct.pack("BB",
                                    option.number,
                                    len(seriallized_value)))
            offset += 2
            data.append(seriallized_value)
            offset += len(seriallized_value)
        data.append(chr(OPTION_END))
        offset += 1
        while offset < DHCP_MIN_PACKET_SIZE:
            data.append(chr(OPTION_PAD))
            offset += 1
        return "".join(data)

    def __str__(self):
        options = [k.name + "=" + str(v) for k, v in self._options.items()]
        fields = [k.name + "=" + str(v) for k, v in self._fields.items()]
        return "<DhcpPacket fields=%s, options=%s>" % (fields, options)
