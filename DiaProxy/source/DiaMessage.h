#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "Types.h" 
#include "AVP.h"
#include "DiaProxy.h"



//class that modelates a DIAMETER Message
//#define __HSS_NODE 0
//#define __EPC_NODE 1

class DiaMessage
{
public:
	DiaMessage (); //constructor
	virtual ~DiaMessage();	//destructor
	int addAVP (AVP *avp);
	int get_size ();
	void message(puchar msg);
	void set_size(int length);
	void set_cmd_code(puchar cmd_code);
	
private:
	int node_type;
	int message_length;
	char buffer[DEFAULT_BUFFER_SIZE];
	puchar data_pointer;
	DIAMETER_HEADER head;
};
