#ifndef AVP_H
#define AVP_H

#include <netdb.h>

#include <arpa/inet.h>
#include "ConnectionKeeper.h"


#define RFC__VERSION	1
#define DRAFT__VERSION	2
#define NORMAL__TYPE		0
#define IPADDRESS__TYPE		1
#define COMPOSED__TYPE 		2
#define DEFAULT_HOST_IP_ADDRESS_IF_FAIL 	0x0a011459


typedef unsigned char			uchar;
typedef unsigned char *			puchar;
typedef unsigned int			uint;
typedef char *				LPTSTR;
typedef const char *			LPCTSTR;

enum SignalReason {
	NO_REASON,
	MAX__INACTIVE__REACHED,
	CONF__ERROR,
};

typedef struct _DIAMETER_HEADER
{
	uchar	ver;
	uchar	length[3];
	uchar	flags;
	uchar	cmd_code[3];
	uint	vendor_id;
	uint	hop2hop;
	uint	end2end;
} DIAMETER_HEADER;

const int DIAMETER_HEADER_LENGTH = sizeof (DIAMETER_HEADER);

typedef struct _AVP_HEADER
{
	uint	avp_code;
	uchar	flags;
	uchar	avp_len[3];
	uint	value;
}AVP_HEADER;

enum avps
{
	acct__application__id			= 0x03010000,
	auth__application__id			= 0x02010000,
	host__ip__address			= 0x01010000,
	origin__host				= 0x08010000,
	origin__realm				= 0x28010000,
	destination__host			= 0x25010000,
	destination__realm			= 0x1b010000,
	product__name				= 0x0d010000,
	result__code				= 0x0c010000,
	supported__vendor__id			= 0x09010000,
	vendor__id				= 0x0a010000,
	vendor__specific__application__id 	= 0x04010000,
	firmware__revision			= 0x0b010000
};

enum result_codes
{
	result__diameter__multi__round__auth			= 0xe9030000,
	result__diameter__success				= 0xd1070000,
	result__diameter__authorized__and__already__registered	= 0x98080000,
	result__diameter__authorized__first__registration	= 0x99080000,
	//new 
	result__diameter__invalid__avp__length 			= 0x96130000,
	result__diameter__invalid__avp__value	 		= 0x8c130000,
	result__diameter__no_common__application 		= 0x92130000,
	result__diameter__unable_to_comply	 		= 0x94130000
	
};


typedef enum  _AvpCode{

	USERNAME_CODE				= 1,
	HOST_IP_ADDRESS_CODE			= 257,
	AUTH_APPLICATION_ID_CODE		= 258,
	ACCT_APPLICATION_ID_CODE		= 259,
	VENDOR_SPECIFIC_APPLICATION_ID_CODE	= 260,
	SESSIONID_CODE				= 263,
	ORIGINHOST_CODE				= 264,
	SUPPORTED_VENDOR_ID_CODE		= 265,
	VENDOR_ID_CODE				= 266,	
	RESULTCODE_CODE				= 268,
	PRODUCTNAME_CODE			= 269,
	AUTHSESSIONSTATE_CODE			= 277,
	ORIGINREALM_CODE			= 296,
	EXPERIMENTAL_RESULTCODE_CODE		= 297,
	ACCOUNTING_RECORD_TYPE_CODE		= 480,
	ACCOUNTING_RECORD_NUMBER_CODE		= 485,
	INDICATION_CODE				= 1002,
	SIP_SERVER_CAPABILITIES_CODE		= 1011,
	SIP_SERVERNAME_CODE			= 1012,
	USERDATA_CODE				= 1017,
	AUTH_DATA_ITEM_CODE			= 1018,
	NUMBERAUTHENTICATIONITEMS_CODE		= 1026
	
}AVP_CODE;			

enum cmd_codes
{
	cmd__code__cer				= 0x101,
	cmd__watchdog				= 0x118,
	cmd__rar				= 0x1f4,
	cmd__mar				= 0x1fa,
	cmd__lur				= 0x1f5,
	cmd__udr				= 0x1f6,
	cmd__lir				= 0x1f7,
	cmd__dpr				= 0x11a,
	cmd__ulr				= 0x28a,
	cmd__air				= 0x28b,
	cmd__idr				= 0x28c,
	cmd__idr_rfe5				= 0x13f,
	cmd__clr				= 0x28d,
	cmd__clr_rfe5				= 0x13d

}; 

//class that modelates a DIAMETER AVP
class AVP
{
public:
	AVP (uint avp_code, uchar avp_flags, puchar avp_data, int=RFC__VERSION, bool=NORMAL__TYPE); //constructor
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




#endif
