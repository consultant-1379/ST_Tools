#define RFC__VERSION	1
#define DRAFT__VERSION	2


#define NORMAL__TYPE		0
#define IPADDRESS__TYPE		1
#define COMPOSED__TYPE 		2

#include <netdb.h>
#include "Types.h" 
#include "cnDiaProxy.h"


//class that modelates a DIAMETER AVP
class AVP
{
public:
	AVP (uint avp_code, uchar avp_flags, puchar avp_data, int=RFC__VERSION, bool=NORMAL__TYPE); //constructor
	AVP (uint avp_code, uchar avp_flags, puchar avp_data, bool ipv6, int=RFC__VERSION, bool=NORMAL__TYPE); //constructor
	AVP (uint avp_code, uchar avp_flags, unsigned int length, puchar avp_data, int=RFC__VERSION); //constructor
	AVP (uint avp_code, uchar avp_flags, int version, int length); //constructor
	virtual ~AVP();	//destructor
	int get_value (puchar avp_value); //returns the data part of the AVP
	void set_data_length (int length);
	void add_sub_attribute (AVP *sub_avp);
	int get_length();
private:
	//class' members
	int total_length;
	int protocol_version;
	AVP_HEADER header;	//the header
	int data_length;	//length of the data part
	puchar avp_payload; 	//the data
	bool is_ip_address;		//indicates if it's a 'normal' AVP or contains an IP address
	puchar data_head;
	int offset;		//only for composed attributes
	int n_pad; 		//bytes dedicated for padding

	int bytes_to_pad (int avp_data_length);  //determines the bits to be added as padding
	bool is_void (char *ip_address);
	void initialize_ip_address (char *ip_address);	
};
