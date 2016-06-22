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

#ifdef SOFTWARESERIAL
const int rx=3;
const int tx=4;
const int en485 = 2;
SoftwareSerial rs485(rx,tx);
#endif

MM485::MM485(unsigned char node_id) {
	// TODO Auto-generated constructor stub
	MM485::node_id = node_id;
	*buffer = 0;
	chr_in = buffer;
	idx_queue_in = 0;
	idx_queue_out = 0;
	for (int i=0; i<NUM_PACKET; i++)
		queue_in[i] = queue_out[i] = NULL;
}

bool MM485::find_pkt(Packet* queue[], Packet *pkt) {
	for (int i=0; i<SIZE_QUEUE; i++)
		if (pkt->crc == queue[i]->crc)
			return true;

//	Serial.println("Pkt not fnd");
	return false;
}

size_t MM485::parse_packet(unsigned char *data, Packet* pkt) {
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
				unsigned char data[MAX_DATA_SIZE];
//				unsigned char msg[MAX_PACKET_SIZE];

				size_t size = parse_packet(data, queue_in[i]);
				Packet pkt(node_id, queue_in[i]->source, queue_in[i]->packet_id, data, size);

				write(&pkt);
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
				write(queue_out[i]);
				queue_out[i]->timeout = millis();

//				Serial.print("Send o ");
			} else
				queue_out[i]->retry++;
		}
}

void MM485::write(Packet* pkt) {
	unsigned char msg[MAX_PACKET_SIZE];
	unsigned char enc[MAX_PACKET_SIZE];

	size_t size = pkt->serialize(msg);

//	Serial.println("----start-write----");
//	sprintf((char*)enc, "Size msg = %u", size);
//	Serial.println((char *)enc);
//	for(unsigned int i = 0; i< size; i++) {
//		sprintf((char*)enc, "\\x%02x", msg[i]);
//		Serial.print((char*)enc);
//	}
//	Serial.println();
//	sprintf((char*)msg, "%i", freeMemory());
//	Serial.print("Mem=");
//	Serial.println((char*)msg);

	enc[0] = enc128((unsigned char*)(enc+1), msg, size);
	enc[enc[0] + 1] = EOM;
//
//	sprintf((char*)msg, "Size enc = %u", enc[0]);
//	Serial.println((char *)msg);
//	for(int i = 0; i< enc[0] + 2; i++) {
//		sprintf((char*)msg, "\\x%02x", enc[i]);
//		Serial.print((char*)msg);
//	}
//	Serial.println();
//	Serial.println("----end--write----");

#ifdef SOFTWARESERIAL
	digitalWrite(en485, HIGH);          // Enable write on 485
	rs485.write(enc, enc[0] + 2);		// + 2 is for 1 byte for stream length and 1 byte for EOM
	rs485.flush();
	digitalWrite(en485, LOW);			// 485 listening mode
#else
	Serial.write(enc, enc[0] + 2);		// + 2 is for 1 byte for stream length and 1 byte for EOM
#endif
}

void MM485::queue_add(Packet* queue[], Packet* pkt) {
	for(unsigned int i = 0; i < SIZE_QUEUE; i++)
		if (queue[i] == NULL) {
			queue[i] = pkt;

//			char msg[10];
//
//			Serial.println("----start-queue-add----");
//			sprintf((char*)msg, "%i", freeMemory());
//			Serial.print("Mem=");
//			Serial.println(msg);
//
//			Serial.print("Add pkt ");
//			Serial.print("N =");
//			Serial.println(i);
//
//			unsigned char s[MAX_PACKET_SIZE];
//			size_t size = queue[i]->serialize(s);
//			for(unsigned int j = 0; j< size; j++) {
//				sprintf((char*)msg, "\\x%02x", s[j]);
//				Serial.print((char*)msg);
//			}
//			Serial.println();
//			sprintf(msg,"CRC = %u", queue[i]->crc);
//			Serial.println(msg);
//			Serial.println("----end-queue-add----");

			return;
		}
	delete pkt;
}

void MM485::handle_data_stream() {
	unsigned char stream[chr_in - buffer - 1]; // -1 is for EOM char

	if (buffer[0] != sizeof(stream))
		return;

	dec128(stream, (unsigned char*)(buffer+1), sizeof(stream)); // TODO: Check if it work

	Packet *pkt = new Packet();

	pkt->deserialize((const unsigned char*)stream);

//	Serial.print("Pkt rcvd:");
//	Serial.print(pkt->source);
//	Serial.print(" - ");
//	Serial.print(pkt->dest);
//	Serial.print(" - ");
//	Serial.print(pkt->length);
//	Serial.print(" - ");
//	Serial.print(" - ");
//	Serial.print(pkt->crc_calculate());
//	Serial.print(" - ");
//	Serial.print(pkt->validate());
//	Serial.print(" - ");
//	Serial.print(pkt->dest == node_id);

	if (pkt->validate() && pkt->dest == node_id && !find_pkt(queue_in, pkt)) {
//		Serial.println("Pkt ok");
		queue_add(queue_in, pkt);
	} else
		delete pkt;
}

void MM485::read() {
#ifdef SOFTWARESERIAL
	while (rs485.available() > 0 && chr_in < buffer + sizeof(buffer)) {
		*chr_in = (uint8_t)rs485.read();
#else
	while (Serial.available() > 0 && chr_in < buffer + sizeof(buffer)) {
		*chr_in = (uint8_t)Serial.read();
#endif

//		char m[10];
//		sprintf(m, "%x - %c", *chr_in, *chr_in);
//		Serial.print(m);
//		Serial.print(" - ");
//		Serial.print(*chr_in == EOM);
//		Serial.print(" - ");
//		Serial.println(chr_in > buffer);

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
		Packet *pkt = new Packet(node_id, node_dest, data, size);
		if (!find_pkt(queue_out, pkt))
			queue_add(queue_out, pkt);
		else
			delete pkt;
    }
}

bool MM485::bus_ready() {
	unsigned long start = millis();
#ifdef SOFTWARESERIAL
	while (rs485.available() > 0 && millis() - start < MAX_WAIT);
	return rs485.available() == 0;
#else
	while (Serial.available() > 0 && millis() - start < MAX_WAIT);
	return Serial.available() == 0;
#endif
}
