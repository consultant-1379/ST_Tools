#include "Utils.h"
#include <string.h>
#include <iostream>

#include <fstream>
#include <sstream>

//determines the bytes to be added as padding to a piece of data
int topad(int len)
{
	int i = 0;
	while(((len + i)*8) % 32)
		i++;
	return i;
}


int str2int (char* str) {
	return atoi (str);
}


void  int2oct (char i[4], int number) {
	sprintf(i,"%d", number);
}

void int2hex (char *buff, int number, int size) {
	buff[size-1] = number%256;
	for (int i = 0; i<=(size-2); i++) {
		int factor = 1;
		for (int j=0;j!=(size-1-i);factor*=256,j++);
		
		buff [i] = number/factor;
	}
}

//converts an IP address contained in a buffer into one in 4-byte format
void ip2oct(uchar ip[4], char *ipstr)
{
	char * tstr = ipstr;
	int tmp = atoi(tstr);
	ip[0] = (uchar)tmp;
	tstr = strchr(tstr,'.') + 1;

	tmp = atoi(tstr);
	ip[1] = (uchar)tmp;
	tstr = strchr(tstr,'.') + 1;

	tmp = atoi(tstr);
	ip[2] = (uchar)tmp;
	tstr = strchr(tstr,'.') + 1;

	tmp = atoi(tstr);
	ip[3] = (uchar)tmp;
}

//converts an integer expressed as text in a buffer to 4-byte format
void int2oct(uchar i[4], char *intstr)
{
	int tmp = atoi(intstr);
	i[0] = (uchar)(0xff & (tmp >> 24));
	i[1] = (uchar)(0xff & (tmp >> 16));
	i[2] = (uchar)(0xff & (tmp >> 8));
	i[3] = (uchar)(0xff & tmp);
}

//converts a 4-byte formatted integer into a integer value
void oct2int(int *i_value, uchar i[4])
{
	*i_value = 0;
	*i_value = *i_value + (int)i[0]*256*256*256;
	*i_value = *i_value + (int)i[1]*256*256;
	*i_value = *i_value + (int)i[2]*256;
	*i_value = *i_value + (int)i[3];
}


//checks if a buffer contains a valid IP address
bool validIP(char *ip)
{
    char * tmp = ip;
 
    bool result;
    for(int i=0;i<3;i++)
	if((tmp=strstr(tmp,".")) == NULL)
	    result = false;
    result = true;
    
    return result;
}

//reads an integer from the standard input
char read_integer () 
{
	int result;
	char tmp[10];
	char ch;
	
	do
	{
		ch = getchar();
	} 
	while (ch == '\n');

	sprintf(tmp,"%c",ch);
	result = atoi(tmp);
	
	ch = getchar(); //\n is extracted
	
	return result;
}

//clears the screen
void clear ()
{
#ifndef _DEBUG
	//system ("clear");
#endif
}

//gets the local name of the host where the proxy is running
char* getlocalhostname (char *name) 
{
	if (gethostname(name, 100))
	{
		name[0] = '\0';
	}
	return name;
}

//returns true if the file whose name is passed as argument exists
bool fExists(char *fName)
{ //bool fExists(char *fName)
	FILE *f;
	if((f = fopen(fName,"r")) != NULL)
	{
		fclose(f);
		return true;
	}
	return false;
} //bool fExists(char *fName)

bool extractAVP (const char *buff, int messagelength, int code, std::string & avpValue) 
{
	int ptr = DIAMETER_HEADER_LENGTH;
	bool notFound = true;
	int avp_code;
	int padded_length;
	int avp_length;
	int avp_code_pos;
        
	while ((ptr< messagelength) && notFound) {
	
		avp_code_pos = ptr;

		//extracting AVP code
		avp_code = ((buff[ptr] & 0xff)<<24) + ((buff[ptr+1] & 0xff)<<16) + 
							((buff[ptr+2] & 0xff)<<8) +(buff[ptr+3] & 0xff);
							
		ptr += 5;
		
		//extracting AVP length
		avp_length = ((buff[ptr] & 0xff)<<16) + ((buff[ptr+1] & 0xff)<<8) + (buff[ptr+2] & 0xff);
		ptr += 3;

		
		if (avp_code == code) {
		
			std::string myAVP (buff+ptr,avp_length - 8);
			avpValue = myAVP;
			notFound = false;
			
		} else {
		
			padded_length = avp_length;
		
			//if the AVP length is not multiple of length, padding applies
			if (avp_length % 4 != 0) {
				padded_length = padded_length + 4 - (avp_length % 4);
			}
		
			ptr = avp_code_pos + padded_length;
						
		}
							
	}
	
	return !notFound;
}

bool extractResultCodeAVP (const char *buff, int messagelength, int & avpValue) 
{
	int ptr = DIAMETER_HEADER_LENGTH;
	bool notFound = true;
	int avp_code;
	int padded_length;
	int avp_length;
	int avp_code_pos;
        
	while ((ptr< messagelength) && notFound) {
	
		avp_code_pos = ptr;

		//extracting AVP code
		avp_code = ((buff[ptr] & 0xff)<<24) + ((buff[ptr+1] & 0xff)<<16) + 
							((buff[ptr+2] & 0xff)<<8) +(buff[ptr+3] & 0xff);
							
		ptr += 5;
		
		//extracting AVP length
		avp_length = ((buff[ptr] & 0xff)<<16) + ((buff[ptr+1] & 0xff)<<8) + (buff[ptr+2] & 0xff);
		ptr += 3;

		
		if (avp_code == RESULTCODE_CODE) {
			avpValue = ((buff[ptr] & 0xff)<<24) + ((buff[ptr+1] & 0xff)<<16) + 
							((buff[ptr+2] & 0xff)<<8) +(buff[ptr+3] & 0xff);
//			printf("RESULTCODE_CODE:%d avp_length: %d\n",  avp_code, avp_length);
//			printf("RESULTCODE_CODE:%d avpValue: %d\n",  avp_code, avpValue);
			notFound = false;
			
		} 
        else if (avp_code == EXPERIMENTAL_RESULTCODE_CODE) {
        	ptr += 20;
			avpValue = ((buff[ptr] & 0xff)<<24) + ((buff[ptr+1] & 0xff)<<16) +
							((buff[ptr+2] & 0xff)<<8) +(buff[ptr+3] & 0xff);
//			printf("EXPERIMENTAL_RESULTCODE_CODE:%d avp_length: %d\n",  avp_code, avp_length);
//			printf("EXPERIMENTAL_RESULTCODE_CODE:%d avpValue: %d\n",  avp_code, avpValue);
            notFound = false;
            
        } 
        else {
		
			padded_length = avp_length;
		
			//if the AVP length is not multiple of length, padding applies
			if (avp_length % 4 != 0) {
				padded_length = padded_length + 4 - (avp_length % 4);
			}
		
			ptr = avp_code_pos + padded_length;
						
		}
							
	}
//	printf("Not found\n");
	return !notFound;
}

//it takes a buffer and interpretates it as a DIAMETER message
//if it finds out any error, this function will kill the proxy and
//write some info in the stdout
//
//just used for Throubleshooting
//
void parseBuffer (const char *buff, int read_length) 
{
	int ptr = read_length;
	bool vendor_specific = false;
	int vendor_id = 0;
	char ccode[4];
	char h2h[5];
	char e2e[5];
	int h2hint;
	int c_code;
	
	h2h[4] = 0x00;
	e2e[4] = 0x00;
	
	//extracting DIAMETER message length
	int diameter_length = (buff[1] & 0xff) << 16;
	diameter_length = diameter_length + (buff[2] & 0xff) <<8;
	diameter_length = diameter_length + (buff[3] & 0xff);

	//comparing the obtained length with the length of the buffer
	if (diameter_length != read_length)
	{
		printf ("\t(parse): sent bytes and diameter length DO NOT MATCH: NOK\n");
		dumpBuffer (buff, read_length);	//prints out the message in HEX mode
	}
	
	//extracting command code
	ccode[0] = (buff [5] & 0xff);
	ccode[1] = (buff [6] & 0xff);
	ccode[2] = (buff [7] & 0xff);
	c_code = ((ccode[0]&0xff)<<16)+((ccode[1]&0xff)<<8)+(ccode[2]&0xff); //in integer
		
	int header_flags = (buff[4]&0xff); //extrating the flags: nothing else done
	
	//extracting the HopByHopId
	h2h[0] = (buff [12] & 0xff);
	h2h[1] = (buff [13] & 0xff);
	h2h[2] = (buff [14] & 0xff);
	h2h[3] = (buff [15] & 0xff);
	h2hint = ((h2h[0]&0xff)<<24) +((h2h[1]&0xff)<<16)+((h2h[2]&0xff)<<8)+(h2h[3]&0xff);
	
	
	//extracting the EndToEndId
	e2e[0] = (buff [16] & 0xff);
	e2e[1] = (buff [17] & 0xff);
	e2e[2] = (buff [18] & 0xff);
	e2e[3] = (buff [19] & 0xff);
	
	//setting the pointer to the end of header = beginning of data
	ptr = 20; //DIAMETER_HEADER
	
	while (ptr< read_length) //while more data to be read
	{
		int padded_length;
		//extracting AVP code
		int avp_code = ((buff[ptr] & 0xff)<<24) + ((buff[ptr+1] & 0xff)<<16) + 
							((buff[ptr+2] & 0xff)<<8) +(buff[ptr+3] & 0xff);
							
		int avp_code_pos = ptr;
		ptr = ptr + 4;
		
		//extracting flags
		int avp_flags = (buff[ptr] & 0xff);
		ptr = ptr + 1;
		
		if ((avp_flags & 0x80) != 0x00) //if the AVP is vendor specific
		{
			vendor_specific = true;	//it is marked
		}
		
		//extracting AVP length
		int avp_length = ((buff[ptr] & 0xff)<<16) + ((buff[ptr+1] & 0xff)<<8) + (buff[ptr+2] & 0xff);
		ptr = ptr + 3;

		padded_length = avp_length;
		
		//if the AVP length is not multiple of length, padding applies
		if (avp_length % 4 != 0) 
		{
			padded_length = padded_length + 4 - (avp_length % 4);
		}
		
		//if it is vendor-specific, then extract the Vendor-Id
		if (vendor_specific)
		{
			vendor_id = ((buff[ptr] & 0xff)<<24) + ((buff[ptr+1] & 0xff)<<16) + ((buff[ptr+2] & 0xff)<<8) + (buff[ptr+3] & 0xff);
		}
		
		//looking for the AVP description
		char* avp_desc = avp_code_desc (avp_code, vendor_id);
		
		if (avp_desc == NULL) //if the AVP is unknown
		{
			printf ("**************** ALARM  ************************\n");
			printf ("\t\t\t(parse) read_length = %d\n", read_length);
			printf ("\t\t\t(parse) header flags = %02x\n", header_flags);
			printf ("\t\t\t(parse): command code = %d\n", c_code);
			printf ("\t\t\t(parse) h2h = %02x %02x %02x %02x (%d)\n", (h2h[0]&0xff),(h2h[1]&0xff),(h2h[2]&0xff),(h2h[3]&0xff),h2hint);
			printf ("\t\t\t(parse) e2e = %02x %02x %02x %02x\n", (e2e[0]&0xff),(e2e[1]&0xff),(e2e[2]&0xff),(e2e[3]&0xff));
			printf ("\t\t\t(parse) bad avp at offset = %d\n", avp_code_pos);
			printf ("\t\t\t(parse) avp flags = %02x\n", avp_flags);
			printf ("\t\t\t(parse) avp_length = %d\n", avp_length);
			printf ("\t\t\t(parse) padded avp_length = %d\n", padded_length);
			printf ("\t\t\t(parse) code = %d (%s)\n", avp_code, "UNKNOWN");
			printf ("\t\t\t(parse) code = %08x (%d)\n", avp_code, "UNKNOWN");
			printf ("\t(parse): UNKNOWN AVP\n");
			dumpBuffer (buff, read_length);	//dump the buffer in HEX mode
			printf ("**************** END OF ALARM  *****************\n");
			sleep (1);
			exit (1);
		}
		
		//updating pointers and variables for the next iteration
		ptr = ptr + padded_length - 8;
		vendor_specific = false;
		vendor_id = 0;
	}
}

//returns the description identified by an avp code and a vendor-id
//this function is only for troubleshooting purpose
//the addition of a new AVP will lead to its update
char* avp_code_desc (int avp_code, int vendor_id) 
{
    //printf ("avp_code = %d/%d\n",vendor_id, avp_code);
    if (vendor_id==0) //if no vendor applies
    {
        switch (avp_code)
        {
            case 263: return "SessionId";
            case 296: return "OriginRealm";
            case 257: return "Host-IP-Address";
            case 266: return "Vendor-Id";
            case 269: return "ProductName";
            case 265: return "Supported-Vendor-Id";
            case 258: return "Auth-Application-Id";
            case 259: return "Acct-Application-Id";
            case 268: return "ResultCode";
            case 264: return "OriginHost";
            case 277: return "AuthSessionState";
            case 297: return "Experimental-ResultCode";
            case 260: return "Vendor-Specific-Application-Id";
            case 480: return "Accounting-Record-Type";
            case 485: return "Accounting-Record-Number";
            case 1002: return "Indication";
            case 1011: return "SIP-Server-Capabilities";
            case 1012: return "SIP-ServerName";
            case 1017: return "UserData";
            case 1018: return "Auth-Data-Item";
            case 1026: return "NumberAuthenticationItems";
            case 1: return "UserName";
            default: return NULL;
        }
    } else

    if (vendor_id ==ERICSSON_VENDOR_ID) //Vendor=Ericsson
    {
        switch (avp_code)
        {
            case 19:  return "Ericsson:avp19";
            default: return NULL;
        }

    } else
    if (vendor_id == 193) //
    {
        switch (avp_code)
        {
            case 607: return "EPC:ValidAVP";
            default: return NULL;
        }
    }

}

//Prints out a buffer in rows of 16 octets
//with a tab after the first 8 ones
//Besides, at the right hand side of every line
//the ASCII equivalence is also printed out
//non printable characters are printed as '.'
void dumpBuffer (const char *buff, int size)
{
	int itr  = 0;
	char line[16];
	char ch[1];
	char logline[50];
	
	printf ("*************buffer dump*****************\n");
	printf ("%04x\t",itr);

	
	memcpy ((char*)line, (char*)&buff[itr], 16);
	
	for (; itr < size;)
	{

		printf ("%02x ", (buff[itr++])&0xff);
		printf ("%02x ", (buff[itr++])&0xff);
		printf ("%02x ", (buff[itr++])&0xff);		
		printf ("%02x ", (buff[itr++])&0xff);
		
		if ((itr) % 16 == 0)
		{
			printLine(line);
			memcpy ((char*)line, &buff[itr], 16);
			printf ("%04x\t",itr);
		}
	}
	printf ("\n");
	printf ("******************************buffer dump end******************************\n");
}

//prints out one line (16 octets) of the buffer
void printLine (char *line)
{
	int itr = 0;
	printf ("\t");
	for (;itr!=8;itr++)
	{
		printChar ((int)line[itr]);
	}
	printf ("   ");

	for (;itr!=16;itr++)
	{
		printChar ((int)line[itr]);
	}
	printf ("\n");
}

//prints out a single octec of the buffer
//checks if the charater is printable or not
void printChar (int octet)
{
	if ( octet<32 || octet>127 )
	{
		printf (".");
	} else
	{
		printf ("%c",octet);
	}
}


bool confirm_message (char * text) 
{
	bool result = false;
	char answer = '\0';
	char old_answer = '\0';

	while (!((answer == 'y') | (answer == 'Y') | (answer == 'n') | (answer == 'N') ))
	{
		printf("%s",text);

		answer = getchar();
		if ((answer == 'y') | (answer == 'Y'))
		{
			result = true;
			getchar();
		} else 
		if ((answer == 'n') | (answer == 'N'))
		{
			result = false;
		} else
		{
			while(answer != '\n')
			{
				answer = getchar();
			}
		}
		old_answer = answer;
	}
	
	return result;
}
