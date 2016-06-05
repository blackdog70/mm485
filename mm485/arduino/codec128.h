/*
 * codec128.h
 *
 *  Created on: Jun 3, 2016
 *      Author: sebastiano
 */

#ifndef MM485_ARDUINO_CODEC128_H_
#define MM485_ARDUINO_CODEC128_H_

#include "Arduino.h"

int enc128(unsigned char* buf, const unsigned char* data, size_t size);
int dec128(unsigned char* buf, const unsigned char* data, size_t size);


#endif /* MM485_ARDUINO_CODEC128_H_ */
