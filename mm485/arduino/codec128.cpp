#include "codec128.h"

int enc128(unsigned char* buf, const unsigned char* data, size_t size) {
    char n = 0;
    int buf_idx = 0;
    char lsb;
    char msb = 0;
    for (unsigned int c = 0; c < size; c++) {
    	int m = (data[c] & 255) << n;
        lsb = (m | msb) & 127;
        msb = (m << 1) >> 8;
        buf[buf_idx++] = lsb;
        if (n < 7) {
            n++;
        } else {
            buf[buf_idx++] = msb;
            msb = 0;
            n = 1;
        }
    }
    if (msb != 0)
        buf[buf_idx++] = msb;
    return buf_idx;
}

int dec128(unsigned char* buf, const unsigned char* data, size_t size) {
	char n = 1;
	int buf_idx = 0;
	char lsb = data[0];
	char msb;
    for (unsigned int c = 1; c < size; c++) {
    	int m = (data[c] & 255) << 8;
        msb = ((m >> n) | lsb) & 255;
        lsb = (m >> (8 + n));
        if (n != 0)
            buf[buf_idx++] = msb;
        if (n < 7)
            n++;
        else
            n = 0;
    }
    if (lsb != 0 || !data[size-1])
        buf[buf_idx++] = lsb;
//    if (data[size-1] == 0) TODO: TO remove after test
//    	buf[buf_idx++] = 0;  TODO: TO remove after test
    return buf_idx;
}
