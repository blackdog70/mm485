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
	source = 0;
	dest = 0;
	packet_id = 0;
	length = 0;
	data[0] = 0;
	crc = 0;
	retry = 0;
	timeout = 0;
}

Packet::Packet(uchar src, uchar dst, const char *d) {
	source = src;
	dest = dst;
	strcpy(data, d);
	length = strlen(data);
	packet_id = id_calculate();
	crc = crc_calculate();
}

Packet::Packet(uchar src, uchar dst, const char *d, unsigned short id) {
	source = src;
	dest = dst;
	strcpy(data, d);
	length = strlen(data);
	packet_id = id;
	crc = crc_calculate();
}

short Packet::id_calculate() {
	return crc_calculate();
}

unsigned long Packet::crc_calculate() {
	uchar s_len = 2+length;
	char s[s_len+1];
	char d[length+1];

	memcpy(d, data, length);
	d[length] = 0;
	sprintf(s, "%c%c%s", dest, length, d);

//	Serial.print("crc =");
//	for(unsigned int i=0; i<s_len; i++) {
//		Serial.print(" - ");
//		Serial.print(s[i], 16);
//	}
//	Serial.println();

	unsigned short crc_modbus = 0xffff;
	const char *p = s;
	for (unsigned int i=0; i<s_len; i++) {
		crc_modbus = update_crc_16(crc_modbus, *p);
		p++;
	}

    return crc_modbus;
}

bool Packet::validate() {
	return crc == crc_calculate();
}

Packet* Packet::deserialize(const char* msg) {
	source = msg[0];
	dest = msg[1];
	packet_id = ((unsigned char)msg[2] << 8) | (unsigned char)msg[3];
	length = msg[4];
	strncpy(data, &msg[5], (unsigned int)length);
	data[(int)length] = 0;
	crc = ((unsigned char)msg[5+length] << 8) | (unsigned char)msg[6+length];
	return this;
}

char* Packet::serialize(char *msg) {
//	char* msg = new char[MAX_PACKET_SIZE];
	char idh = (char)(packet_id >> 8);
	char idl = (char)(packet_id & 0xFFu);
	char crch = (char)(crc >> 8);
	char crcl = (char)(crc & 0xFFu);
	char s[length+1];

	memcpy(s, data, length);
	s[length] = 0;
	sprintf(msg, "%c%c%c%c%c%s%c%c%c", source, dest, idh, idl, length, s, crch, crcl, EOM);
	return msg;
}
