/*
 * packet.h
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#ifndef PACKET_H_
#define PACKET_H_

#define MAX_DATA_SIZE 20 // Take care do not exceed 255 chars

class packet {
public:
    char source;
    char dest;
    int packet_id;
    char length;
    char data[MAX_DATA_SIZE];
    int crc;

	packet();
	virtual ~packet();
};

#endif /* PACKET_H_ */
