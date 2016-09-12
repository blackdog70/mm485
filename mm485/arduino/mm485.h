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
#define EOP (uint8_t)0xfe				   // Used to avoid problem with enc128
#define EOM (uint8_t)0xff
// QUERY: COMMAND > COMMAND_PATTERN
// ANSWER: COMMAND <= COMMAND_PATTERN
#define COMMAND_PATTERN  0x7f

/*
 * Serial define
 */
#define NUM_PACKET 2
#define MAX_BUFFER_SIZE (NUM_PACKET*MAX_PACKET_SIZE)
#define SIZE_QUEUE 2
// #define BUS_MAX_WAIT 300UL // time in milliseconds
#define PACKET_TIMEOUT 2000UL // millis
#define TX_WAIT 1
#define RX_WAIT 1
#define TX_DELAY 5
#define PACKET_DELAY 5 // millis, in source the total delay will be PACKET_DELAY * node_id

#include <SoftwareSerial.h>

extern SoftwareSerial rs485;
extern const int en485;

struct payload {
	uint8_t code;
};

struct packet_core {
    uint16_t crc;
	uint16_t packet_id;
	uint8_t source;
	uint8_t dest;
    uint8_t data_size;
};

#define PACKET_SIZE (sizeof(packet_core) + sizeof(payload))

template< typename T >
struct Packet_egg {
	packet_core core;
    T payload;
};

struct Packet : Packet_egg<payload> {};

class MM485 {
public:
	uint8_t node_id;

	MM485(unsigned char node_id);
	virtual ~MM485() {};
	void send(uint8_t to, payload* payload, uint8_t size);
	virtual uint8_t run();

private:
	unsigned char buffer[MAX_BUFFER_SIZE];
	uint8_t* chr_in;
	Packet* packet_in;
	Packet* packet_out;
	uint8_t out_ready;
    uint8_t retry;
    unsigned long out_delay;

	void clear_buffer();

protected:
	/*
	 * fill data with a response for Packet
	 * return size of data
	 */
	virtual uint8_t parse_packet(payload *payload);
	virtual void parse_ack(Packet*) {};
	virtual uint16_t crc_calculate(Packet*);
	virtual uint16_t id_calculate(Packet*);
	virtual void write(Packet* pkt);
};

#endif /* MM485_H_ */
