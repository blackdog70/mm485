/*
 * codec128.h
 *
 *  Created on: Jun 3, 2016
 *      Author: sebastiano
 */

#ifndef MM485_ARDUINO_CODEC128_H_
#define MM485_ARDUINO_CODEC128_H_

#include "Arduino.h"

uint8_t enc128(unsigned char* buf, const unsigned char* data, uint8_t size);
uint8_t dec128(unsigned char* buf, const unsigned char* data, uint8_t size);


#endif /* MM485_ARDUINO_CODEC128_H_ */
