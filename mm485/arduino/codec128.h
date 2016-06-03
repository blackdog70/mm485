/*
 * codec128.h
 *
 *  Created on: Jun 3, 2016
 *      Author: sebastiano
 */

#ifndef MM485_ARDUINO_CODEC128_H_
#define MM485_ARDUINO_CODEC128_H_

int enc128(char* buf, const char* data, char size);
int dec128(char* buf, const char* data, char size);


#endif /* MM485_ARDUINO_CODEC128_H_ */
