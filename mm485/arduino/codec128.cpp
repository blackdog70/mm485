#include "codec128.h"

int enc128(char* buf, const char* data, char size) {
    char n = 0;
    int buf_idx = 0;
    char lsb;
    char msb = 0;
    for (int c = 0; c < size; c++) {
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

int dec128(char* buf, const char* data, char size) {
    char n = 1;
    int buf_idx = 0;
    char lsb = data[0];
    char msb;
    for (int c = 1; c < size; c++) {
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
    if (lsb != 0)
        buf[buf_idx++] = lsb;
    return buf_idx;
}
