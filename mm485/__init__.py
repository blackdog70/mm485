# coding: utf-8
import logging
import logging.config
import threading
import time

from PyCRC.CRC16 import CRC16
from docutils.nodes import paragraph

MAX_RETRY = 3
PACKET_TIMEOUT = 0.03 # seconds
TX_DELAY = 10  # milliseconds
MAX_QUEUE_OUT_LEN = 13
MAX_QUEUE_IN_LEN = 10
MAX_DATA_SIZE = 10
MAX_PACKET_SIZE = 8 + MAX_DATA_SIZE

# QUERY: COMMAND > COMMAND_PATTERN
# ANSWER: COMMAND <= COMMAND_PATTERN
COMMAND_PATTERN = 0b01111111

FORMAT = '%(asctime)-15s %(levelname)-8s [%(module)s:%(funcName)s:%(lineno)s] [%(node)s] : %(message)s'
logging.basicConfig(level=logging.WARNING, format=FORMAT)


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
        self.source = data[0] if data is not None else 0
        self.dest = data[1] if data is not None else 0
        self.size = data[2] if data is not None else 0
        self.data = data[3:] if data is not None else 0

    @staticmethod
    def _serialize(data):
        if isinstance(data, bytes) or isinstance(data, bytearray):
            ret = data
        else:
            ret = bytes([data])
        return ret

    def serialize(self):
        r = bytearray(self._serialize(self.source))
        r += self._serialize(self.dest)
        r += self._serialize(self.size)
        r += self._serialize(self.data)
        return r


class DomuNet(threading.Thread):
    READY = 0
    BUSY = 1

    def __init__(self, node_id, port):
        super(DomuNet, self).__init__()
        self.state = None
        self._node_id = node_id
        self.lock = threading.RLock()
        self.port = port
        self.port.timeout = 0.1
        self._msg_id = 0
        self._stop = threading.Event()
        self.queue_in = []
        self.queue_out = []
        self.buffer = bytearray()
        self._msg = None
        self._msg_in = None
        self._crc_in = 0
        self.bus_state = self.READY
        self.byte_timing = self.port.baudrate / 1000.0 / 8.0
        self.wait_for_bus =  self.byte_timing * self._node_id
        self.tx_complete = MAX_PACKET_SIZE / self.byte_timing  # ms
        self.logextra = {'node': node_id}

    def parse_query(self, packet):
        pass

    def CRC(self, data):
        return CRC16(modbus_flag=True).calculate(bytes(data)).to_bytes(2, byteorder='little')

    def parse_answer(self, packet):
        pass

    def parse_packet(self, pkt_in):
        data = self.parse_query(pkt_in)
        packet = Packet()
        packet.source = self._node_id
        packet.dest = pkt_in.source
        packet.data = data
        logging.info('Found %s', packet.data, extra=self.logextra)
        mdelay(TX_DELAY)
        self.write(packet)
        logging.debug("REPLY-->%s", packet.serialize(), extra=self.logextra)
        logging.info('Msg completed', extra=self.logextra)

    # TODO: Valutare necessità di gestione dei retry
    def parse_queue_out(self):
        """Parse output queue for packet to send"""
        with self.lock:
            if self.queue_out:
                logging.debug("Parse queue out: %s", [str(q) for q in self.queue_out], extra=self.logextra)
                for pkt in self.queue_out:
                    if self.bus_ready():
                        self.write(pkt)
                        logging.debug("OUT-->%s", pkt.serialize(), extra=self.logextra)
                        timeout = time.time()
                        received = None
                        while received is None and ((time.time() - timeout) <= PACKET_TIMEOUT):
                            received = self.receive()
                        if received:
                            received = Packet(received)
                            logging.info('Received %s as ack', received.data, extra=self.logextra)
                            self.parse_answer(received)
                            self.queue_out.remove(pkt)
                        else:
                            logging.info('Timeout!! %s', pkt.serialize(), extra=self.logextra)
                    else:
                        logging.info("Bus busy!!", extra=self.logextra)
                        break

    def receive(self):
        header_found = False
        while self.port.in_waiting >= 3 and not header_found:
            logging.debug("Looking for header: %s", self.port.in_waiting, extra=self.logextra)
            header_found = (self.port.read(2) == b'\x08\x70')
        if header_found:
            logging.debug("In waiting len: %s", self.port.in_waiting, extra=self.logextra)
            size = self.port.read()[0]
            if size:
                data = self.port.read(size)  # FIXME: A volte il pacchetto in arrivo ha source e dest OK e size = 0
                if len(data) == size:
                    crc = self.port.read() + self.port.read()
                    if crc == self.CRC(data):
                        if data[1] == self._node_id:
                            logging.debug("IN-->%s", data, extra=self.logextra)
                            return data
                        self.bus_state = (data[3] > COMMAND_PATTERN)
                        logging.debug("Bus state: %s", "BUSY" if self.bus_state else "READY", extra=self.logextra)
                    else:
                        logging.error("CRC error!!", extra=self.logextra)
                else:
                    logging.error("Size is wrong!!", extra=self.logextra)
            else:
                logging.error("Size is zero!!", extra=self.logextra)
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
        while (time.time() - tx_start) < (self.tx_complete / 1000.0):
            pass
        self.port.setRTS(True)

    def run(self):
        while not self._stop.isSet():
            try:
                # data = self._port.read(self._port.in_waiting or 1)  # blocking
                # self.data_received(data)
                packet_in = self.receive()
                if packet_in:
                    self.parse_packet(Packet(packet_in))
                else:
                    if self.bus_state == self.READY:
                        self.parse_queue_out()
                time.sleep(0.02)
            except Exception as e:
                # FIXME: argument must be an int, or have a fileno() method.
                logging.error("Running error: %s", e, extra=self.logextra)
        pass

    # TODO: To be completed
    def join(self, timeout=None):
        """Stop the main thread"""
        with self.lock:
            self._stop.set()
            super(DomuNet, self).join(timeout)

    def bus_ready(self):
        mdelay(self.wait_for_bus)
        logging.debug("Bus ready status: %s", self.port.in_waiting, extra=self.logextra)
        return self.port.in_waiting < 3

    def send(self, dest_node_id, data):
        """Push a packet on output queue"""
        if len(data) < MAX_PACKET_SIZE:
            command = ord(data[0]) if isinstance(data, str) else data[0]
            if command > COMMAND_PATTERN:
                if len(self.queue_out) < MAX_QUEUE_OUT_LEN:
                    with self.lock:
                        packet = Packet()
                        packet.source = self._node_id
                        packet.dest = dest_node_id
                        packet.data = data
                        packet.size = len(data)
                        self.queue_out.append(packet)
            else:
                logging.critical("Command must be query type (>%s)", COMMAND_PATTERN, extra=self.logextra)
        else:
            logging.critical("The data exceeds the maximum size of %s characters", MAX_DATA_SIZE, extra=self.logextra)


if __name__ == "__main__":
    a = Packet(b'\x01\x02\x03\x01\x03\x02\x01\x01')
    b = a
    print(b)
