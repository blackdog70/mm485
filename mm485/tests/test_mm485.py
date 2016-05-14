# coding: utf-8
import unittest
import serial
from mm485.mm485 import MM485, Packet, NullPort

class TestPacket(unittest.TestCase):

    def test_crc(self):
        packet = Packet(1, 2, 'Test')
        assert packet.crc_calculate() == '90'.decode('hex') + 'ee'.decode('hex')

    def test_validate(self):
        packet = Packet(1, 2, 'Test', crc='90'.decode('hex') + 'ee'.decode('hex'))
        assert packet.validate()

class TestMM485(unittest.TestCase):

    def setUp(self):
        # ser = serial.serial_for_url('/dev/ttyUSB0', baudrate=9600)
        ser = NullPort()
        self.a = MM485(1, ser)
        # ser = serial.serial_for_url('/dev/ttyUSB1', baudrate=9600)
        self.b = MM485(2, ser)
        # self.a.start()
        # self.b.start()

    def test_open(self):
        # assert self.a.is_alive and self.a._port.is_open == True
        # assert self.b.is_alive and self.b._port.is_open == True
        assert self.a._port.is_open == True
        assert self.b._port.is_open == True

    def test_crc(self):
        pkt = Packet(1, 2, 'Test', 0, crc='90'.decode('hex') + 'ee'.decode('hex'))
        assert pkt.validate()

    def test_handle_packet_duplicated(self):
        msg = chr(2) + chr(1) + '00' + chr(4) + 'Test' + '90'.decode('hex') + 'dd'.decode('hex') + Packet.EOM
        self.a.data_received(msg + msg)
        assert len(self.a.queue_in) == 1

    def test_handle_packet_wrong(self):
        msg = chr(2)+chr(1)+'01' + chr(5) + 'Test1}' + Packet.EOM
        self.a.data_received(msg)
        assert len(self.a.queue_in) == 0

    def test_parse_queues(self):
        # Send a packet
        self.a.send(2, 'Test')

        # Prepare answer packet with same packet it
        msg = chr(2) + chr(1) + self.a.queue_out[0].packet_id + chr(4) + 'Test00'
        crc = Packet().deserialize(bytearray(msg)).crc_calculate()
        msg = msg[:-2]
        msg += crc + Packet.EOM

        # Receive packet
        self.a.data_received(msg)

        # Query queues
        self.a.parse_queues()
        assert len(self.a.queue_in) == 0
        assert len(self.a.queue_out) == 0