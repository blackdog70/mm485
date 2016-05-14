import serial
import time

from mm485.mm485 import MM485

class Ping(MM485):
    def parse_packet(self, packet):
        with self.lock:
            print self._node_id, ' received ', packet.data
            if packet.data == 'Ping':
                self.send(packet.source, 'Pong', packet.packet_id)

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
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
