#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "AVP.h"

void AVP::add_sub_attribute (AVP *sub_avp)
{
	int sub_avp_length = sub_avp->get_length();
	int n_pad = bytes_to_pad (sub_avp_length);

	sub_avp->get_value (data_head+offset);
	offset += sub_avp_length + n_pad;
	data_length = data_length + sub_avp_length + n_pad;
	total_length = sizeof(AVP_HEADER) + data_length - 4;
}

bool AVP::is_void (char *ip_address) 
{
	int summatory=	ip_address[0] + \
			ip_address[1] + \
			ip_address[2] + \
			ip_address[3];
			
	return (summatory==0);
}

void AVP::initialize_ip_address (char *ip_address)
{
	struct hostent *hent;
	char host_name[200];
	bool hdone = false;
	if(gethostname(host_name,199) == 0)
	{
		if((hent = gethostbyname(host_name)) != NULL)
		{
			ip_address[0] = (uchar)hent->h_addr_list[0][0];
			ip_address[1] = (uchar)hent->h_addr_list[0][1];
			ip_address[2] = (uchar)hent->h_addr_list[0][2];
			ip_address[3] = (uchar)hent->h_addr_list[0][3];
			hdone = true;
		}
	}
	if(!hdone)
	{
		for(int i=0;i<4;i++) 
		{
			ip_address[3-i] = DEFAULT_HOST_IP_ADDRESS_IF_FAIL >> (i*8);
		}
	}
}

//for composed AVPs
AVP::AVP (uint avp_code, uchar avp_flags, int version,int _data_length)
{
	protocol_version = version;
	is_ip_address = false;

	memset(&header,0,sizeof(AVP_HEADER));
	header.avp_code = avp_code;
	header.flags = avp_flags;
	
	data_length = 0;
	offset = 0;
	total_length = sizeof(AVP_HEADER) - 4;

	data_head = (puchar)malloc (2*_data_length);
		
	//adjusting the value of the length to a 3-octet word
	header.avp_len[0] = 0xff & ((_data_length+8) >> 16);
	header.avp_len[1] = 0xff & ((_data_length+8) >> 8);
	header.avp_len[2] = 0xff & (_data_length+8);
}

//constructor of the class that allows to create an AVP
AVP::AVP (uint avp_code, uchar avp_flags, puchar avp_data, int version, bool type)
{
	char tmp_ip_address[4];
	total_length = sizeof(AVP_HEADER)-4;
	
	protocol_version = version;
	is_ip_address = type;
	
	if (is_ip_address) 
	{
	
		if (is_void((char*)avp_data)) 
		{ 
			initialize_ip_address (tmp_ip_address);
		}  else 
		{
			memcpy (tmp_ip_address, avp_data,4);
		}
	
		if (version==RFC__VERSION)
		{
			//if it is an IP address
			data_length = 6;
			data_head = (puchar)malloc(data_length);
			data_head[0] = 0x00;
			data_head[1] = 0x01;
			memcpy ((char*)data_head+2, (const char*)tmp_ip_address, data_length);
		} else
		{	//DRAFT__VERSION
			data_length = 4;
			data_head = (puchar)malloc(data_length);
			memcpy ((char*)data_head, (const char*)tmp_ip_address, data_length);
		}
	} else {
		//normal case
		data_length = strlen ((const char*)avp_data);
		if (data_length<4) //made up of 0x00s
		{
			data_length = sizeof (avp_data);
			data_head = (puchar)malloc (data_length);
			memset (data_head, 0, data_length);
			memcpy (data_head, avp_data, data_length);
		} else 
		{	//non-zeroed values!!!!
			n_pad = bytes_to_pad (data_length);
			data_head = (puchar)malloc (data_length+n_pad);
			memcpy ((char*)data_head, (const char*)avp_data,data_length);
		}
	}
	
	
	total_length += data_length;
	n_pad = bytes_to_pad (data_length);
	
	memset(&header,0,sizeof(AVP_HEADER)-8);
	header.avp_code = avp_code;
	header.flags = avp_flags;
	
	//adjusting the value of the length to a 3-octet word
	header.avp_len[0] = 0xff & ((total_length) >> 16);
	header.avp_len[1] = 0xff & ((total_length) >> 8);
	header.avp_len[2] = 0xff & (total_length);
	
	total_length += n_pad;
}

AVP::AVP (uint avp_code, uchar avp_flags, puchar avp_data, bool ipv6, int version, bool type)
{
	char tmp_ip_address[16];
	total_length = sizeof(AVP_HEADER)-4;
	
//popo
	memcpy (tmp_ip_address, avp_data,16);
	
	//if it is an IP address
	data_length = 18;
	data_head = (puchar)malloc(data_length);
	data_head[0] = 0x00;
	data_head[1] = 0x02;
	memcpy ((char*)data_head+2, avp_data, 16);

                        	
	total_length += data_length;
	n_pad = bytes_to_pad (data_length);
	
	memset(&header,0,sizeof(AVP_HEADER)-8);
	header.avp_code = avp_code;
	header.flags = avp_flags;
	
	//adjusting the value of the length to a 3-octet word
	header.avp_len[0] = 0xff & ((total_length) >> 16);
	header.avp_len[1] = 0xff & ((total_length) >> 8);
	header.avp_len[2] = 0xff & (total_length);
	
	total_length += n_pad;
}
//constructor of the class that allows to create an AVP
AVP::AVP (uint avp_code, uchar avp_flags, unsigned int length, puchar avp_data, int version)
{

	total_length = sizeof(AVP_HEADER)-4;	
	protocol_version = version;
	data_length = length;
	data_head = (puchar)malloc (data_length);
	memset (data_head, 0, data_length);
	memcpy (data_head, avp_data, data_length);
		
	total_length += data_length;
	n_pad = bytes_to_pad (data_length);
		
	memset(&header,0,sizeof(AVP_HEADER)-8);
	header.avp_code = avp_code;
	header.flags = avp_flags;
	
	//adjusting the value of the length to a 3-octet word
	header.avp_len[0] = 0xff & ((total_length) >> 16);
	header.avp_len[1] = 0xff & ((total_length) >> 8);
	header.avp_len[2] = 0xff & (total_length);
	
	total_length += n_pad;
}


//destructor
AVP::~AVP ()
{
//	free (avp_payload);
	free (data_head);
}


void AVP::set_data_length (int length) 
{

	total_length = sizeof(AVP_HEADER) - 4;
	total_length += length;
	n_pad = bytes_to_pad (length);

	header.avp_len[0] = 0xff & ((total_length) >> 16);
	header.avp_len[1] = 0xff & ((total_length) >> 8);
	header.avp_len[2] = 0xff & (total_length);
}

//returns the value of the AVP
int AVP::get_value (puchar dst)
{
	memcpy (dst, &header, sizeof(AVP_HEADER)-4);
	memcpy (dst+sizeof(AVP_HEADER)-4,data_head,data_length);
	return (total_length);
}


//determines the bits to be added as padding
int AVP::bytes_to_pad(int len)
{
	int i = 0;
	while(((len + i)*8) % 32)
		i++;
	return i;
}

int AVP::get_length ()
{
	return (int)(total_length);
}
