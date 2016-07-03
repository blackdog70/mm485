/*
 * mm485.h
 *
 *  Created on: May 15, 2016
 *      Author: sebastiano
 */

#ifndef MM485_H_
#define MM485_H_

#define SOFTWARESERIAL

#include <packet.h>

#define NUM_PACKET 2
#define MAX_BUFFER_SIZE NUM_PACKET*MAX_PACKET_SIZE
#define SIZE_QUEUE 3
#define BUS_MAX_WAIT 300 // time in milliseconds
#define PACKET_TIMEOUT 1000 // millis
#define TX_WAIT 10
#define RX_WAIT 10
#define RETRY_WAIT 5

#ifdef SOFTWARESERIAL
#include <SoftwareSerial.h>

extern SoftwareSerial rs485;
extern const int en485;
#else
extern HardwareSerial SSerial;
#endif


class MM485 {
public:
	uint8_t node_id;

	MM485(unsigned char node_id);
	virtual ~MM485() {};
	void send(uint8_t to, const unsigned char* data, size_t size);
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

protected:
	/*
	 * fill data with a response for Packet
	 * return size of data
	 */
	virtual size_t parse_packet(unsigned char *data, Packet*);
	virtual void parse_ack(Packet*) {};
	void write(Packet* pkt);
};

#endif /* MM485_H_ */
