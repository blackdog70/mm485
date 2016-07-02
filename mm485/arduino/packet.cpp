/*
 * packet.cpp
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#include "packet.h"
#include "string.h"
#include "stdio.h"

Packet::Packet() {
	clear();
}

Packet::Packet(uint8_t src, uint8_t dst, const unsigned char* d, size_t size) {
	source = src;
	dest = dst;
	length = size;
	memcpy(data, d, length);
	packet_id = id_calculate();
	crc = crc_calculate();
}

Packet::Packet(uint8_t src, uint8_t dst, uint16_t id, const unsigned char* d, size_t size) {
	source = src;
	dest = dst;
	length = size;
	memcpy(data, d, length);
	packet_id = id;
	crc = crc_calculate();
}

uint16_t Packet::id_calculate() {
	return crc_calculate();
}

uint16_t Packet::crc_calculate() {
	size_t s_len = 2+length;
	char s[s_len];

	s[0] = dest;
	s[1] = length;
	memcpy((uint8_t *)(s+2), data, length);

    return ModRTU_CRC(s, s_len);
}

bool Packet::validate() {
	return crc == crc_calculate();
}

void Packet::clear() {
	source = dest = 0;source = dest = packet_id = length = data[0] = crc = retry = timeout = 0;
}

bool Packet::is_empty() {
	return source == 0 && dest == 0;
}

Packet* Packet::deserialize(const unsigned char* msg) {
	source = msg[0];
	dest = msg[1];
	packet_id = ((unsigned char)msg[2] << 8) | (unsigned char)msg[3];
	length = msg[4];
	memcpy(data, (char *)(msg+5), length);
	crc = ((unsigned char)msg[5+length] << 8) | (unsigned char)msg[6 + length];

	return this;
}

size_t Packet::serialize(unsigned char *msg) {
	msg[0] = source;
	msg[1] = dest;
	msg[2] = (unsigned char)((packet_id >> 8) & 0xff);
	msg[3] = (unsigned char)(packet_id & 0xff);
	msg[4] = length;
	memcpy((char *)(msg+5), data, length);
	msg[5+length] = (unsigned char)((crc >> 8) & 0xff);
	msg[6+length] = (unsigned char)(crc & 0xff);
	msg[7+length] = EOP;

	return 8+length;
}
