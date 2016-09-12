#include "codec128.h"

uint8_t enc128(unsigned char* buf, const unsigned char* data, uint8_t size) {
    char n = 0;
    uint8_t buf_idx = 0;
    uint16_t lsb;
    uint16_t msb = 0;

//	Serial.println("==encode==");

    for (unsigned int c = 0; c < size; c++) {
        lsb = (((data[c] & 0xff) << n) | msb) & 0x7f;
        msb = ((data[c] & 0xff) >> (7 - n)) & 0xff;
        buf[buf_idx++] = lsb;

//		Serial.print(lsb, HEX);
//		Serial.print(" ");

        if (n < 7) {
            n++;
        } else {
            lsb = msb & 0x7f;
            msb = (msb >> 7) & 0xff;
            buf[buf_idx++] = lsb;

//    		Serial.print(lsb, HEX);
//    		Serial.print(" ");

            n = 1;
        }
    }

// The following check has hungry of memory, so the calling function will add a closure byte to the data parameter.
//    if (msb || ((buf_idx + 1) < (int)((size * 1.249) + 0.5)))
	if (msb)
        buf[buf_idx++] = msb;

//	Serial.println();
//	Serial.println("==encode==");

    return buf_idx;
}

uint8_t dec128(unsigned char* buf, const unsigned char* data, uint8_t size) {
	char n = 1;
	uint8_t buf_idx = 0;
	uint16_t lsb = data[0];
	uint16_t msb;
    for (unsigned int c = 1; c < size; c++) {
        msb = (((data[c] & 0xff) << (8 - n)) | lsb) & 0xff;
        lsb = ((data[c] & 0xff) >> n) & 0xff;
        if (n != 0)
            buf[buf_idx++] = msb;
        if (n < 7)
            n++;
        else
            n = 0;
    }
    if (lsb)
        buf[buf_idx++] = lsb;
    return buf_idx;
}
