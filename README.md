MM485 - Multi Master RS485
--------------------------

The goal of this python module is to implement a simple multimaster protocol for RS485 network.
It is thinked to solve collisions by software, following this simple rules:

* Before that Master send a packet, the input buffer has to be empty
* For every packet sent by Master there will be a reply
* If there is no reply the Master resend the message
* Only the Master will take care for collisions

A packet is composed by:

* source: code for the master node
* destination: code for destination node
* id: identificator used to accomplish acknowledgment on message replying
* data length: bytes used by data
* data: message
* crc: crc value
* EOM: end of message