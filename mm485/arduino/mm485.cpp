/*
 * mm485.cpp
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#include "Arduino.h"
#include "mm485.h"

MM485::MM485(char node_id) {
	// TODO Auto-generated constructor stub
	MM485::node_id = node_id;
	*buffer = 0;
	chr_in = buffer;
	idx_queue_in = 0;
	idx_queue_out = 0;
	for (int i=0; i<NUM_PACKET; i++)
		queue_in[i] = queue_out[i] = NULL;
}

MM485::~MM485() {
	// TODO Auto-generated destructor stub
}

bool MM485::find_pkt(Packet* queue[], Packet *pkt) {
	for (int i=0; i<idx_queue_in; i++)
		if (pkt->crc == queue[i]->crc)
			return true;
	return false;
}

size_t MM485::parse_packet(char *data, Packet* pkt) {
	data[0] = ACK;
	return 1;
}

void MM485::parse_queue_in() {
	int idx_ack = -1;
	for(int i = 0; i < SIZE_QUEUE; i++)
		if (queue_in[i] != NULL) {

//			Serial.print("Ana pkt ");
//			char d[queue_in[i]->length];
//			memcpy(d, queue_in[i]->data, queue_in[i]->length);
//			d[queue_in[i]->length] = 0;
//			Serial.println(queue_in[i]->data);

			for(int j = 0; j < SIZE_QUEUE; j++)
				if (queue_out[j] != NULL && queue_in[i]->packet_id == queue_out[j]->packet_id)
					idx_ack = j;
			if (idx_ack >= 0) {

//				Serial.print("Del pkt ");
//				Serial.println(queue_out[idx_ack]->data);

				parse_ack(queue_in[i]);
				delete queue_out[idx_ack];
				queue_out[idx_ack] = NULL;
			} else {
				char data[MAX_DATA_SIZE];
				char msg[MAX_PACKET_SIZE];

				size_t size = parse_packet(data, queue_in[i]);
				Packet p(node_id, queue_in[i]->source, queue_in[i]->packet_id, data, size);

				size = p.serialize(msg);
				Serial.write(msg, size);

//				Serial.print(" === ");
//				Serial.print("Send ");
//				Serial.print(p.crc);
//				Serial.print(p.packet_id);
//				Serial.print(size);
//				Serial.print(" === ");
			}
			delete queue_in[i];
			queue_in[i] = NULL;
		}
}

void MM485::parse_queue_out() {
	for(int i = 0; i < SIZE_QUEUE; i++)
		if (queue_out[i] != NULL && ((millis() - queue_out[i]->timeout) > PACKET_TIMEOUT)) {
			if (bus_ready()) {
				char msg[MAX_PACKET_SIZE];

				size_t size = queue_out[i]->serialize(msg);
				Serial.write(msg, size);
				queue_out[i]->timeout = millis();

//				Serial.print("Send o ");
//				Serial.println(size);
			} else
				queue_out[i]->retry++;
		}
}

void MM485::queue_add(Packet* queue[], Packet* pkt) {
	for(unsigned int i = 0; i < SIZE_QUEUE; i++)
		if (queue[i] == NULL) {
			queue[i] = pkt;
			break;
		}

//	Serial.println("Add pkt");
//	for(unsigned int i = 0; i < SIZE_QUEUE; i++) {
//		if (queue[i] != NULL) {
//			Serial.print(i);
//			Serial.print(" - ");
//			Serial.println(queue[i]->data);
//		}
//	}
}

void MM485::handle_packet() {
	Packet *pkt = new Packet();

	pkt->deserialize((const char*)buffer);

//	Serial.print("Pkt rcvd:");
//	Serial.print(pkt->source);
//	Serial.print(" - ");
//	Serial.print(pkt->dest);
//	Serial.print(" - ");
//	Serial.print(pkt->length);
//	Serial.print(" - ");
//	Serial.print(pkt->data);
//	Serial.print(" - ");
//	Serial.print(pkt->crc_calculate());
//	Serial.print(" - ");
//	Serial.print(pkt->validate());
//	Serial.print(" - ");
//	Serial.print(pkt->dest == node_id);

	if (idx_queue_in < SIZE_QUEUE and pkt->validate() and pkt->dest == node_id) {
//		Serial.println("Pkt ok");
		if (!find_pkt(queue_in, pkt))
			queue_add(queue_in, pkt);
//			Serial.println("Pkt not fnd");
	}
}

void MM485::read() {
//	Serial.print("Len ");
//	Serial.println(strlen((char*)buffer));
	while (Serial.available() > 0 && chr_in < buffer + sizeof(buffer)) {
		*chr_in = (unsigned char)Serial.read();

//		char m[10];
//		sprintf(m, "%x - %c", *chr_in, *chr_in);
//		Serial.println(m);

		if (*chr_in == EOM) {
			handle_packet();
			buffer[0] = 0;		// Clear buffer
			chr_in = buffer;	// Reposition of pointer chr_in
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

void MM485::send(uint8_t node_dest, const char* data, size_t size) {
    if (size <= MAX_DATA_SIZE) {
		Packet *pkt = new Packet(node_id, node_dest, data, size);
		if (!find_pkt(queue_out, pkt))
			queue_add(queue_out, pkt);
    }
}

bool MM485::bus_ready() {
	unsigned long start = millis();
	while (Serial.available() > 0 && millis() - start < MAX_WAIT);
	return Serial.available() == 0;
}