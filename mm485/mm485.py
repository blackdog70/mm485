# coding: utf-8
import time
import threading
import logging
import logging.config

# import serial
# from serial.threaded import Packetizer, ReaderThread
from PyCRC.CRC16 import CRC16

MAX_RETRY = 3
MAX_WAIT = 0.2
RAND_WAIT = 10
ACK = b'\3'
PACKET_SEND = 1
PACKET_READY = 2
MAX_QUEUE_OUT_LEN = 3
MAX_QUEUE_IN_LEN = 2

FORMAT = '%(asctime)-15s %(levelname)s [%(node)s] : %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT)

class NullPort(object):
    is_open = True
    in_waiting = 0

    def __init__(self):
        logging.info('Init NULL PORT')

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
    EOM = b'\255'  # End Of Message

    source = ''
    dest = ''
    packet_id = ''
    data = ''
    length = ''
    crc = ''

    def __init__(self, source=None, dest=None, data=None, packet_id=None, length=None, crc=None):
        self.retry = 0
        if source is not None and dest is not None and data is not None:
            self.source = source
            self.dest = dest
            self.packet_id = self.id_calculate() if packet_id is None else packet_id
            self.data = data
            self.length = len(data) if length is None else length
            self.crc = self.crc_calculate() if crc is None else crc

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.serialize() == other.serialize()

    def id_calculate(self):
        return self.crc_calculate()

    def crc_calculate(self):
        crc = hex(CRC16().calculate(str(self.dest) + str(self.length) + str(self.data)))[2:].rjust(4, '0')
        return crc[2:].decode('hex') + crc[:2].decode('hex')

    def validate(self):
        return self.crc == self.crc_calculate()

    def deserialize(self, msg):
        try:
            self.source = msg[0]
            self.dest = msg[1]
            self.packet_id = msg[2:4]
            self.length = msg[4]
            self.data = msg[5:5 + self.length]
            self.crc = msg[-2:]
        except Exception as e:
            pass
        return self

    def serialize(self):
        msg = '{source:c}{dest:c}{id:0>2}{len:c}{data}{crc}{eom}'.format(source=self.source,
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
        self._node_id = node_id
        self.lock = threading._RLock()
        self._port = port
        self._port.timeout = 0.1
        self._msg_id = 0
        self._stop = threading.Event()
        self.queue_in = []
        self.queue_out = []
        self.buffer = bytearray()
        self._msg = None
        self._msg_in = None
        self._crc_in = 0
        extra = {'node': node_id}
        logger = logging.getLogger(__name__)
        self.logger = logging.LoggerAdapter(logger, extra)
        self.extra = {'node': node_id}

    def parse_packet(self, packet):
        self.logger.info('Indentification for msg %s', packet.serialize())
        return 'ACK'

    def parse_queue_in(self):
        with self.lock:
            if self.queue_in:
                self.logger.debug("Parse queue in: %s", [str(q) for q in self.queue_in])
            pkt_received = list(self.queue_in)
            for pkt_in in pkt_received:
                pkt_ack = [pkt_out for pkt_out in self.queue_out if pkt_in.packet_id == pkt_out.packet_id]
                if pkt_ack:
                    self.logger.info('Received %s as ack for %s', pkt_in.serialize(), pkt_ack[0].serialize())
                    self.queue_out.remove(pkt_ack[0])
                else:
                    packet = Packet(source=self._node_id,
                                    dest=pkt_in.source,
                                    data=self.parse_packet(pkt_in),
                                    packet_id=pkt_in.packet_id)
                    self.logger.info('Found reply %s', packet.data)
                    self.write(packet)
                self.queue_in.remove(pkt_in)

    def parse_queue_out(self):
        with self.lock:
            if self.queue_out:
                self.logger.debug("Parse queue out: %s", [str(q) for q in self.queue_out])
            for pkt in self.queue_out:
                if self.wait_for_bus():
                    self.write(pkt)
                else:
                    self.logger.info("Bus is busy")
                    pkt.retry += 1  # TODO: Test retry

    def write(self, pkt):
        msg = pkt.serialize()
        self.logger.info("Send msg %s - Retry:%s", msg, pkt.retry)
        self._port.write(msg)

    def handle_packet(self, packet):
        self.logger.info("Received msg %s", packet)
        pkt = Packet().deserialize(packet)
        if len(self.queue_in) < MAX_QUEUE_IN_LEN and pkt.validate() and pkt.dest == self._node_id:
            if pkt not in self.queue_in:
                self.logger.info('Add packet to input queue')
                with self.lock:
                    self.queue_in.append(pkt)
        else:
            self.logger.info('Packet is invalid')

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
                self.parse_queue_in()
                self.parse_queue_out()
                time.sleep(0.01)
            except Exception as e:
                print e
        pass

    def join(self, timeout=None):
        with self.lock:
            self._stop.set()
            super(MM485, self).join(timeout)

    def send(self, to, data, msg_id=None):
        if len(self.queue_out) < MAX_QUEUE_OUT_LEN:
            with self.lock:
                packet = Packet(self._node_id, to, data, msg_id)
                if packet not in self.queue_out:
                    self.queue_out.append(packet)

    # wait until no chars in buffer or TIMEOUT
    # return buffer's chars number
    def wait_for_bus(self):
        start = time.time()
        while self._port.in_waiting != 0 and time.time() - start < MAX_WAIT:
            time.sleep(0.01)
        return self._port.in_waiting == 0
