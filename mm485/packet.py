import logging

from PyCRC.CRC16 import CRC16


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
    # if msb or len(v) < round(((len(data) / 7) * 8) + 0.5):
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
        return self.crc + self.packet_id + self.source + self.dest + self.length + self.data + self.EOP

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