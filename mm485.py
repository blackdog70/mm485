# coding: utf-8
import time
import threading

# import serial
# from serial.threaded import Packetizer, ReaderThread
from PyCRC.CRC16 import CRC16

MAX_RETRY = 3
MAX_WAIT = 3
RAND_WAIT = 10
ACK = b'\3'
PACKET_SEND = 1
PACKET_READY = 2
MAX_QUEUE_OUT_LEN = 3
MAX_QUEUE_IN_LEN = 2

l_hex2 = lambda value: bytearray(hex(int(value))[2:].rjust(2, '0'))


# mfrom = lambda msg: msg[:2]
# mto = lambda msg: msg[2:4]
# mmsg = lambda msg: msg[4:6]
# mlen = lambda msg: int(msg[6:8])
# mdata = lambda msg: msg[8:8+mlen(msg)]
# mcrc = lambda msg: msg[-4:]

class NullPort(object):
    is_open = True
    in_waiting = 0

    def __init__(self):
        print 'Init NullPort'

    def open(self):
        pass

    def close(self):
        pass

    def write(self, data):
        pass

    def read(self, len):
        return bytearray()


# class CRC16(object):
#     def calculate(self, data):
#         return 0

class Packet(object):
    EOM = b'\2'  # End Of Message

    source = ''
    dest = ''
    packet_id = ''
    data = ''
    length = ''
    crc = ''
    retry = 0

    def __init__(self, source=None, dest=None, data=None, packet_id=None, length=None, crc=None):
        if source is not None and dest is not None and id is not None:
            self.source = source
            self.dest = dest
            self.packet_id = self.id_calculate() if packet_id is None else packet_id
            self.data = data
            self.length = len(data) if length is None else length
            self.crc = self.crc_calculate() if crc is None else crc

    def __eq__(self, other):
        return self.serialize() == other.serialize()

    def id_calculate(self):
        return self.crc_calculate()

    def crc_calculate(self):
        crc = hex(CRC16().calculate(str(self.dest) + str(self.length) + str(self.data)))[2:]
        return crc[2:].decode('hex') + crc[:2].decode('hex')
    
    def validate(self):
        return self.crc == self.crc_calculate()

    def deserialize(self, msg):
        try:
            self.source = msg[:2]
            self.dest = msg[2:4]
            self.packet_id = msg[4:6]
            self.length = int(msg[6:8])
            self.data = msg[8:8+self.length]
            self.crc = msg[-2:]
        except Exception as e:
            return False
        else:
            return self

    def serialize(self):
        msg = '{source}{dest}{id}{len}{data}{crc}{eom}'.format(source=self.source,
                                                               dest=self.dest,
                                                               id=self.packet_id,
                                                               len=self.length,
                                                               data=self.data,
                                                               crc=self.crc,
                                                               eom=self.EOM)
        return bytearray(msg)


class MM485(threading.Thread):
    TERMINATOR = Packet.EOM

    def __init__(self, node_id, port):
        super(MM485, self).__init__()
        self.state = None
        self._node_id = l_hex2(node_id)
        self.lock = threading._RLock()
        self._port = port
        self._msg_id = 0
        self._stop = threading.Event()
        self.queue_in = []
        self.queue_out = []
        self.buffer = bytearray()
        self._msg = None
        self._msg_in = None
        self._crc_in = 0

    def parse_packet(self, packet):
        pass

    def parse_queues(self):
        pkt_received = list(self.queue_in)
        for pkt_in in pkt_received:
            pkt_ack = [pkt_out for pkt_out in self.queue_out if pkt_in.packet_id == pkt_out.packet_id][0]
            if pkt_ack:
                self.queue_out.remove(pkt_ack)
                self.queue_in.remove(pkt_in)
            else:
                self.parse_packet(pkt_in)

    def send_packets(self):
        for pkt in self.queue_out:
            if self.wait_for_bus():
                msg = pkt.serialize()
                self._port.write(msg)
            else:
                pkt.retry += 1

    def handle_packet(self, packet):
        print self._node_id, ' < ', packet
        pkt = Packet().deserialize(packet)
        if len(self.queue_in) < MAX_QUEUE_IN_LEN and pkt.validate() and pkt.dest == self._node_id:
            if pkt not in self.queue_in:
                self.queue_in.append(pkt)

    def data_received(self, data):
        """Buffer received data, find TERMINATOR, call handle_packet"""
        self.buffer.extend(data)
        while self.TERMINATOR in self.buffer:
            packet, self.buffer = self.buffer.split(self.TERMINATOR, 1)
            self.handle_packet(packet)

    def run(self):
        while not self._stop.isSet():
            try:
                data = self._port.read(self._port.in_waiting or 1)  # blocking
                self.data_received(data)
                self.parse_queues()
                self.send_packets()
                time.sleep(1)
            except Exception as e:
                print e
        pass

    def join(self, timeout=None):
        self.lock.acquire()
        self._stop.set()
        super(MM485, self).join(timeout)
        self.lock.release()

    def send(self, to, data):
        if len(self.queue_out) < MAX_QUEUE_OUT_LEN:
            packet = Packet(self._node_id, to, data)
            self.queue_out.append(packet)

    # wait until no chars in buffer or TIMEOUT
    # return buffer's chars number
    def wait_for_bus(self):
        start = time.time()
        while self._port.in_waiting != 0 and time.time() - start < MAX_WAIT:
            time.time(0.5)
        return self._port.in_waiting == 0

    # wait until packet in buffer or TIMEOUT
    # return buffer's chars number
    def wait_for_packet(self):
        start = time.time()
        while len(self.queue_in) == 0 and time.time() - start < MAX_WAIT:
            time.sleep(0.5)
        return len(self.queue_in) > 0


if __name__ == '__main__':
    p = Packet('01', '02', '01', 'Pippo')
    print p.serialize()
    #    ser = serial.serial_for_url('/dev/ttyUSB0')
    ser = NullPort()
    a = MM485('01', ser)
    #    ser = serial.serial_for_url('/dev/ttyUSB1')
    #    ser = NullPort()
    #    b = MM485('02', ser)
    a.daemon = True
    #    b.daemon = True
    #    a.start()
    msg1 = '02010105Test100' + Packet.EOM
    msg2 = '02010205Test200' + Packet.EOM
    msg3 = '02010305Test300' + Packet.EOM
    a.data_received(msg1 + msg2 + msg3)
    assert len(a.queue_in) <= MAX_QUEUE_IN_LEN
    assert a.send('02', 'test1')
    assert a.send('02', 'test2')
    assert a.send('02', 'test3')
    #    a.join(1)
    a.parse_queues()
    assert len(a.queue_in) == 0
    assert len(a.queue_out) == 1
    a.send('02', 'xxxx')
    a.parse_queues()
    assert len(a.queue_in) == 0
    assert len(a.queue_out) == 2
