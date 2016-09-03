/*
 * mm485.h
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#ifndef MM485_H_
#define MM485_H_

#include <packet.h>
#include <settings.h>

#define NUM_PACKET 2
#define MAX_BUFFER_SIZE (NUM_PACKET*MAX_PACKET_SIZE)
#define SIZE_QUEUE 2
// #define BUS_MAX_WAIT 300UL // time in milliseconds
#define PACKET_TIMEOUT 2000UL // millis
#define TX_WAIT 1
#define RX_WAIT 1
#define TX_DELAY 5
#define PACKET_DELAY 5 // millis, in source the total delay will be PACKET_DELAY * node_id


#ifdef SOFTWARESERIAL
#include <SoftwareSerial.h>

extern SoftwareSerial rs485;
extern const int en485;
#else
//extern HardwareSerial SSerial;
#endif


class MM485 {
public:
	uint8_t node_id;

	MM485(unsigned char node_id);
	virtual ~MM485() {};
	void send(uint8_t to, const unsigned char* data, uint8_t size);
	virtual void run();

private:
	unsigned char buffer[MAX_BUFFER_SIZE];
	uint8_t* chr_in;
	Packet* queue_in[SIZE_QUEUE];
	Packet* queue_out[SIZE_QUEUE];
	int idx_queue_in;
	int idx_queue_out;

	void handle_data_stream();
	void parse_queue_in();
	void parse_queue_out();
	void queue_add(Packet* queue[], Packet* pkt);
	void read();
	bool bus_ready();
	bool find_pkt(Packet* queue[], Packet *);
	void clear_buffer();

protected:
	/*
	 * fill data with a response for Packet
	 * return size of data
	 */
	virtual uint8_t parse_packet(unsigned char *data, Packet*);
	virtual void parse_ack(Packet*) {};
	void write(Packet* pkt);
};

#endif /* MM485_H_ */
