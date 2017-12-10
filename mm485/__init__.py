# coding: utf-8
import logging
import logging.config
import struct
import threading
import time
from struct import pack

from PyCRC.CRC16 import CRC16
# from docutils.nodes import paragraph
# from twisted.application.internet import _ReconnectingProtocolProxy
# from __builtin__ import len

MAX_RETRY = 3
PACKET_TIMEOUT = 1  # seconds
TX_DELAY = 10  # milliseconds
MAX_QUEUE_OUT_LEN = 250  # 13
MAX_QUEUE_IN_LEN = 10
MAX_DATA_SIZE = 12
MAX_PACKET_SIZE = 5 + MAX_DATA_SIZE

# QUERY: COMMAND > COMMAND_PATTERN
# ANSWER: COMMAND <= COMMAND_PATTERN
COMMAND_PATTERN = 0b01111111

FORMAT = '%(asctime)-15s %(levelname)-8s [%(module)s:%(funcName)s:%(lineno)s] [%(node)s] : %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT)


def mdelay(value):
    """ Delay in milliseconds"""
    if value > 200:
        raise BaseException("{} too long for udelay. Max value accepted is 200!".format(value))
    start = time.time()
    while time.time() < (start + (value / 1000)):
        pass
    return time.time()


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


class Packet(object):
    def __init__(self, data=None):
        # self.source = data[0] if data is not None else 0
        # self.dest = data[1] if data is not None else 0
        # self.data = data[2:] if data is not None else 0
        self.source = struct.unpack("h", data[0:2])[0] if data is not None else 0
        self.dest = struct.unpack("h", data[2:4])[0] if data is not None else 0
        self.data = data[4:] if data is not None else 0

    @staticmethod
    def _serialize(data):
        if isinstance(data, bytes) or isinstance(data, bytearray):
            ret = data
        else:
            ret = bytes([data])
        return ret

    def serialize(self):
        r = bytearray(self._serialize(struct.pack('h', self.source)))
        r += self._serialize(struct.pack('h', self.dest))
        r += self._serialize(self.data)
        return r


class DomuNet(threading.Thread):
    def __init__(self, node_id, port):
        super(DomuNet, self).__init__()
        self.state = None
        self.node_id = node_id
        self.lock = threading.RLock()
        self.port = port
        self.port.timeout = 0.1
        self._msg_id = 0
        self._stop_domunet = threading.Event()
        self._pause_domunet = threading.Event()
        # self.queue_in = []
        self.queue_out = list()
        self.buffer = bytearray()
        self._msg = None
        self._msg_in = None
        self._crc_in = 0
        self.bus_busy = False
        self.byte_timing = 10.0 / self.port.baudrate  # 10 = 1 bit start + 8 bit data + 1 bit stop
        self.wait_for_bus = self.byte_timing * self.node_id
        self.tx_complete = MAX_PACKET_SIZE * self.byte_timing  # ms FIXME: Forse è il caso di fare una moltiplicazione anzichè una division
        self.logextra = {'node': node_id}

    def parse_query(self, packet):
        pass

    def CRC(self, data):
        return CRC16(modbus_flag=True).calculate(bytes(data)).to_bytes(2, byteorder='little')

    def parse_answer(self, packet):
        pass

    def parse_packet(self, pkt_in):
        data = self.parse_query(pkt_in)
        if data == 0:
            # don't send an answer if packet is unrecognized
            return
        packet = Packet()
        packet.source = self.node_id
        packet.dest = pkt_in.source
        packet.data = data
        logging.debug('Found %s', packet.data, extra=self.logextra)
        mdelay(TX_DELAY)
        self.write(packet)
        logging.debug("REPLY-->%s", packet.serialize(), extra=self.logextra)
        logging.debug('Msg completed', extra=self.logextra)

    # TODO: Valutare necessità di gestione dei retry
    def parse_queue_out(self):
        """Parse output queue for packet to send"""
        with self.lock:
            # return
            if self.queue_out:
                logging.debug("Parse queue out: %s", [str(q) for q in self.queue_out], extra=self.logextra)
                for pkt in list(self.queue_out):
                    if self.bus_ready():
                        self.write(pkt)
                        logging.debug("OUT-->%s", pkt.serialize(), extra=self.logextra)
                        timeout = time.time()
                        received = None
                        while not received and ((time.time() - timeout) <= PACKET_TIMEOUT):
                            received = self.receive()
                        if received:
                            received = Packet(received)
                            logging.debug('Received %s as answer', received.data, extra=self.logextra)
                            self.parse_answer(received)
                            self.queue_out.remove(pkt)
                        else:
                            self.port.flushInput()
                            raise Exception('Timeout!! {}'.format(pkt.serialize()))
                    else:
                        logging.info("Bus busy!!", extra=self.logextra)
                        break

    def receive(self):
        header_found = False
        while self.port.in_waiting >= 3 and not header_found:
            logging.debug("Looking for header: %s", self.port.in_waiting, extra=self.logextra)
            read = self.port.read(2)
            header_found = (read == b'\x08\x70')
        if header_found:
            logging.debug("In waiting len: %s", self.port.in_waiting, extra=self.logextra)
            size = self.port.read()[0]
            if size:
                data = self.port.read(size)  # FIXME: A volte il pacchetto in arrivo ha source e dest OK e size = 0
                logging.debug("IN-->%s", [hex(i) for i in data], extra=self.logextra)
                if len(data) == size:
                    crc = self.port.read(2)
                    if crc == self.CRC(data):
                        if struct.unpack("h", data[2:4])[0] == self.node_id:
                            logging.debug("IN-->%s", [hex(i) for i in data], extra=self.logextra)
                            self.bus_busy = False
                            return data
                        self.bus_busy = (data[3] > COMMAND_PATTERN)
                        logging.debug("Bus state: %s", "BUSY" if self.bus_busy else "READY", extra=self.logextra)
                    else:
                        raise Exception("CRC error!!")
                else:
                    raise Exception("Size %s is wrong!!", len(data))
            else:
                raise Exception("Size is zero!!")
        # else:
        #     logging.debug("Header not found!!", extra=self.logextra)
        return None

    # FIXME: Se troppo veloce si disallinea, perdo la risposta al messaggio in corso ed inizio ad ottenere in risposta
    # il messaggio successivo!!!
    def write(self, pkt):
        pkt = pkt.serialize()
        cksum = self.CRC(pkt)
        self.port.setRTS(False)
        tx_start = time.time()
        self.port.write(b'\x08\x70')
        self.port.write([len(pkt)])
        self.port.write(bytes(pkt))
        self.port.write(cksum)
        while (time.time() - tx_start) < self.tx_complete:
            pass
        self.port.setRTS(True)

    def run(self):
        while not self._stop_domunet.isSet():
            if not self._pause_domunet.is_set():
                try:
                    # data = self._port.read(self._port.in_waiting or 1)  # blocking
                    # self.data_received(data)
                    packet_in = self.receive()
                    if packet_in:
                        packet = Packet(packet_in)
                        self.parse_packet(packet)
                    else:
                        self.parse_queue_out()
                    time.sleep(0.05)
                except Exception as e:
                    # FIXME: argument must be an int, or have a fileno() method.
                    logging.error("Running error: %s", e, extra=self.logextra)
        pass

    def stop(self):
        """Stop the main thread"""
        with self.lock:
            self._stop_domunet.set()

    def pause(self):
        """pause the main thread"""
        with self.lock:
            self._pause_domunet.set()

    def resume(self):
        """resume the main thread"""
        with self.lock:
            self._pause_domunet.clear()


    def bus_ready(self):
        if self.bus_busy:
            return False
        mdelay(self.wait_for_bus)
        logging.debug("Bus ready status: %s", self.port.in_waiting, extra=self.logextra)
        return self.port.in_waiting  < 3

    def send(self, dest_node_id, data):
        """Push a packet on output queue"""
        if len(data) < MAX_PACKET_SIZE:
            command = ord(data[0]) if isinstance(data, str) else data[0]
            if command > COMMAND_PATTERN:
                if len(self.queue_out) < MAX_QUEUE_OUT_LEN:
                    with self.lock:
                        packet = Packet()
                        packet.source = self.node_id
                        packet.dest = dest_node_id
                        packet.data = data
                        self.queue_out.append(packet)
                else:
                    logging.critical("Queue out full", extra=self.logextra)
            else:
                logging.critical("Command must be query type (>%s)", COMMAND_PATTERN, extra=self.logextra)
        else:
            logging.critical("The data exceeds the maximum size of %s characters", MAX_DATA_SIZE, extra=self.logextra)


if __name__ == "__main__":
    a = Packet(b'\x01\x00\x02\x00\x03\x01\x03\x02\x01\x01')
    b = a
    print(b)
