import serial
import time

from mm485.mm485 import MM485

class Ping(MM485):
    def parse_packet(self, packet):
        msg = super(Ping, self).parse_packet(packet)
        with self.lock:
            if packet.data == 'Ping':
                msg = 'Pong'
        return msg

    def parse_ack(self, packet):
        pass

if __name__ == '__main__':
    ser = serial.serial_for_url('/dev/ttyUSB0')
    a = Ping(1, ser)
    ser = serial.serial_for_url('/dev/ttyUSB1')
    b = Ping(2, ser)
    a.daemon = True
    b.daemon = True
    a.start()
    b.start()
    try:
        while True:
            a.send(2, 'Ping')
            # time.sleep(0.1)
    except KeyboardInterrupt:
        pass
