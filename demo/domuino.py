from builtins import bytes
from struct import pack

from serial import serial_for_url, rs485
import time
import struct
import logging

from simpledude import SimpleDude
from mm485 import DomuNet

#define ACK (uint8_t)0x7d
#define ERR (uint8_t)0x7e

LOGO = [
0x08, 0x40,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xc0, 0xe0, 0xf0, 0xf8, 0xfc, 0xfe, 0xff, 0xff, 0xfe, 0xfc, 0xf8, 0xf0, 0xe0, 0xc0, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xc0, 0xe0, 0xf0, 0xf8, 0xfc, 0xfe, 0xff, 0xff, 0xff, 0xbf, 0x5f, 0x5f, 0x1f, 0xff, 0xff, 0xff, 0xff, 0xff, 0x1f, 0x5f, 0x1f, 0xff, 0xff, 0xff, 0xfe, 0xfc, 0xf8, 0xf0, 0xe0, 0xfc, 0xfc, 0xfc, 0xfc, 0xfc, 0xfc, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xc0, 0xe0, 0xf0, 0xf8, 0xfc, 0xfe, 0xff, 0xff, 0xff, 0xff, 0xff, 0xf8, 0x02, 0x78, 0xff, 0xff, 0x1f, 0x5f, 0x1f, 0xff, 0xfe, 0xfc, 0xf9, 0x03, 0xfd, 0xfe, 0xff, 0x1f, 0x5f, 0x1f, 0xff, 0xf8, 0x02, 0xf8, 0xff, 0x1f, 0x5f, 0x1f, 0xff, 0xff, 0xff, 0xff, 0xff, 0xf0, 0xe0, 0xc0, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xe7, 0xdb, 0xc7, 0xe6, 0xe4, 0xe1, 0xe3, 0xe0, 0xcf, 0x9f, 0x3f, 0x7f, 0xff, 0x00, 0xff, 0xff, 0xcf, 0x37, 0x87, 0xfe, 0x7c, 0x39, 0x80, 0xfd, 0xfe, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x07, 0x07, 0x07, 0x07, 0x07, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xf1, 0xf5, 0x71, 0xef, 0xdf, 0xbf, 0x77, 0xeb, 0x0b, 0xe3, 0xfe, 0xfc, 0x00, 0x9f, 0xcf, 0xe7, 0xf0, 0xf9, 0xf8, 0xfa, 0xfb, 0xfb, 0xfb, 0xfb, 0xf1, 0xed, 0xf1, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1f, 0x1f, 0x1f, 0x1f, 0x1f, 0x1f, 0x1f, 0x1f, 0x18, 0x1a, 0x18, 0x1d, 0x1d, 0x1d, 0x1c, 0x1c, 0x1b, 0x17, 0x2f, 0x00, 0x07, 0x13, 0x19, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x18, 0x1b, 0x1c, 0x1f, 0x1f, 0x1f, 0x1f, 0x1f, 0x1f, 0x1f, 0x1f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]

# TODO: Test corrispondenza valori TEST == NUMERO
# PARAMETERS MUST BE VALUE <= 0x7f
PARAMETERS = {
    "SWITCH": 0x01,
    "LIGHT": 0x02,
    "BINARY_OUT": 0x03,
    "EMS": 0x04,
    "DHT": 0x05,
    "PIR": 0x06,
    "LUX": 0x07,
    "START": 0x7a,
    "HBT": 0x7b,
    "RAM": 0x7c,
    "PONG": 0x7d,
    "ACK": 0x7e,
    "ERR": 0x7f,
    0x01: "SWITCH",
    0x02: "LIGHT",
    0x03: "BINARY_OUT",
    0x04: "EMS",
    0x05: "DHT",
    0x06: "PIR",
    0x07: "LUX",
    0x7a: "START",
    0x7b: "HBT",
    0x7c: "RAM",
    0x7d: "PONG",
    0x7e: "ACK",
    0x7f: "ERR",
}

ANSWERS = PARAMETERS

# TODO: Test corrispondenza valori TEST == NUMERO
# QUERIES MUST BE VALUE > 0x7f
QUERIES = {
    "START": 0x80,
    "PING": 0x81,
    "RESET": 0x82,
    "STANDBY": 0x83,
    "RUN": 0x84,
    "CONFIG": 0x88,
    "HUB": 0x89,
    "LCDWRITE": 0x93,
    "LCDPRINT": 0x92,
    "LCDCLEAR": 0x91,
    "MEM": 0x90,
    "HBT": 0x9f,
    "DHT": 0xA0,
    "EMS": 0xA1,
    "BINARY_OUT": 0xA2,
    "SWITCH": 0xA3,
    "LIGHT": 0xA4,
    "PIR": 0xA5,
    "LUX": 0xA6,
    0x80: "START",
    0x81: "PING",
    0x82: "RESET",
    0x83: "STANDBY",
    0x84: "RUN",
    0x88: "CONFIG",
    0x89: "HUB",
    0x90: "MEM",
    0x91: "LCDCLEAR",
    0x92: "LCDPRINT",
    0x93: "LCDWRITE",
    0x9f: "HBT",
    0xA0: "DHT",
    0xA1: "EMS",
    0xA2: "BYNARY_OUT",
    0xA3: "SWITCH",
    0xA4: "LIGHT",
    0xA5: "PIR",
    0xA6: "LUX",
}


class Domuino(DomuNet):
    def parse_query(self, packet):
        try:
            if packet.data[0] not in QUERIES:
                self.logger.error("Error packet: %s", packet.serialize(), extra=self.logextra)
                return 0
            msg = bytes([ANSWERS['ACK']])
            with self.lock:
                # self.logger.info("Parsing command %s", QUERIES[packet.data[0]])
                value = {'node': packet.source, 'type': QUERIES[packet.data[0]]}
                if packet.data[0] == QUERIES["MEM"]:
                    value.update({'value': struct.unpack("h", packet.data[1:3])[0]})
                elif packet.data[0] == QUERIES['EMS']:  # ems
                    value.update({'value': struct.unpack("ff", packet.data[1:])})
                elif packet.data[0] == QUERIES['DHT']:  # TEMP & HUM
                    value.update({'temperature': struct.unpack("h", packet.data[1:3])[0] / 10.0,
                                  'humidity': struct.unpack("h", packet.data[3:5])[0] / 10.0})
                elif packet.data[0] == QUERIES['PIR']:
                    value.update({'value': struct.unpack("b", packet.data[1:2])[0]})
                elif packet.data[0] == QUERIES['LUX']:
                    value.update({'value': struct.unpack("h", packet.data[1:3])[0]})
                elif packet.data[0] == QUERIES["SWITCH"]:
                    value.update({'state': list(packet.data[1:7])})
                elif packet.data[0] == QUERIES['START']:
                    pass
                elif packet.data[0] == QUERIES['WRITE']:
                    pass
        except Exception as e:
            raise e
        self.logger.info(value, extra=self.logextra)
        return msg

    def parse_answer(self, packet):
        try:
            # self.logger.info("Parsing command %s", str(ANSWERS[packet.data[0]]))
            value = {'node': packet.source, 'type': QUERIES[packet.data[0]]}
            if packet.data[0] == QUERIES["MEM"]:
                value.update({'value': struct.unpack("h", packet.data[1:3])[0]})
            elif packet.data[0] == QUERIES['PIR']:
                value.update({'value': struct.unpack("b", packet.data[1:2])[0]})
            elif packet.data[0] == QUERIES['DHT']:  # TEMP & HUM
                value.update({'temperature': struct.unpack("h", packet.data[1:3])[0] / 10.0,
                              'humidity': struct.unpack("h", packet.data[3:5])[0] / 10.0})
            elif packet.data[0] == QUERIES['EMS']:  # ems
                value.update({'value': struct.unpack("ff", packet.data[1:9])})
            elif packet.data[0] == QUERIES['LUX']:
                value.update({'value': struct.unpack("h", packet.data[1:3])[0]})
            elif packet.data[0] == QUERIES['START']:
                # value.update({'value': struct.unpack("h", packet.data[1:3])[0]})
                pass
            elif packet.data[0] == QUERIES['RESET']:
                dude = SimpleDude(ser,
                                  hexfile="/home/sebastiano/Documents/sloeber-workspace/domuino/Release/domuino.hex",
                                  mode485=True)

                time.sleep(1)
                dude.program()
                pass

            # if packet.data[0] == PARAMETERS['PONG']:
            #     print("PONG")
            self.logger.info(value, extra=self.logextra)
        except Exception as e:
            raise e

if __name__ == '__main__':
    # ser = serial_for_url('/dev/ttyUSB0', rtscts=True, baudrate=38400)
    ser = rs485.RS485('/dev/ttyUSB1', baudrate=38400, timeout=2)
    # ser.rs485_mode = rs485.RS485Settings(rts_level_for_rx=True,
    #                                      rts_level_for_tx=False,
    #                                      delay_before_rx=0.01,
    #                                      delay_before_tx=0.01
    #                                      )
    a = Domuino(1, ser)
    a.daemon = True
    # b.daemon = True
    a.start()
    # b.start()
    try:
        # a.send(2, bytearray((QUERIES["HUB"], 1))) # Set HUB to 1
        # a.send(4, bytearray((QUERIES["HUB"], 1))) # Set HUB to 1
        # a.send(4, bytearray((QUERIES["CONFIG"], PARAMETERS["BINARY_OUT"], 0, 1, 0)))
        # a.send(4, bytearray((QUERIES["CONFIG"], PARAMETERS["BINARY_OUT"], 1, 1, 0)))
        # a.send(2, bytearray((QUERIES['CONFIG'], PARAMETERS['DHT'], 10)))
        # a.send(3, bytearray((QUERIES['CONFIG'], PARAMETERS['HBT'], 30)))
        # a.send(3, bytearray((QUERIES['CONFIG'], PARAMETERS['PIR'], 1)))
        # a.send(3, bytearray((QUERIES['CONFIG'], PARAMETERS['LUX'], 2)))
        # a.send(258, bytearray((QUERIES["RESET"],)))
        # a.send(258, bytearray((QUERIES["STANDBY"],)))
        # a.send(258, bytearray((QUERIES["RUN"],)))
        # ser.setRTS(True)

        a.send(258, bytearray((QUERIES["LCDCLEAR"], )))

        data = list()
        row = 0
        col = 30
        for i, value in enumerate(LOGO[2:]):
            data.append(value)
            i += 1
            if not i % 8 and i % LOGO[1]:
                a.send(258, bytearray((QUERIES["LCDWRITE"], row, col, len(data)) + tuple(data)))
                # time.sleep(0.01)
                col += 8
                data.clear()
            if not i % LOGO[1]:
                a.send(258, bytearray((QUERIES["LCDWRITE"], row, col, len(data)) + tuple(data)))
                # time.sleep(0.01)
                row += 1
                col = 30
                data.clear()

        a.send(258, bytearray((QUERIES["LCDPRINT"], 0, 5, 0) + tuple(ord(c) for c in str("Start\0"))))
        a.send(258, bytearray((QUERIES["LCDPRINT"], 7, 0, 0) + tuple(ord(c) for c in str("Temp: \0"))))
        a.send(258, bytearray((QUERIES["LCDPRINT"], 7, 70, 0) + tuple(ord(c) for c in str("Hum: \0"))))
        count = 0
        while True: #a.is_alive():
            # a.send(258, bytearray((QUERIES["MEM"],)))
            # a.send(258, bytearray((QUERIES["LCDPRINT"], 1, 0, 0) + tuple(ord(c) for c in str("Counter-\0"))))
            a.send(258, bytearray((QUERIES["LCDPRINT"], 0, 85, 1) + tuple(ord(c) for c in str(count))))
            a.send(258, bytearray((QUERIES["LCDPRINT"], 7, 35, 0) + tuple(ord(c) for c in str(count) + " C")))
            a.send(258, bytearray((QUERIES["LCDPRINT"], 7, 100, 0) + tuple(ord(c) for c in str(count) + " %")))
            count += 1
            # a.send(2, bytearray((QUERIES["PIR"],)))
            # a.send(2, bytearray((QUERIES["DHT"],)))
            # a.send(2, bytearray((QUERIES["EMS"],)))
            # a.send(2, bytearray((QUERIES["LUX"],)))
            # a.send(3, bytearray((QUERIES['MEM'],)))
            # a.send(4, bytearray((QUERIES['MEM'],)))
            # a.send(4, bytearray((QUERIES["BINARY_OUT"], 0, 0)))
            # a.send(4, bytearray((QUERIES["BINARY_OUT"], 1, 0)))
            # time.sleep(1)
            # a.send(4, bytearray((QUERIES["BINARY_OUT"], 0, 1)))
            # a.send(4, bytearray((QUERIES["BINARY_OUT"], 1, 1)))
            # ser.setRTS(False)
            # ser.write(bytes([ord("A")]))
            # time.sleep(0.005)
            # ser.setRTS(True)
            # f = bytes()
            # f = ser.read_all()
            # if f:
            #     print([chr(c) for c in f])
            # print("Loop")
            time.sleep(1)
    except KeyboardInterrupt:
        pass
