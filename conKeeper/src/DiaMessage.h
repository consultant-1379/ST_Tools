#include "ConnectionKeeper.h"
#include "AVP.h"



//class that modelates a DIAMETER Message
//#define __HSS_NODE 0
//#define __EPC_NODE 1

class DiaMessage
{
public:
	DiaMessage (); //constructor
	virtual ~DiaMessage();	//destructor
	void addAVP (AVP *avp);
	int get_size ();
	void message(puchar msg);
	void set_size(int length);
	
private:
	int node_type;
	int message_length;
	char buffer[DEFAULT_BUFFER_SIZE];
	puchar data_pointer;
	DIAMETER_HEADER head;
};
