/*
 * packet.h
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#ifndef PACKET_H_
#define PACKET_H_

#include "Arduino.h"
#include "crc/Crc.h"

typedef unsigned char uchar;

#define MAX_DATA_SIZE 20
#define MAX_PACKET_SIZE 8+MAX_DATA_SIZE+1 // Take care do not exceed 255 chars
#define EOM (unsigned char)0xff
#define PACKET_TIMEOUT 100 // millis

class Packet {
public:
	uchar source;
	uchar dest;
    unsigned short packet_id;
    uchar length;
    char data[MAX_DATA_SIZE];
    unsigned short crc;
    uchar retry;
    unsigned long timeout;

    Packet();
    Packet(uchar source, uchar dest, const char* data);
    Packet(uchar source, uchar dest, const char* data, unsigned short packet_id);
	virtual ~Packet() {};
	bool validate();
	Packet* deserialize(const char*);
	char* serialize(char* msg);

private:
	short id_calculate();
	unsigned long crc_calculate();
};

#endif /* PACKET_H_ */
