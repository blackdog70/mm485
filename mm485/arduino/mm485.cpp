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
#if DEBUG
	const int rx= 2;		// Arduino Nano
	const int tx= 3;		// Arduino Nano
	const int en485 = 4;	// Arduino Nano
#else
	const int rx= 2; 		// Pin 7 Attiny85
	const int tx= 0;		// Pin 5 Attiny85
	const int en485 = 1;	// Pin 6 Attiny85
#endif
SoftwareSerial rs485(rx,tx);
#endif

// FIXME: Baudrate da variabile o costante
unsigned long TX_COMPLETE = (unsigned int)(float(float(MAX_PACKET_SIZE) / ((BAUDRATE / 1000) / 8))) + RX_WAIT;

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
	return false;
}

uint8_t MM485::parse_packet(unsigned char *data, Packet* pkt) {
	data[0] = ACK;
	return 1;
}

void MM485::parse_queue_in() {
	int idx_ack = -1;
	for(int i = 0; i < SIZE_QUEUE; i++)
		if (queue_in[i] != NULL) {
		    if (queue_in[i]->data[0] <= COMMAND_PATTERN) {
#ifdef DEBUG
				Serial.print("Reply: ");
				Serial.println(queue_in[i]->data[0], HEX);
#endif
		        // pkt is an answer
                for(int j = 0; j < SIZE_QUEUE; j++)
                    if (queue_out[j] != NULL && queue_in[i]->packet_id == queue_out[j]->packet_id)
                        idx_ack = j;
                if (idx_ack >= 0) {
                    parse_ack(queue_in[i]);
                    delete queue_out[idx_ack];
                    queue_out[idx_ack] = NULL;
                }
			} else {
			    // pkt is a query
				unsigned char data[MAX_DATA_SIZE];

				uint8_t size = parse_packet(data, queue_in[i]);
				Packet pkt(node_id, queue_in[i]->source, queue_in[i]->packet_id, data, size);

				delay(TX_DELAY);

				write(&pkt);
			}
			delete queue_in[i];
			queue_in[i] = NULL;
		}
}

void MM485::parse_queue_out() {
	/* The message queue will be sent only if there is no incoming data.
	 * Each packet has his own timeout to avoid collisions, at start the timeout is 0 so the packet is sent immediately.
	 * If there is collisions or the network is down the packet will be resent so the timeout will have a value to delay
	 * the packet transmission in order to give a kind of priority to the messages.
	 * The node id of the device will be used to calculate the delay and drive this priority.
	 */
#ifdef SOFTWARESERIAL
	if (rs485.available() == 0)
#else
	if (Serial.available() == 0)
#endif
		for(int i = 0; i < SIZE_QUEUE; i++)
			if (queue_out[i] != NULL && ((millis() - queue_out[i]->timeout) > (PACKET_DELAY * node_id))) {
//			if (queue_out[i] != NULL) {
				write(queue_out[i]);
				queue_out[i]->timeout = millis();
				delay(2*TX_COMPLETE);
			}
}

void MM485::write(Packet* pkt) {
	unsigned char msg[MAX_PACKET_SIZE];
	unsigned char enc[MAX_PACKET_SIZE];

	uint8_t size = pkt->serialize(msg);

	enc[0] = enc128((unsigned char*)(enc+1), msg, size);
	enc[enc[0] + 1] = EOM;

#ifdef SOFTWARESERIAL
	size = enc[0] + 2;					// + 2 is for 1 byte for stream length and 1 byte for EOM
	uint8_t* buffer = enc;
	digitalWrite(en485, HIGH);          // Enable write on 485
	delay(TX_WAIT);
	unsigned long tx_start = millis();  // Used to wait for complete transmission
	while(size--)
		rs485.write(*buffer++);
	rs485.flush();
	while ((millis() - tx_start) < TX_COMPLETE) {}; // wait for complete transmission
	digitalWrite(en485, LOW);			// 485 listening mode
#else
	Serial.write(enc, enc[0] + 2);		// + 2 is for 1 byte for stream length and 1 byte for EOM
#endif
}

void MM485::queue_add(Packet* queue[], Packet* pkt) {
	for(unsigned int i = 0; i < SIZE_QUEUE; i++)
		if (queue[i] == NULL) {
			queue[i] = pkt;
			return;
		}
	delete pkt;
}

void MM485::handle_data_stream() {
	unsigned char stream[chr_in - buffer - 1]; // -1 is for LEN char

	if (buffer[0] != sizeof(stream)) {
#ifdef DEBUG
		Serial.print("Invalid stream: ");
		Serial.println(buffer[0]);
#endif
		return;
	}

	dec128(stream, (unsigned char*)(buffer + 1), sizeof(stream));

	Packet *pkt = new Packet();

	pkt->deserialize((const unsigned char*)stream);

	if (pkt->validate() && pkt->dest == node_id && !find_pkt(queue_in, pkt)) {
#ifdef DEBUG
		Serial.println("Packet OK");
#endif
		queue_add(queue_in, pkt);
	} else {
#ifdef DEBUG
		Serial.println("Invalid packet");
#endif
		delete pkt;
	}
}

void MM485::clear_buffer() {
	buffer[0] = 0;		// Clear buffer
	chr_in = buffer;	// Repositioning of pointer chr_in
}

void MM485::read() {
#ifdef SOFTWARESERIAL
	while (rs485.available() > 0) {
		*chr_in = (uint8_t)rs485.read();
#else
	while (Serial.available() > 0) {
		*chr_in = (uint8_t)Serial.read();
#endif
		if (*chr_in == EOM && chr_in > buffer) {
			handle_data_stream();
			clear_buffer();
		} else {
			if (chr_in >= buffer + sizeof(buffer)) {
				clear_buffer();
			} else
				chr_in++;
		}
	}
}

void MM485::run() {
	read();
	parse_queue_in();
	parse_queue_out();
}

void MM485::send(uint8_t node_dest, const unsigned char* data, uint8_t size) {
    if (size <= MAX_DATA_SIZE) {
		Packet *pkt = new Packet(node_id, node_dest, data, size);
		if (!find_pkt(queue_out, pkt))
			queue_add(queue_out, pkt);
		else
			delete pkt;
    }
}

