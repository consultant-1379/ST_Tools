#include "DiaMessage.h"

DiaMessage::DiaMessage ()
{	
	data_pointer = (puchar) buffer+DIAMETER_HEADER_LENGTH;	//starts at payload
	message_length = DIAMETER_HEADER_LENGTH;

	memset(buffer,0,DEFAULT_BUFFER_SIZE);
	memset(&head,0,DIAMETER_HEADER_LENGTH);
	
	head.ver = 1;
//	head.cmd_code[1] = 1;
//	head.cmd_code[2] = 1;

	head.flags = 0x80;

	set_size (0);

	srand((unsigned)time(NULL));
	head.hop2hop = rand();
	head.end2end = rand();
	
	memcpy (buffer, &head, DIAMETER_HEADER_LENGTH);
}

//destructor
DiaMessage::~DiaMessage ()
{
	//free (avp_payload);
}

int DiaMessage::addAVP (AVP *avp)
{
	int l_avp = avp->get_value (data_pointer);
	data_pointer += l_avp;
}

//returns the value of the AVP
int DiaMessage::get_size ()
{
	return (data_pointer-(puchar)buffer);
}

void DiaMessage::message(puchar msg)
{
	set_size (data_pointer-(puchar)buffer);
	memcpy (msg, buffer, ((char*)data_pointer - (char*)buffer));
}

void DiaMessage::set_size(int length)
{
	head.length[0] = 0xff & (length >> 16);
	head.length[1] = 0xff & (length >> 8);
	head.length[2] = 0xff &  length;
	memcpy (buffer,&head,DIAMETER_HEADER_LENGTH);
	
}
void DiaMessage::set_cmd_code(puchar cmd_code)
{
	head.cmd_code[1] = cmd_code[1];
	head.cmd_code[2] = cmd_code[2];

}
