/*
 * mm485.h
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#ifndef MM485_H_
#define MM485_H_

#include "packet.h"

#define NUM_PACKET 3
#define MAX_BUFFER_SIZE NUM_PACKET*MAX_PACKET_SIZE
#define SIZE_QUEUE 3
#define MAX_WAIT 10 // time in milliseconds

class MM485 {
public:
	unsigned char node_id;

	MM485(char node_id);
	virtual ~MM485();
	void send(uchar to, const char* data);
	void run();

private:
	unsigned char buffer[MAX_BUFFER_SIZE];
	unsigned char *chr_in;
	Packet* queue_in[SIZE_QUEUE];
	Packet* queue_out[SIZE_QUEUE];
	int idx_queue_in;
	int idx_queue_out;

	void handle_packet();
	void parse_queue_in();
	void parse_queue_out();
	void queue_add(Packet* queue[], Packet* pkt);
	void read();
	bool bus_ready();
	bool find_pkt(Packet* queue[], Packet *);

protected:
	virtual char* parse_packet(char *data, Packet*);
	virtual void parse_ack(Packet*) {};
};

#endif /* MM485_H_ */
