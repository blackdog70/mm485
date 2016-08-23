from serial import serial_for_url, rs485
import time
import struct
import logging

from mm485 import MM485, Packet, CRC16

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
    "HBT": 0x7d,
    "RAM": 0x7e,
    "PONG": 0x7f,
    0x01: "SWITCH",
    0x02: "LIGHT",
    0x03: "BINARY_OUT",
    0x04: "EMS",
    0x05: "DHT",
    0x06: "PIR",
    0x07: "LUX",
    0x7d: "HBT",
    0x7e: "RAM",
    0x7f: "PONG",
}

# TODO: Test corrispondenza valori TEST == NUMERO
# QUERIES MUST BE VALUE > 0x7f
QUERIES = {
    "PING": 0x81,
    "RESET": 0x82,
    "CONFIG": 0x88,
    "HUB": 0x89,
    "MEM": 0x90,
    "HBT": 0x9f,
    "DHT": 0xA0,
    "EMS": 0xA1,
    "BINARY_OUT": 0xA2,
    "SWITCH": 0xA3,
    "LIGHT": 0xA4,
    "PIR": 0xA5,
    "LUX": 0xA6,
    0x81: "PING",
    0x82: "RESET",
    0x88: "CONFIG",
    0x89: "HUB",
    0x90: "MEM",
    0x9f: "HBT",
    0xA0: "DHT",
    0xA1: "EMS",
    0xA2: "BYNARY_OUT",
    0xA3: "SWITCH",
    0xA4: "LIGHT",
    0xA5: "PIR",
    0xA6: "LUX",
}


class Ping(MM485):
    def parse_query(self, packet):
        msg = super(Ping, self).parse_query(packet)
        with self.lock:
            # logging.info("Parsing command %s", QUERIES[packet.data[0]])
            if packet.data[0] == QUERIES['PING']:
                print("Pong")
            if packet.data == 'Test':
                msg = 'Tested'
            if packet.data[0] == QUERIES['EMS']:  # ems
                print(packet.data[1], struct.unpack("f",packet.data[2:]))
            if packet.data[0] == QUERIES['DHT']:  # TEMP & HUM
                print("Temperatura: ", struct.unpack("h", packet.data[1:3])[0] / 10.0)
                print("Umidità: ", struct.unpack("h", packet.data[3:5])[0] / 10.0)
            if packet.data[0] == QUERIES['HBT']:
                print(packet.data)
            if packet.data[0] == QUERIES['PIR']:
                print("Pir: ", struct.unpack("h", packet.data[1:3])[0])
            if packet.data[0] == QUERIES['LUX']:
                print("Lux: ", struct.unpack("h", packet.data[1:3])[0])
        return msg

    def parse_answer(self, packet):
        # logging.info("Parsing command %s", str(ANSWERS[packet.data[0]]))
        if packet.data[0] == PARAMETERS['RAM']:
            print("RAM FREE:", struct.unpack("h", packet.data[1:3])[0])
        if packet.data[0] == PARAMETERS['PONG']:
            print("PONG")


if __name__ == '__main__':
    # ser = serial_for_url('/dev/ttyUSB0', rtscts=True, baudrate=38400)
    ser = rs485.RS485('/dev/ttyUSB0', baudrate=38400)
    # ser.rs485_mode = rs485.RS485Settings(rts_level_for_rx=True,
    #                                      rts_level_for_tx=False,
    #                                      delay_before_rx=0.01,
    #                                      delay_before_tx=0.01
    #                                      )
    a = Ping(1, ser)
    a.daemon = True
    # b.daemon = True
    a.start()
    # b.start()
    try:
        # a.send(2, b'\x89\x01') # Set HUB to 1
        # a.send(2, bytearray((CONFIG, 0, SWITCH, 0, 0)))
        # a.send(2, bytearray((CONFIG, 0, LIGHT, 0, 0, 0)))
        # a.send(2, bytearray((CONFIG, 0, SENSOR, 5)))
        # a.send(2, bytearray((QUERIES['CONFIG'], PARAMETERS['DHT'], 10)))
        # a.send(3, bytearray((QUERIES['CONFIG'], PARAMETERS['HBT'], 30)))
        # a.send(3, bytearray((QUERIES['CONFIG'], PARAMETERS['PIR'], 5)))
        # a.send(3, bytearray((QUERIES['CONFIG'], PARAMETERS['LUX'], 10)))
        # a.send(2, bytearray((QUERIES['RESET'],)))
        while True:
            a.send(3, bytearray((QUERIES['MEM'],)))
            print("Loop")
            time.sleep(2)
    except KeyboardInterrupt:
        pass
