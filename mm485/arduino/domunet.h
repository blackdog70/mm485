/*
 * mm485.h
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#ifndef MM485_H_
#define MM485_H_

//#include <packet.h>
#include "settings.h"
#include <crc16.h>

/*
 * Packet define
 */
// Full packet Size
// 2 char header
// 1 char packet len
// 1 char source
// 1 char dest
// 1 char data length
// n char data
// 2 char crc
#define MAX_DATA_SIZE 10
#define MAX_PACKET_SIZE 8+MAX_DATA_SIZE // Take care do not exceed 254 chars 255=0xff if for EOM
// QUERY: COMMAND > COMMAND_PATTERN
// ANSWER: COMMAND <= COMMAND_PATTERN
#define COMMAND_PATTERN  0x7f

/*
 * Serial define
 */
#define NUM_PACKET 1
#define MAX_BUFFER_SIZE (NUM_PACKET*MAX_PACKET_SIZE)
#define SIZE_QUEUE 2
// #define BUS_MAX_WAIT 300UL // time in milliseconds
#define PACKET_TIMEOUT 100UL // millis
#define TX_DELAY 3
//#define PACKET_DELAY 5 // millis, in source the total delay will be PACKET_DELAY * node_id
#define PACKET_DELAY 20UL // millis, in source the total delay will be PACKET_DELAY * node_id
#define BUSY 1
#define READY 0

#include <SoftwareSerial.h>

extern SoftwareSerial rs485;
extern const int en485;

struct base_payload {
	uint8_t code;
	base_payload(uint8_t c):code(c) {};
};

struct max_size_payload : base_payload {
	uint8_t data[MAX_DATA_SIZE];
	max_size_payload():base_payload(0) {};
};

struct packet_core {
	uint8_t source;
	uint8_t dest;
    uint8_t data_size;
};

struct Packet {
	packet_core core;
	max_size_payload payload;
};

class DomuNet {
public:
	uint8_t node_id;

	DomuNet(uint8_t node_id, uint32_t baudrate);
	virtual ~DomuNet() {};
	uint8_t send(uint8_t to, void* payload, uint8_t size);
//	virtual void run();
	uint8_t receive();

private:
	char buffer[MAX_BUFFER_SIZE];
	void clear_buffer();
	uint8_t bus_ready();

protected:
	Packet packet_in;
	Packet packet_out;
	uint8_t bus_state;
	uint32_t wait_for_bus;

//	virtual uint8_t parse_packet(void *payload);
	virtual void parse_ack(Packet*) {};
	virtual void write(Packet* pkt);
};

#endif /* MM485_H_ */
