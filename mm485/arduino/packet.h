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
#include <settings.h>

// Full packet Size
// 1 char packet len
// 1 char source
// 1 char dest
// 2 char packet id
// 1 char data length
// n char data
// 2 char crc
// 1 char EOM
// 1 char EOP
#define MAX_DATA_SIZE 10
#define MAX_PACKET_SIZE 10+MAX_DATA_SIZE+1 // Take care do not exceed 254 chars 255=0xff if for EOM
#define ACK (uint8_t)0x7d
#define ERR (uint8_t)0x7e
#define EOP (uint8_t)0xfe
#define EOM (uint8_t)0xff
// QUERY: COMMAND > COMMAND_PATTERN
// ANSWER: COMMAND <= COMMAND_PATTERN
#define COMMAND_PATTERN  0x7f

class Packet {
public:
	uint8_t source;
	uint8_t dest;
	uint16_t packet_id;
    uint8_t length;
    unsigned char data[MAX_DATA_SIZE];
    uint16_t crc;
    uint8_t retry;
    unsigned long timeout;

    Packet();
    Packet(uint8_t source, uint8_t dest, const unsigned char* data, uint8_t size);
    Packet(uint8_t source, uint8_t dest, uint16_t packet_id, const unsigned char* data, uint8_t size);
	virtual ~Packet() {};
	bool validate();
	Packet* deserialize(const unsigned char* data);
	uint8_t serialize(unsigned char* data);
	bool is_empty();
	void clear();

//private:
	uint16_t id_calculate();
	uint16_t crc_calculate();
};

#endif /* PACKET_H_ */
