/*
 * mm485.cpp
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#include "Arduino.h"
#include "mm485.h"
#include "codec128.h"

#ifdef SOFTWARESERIAL
const int rx=2;
const int tx=0;
const int en485 = 1;
SoftwareSerial rs485(rx,tx);
#endif

MM485::MM485(unsigned char node_id) {
	// TODO Auto-generated constructor stub
	MM485::node_id = node_id;
	*buffer = 0;
	chr_in = buffer;
	for (int i=0; i<NUM_PACKET; i++) {
		queue_in[i].clear();
		queue_out[i].clear();
	}
}

bool MM485::find_pkt(Packet queue[], Packet *pkt) {
	for (int i=0; i<SIZE_QUEUE; i++)
		if (pkt->crc == queue[i].crc)
			return true;
	return false;
}

size_t MM485::parse_packet(unsigned char *data, Packet* pkt) {
	data[0] = ACK;
	return 1;
}

void MM485::parse_queue_in() {
	int idx_ack = -1;
	for(int i = 0; i < SIZE_QUEUE; i++)
		if (!queue_in[i].is_empty()) {
			for(int j = 0; j < SIZE_QUEUE; j++)
				if (!queue_out[j].is_empty() && queue_in[i].packet_id == queue_out[j].packet_id)
					idx_ack = j;
			if (idx_ack >= 0) {
				parse_ack(&queue_in[i]);
				queue_out[idx_ack].clear();
			} else {
				unsigned char data[MAX_DATA_SIZE];

				size_t size = parse_packet(data, &queue_in[i]);
				Packet pkt(node_id, queue_in[i].source, queue_in[i].packet_id, data, size);

				write(&pkt);
			}
			queue_in[i].clear();
		}
}

void MM485::parse_queue_out() {
	for(int i = 0; i < SIZE_QUEUE; i++)
		if (!queue_out[i].is_empty() && ((millis() - queue_out[i].timeout) > PACKET_TIMEOUT)) {
			if (bus_ready()) {
				write(&queue_out[i]);
				queue_out[i].timeout = millis();
			} else
				queue_out[i].retry++;
		}
}

void MM485::write(Packet* pkt) {
	unsigned char msg[MAX_PACKET_SIZE];
	uint8_t enc[MAX_PACKET_SIZE];
	size_t size = pkt->serialize(msg);

	enc[0] = enc128((unsigned char*)(enc+1), msg, size);
	enc[enc[0] + 1] = EOM;

#ifdef SOFTWARESERIAL
	digitalWrite(en485, HIGH);          // Enable write on 485
	size = enc[0] + 2;					// + 2 is for 1 byte for stream length and 1 byte for EOM
	uint8_t* buffer = enc;
	while(size--)
		rs485.write(*buffer++);
//	rs485.flush();
	digitalWrite(en485, LOW);			// 485 listening mode
#else
	Serial.write(enc, enc[0] + 2);		// + 2 is for 1 byte for stream length and 1 byte for EOM
#endif
}

void MM485::queue_add(Packet queue[], Packet* pkt) {
	for(unsigned int i = 0; i < SIZE_QUEUE; i++)
		if (queue[i].is_empty()) {
			memcpy(&queue[i], pkt, sizeof(Packet));
			return;
		}
}

void MM485::handle_data_stream() {
	unsigned char stream[chr_in - buffer - 1]; // -1 is for EOM char

	if (buffer[0] != sizeof(stream))
		return;

	dec128(stream, (unsigned char*)(buffer+1), sizeof(stream)); // TODO: Check if it work

	Packet pkt;

	pkt.deserialize((const unsigned char*)stream);

	if (pkt.validate() && pkt.dest == node_id && !find_pkt(queue_in, &pkt))
		queue_add(queue_in, &pkt);
}

void MM485::read() {
#ifdef SOFTWARESERIAL
	while (rs485.available() > 0 && chr_in < buffer + sizeof(buffer)) {
		*chr_in = (uint8_t)rs485.read();
#else
	while (Serial.available() > 0 && chr_in < buffer + sizeof(buffer)) {
		*chr_in = (uint8_t)Serial.read();
#endif

		if (*chr_in == EOM && chr_in > buffer) {
			handle_data_stream();
			buffer[0] = 0;		// Clear buffer
			chr_in = buffer;	// Repositioning of pointer chr_in
		} else {
			chr_in++;
		}
	}
}

void MM485::run() {
	read();
	parse_queue_in();
	parse_queue_out();
}

void MM485::send(uint8_t node_dest, const unsigned char* data, size_t size) {
    if (size <= MAX_DATA_SIZE) {
		Packet pkt(node_id, node_dest, data, size);
		if (!find_pkt(queue_out, &pkt))
			queue_add(queue_out, &pkt);
    }
}

bool MM485::bus_ready() {
	unsigned long start = millis();
#ifdef SOFTWARESERIAL
	while (rs485.available() > 0 && millis() - start < BUS_MAX_WAIT);
	return rs485.available() == 0;
#else
	while (Serial.available() > 0 && millis() - start < BUS_MAX_WAIT);
	return Serial.available() == 0;
#endif
}
