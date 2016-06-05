/*
 * packet.cpp
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#include "packet.h"
#include "string.h"
#include "stdio.h"
//#include "codec128.h"

Packet::Packet() {
	source = 0;
	dest = 0;
	packet_id = 0;
	length = 0;
	data[0] = 0;
	crc = 0;
	retry = 0;
	timeout = 0;
}

Packet::Packet(uint8_t src, uint8_t dst, const unsigned char* d, size_t size) {
	source = src;
	dest = dst;
	length = size;
	memcpy(data, d, length);
	packet_id = id_calculate();
	crc = crc_calculate();
}

Packet::Packet(uint8_t src, uint8_t dst, unsigned short id, const unsigned char* d, size_t size) {
	source = src;
	dest = dst;
	length = size;
	memcpy(data, d, length);
	packet_id = id;
	crc = crc_calculate();
}

short Packet::id_calculate() {
	return crc_calculate();
}

unsigned long Packet::crc_calculate() {
	uint8_t s_len = 2+length;
	char s[s_len];

	s[0] = dest;
	s[1] = length;
	memcpy((char *)(s+2), data, length);

//	Serial.print("crc=");
//	for(unsigned int i=0; i<s_len; i++) {
//		Serial.print(s[i], 16);
//		Serial.print(" ");
//	}

	unsigned short crc_modbus = 0xffff;
	const char *p = s;
	for (;p < s + s_len; p++)
		crc_modbus = update_crc_16(crc_modbus, *p);

    return crc_modbus;
}

bool Packet::validate() {
	return crc == crc_calculate();
}

Packet* Packet::deserialize(const unsigned char* msg) {
	source = msg[0];
	dest = msg[1];
	packet_id = ((unsigned char)msg[2] << 8) | (unsigned char)msg[3];
	length = msg[4];
	memcpy(data, (char *)(msg+5), length);
//	char l = msg[4];
//	length = dec128(data, (unsigned char*)(msg + 5), l);
//	data[(int)length] = 0;
	crc = ((unsigned char)msg[5+length] << 8) | (unsigned char)msg[6+length];
	return this;
}

size_t Packet::serialize(unsigned char *msg) {
	msg[0] = source;
	msg[1] = dest;
	msg[2] = (unsigned char)(packet_id >> 8);
	msg[3] = (unsigned char)(packet_id & 0xFFu);
	msg[4] = length;
	memcpy((char *)(msg+5), data, length);
//	char l = enc128((unsigned char*)(msg + 5), data, length);
//	msg[4] = l;
	msg[5+length] = (unsigned char)(crc >> 8);
	msg[6+length] = (unsigned char)(crc & 0xFFu);
//	msg[7+length] = EOM;
//	return 8+length;
	return 7+length;
}
