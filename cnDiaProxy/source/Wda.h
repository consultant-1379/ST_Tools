#ifndef WDA_H
#define WDA_H

const long WDA_AVPS_GENERIC_LENGTH = 8;
const long WDA_SIZE = 12;

//This is the Result-Code AVP set to SUCCESS (2001)
const unsigned char WDA[] = \
{ \
	0x00, 0x00, 0x01, 0x0c, 0x40, 0x00, 0x00, 0x0c, 0x00, 0x00, 0x07, 0xd1 \
};


#endif
