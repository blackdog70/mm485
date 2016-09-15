/*
 * mm485.cpp
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#include "Arduino.h"
#include "mm485.h"
#include "codec128.h"
#include "FreeMemory.h"

#ifdef ATTINY
	const int rx= 2; 		// Pin 7 Attiny85
	const int tx= 0;		// Pin 5 Attiny85
	const int en485 = 1;	// Pin 6 Attiny85
#else
	const int rx= 2;		// Arduino Nano
	const int tx= 3;		// Arduino Nano
	const int en485 = 4;	// Arduino Nano
#endif
SoftwareSerial rs485(rx,tx);

// FIXME: Baudrate da variabile o costante
unsigned long TX_COMPLETE = (unsigned int)(float(float(MAX_PACKET_SIZE) / ((BAUDRATE / 1000) / 8))) + RX_WAIT;

MM485::MM485(unsigned char node_id) {
	// TODO Auto-generated constructor stub
	MM485::node_id = node_id;
	*buffer = 0;
	chr_in = buffer;
	packet_in = (Packet*)malloc(PACKET_SIZE);
	packet_out = (Packet*)malloc(PACKET_SIZE);
	out_ready = 0;
	out_delay = 0;
	retry = 0;
}

uint8_t MM485::parse_packet(void *data) {
	return 0;
}

uint16_t MM485::crc_calculate(Packet* pkt) {
#ifdef DEBUG
	Serial.println("Data for CRC");
	for(int i=0; i< 2 + pkt->core.data_size; i++) {
		Serial.print(i);
		Serial.print(" :");
		Serial.println(*(&(pkt->core.dest) + i), HEX);
	}
#endif
    return ModRTU_CRC((char *)&(pkt->core.dest), 2 + pkt->core.data_size); // 4 is sizeof dest + data_size + packet_id
}

uint16_t MM485::id_calculate(Packet* pkt) {
	return crc_calculate(pkt);
}

void MM485::write(Packet* pkt) {
	unsigned char stream[sizeof(packet_core) + pkt->core.data_size + 2];    // +2 it to be sure the char allocation is enough

	pkt->core.source = node_id;
	pkt->core.crc = crc_calculate(pkt);

#ifdef DEBUG
	Serial.println("Stream");
	unsigned char *p = (uint8_t*)pkt;
	for(unsigned int i=0; i < sizeof(packet_core) + pkt->core.data_size; i++) {
		Serial.print(i);
		Serial.print(" :");
		Serial.println(*(p + i), HEX);
	}
#endif

	uint8_t size = enc128(stream,(uint8_t*)pkt, sizeof(packet_core) + pkt->core.data_size);

#ifdef DEBUG
	Serial.println("Stream encoded");
	for(int i=0; i<size; i++) {
		Serial.print(i);
		Serial.print(" :");
		Serial.println(stream[i], HEX);
	}
#endif

	digitalWrite(en485, HIGH);          			// 485 write mode
	delay(TX_WAIT);
	unsigned long tx_start = millis();  			// Used to wait for complete transmission
	rs485.write(size + 1);
	rs485.write(pkt->core.dest);
	for(int i = 0; i < size; i++)
		rs485.write(stream[i]);
	rs485.write(EOM);
	rs485.flush();
	while ((millis() - tx_start) < TX_COMPLETE) {}; // wait for complete transmission
	digitalWrite(en485, LOW);						// 485 read mode

#ifdef DEBUG
	Serial.println("Stream sent");
#endif
}

void MM485::clear_buffer() {
	buffer[0] = 0;		// Clear buffer
	chr_in = buffer;	// Repositioning of pointer chr_in
	rs485.flush();		// Clear serial buffer
}

uint8_t MM485::run() {
	if (rs485.available() > 0) {
#ifdef DEBUG
		Serial.println("Receive packet");
#endif
		while (rs485.available() > 0) {
			*chr_in = (uint8_t)rs485.read();
			if (*chr_in == EOM && chr_in > buffer) {
				uint8_t received = chr_in - buffer - 1;
				if ((buffer[0] == received) && (buffer[1] == node_id)) {
					Packet* packet = (Packet*)realloc(packet_in, received);
					if (packet != NULL) {
						packet_in = packet;
#ifdef DEBUG
							Serial.print("Received: ");
							Serial.println(received);
#endif
						dec128((unsigned char*)packet_in, (unsigned char*)(buffer + 2), received);
						if (packet_in->core.crc == crc_calculate(packet_in)) {
#ifdef DEBUG
							Serial.println("Packet OK");
#endif
							if (packet_in->payload.code <= COMMAND_PATTERN) {
#ifdef DEBUG
								Serial.print("Reply: ");
								Serial.println(packet_in->payload.code, HEX);
#endif
								// pkt is an answer
								if (packet_in->core.packet_id == packet_out->core.packet_id) {
									parse_ack(packet_in);
									out_ready = 0;								// Packet transmitted
								}
							} else {
								// pkt is a query
								unsigned char payload_[MAX_DATA_SIZE];

								memcpy(payload_, &packet_in->payload, packet_in->core.data_size);
								packet_in->core.data_size = parse_packet(&payload_);
								packet = (Packet*)realloc(packet_in, sizeof(Packet) + packet_in->core.data_size + 1);  // +1 is for EOP char added in write method
						    	if (packet != NULL) {
						    		packet_in = packet;
									packet_in->core.dest = packet_in->core.source;
									memcpy(&packet_in->payload, payload_, packet_in->core.data_size);
#ifdef DEBUG
	Serial.println("Payload");
	unsigned char *p = (uint8_t*)&(packet_in->payload);
	for(int i=0; i<packet_in->core.data_size; i++) {
		Serial.print(i);
		Serial.print(" :");
		Serial.println(*(p + i), HEX);
	}
#endif
									delay(TX_DELAY);

									write(packet_in);
								}
							}
						} else {
#ifdef DEBUG
							Serial.println("Invalid packet");
#endif
						}
					}
					if (packet == NULL) {
			    		free(packet_in);
#ifdef DEBUG
						Serial.println("Memory error!!!");
#endif
					}
				} else {
#ifdef DEBUG
					Serial.print("Invalid stream: ");
					Serial.print(buffer[0]);
					Serial.print(" != ");
					Serial.println(received);
#endif
				}
				clear_buffer();
			} else {
				if (chr_in >= buffer + sizeof(buffer)) {
					clear_buffer();
				} else
					chr_in++;
			}
		}
	} else {
		/* The message queue will be sent only if there is no incoming data.
		 * Each packet has his own timeout to avoid collisions, at start the timeout is 0 so the packet is sent immediately.
		 * If there is collisions or the network is down the packet will be resent so the timeout will have a value to delay
		 * the packet transmission in order to give a kind of priority to the messages.
		 * The node id of the device will be used to calculate the delay and drive this priority.
		 */
		if (out_ready && ((millis() - out_delay) > (PACKET_DELAY * node_id))) {
#ifdef DEBUG
			Serial.println("Send packet");
#endif
			write(packet_out);
			out_delay = millis();
			delay(2*TX_COMPLETE);
#ifdef DEBUG
			Serial.println("Packet sent");
#endif
		}
	}
	return !out_ready;
}

void MM485::send(uint8_t node_dest, void* data, uint8_t size) {
    if (size <= MAX_DATA_SIZE and !out_ready) {
    	Packet* packet = (Packet*)realloc(packet_out, sizeof(Packet) + size + 1); 	// +1 is for EOP char added in write method
    	if (packet != NULL) {
    		packet_out = packet;
			packet_out->core.dest = node_dest;
			packet_out->core.data_size = size;
			memcpy(&packet_out->payload, data, size);
			packet_out->core.packet_id = id_calculate(packet_out);
			out_ready = 1;															// packet Ready for transmission
    	} else {
    		free(packet_out);
#ifdef DEBUG
			Serial.println("Memory error!!!");
#endif
    	}
    }
}

