/*
 * packet.h
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#ifndef PACKET_H_
#define PACKET_H_

#include "Arduino.h"
#include <crc16.h>

#define MAX_DATA_SIZE 16
#define MAX_PACKET_SIZE 8+MAX_DATA_SIZE+1 // Take care do not exceed 254 chars 255=0xff if for EOM
#define EOP (uint8_t)0xff
#define ACK (uint8_t)0xfd
#define ERR (uint8_t)0xfe
#define EOM (uint8_t)0xff
#define PACKET_TIMEOUT 1000 // millis

class Packet {
public:
	uint8_t source;
	uint8_t dest;
	uint16_t packet_id;
    size_t length;
    unsigned char data[MAX_DATA_SIZE];
    uint16_t crc;
    uint8_t retry;
    unsigned long timeout;

    Packet();
    Packet(uint8_t source, uint8_t dest, const unsigned char* data, size_t size);
    Packet(uint8_t source, uint8_t dest, uint16_t packet_id, const unsigned char* data, size_t size);
//	virtual ~Packet() {};
	virtual ~Packet() {};
	bool validate();
	Packet* deserialize(const unsigned char* data);
	size_t serialize(unsigned char* data);

//private:
	uint16_t id_calculate();
	uint16_t crc_calculate();
};

#endif /* PACKET_H_ */
