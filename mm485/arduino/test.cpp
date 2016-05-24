// Do not remove the include below
#include "test.h"
#include "mm485.h"
#include "FreeMemory/FreeMemory.h"

class MyMM485 : public MM485 {
public:
	MyMM485(char node_id) : MM485(node_id) {};
	virtual ~MyMM485() {};
protected:
	char* parse_packet(char* data, Packet* pkt) {
		strcpy(data, (char *)MM485::parse_packet(data, pkt));
		if (!memcmp(pkt->data, "Ping", pkt->length))
			sprintf(data, "Pong");
		if (!memcmp(pkt->data, "MEM", pkt->length))
			sprintf(data, "%i", freeMemory());

//		Serial.print(pkt->data);
//		Serial.print("-->");
//		Serial.println(msg);

        return data;
	}
};

MyMM485 *node;
unsigned long timer;
int led = 13;

//The setup function is called once at startup of the sketch
void setup()
{
	node = new MyMM485(2);

	Serial.begin(115200);
	Serial.println("start");
	timer = millis();
	pinMode(led, OUTPUT);
}

// The loop function is called in an endless loop
void loop()
{
//	node->read();

//	Serial.println("---------");
	node->run();
	node->send(1, "Test");
	if (millis() - timer < 500)
		digitalWrite(led, HIGH);
	if (millis() - timer > 500)
		digitalWrite(led, LOW);
	if (millis() -timer > 1000)
		timer = millis();
	delay(250);
}
