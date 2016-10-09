/*
 * mm485.cpp
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#include <domunet.h>
#include "Arduino.h"
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
unsigned long BYTE_TIMING = (BAUDRATE / 1000) / 8;
unsigned long TX_COMPLETE = (unsigned int)(float(float(MAX_PACKET_SIZE) / BYTE_TIMING));
unsigned long WAIT_FOR_BUS = BYTE_TIMING * NODE_ID;

// TODO: node_id può essere eliminato in favore della costante NODE_ID
DomuNet::DomuNet(unsigned char node_id) {
	// TODO Auto-generated constructor stub
	DomuNet::node_id = node_id;
	buffer[0] = 0;
//	packet_in = (Packet*)malloc(MAX_PACKET_SIZE);
//	packet_out = (Packet*)malloc(MAX_PACKET_SIZE);
	bus_state = READY;
}

//uint8_t MM485::parse_packet(void *data) {
//	return 0;
//}

void DomuNet::write(Packet* pkt) {
	pkt->core.source = node_id;

#ifdef DEBUG
	Serial.println("Stream");
	Serial.print("Size ");
	Serial.println(sizeof(packet_core) + pkt->core.data_size);
	unsigned char *p = (uint8_t*)pkt;
	for(unsigned int i=0; i < sizeof(packet_core) + pkt->core.data_size; i++) {
		Serial.print(i);
		Serial.print(" :");
		Serial.println(*(p + i), HEX);
	}
#endif

	uint8_t size = sizeof(packet_core) + pkt->core.data_size;
	char *s = (char *)pkt;
	uint16_t chksum = ModRTU_CRC(s, size);

	digitalWrite(en485, HIGH);          			// 485 write mode
//	unsigned long tx_start = millis();  			// Used to wait for complete transmission
	rs485.write(0x08);
	rs485.write(0x70);
	rs485.write(size);
	for (uint8_t i = 0; i < size; i++)
		rs485.write(*(s+i));
	uint8_t *byte = (uint8_t *)&chksum;
	rs485.write(*byte);
	rs485.write(*(byte+1));
//	while ((millis() - tx_start) < TX_COMPLETE) {}; // wait for complete transmission
	digitalWrite(en485, LOW);						// 485 read mode

#ifdef DEBUG
//	Serial.println("Stream sent");
#endif
}

void DomuNet::clear_buffer() {
	buffer[0] = 0;		// Clear buffer
//	rs485.flush();		// Clear serial buffer
}

uint8_t DomuNet::bus_ready() {
	unsigned long start = millis();
	while ((micros() - start) < WAIT_FOR_BUS) {};
	return rs485.available() < 3;
}

uint8_t DomuNet::receive() {
	if (rs485.available() < 3)
		return 0;
#ifdef DEBUG
	Serial.print("Receiving: ");
	Serial.println(rs485.available());
#endif
	int ch = rs485.read();
	while(ch != 0x08) {
#ifdef DEBUG
		Serial.println(ch, HEX);
#endif
		if (rs485.available() < 3) {
#ifdef DEBUG
			Serial.print("0x08 Not found.");
#endif
			return 0;
		}
		ch = rs485.read();
	}
	if (rs485.read() != 0x70) {
#ifdef DEBUG
		Serial.print("0x70 Not found.");
#endif
		return 0;
	}
	uint16_t size = rs485.read();
#ifdef DEBUG
	Serial.print("Packet size: ");
	Serial.println(size);
#endif
	unsigned long timeout = millis();
	while((uint16_t)rs485.available() < size + 2) {
		if (millis() - timeout > PACKET_TIMEOUT) {
#ifdef DEBUG
			Serial.println("TIMEOUT");
#endif
			clear_buffer();
			return 0;
		}
	}
	for (uint16_t i = 0; i < size; i++)
		buffer[i] = (uint8_t)rs485.read();
#ifdef DEBUG
	Serial.println("Payload In: ");
	for(uint16_t i=0; i<size; i++) {
		Serial.print(i);
		Serial.print(" :");
		Serial.println((uint8_t)buffer[i], HEX);
	}
#endif
	uint16_t chksum;
	uint8_t *byte = (uint8_t *)&chksum;
	*byte = rs485.read();
	*(byte+1) = rs485.read();
	if (chksum!=ModRTU_CRC(buffer, size)) {
#ifdef DEBUG
		Serial.print("CRC Error.");
		Serial.println(chksum, HEX);
#endif
		clear_buffer();
		return 0;
	}
	if (buffer[1] != node_id) {
		/* If packet code is > COMMAND_PATTERN means that some other node is using the bus for a query
		 * so the bus has to be intended BUSY, otherwise the packet is a query closure and the bus has to be intended READY
		 */
		bus_state = (buffer[3] > COMMAND_PATTERN);
	#ifdef DEBUG
		Serial.print("Bus state: ");
		Serial.println(bus_state, HEX);
	#endif
		clear_buffer();
		return 0;
	}
	memcpy(&packet_in, buffer, size);
	return 1;
}

uint8_t DomuNet::send(uint8_t node_dest, void* data, uint8_t size) {
    if ((size <= MAX_DATA_SIZE) && bus_ready()) {
#ifdef DEBUG
    	Serial.println("Prepare send");
#endif
		packet_out.core.dest = node_dest;
		packet_out.core.data_size = size;
		memcpy(&packet_out.payload, data, size);
#ifdef DEBUG
		Serial.print("Size ");
		Serial.println(sizeof(packet_core) + packet_out.core.data_size);
		unsigned char *p = (uint8_t*)&packet_out;
		for(unsigned int i=0; i < sizeof(packet_core) + packet_out.core.data_size; i++) {
			Serial.print(i);
			Serial.print(" :");
			Serial.println(*(p + i), HEX);
		}
#endif
		write(&packet_out);
		unsigned long timeout = millis();
#ifdef DEBUG
		Serial.print("Timeout start: ");
		Serial.println(timeout);
#endif
		uint8_t received = 0;
		while(!received && ((millis() - timeout) <= PACKET_TIMEOUT))
			received = receive();
#ifdef DEBUG
		Serial.print("Timeout stop: ");
		Serial.println(millis());
		Serial.print("Packet sent status: ");
		Serial.println(received);
#endif
		return received;
	}
    return 0;
}

