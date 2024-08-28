#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include "Types.h"
#include <iostream>

#include "cnDiaProxy.h"

int topad(int len);

void ip2oct(uchar ip[4], char *ipstr);

void int2oct (char i[4], int number);

void int2oct(uchar i[4], char *intstr);

void int2hex (char *buff, int number, int size);

bool validIP(char *ip);

char read_integer ();

void clear ();

void oct2int(int *i_value, uchar i[4]);

bool fExists(char *fName);

char* getlocalhostname (char *);

//void log_message_type (int cmd_code, bool request, DIAMETER_HEADER h);

void parseBuffer (const char *buff, int read_length);

char* avp_code_desc (int avp_code, int vendor_id);

void dumpBuffer (const char *buff, int size);

void printLine (char *line);

void printChar (int octet);

int str2int (char* str);

bool confirm_message (char *text);

bool extractAVP (const char *buff, int messagelength, int code, std::string & avpValue) ;
bool extractResultCodeAVP (const char *buff, int messagelength, int & avpValue) ;
