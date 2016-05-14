# coding: utf-8
import unittest
import serial
from mm485 import MM485, Packet, NullPort

class TestPacket(unittest.TestCase):

    def test_crc(self):
        packet = Packet('01', '02', 'Test')
        assert packet.crc_calculate() == 'a0'.decode('hex') + 'ed'.decode('hex')

    def test_validate(self):
        packet = Packet('01', '02', 'Test', crc='a0'.decode('hex') + 'ed'.decode('hex'))
        assert packet.validate()

class TestMM485(unittest.TestCase):

    def setUp(self):
        # ser = serial.serial_for_url('/dev/ttyUSB0', baudrate=9600)
        ser = NullPort()
        self.a = MM485('01', ser)
        # ser = serial.serial_for_url('/dev/ttyUSB1', baudrate=9600)
        self.b = MM485('02', ser)
        # self.a.start()
        # self.b.start()

    def test_open(self):
        # assert self.a.is_alive and self.a._port.is_open == True
        # assert self.b.is_alive and self.b._port.is_open == True
        assert self.a._port.is_open == True
        assert self.b._port.is_open == True

    def test_handle_packet_duplicated(self):
        msg = '02010105Test1}' + Packet.EOM
        self.a.data_received(msg + msg)
        assert len(self.a.queue_in) == 1

    def test_handle_packet_wrong(self):
        msg = '02010105Test100' + Packet.EOM
        self.a.data_received(msg)
        assert len(self.a.queue_in) == 0

    def test_parse_queues(self):
        # Send a packet
        self.a.send('02', 'Test')

        # Prepare answer packet with same packet it
        msg = '0201%s04Test00' % self.a.queue_out[0].packet_id
        crc = Packet().deserialize(msg).crc_calculate()
        msg = msg[:-2]
        msg += crc + Packet.EOM

        # Receive packet
        self.a.data_received(msg)

        # Query queues
        self.a.parse_queues()
        assert len(self.a.queue_in) == 0
        assert len(self.a.queue_out) == 0