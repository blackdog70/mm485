# coding: utf-8
import unittest
import serial
import binascii

from mm485 import MM485, Packet, NullPort, enc128, dec128


class TestPacket(unittest.TestCase):
    def test_crc(self):
        packet = Packet(1, 2, 'Test')
        assert packet.crc_calculate() == b'\x01\xd5'

    def test_validate(self):
        packet = Packet(1, 2, 'Test', crc=b'\x01\xd5')
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
        pkt = Packet(1, 2, 'Test', 0, crc=binascii.unhexlify(b'01') + binascii.unhexlify(b'd5'))
        assert pkt.validate()

    def test_handle_packet_duplicated(self):
        pkt = Packet(2, 1, "Test").encode()
        # msg = enc128(b'\x02\x0100\x04Test2\xd5')
        # pkt = bytes([len(msg)]) + bytes(msg) + Packet.EOM
        self.a.data_received(pkt + pkt)
        assert len(self.a.queue_in) == 1

    def test_handle_packet_wrong(self):
        msg = bytes(''.join([chr(2), chr(1), '01', chr(5), 'Test1}']), 'utf-8') + Packet.EOM
        self.a.data_received(msg)
        assert len(self.a.queue_in) == 0

    def test_serialize(self):
        pkt = Packet(1, 2, 'Test').serialize()
        self.assertEqual(pkt, b'\x01\x02\x01\xd5\x04Test\x01\xd5\xfc')

    def test_parse_queues(self):
        # Send a packet
        self.a.send(2, 'Test')

        # Prepare answer packet with same packet it
        msg = Packet(2, 1, "Test", self.a.queue_out[0].packet_id).encode()

        # Receive packet
        self.a.data_received(msg)

        # Query queues
        self.a.parse_queue_in()
        assert len(self.a.queue_in) == 0
        assert len(self.a.queue_out) == 0

    def test_double_send(self):
        pass
