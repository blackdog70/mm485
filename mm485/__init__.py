# coding: utf-8
import time
import threading
import logging
import logging.config

# import serial
# from serial.threaded import Packetizer, ReaderThread
# from _ast import mod

from PyCRC.CRC16 import CRC16

MAX_RETRY = 3
RETRY_DELAY = 0.1
MAX_WAIT = 0.3
RAND_WAIT = 10
PACKET_SEND = 1
PACKET_READY = 2
PACKET_TIMEOUT = 2
MAX_QUEUE_OUT_LEN = 13
MAX_QUEUE_IN_LEN = 10
MAX_DATA_SIZE = 10
TX_DELAY = 2  # milliseconds
RX_DELAY = 2  # milliseconds
MAX_PACKET_SIZE = 10 + MAX_DATA_SIZE + 1

# QUERY: COMMAND > COMMAND_PATTERN
# ANSWER: COMMAND <= COMMAND_PATTERN
COMMAND_PATTERN = 0b01111111

FORMAT = '%(asctime)-15s %(levelname)-8s [%(node)s] : %(message)s'
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


# class CRC16(object):
#     def calculate(self, data):
#         return 0

def enc128(data):
    def enc(_c, _n, _msb):
        _lsb = ((_c << _n) | _msb) & 127
        _msb = _c >> (7 - _n)
        return _lsb, _msb

    v = []
    n = 0
    msb = 0
    for c in data:
        lsb, msb = enc(c, n, msb)
        v.append(lsb)
        if n < 7:
            n += 1
        else:
            lsb, msb = enc(msb, 0, 0)
            v.append(lsb)
            n = 1
    if msb:
        v.append(msb)
    return v


def dec128(data):
    v = []
    n = 1
    lsb = data[0]
    for c in data[1:]:
        msb = ((c << (8 - n)) | lsb) & 255
        lsb = c >> n
        if n != 0:
            v.append(msb)
        n = n + 1 if n < 7 else 0
    if lsb:
        v.append(lsb)
    return v


class Packet(object):
    ACK = b'\x7d'
    ERR = b'\x7e'
    EOP = b'\xfe'  # End of packet
    EOM = b'\xff'  # End Of message

    source = ''
    dest = ''
    packet_id = ''
    data = ''
    length = ''
    crc = ''

    def __init__(self, source=None, dest=None, data=None, packet_id=None, length=None, crc=None):
        self.retry = 0
        self.timeout = 0
        self.logextra = {'node': source}
        if source is not None and dest is not None and data is not None:
            self.source = source if isinstance(source, bytes) else bytes([source])
            self.dest = dest if isinstance(dest, bytes) else bytes([dest])
            self.data = bytearray(data, "utf-8") if isinstance(data, str) else data
            self.length = bytes([len(data)]) if length is None else bytes([length])
            self.packet_id = self.id_calculate() if packet_id is None else (
                packet_id if isinstance(packet_id, bytes) else bytes([packet_id])
            )
            self.crc = self.crc_calculate() if crc is None else crc

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.serialize() == other.serialize()

    def id_calculate(self):
        return self.crc_calculate()

    def crc_calculate(self):
        crc = 0
        try:
            crc = CRC16(modbus_flag=True).calculate(self.dest + self.length + bytes(self.data))
            crc = crc.to_bytes(2, byteorder='little')
        except Exception as e:
            logging.error("CRC error: %s", e, extra=self.logextra)
        return crc

    def validate(self):
        return self.crc == self.crc_calculate()

    def deserialize(self, msg):
        try:
            self.crc = bytes([msg[0], msg[1]])
            self.packet_id = bytes([msg[2], msg[3]])
            self.source = bytes([msg[4]])
            self.dest = bytes([msg[5]])
            self.length = bytes([msg[6]])
            self.data = msg[7:7 + self.length[0]]
            # self.data = bytes(dec128(msg[5:5 + msg[4]]))
            # self.length = bytes([len(self.data)])
            logging.debug("Deserialized packet: %s", self.__str__(), extra=self.logextra)
        except Exception as e:
            logging.error("Error deserialization of %s : %s", msg, e, extra=self.logextra)
        return self

    def serialize(self):
        return self.crc + self.packet_id + self.source + self.dest + self.length + self.data
        
    def decode(self, data):
        logging.info('Decode stream %s', data, extra=self.logextra)
        decoded = bytes(dec128(data))
        logging.debug("Decoded stream: %s", decoded, extra=self.logextra)
        return self.deserialize(decoded)
    
    def encode(self):
        serialized = self.serialize()
        logging.info('Encode stream %s', serialized, extra=self.logextra)
        encoded = bytes(enc128(serialized))
        logging.debug("Encoded stream: %s", encoded, extra=self.logextra)
        return encoded


class MM485(threading.Thread):
    TERMINATOR = Packet.EOM

    def __init__(self, node_id, port):
        super(MM485, self).__init__()
        self.state = None
        self._node_id = bytes([node_id])
        self.lock = threading.RLock()
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
        self.tx_complete = ((MAX_PACKET_SIZE / (self._port.baudrate / 1000.0 / 8.0)) + RX_DELAY) # ms
        self.logextra = {'node': node_id}

    def parse_query(self, packet):
        logging.info('Querying for %s', packet.data, extra=self.logextra)
        if packet.data == Packet.ERR:
            pass
        return Packet.ACK

    def parse_answer(self, packet):
        pass

    def parse_queue_in(self):
        """Parse input queue for queries and answers"""
        with self.lock:
            if self.queue_in:
                logging.debug("Parse queue in: %s", [str(q) for q in self.queue_in], extra=self.logextra)
            pkt_received = list(self.queue_in)
            for pkt_in in pkt_received:
                if pkt_in.data[0] <= COMMAND_PATTERN:
                    # An answer is in queue
                    logging.info('Received %s as ack', pkt_in.data, extra=self.logextra)
                    pkt_ack = [pkt_out for pkt_out in self.queue_out if pkt_in.packet_id == pkt_out.packet_id]
                    if pkt_ack:
                        logging.info('       for %s', pkt_ack[0].data, extra=self.logextra)
                        self.parse_answer(pkt_in)
                        self.queue_out.remove(pkt_ack[0])
                    else:
                        logging.info("Query not found, already answered or wrong packet??", extra=self.logextra)
                else:
                    # A query is in queue
                    data = self.parse_query(pkt_in)
                    packet = Packet(source=self._node_id,
                                    dest=pkt_in.source,
                                    data=data,
                                    packet_id=pkt_in.packet_id)
                    logging.info('Found %s', packet.data, extra=self.logextra)

                    self.write(packet)
                logging.info('Msg completed', extra=self.logextra)
                self.queue_in.remove(pkt_in)

    def parse_queue_out(self):
        """Parse output queue for packet to send"""
        with self.lock:
            if self.queue_out:
                logging.debug("Parse queue out: %s", [str(q) for q in self.queue_out], extra=self.logextra)
            if not self._port.in_waiting:
                for pkt in self.queue_out:
                    self.write(pkt)
                    pkt.timeout = time.time()
                    mdelay(2*self.tx_complete)

    def write(self, pkt):
        """Send a packet to serial port

        :param pkt: instance of packet
        :return:
        """
        msg = pkt.encode()
        logging.info("Send %s [%s]", msg, pkt.retry, extra=self.logextra)
        self._port.setRTS(False)
        mdelay(TX_DELAY)
        tx_start = time.time()
        self._port.write([len(msg)])
        self._port.write(msg)
        self._port.write([self.TERMINATOR])
        while (time.time() - tx_start) < (self.tx_complete / 1000.0):
            pass
        self._port.setRTS(True)

    def handle_data_stream(self, stream):
        """Check input data stream for validity

        :param stream: stream of data
        :return:
        """
        if stream[0] != len(stream[1:]):
            logging.info("Data stream is invalid", extra=self.logextra)
            return
        pkt = Packet().decode(stream[1:])
        logging.debug('Packet format: %s', pkt, extra=self.logextra)
        if len(self.queue_in) < MAX_QUEUE_IN_LEN:
            if pkt.validate() and pkt.dest == self._node_id:
                if pkt not in self.queue_in:
                    logging.info('Add %s to input queue', pkt, extra=self.logextra)
                    with self.lock:
                        self.queue_in.append(pkt)
                else:
                    logging.info('Packet already in queue', extra=self.logextra)
            else:
                logging.info('Packet is invalid', extra=self.logextra)
        else:
            logging.info('Input queue is full', extra=self.logextra)

    def data_received(self, data):
        """Bufferize received data, find TERMINATOR, call handle_data_stream"""
        if data:
            self.buffer.extend(data)
            logging.info("Received %s", self.buffer, extra=self.logextra)
        while self.TERMINATOR in self.buffer:
            data_stream, self.buffer = self.buffer.split(self.TERMINATOR, 1)
            self.handle_data_stream(data_stream)

    def run(self):
        while not self._stop.isSet():
            try:
                data = self._port.read(self._port.in_waiting or 1)  # blocking
                self.data_received(data)
                self.parse_queue_in()
                self.parse_queue_out()
                time.sleep(0.01)
            except Exception as e:
                # FIXME: argument must be an int, or have a fileno() method.
                logging.warning("Running error: %s", e, extra=self.logextra)
        pass

    #TODO: To be completed
    def join(self, timeout=None):
        """Stop the main thread"""
        with self.lock:
            self._stop.set()
            super(MM485, self).join(timeout)

    def send(self, dest_node_id, data, msg_id=None):
        """Push a packet on output queue"""
        if len(data) < MAX_PACKET_SIZE:
            command = ord(data[0]) if isinstance(data, str) else data[0]
            if command > COMMAND_PATTERN:
                if len(self.queue_out) < MAX_QUEUE_OUT_LEN:
                    with self.lock:
                        packet = Packet(self._node_id, dest_node_id, data, msg_id)
                        if packet not in self.queue_out:
                            self.queue_out.append(packet)
            else:
                logging.critical("Command must be query type (>%s)", COMMAND_PATTERN, extra=self.logextra)
        else:
            logging.critical("The data exceeds the maximum size of %s characters", MAX_DATA_SIZE, extra=self.logextra)

    def bus_ready(self):
        """Wait until no chars in buffer or TIMEOUT

        :return : buffer's chars number
        """
        start = time.time()
        while self._port.in_waiting != 0 and time.time() - start < MAX_WAIT:
            time.sleep(0.01)
        return self._port.in_waiting == 0

if __name__ == "__main__":
    # print(hex(CRC16().calculate(bytes([1, 6, 4, 0, 0xAC, 0x29, 0x70, 0x45]))))

    orig = [2, 1, 0x85, 0xf9, 0x03, 0x06, 0, 0x80, 0x85, 0xf9]
    enc = enc128(orig)

    print([(hex(i), chr(i)) for i in enc])
    # enc = [2, 2, 0x38, 0x48, 0x66, 0, 1, 0, 0x7C, 0x7F, 0x2D, 0x2B, 0x64, 0x21, 0x5A, 0x7F]

    dec = dec128(enc)

    print([i for i in dec])
    print([hex(i) for i in dec])
    p = Packet().deserialize(dec)
    print([hex(i) for i in p.crc_calculate()])
