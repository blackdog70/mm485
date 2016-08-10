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
RETRY_DELAY = 0.05
MAX_WAIT = 0.3
RAND_WAIT = 10
PACKET_SEND = 1
PACKET_READY = 2
PACKET_TIMEOUT = 2
MAX_QUEUE_OUT_LEN = 13
MAX_QUEUE_IN_LEN = 10
MAX_DATA_SIZE = 50
MAX_PACKET_SIZE = 8 + MAX_DATA_SIZE + 1

FORMAT = '%(asctime)-15s %(levelname)-8s [%(node)s] : %(message)s'
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
    EOP = b'\xfc'  # End of packet
    ACK = b'\xfd'
    ERR = b'\xfe'
    EOM = b'\xff'  # End Of message

    source = ''
    dest = ''
    packet_id = ''
    data = ''
    length = ''
    crc = ''

    def __init__(self, source=None, dest=None, data=None, packet_id=None, length=None, crc=None):
        extra = {'node': source}
        logger = logging.getLogger(__name__)
        self.logger = logging.LoggerAdapter(logger, extra)
        self.retry = 0
        self.timeout = 0
        if source is not None and dest is not None and data is not None:
            # args = [source, dest, data, length, packet_id, crc]
            # chk_str = [isinstance(i, str) for i in args]
            # chk_bytes = [isinstance(i, bytes) for i in args]
            # if all([i[0] or i[1] for i in zip(chk_str, chk_bytes)]):
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
            crc = crc.to_bytes(2, byteorder='big')
        except Exception as e:
            self.logger.error("CRC error: %s", e)
        return crc

    def validate(self):
        return self.crc == self.crc_calculate()

    def deserialize(self, msg):
        try:
            self.source = bytes([msg[0]])
            self.dest = bytes([msg[1]])
            self.packet_id = bytes([msg[2], msg[3]])
            self.length = bytes([msg[4]])
            self.data = msg[5:5 + self.length[0]]
            # self.data = bytes(dec128(msg[5:5 + msg[4]]))
            # self.length = bytes([len(self.data)])
            self.crc = bytes([msg[-2], msg[-1]])
            logging.debug("Deserialized packet: ", self.__str__())
        except Exception as e:
            self.logger.error("Error deserialization of %s : %s", msg, e)
        return self

    def serialize(self):
        # data = bytes(enc128(self.data))
        # return self.source + self.dest + self.packet_id + bytes([len(data)]) + data + self.crc + self.EOM
        return self.source + self.dest + self.packet_id + self.length + self.data + self.crc + self.EOP
        
    def decode(self, data):
        self.logger.info('Decode stream %s', data)                
        decoded = bytes(dec128(data))[:-1]
        logging.debug("Decoded stream: %s", decoded)
        return self.deserialize(decoded)
    
    def encode(self):
        serialized = self.serialize()
        self.logger.info('Encode stream %s', serialized)
        encoded = bytes(enc128(serialized))
        logging.debug("Encoded stream: %s", encoded)
        return bytes([len(encoded)]) + encoded + Packet.EOM


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
        extra = {'node': node_id}
        logger = logging.getLogger(__name__)
        self.logger = logging.LoggerAdapter(logger, extra)
        # self.extra = {'node': node_id}

    def parse_packet(self, packet):
        self.logger.info('Querying for %s', packet.data)
        if packet.data == Packet.ERR:
            pass
        return Packet.ACK

    def parse_ack(self, packet):
        pass

    def parse_queue_in(self):
        with self.lock:
            if self.queue_in:
                self.logger.debug("Parse queue in: %s", [str(q) for q in self.queue_in])
            pkt_received = list(self.queue_in)
            for pkt_in in pkt_received:
                pkt_ack = [pkt_out for pkt_out in self.queue_out if pkt_in.packet_id == pkt_out.packet_id]
                if pkt_ack:
                    self.logger.info('Received %s as ack for %s', pkt_in.data, pkt_ack[0].data)
                    self.parse_ack(pkt_in)
                    self.queue_out.remove(pkt_ack[0])
                else:
                    data = self.parse_packet(pkt_in)
                    packet = Packet(source=self._node_id,
                                    dest=pkt_in.source,
                                    data=data,
                                    packet_id=pkt_in.packet_id)
                    self.logger.info('Found %s', packet.data)
                    self.write(packet)
                self.logger.info('Msg completed')
                self.queue_in.remove(pkt_in)

    def parse_queue_out(self):
        with self.lock:
            if self.queue_out:
                self.logger.debug("Parse queue out: %s", [str(q) for q in self.queue_out])
            for pkt in self.queue_out:
                if time.time() - pkt.timeout > PACKET_TIMEOUT:
                    if self.bus_ready():
                        self.write(pkt)
                        pkt.timeout = time.time()
                    else:
                        self.logger.info("Bus is busy")
                        pkt.retry += 1  # TODO: Test retry
                        time.sleep(RETRY_DELAY)

    def write(self, pkt):
        msg = pkt.encode()
        self.logger.info("Send %s [%s]", msg, pkt.retry)
        self._port.write(msg)

    def handle_data_stream(self, packet):
        if packet[0] != len(packet[1:]):
            self.logger.info("Data stream is invalid")
            return
        pkt = Packet().decode(packet[1:])
        self.logger.debug('Packet format: %s', pkt)
        if len(self.queue_in) < MAX_QUEUE_IN_LEN:
            if pkt.validate() and pkt.dest == self._node_id:
                if pkt not in self.queue_in:
                    self.logger.info('Add %s to input queue', pkt)
                    with self.lock:
                        self.queue_in.append(pkt)
                else:
                    self.logger.info('Packet already in queue')
            else:
                self.logger.info('Packet is invalid')
        else:
            self.logger.info('Input queue is full')

    def data_received(self, data):
        """Buffer received data, find TERMINATOR, call handle_packet"""
        if data:
            self.buffer.extend(data)
            self.logger.info("Received %s", self.buffer)
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
                self.logger.warning("Running error: %s", e)  # FIXME: argument must be an int, or have a fileno() method.
        pass

    def join(self, timeout=None):
        with self.lock:
            self._stop.set()
            super(MM485, self).join(timeout)

    def send(self, dest_node_id, data, msg_id=None):
        if len(data) < MAX_PACKET_SIZE:
            if len(self.queue_out) < MAX_QUEUE_OUT_LEN:
                with self.lock:
                    packet = Packet(self._node_id, dest_node_id, data, msg_id)
                    if packet not in self.queue_out:
                        self.queue_out.append(packet)
        else:
            self.logger.critical("The data exceeds the maximum size of %s characters", MAX_DATA_SIZE)

    # wait until no chars in buffer or TIMEOUT
    # return buffer's chars number
    def bus_ready(self):
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
