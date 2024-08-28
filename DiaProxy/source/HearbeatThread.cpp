//==============================================================================
//#****h* src/DiaThread.cpp
//# MODULE
//#   DiaProxy.capp
//#
//# AUTHOR    
//#   TV 
//#
//# VERSION
//#   2.0
//#   	Ckecked by: -
//#	Aproved by: -
//#
//# DATE
//#   September, 2005
//#
//# DESCRIPTION
//# 	
//#   
//# IMPORTS
//#   
//# REFERENCES
//#	[1]	NONE
//#
//# -----------------------------------------------------------------------------
//# HISTORY
//#   Olov Marklund		   	2005/06/10    Creation
//#   Jose Manuel Santos	   	2005/09/26    Comments added
//#   Jose Manuel Santos		2005/11/22    Avoid '0x00000000' end2end ID
//#   Jose Manuel Santos		2006/01/10    Adding the support for PNR messages
//#******
//==============================================================================
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <signal.h>
#include <pthread.h>

#include <sys/types.h>
#include <sys/ioctl.h>
#include <netinet/in.h>

#include <sys/socket.h>
#include <netinet/tcp.h>
#include <net/if.h>
#include <stropts.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <unistd.h>
#include <netdb.h>
#include <sys/timeb.h>
#include <sys/time.h>
#include <vector>
#include <map>

#include "HearbeatThread.h"
#include "ClientThread.h"
#include "DiaMessage.h"
#include "Logger.h"

extern time_t start, stop, lastaction;
extern CER_DATA cer_data;
extern pthread_t ProxyThreadID;
extern pthread_t SignalThreadID;
extern pthread_t HearbeatThreadID;

extern SignalReason sigReason;
extern bool haveToExit;
//extern struct sockaddr_in diameter_addr;
//extern struct sockaddr_in loc_addr;
extern int local_port;
extern int server_port;
extern pthread_mutex_t TOOL_STATUS;

extern std::vector<DiaServerConnection> v_connections;
extern std::vector<ClientConnection> v_client;
extern std::vector<Transaction> v_transaction;
extern std::map<std::string, Session> m_session;
extern DiaProxyStatus diaProxyState;

int hearbeatSockId = -1;

using namespace std;

void* _HearbeatThread(void *arg)
{ 
	bool myHaveToExit;
	bool serverFound = false;
	char tmp_diameter_host[100];
	int counter = 0;
        stringstream logString;

	printf ("*************************************************\n");
	printf ("*************************************************\n");
	printf ("\tREDUNDANCY CONFIGURATION\n\n");
	printf ("\t\tZONE 1 IP:\t%s\n",cer_data.diameter_primary_host);
	printf ("\t\tZONE 2 IP:\t%s\n\n",cer_data.diameter_secondary_host);

	printf ("*************************************************\n");
	printf ("*************************************************\n\n");

    logString.clear();
    logString.str("");
    logString << "(HearbeatThread) :FINDING ACTIVE ZONE..." <<endl;
    LOG(INFO, logString.str());

	strcpy(tmp_diameter_host,cer_data.diameter_secondary_host);

	do {

		pthread_mutex_lock(&TOOL_STATUS);
			myHaveToExit = haveToExit;
		pthread_mutex_unlock(&TOOL_STATUS);

		if (myHaveToExit)  	resetExit (0);

		if(strcmp(tmp_diameter_host,cer_data.diameter_primary_host) == 0) 	strcpy(tmp_diameter_host,cer_data.diameter_secondary_host);
		else 									strcpy(tmp_diameter_host,cer_data.diameter_primary_host);

		serverFound = checkConnection(tmp_diameter_host);
		counter ++;
		if (counter > MAX_ACTIVE_NODE_FIND_RETRIES) {
                    logString.clear();
                    logString.str("");
                    logString << "(HearbeatThread) :ERROR. Too many failed tries finding active node." <<endl;
                    LOG(ERROR, logString.str());
                    
		    resetExit (1);
		
		}

	} while (!serverFound);

        logString.clear();
        logString.str("");

	if(strcmp(tmp_diameter_host,cer_data.diameter_primary_host) == 0) 
                logString << "(HearbeatThread) :Active Diameter Server on ZONE 1 "<< tmp_diameter_host<<":"<< server_port<<endl;
	else 									
                logString << "(HearbeatThread) :Active Diameter Server on ZONE 2 "<< tmp_diameter_host<<":"<< server_port<<endl;

        LOG(EVENT, logString.str());

	pthread_mutex_lock(&TOOL_STATUS);
		strcpy(cer_data.diameter_host,tmp_diameter_host);
		diaProxyState = DIAPROXY_STARTING;
	pthread_mutex_unlock(&TOOL_STATUS);

	while (true){

		
		if(strcmp(cer_data.diameter_host,cer_data.diameter_primary_host) == 0) 	strcpy(tmp_diameter_host,cer_data.diameter_secondary_host);
		else 										strcpy(tmp_diameter_host,cer_data.diameter_primary_host);
		
		serverFound = false;

		do {
			sleep (cer_data.hearbeatTime);
			
			pthread_mutex_lock(&TOOL_STATUS);
				myHaveToExit = haveToExit;
			pthread_mutex_unlock(&TOOL_STATUS);

			if(myHaveToExit){ 
                            logString.clear();
                            logString.str("");
                            logString << "(HearbeatThread) :Terminating... " <<endl;
                            LOG(ERROR, logString.str());

			    resetExit (0);
			} 

			serverFound = checkConnection(tmp_diameter_host);
	
		} while (!serverFound);

		pthread_mutex_lock(&TOOL_STATUS);
			strcpy(cer_data.diameter_host,tmp_diameter_host);
		pthread_mutex_unlock(&TOOL_STATUS);

                logString.clear();
                logString.str("");

		if(strcmp(tmp_diameter_host,cer_data.diameter_primary_host) == 0) 
                    logString << "(HearbeatThread) : Diameter Server on ZONE 1 has became active "<< tmp_diameter_host<<":"<< server_port<<endl;
		else 									
                    logString << "(HearbeatThread) :Diameter Server on ZONE 2 has became active "<< tmp_diameter_host<<":"<< server_port<<endl;

                LOG(EVENT, logString.str());

	}
}




bool checkConnection(char * connection_host)
{
	bool result = false;
        stringstream logString;
	uchar cer_msg[DEFAULT_BUFFER_SIZE];
	
	int cer_len = createCER(cer_msg,&cer_data);
	int sock_result;
	int errsv;
	
	struct sockaddr_in diameter_addr;
	struct sockaddr_in loc_addr;
	

   	if(cer_data.use_sctp!=0){
#ifdef _DIA_PROXY_DEBUG
            logString.clear();
            logString.str("");
            logString << "(HearbeatThread): Trying to establish connection to Diameter: " ;
            logString << connection_host << " port " <<server_port<<" using SCTP" <<endl;
            LOG(DEBUG, logString.str());
                            
#endif
		
       		hearbeatSockId = socket(AF_INET,SOCK_STREAM,IPPROTO_SCTP);
   	}
   	else {
#ifdef _DIA_PROXY_DEBUG
            logString.clear();
            logString.str("");
            logString << "(HearbeatThread): Trying to establish connection to Diameter: " ;
            logString << connection_host << " port " <<server_port<<" using TCP" <<endl;
            LOG(DEBUG, logString.str());
#endif

     	 	hearbeatSockId = socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
   	}

	if(hearbeatSockId == -1) { 
            errsv = errno;
            logString.clear();
            logString.str("");
            logString << "(HearbeatThread): Failed to create socket" <<endl;
            logString <<"\tError: " << strerror(errsv) << endl;            
            LOG(ERROR, logString.str());
							
	    resetExit (1);
	} 

    struct timeval sendTimer;
    sendTimer.tv_sec = DEFAULT_SEND_TIME;
    sendTimer.tv_usec = 0;

    if (setsockopt (hearbeatSockId, SOL_SOCKET, SO_SNDTIMEO, &sendTimer, sizeof (sendTimer))) {
    	errsv = errno;
        logString.clear();
        logString.str("");
        logString << "(HearbeatThread): ailed when changing SO_SNDTIMEO" <<endl;
        logString <<"\tError: " << strerror(errsv) << endl;
        LOG(ERROR, logString.str());

        resetExit (1);
    }

	memset(&diameter_addr,0,sizeof(sockaddr_in));
	diameter_addr.sin_family = AF_INET;
	diameter_addr.sin_port = htons(server_port);
        
 	struct hostent *he;
	he = gethostbyname(connection_host); 
	if (he == 0) {
		logString.clear();
            logString.str("");
            logString << "(HearbeatThread): Destination host not valid " << connection_host <<endl;
            logString <<"\tError: " << strerror(errsv) << endl;            
            LOG(ERROR, logString.str());
	    
            resetExit (1);
	}

	bcopy(he->h_addr_list[0], &diameter_addr.sin_addr.s_addr, he->h_length);
	
	memset(&loc_addr,0,sizeof(sockaddr_in));
	loc_addr.sin_family = AF_INET;

	if(cer_data.use_sctp)
		loc_addr.sin_addr.s_addr = inet_addr(cer_data.diaproxy_host);

	socklen_t len = sizeof(diameter_addr);

	if(bind(hearbeatSockId,(struct sockaddr*)&loc_addr,sizeof(loc_addr)) < 0)
	{
            errsv = errno;
            logString.clear();
            logString.str("");
            logString << "(HearbeatThread):Failed to bind to local socket" <<endl;
            logString <<"\tError: " << strerror(errsv) << endl;            
            LOG(ERROR, logString.str());
							
	    resetExit (1);
	}

	sock_result = connect(hearbeatSockId,(sockaddr*)&diameter_addr,len);
		
	if (sock_result == -1 && errno != 115){
#ifdef _DIA_PROXY_DEBUG
            errsv = errno;
            logString.clear();
            logString.str("");
            logString << "(HearbeatThread):Failing to network connect to Diameter Server "<<inet_ntoa(diameter_addr.sin_addr)<<":" << ntohs(diameter_addr.sin_port) <<endl;
            logString <<"\tError: " << strerror(errsv) << endl;            
            LOG(DEBUG, logString.str());
#endif
		
            if(hearbeatSockId != -1){
		close(hearbeatSockId);
            }

	    return false;
	}			

	
	if(hearbeatSockId != -1) { 
		
#ifdef _DIA_PROXY_DEBUG
            errsv = errno;
            logString.clear();
            logString.str("");
            logString << "(HearbeatThread): Network connection to "<<inet_ntoa(diameter_addr.sin_addr)<<":" << ntohs(diameter_addr.sin_port) <<endl;
            logString <<"\tError: " << strerror(errsv) << endl;            
            LOG(DEBUG, logString.str());
#endif		
	    fd_set fds;
	    struct timeval tv;
	    tv.tv_sec = 2;
	    tv.tv_usec = 0;
	    FD_ZERO(&fds);
	    FD_SET(hearbeatSockId, &fds);

	    int res = send(hearbeatSockId,(const char*)cer_msg,cer_len,0);

	    if(res > 0) { 
			
	        fd_set tmpset = fds;
	        tv.tv_sec = 4;
	        tv.tv_usec = 0;
					
	        select(hearbeatSockId+1, &tmpset, NULL, NULL, &tv);

			if(FD_ISSET(hearbeatSockId, &tmpset)){
				result = receive_CEA(hearbeatSockId);
				if(hearbeatSockId != -1){
					closeHearbeatConnection(hearbeatSockId,&cer_data);
				}
				return result;
			}
				else {
				if(hearbeatSockId != -1){
					close(hearbeatSockId);
				}
				return false;
		}

	    } 
	    else { 
	        if(hearbeatSockId != -1){
		    close(hearbeatSockId);
	        }
		return false;
	    } 
				
		
	} //if(diameter_sock != INVALID_SOCKET)

	printf("(HearbeatThread) : Failed something wrong in the code\n");

	if(hearbeatSockId != -1){
		close(hearbeatSockId);
	}
	resetExit (1);

} //bool checkConnection(char *arg)
int closeHearbeatConnection(int hearbeatSockId, struct CER_DATA *cerdata)
{

	uchar dpr_msg[DEFAULT_BUFFER_SIZE];

    int dpr_len = createDPR(dpr_msg,&cer_data);
    int res = send(hearbeatSockId,(const char*)dpr_msg,dpr_len,0);
    if (res == dpr_len){
        uchar buff[DEFAULT_BUFFER_SIZE];
        memset(buff,0,DEFAULT_BUFFER_SIZE);
        struct timeval tv;
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(hearbeatSockId, &fds);
        fd_set tmpset = fds;
        tv.tv_sec = 2;
        tv.tv_usec = 0;
        select(hearbeatSockId+1, &tmpset, NULL, NULL, &tv);
        if(FD_ISSET(hearbeatSockId, &tmpset)){
        	int received = recv(hearbeatSockId,(LPTSTR)buff,DIAMETER_HEADER_LENGTH,0);
        }
    }
    close(hearbeatSockId);
}

int createDPR(uchar *dprmsg, struct CER_DATA *cerdata)
 {

 	int version=RFC__VERSION;

 	DiaMessage DPRMessage = DiaMessage();
	uchar cmd_code[3];
 	cmd_code[1] = 0x01;
	cmd_code[2] = 0x1a;
	DPRMessage.set_cmd_code(cmd_code);
 	AVP *avp;
 	//Origin-Host
 	uchar origin[] = "Diaproxy.hearbeat.ericsson.se";
 	avp = new AVP (origin__host,0x40,origin,version);
 	DPRMessage.addAVP (avp);
 	free (avp);

 	//Origin-Realm
 	avp = new AVP (origin__realm,0x40,cer_data.origin_realm,version);
 	DPRMessage.addAVP (avp);
 	free (avp);

 	//Disconnect cause = 2
 	char hex_value[4];
 	int2hex (hex_value,2,4);
 	avp = new AVP (disconnect__cause, 0x40,4, (uchar*)hex_value, version);
 	DPRMessage.addAVP (avp);
 	free (avp);

 	//finishing the message
 	DPRMessage.message(dprmsg);
 	return DPRMessage.get_size();
 }
int createCER(uchar *cermsg, struct CER_DATA *cerdata)
{ //int createCER(uchar *cermsg, struct CER_DATA *cerdata)

	int version=RFC__VERSION;
	char firmware_value[4];

	DiaMessage CERMessage = DiaMessage();
	uchar cmd_code[3];
	cmd_code[1]=0x01;
	cmd_code[2]=0x01;

	CERMessage.set_cmd_code(cmd_code);
	AVP *avp;
	//Origin-Host
	uchar origin[] = "Diaproxy.hearbeat.ericsson.se";
	avp = new AVP (origin__host,0x40,origin,version);
	CERMessage.addAVP (avp);
	free (avp);

	//Origin-Realm
	avp = new AVP (origin__realm,0x40,cer_data.origin_realm,version);
	CERMessage.addAVP (avp);
	free (avp);
	
	//Host-IP-Address
	avp = new AVP (host__ip__address,0x40, cer_data.host_ip_address, version, true);
	CERMessage.addAVP (avp);
	free (avp);

	//Vendor-ID
	avp = new AVP (vendor__id, 0x40, 4, cerdata->vendor_id,version);
	CERMessage.addAVP (avp);
	free (avp);
	
	//Product-Name
	avp = new AVP (product__name, (uchar)0x00,cerdata->product_name,version);
	CERMessage.addAVP (avp);
	free (avp);

	
	int sub_attr_len=0;	
		
	int index;
	for (index=0;index!=cer_data.number_of_supported_vendor_ids;index++) {
		puchar hex_value[4];  
		int current_vendor_id = cer_data.list_of_supported_vendor_ids[index];
			
		int2hex ((char*)hex_value,current_vendor_id,4);
		avp = new AVP (supported__vendor__id, (uchar)0x40, 4, (puchar)hex_value, version);
		CERMessage.addAVP (avp);
		free (avp);
	}
		
	for (index=0;index!=cer_data.number_of_auth_application_ids;index++) {
		puchar hex_value[4];  
		int current_vendor_id = cer_data.list_of_auth_application_ids[index];
			
		int2hex ((char*)hex_value,current_vendor_id,4);
		avp = new AVP (auth__application__id, (uchar)0x40, 4,(puchar)hex_value,version);
		CERMessage.addAVP (avp);
		free (avp);
	}
		
	for (index=0;index < 2 * cer_data.number_of_vendor_specific_application_ids;index++) {
		char hex_value[4];  

		//Supported-Vendor-ID
		int current_vendor_id = cer_data.list_of_vendor_specific_application_ids[index];
		int2hex (hex_value,current_vendor_id,4);
		AVP *sub_avp1 = new AVP (vendor__id,0x40, 4, (uchar*)hex_value, version);
		sub_attr_len = sub_avp1->get_length();
			
		//Auth-Application-ID
		int2hex(hex_value, cer_data.list_of_vendor_specific_application_ids[++index],4);
		AVP *sub_avp2 = new AVP (auth__application__id,0x40, 4, (uchar*)hex_value, version);
		sub_attr_len += sub_avp2->get_length();
	
		//Vendor-Specific-Application-Id
		AVP *parent_avp = new AVP (vendor__specific__application__id,0x40, version,sub_attr_len);
			
		parent_avp->add_sub_attribute(sub_avp1);
		parent_avp->add_sub_attribute(sub_avp2);
					
		free (sub_avp1);
		free (sub_avp2);
				
		CERMessage.addAVP (parent_avp);
	}
		
	//firmware revision
	int2hex (firmware_value, DEFAULT_FIRMWARE_REVISION, 4);
	avp = new AVP (firmware__revision, (uchar)0x00, 4, (uchar*)firmware_value,version);
	CERMessage.addAVP (avp);
	free (avp);

	//finishing the message
	CERMessage.message(cermsg);
	return CERMessage.get_size();
} //int createCER(uchar *cermsg, struct CER_DATA *cerdata)





bool receive_CEA (int hearbeatSockId) 
{

	DIAMETER_HEADER *head;
	AVP_HEADER *avphead;
        stringstream logString;
	
	bool ok = false;
	uchar buff[DEFAULT_BUFFER_SIZE];
	int received;
	
	memset(buff,0,DEFAULT_BUFFER_SIZE);
						
	received = recv(hearbeatSockId,(LPTSTR)buff,DEFAULT_BUFFER_SIZE,0);

#ifdef _DIA_PROXY_DEBUG
        logString.clear();
        logString.str("");
        logString << "(HearbeatThread): CEA received  " ;
        LOG(DEBUG, logString.str());
#endif
	
	if(received > 0)
	{ //if(received > 0)
		if((uint)received > DIAMETER_HEADER_LENGTH)
		{
			head = (DIAMETER_HEADER*)buff;
			if(head->flags == 0)
			{
				uint ccode = (head->cmd_code[0]<<16) + (head->cmd_code[1]<<8) + head->cmd_code[2];
				if(ccode == cmd__code__cer) {
					ok = true;
				}
			}
		}

		if(ok)
		{
			int offs = DIAMETER_HEADER_LENGTH;
			while(offs<received)
			{ //while(offs<received)
				avphead = (AVP_HEADER*)(buff+offs);
				uint avplen = 0;
	
				avplen = (avphead->avp_len[0] << 16) + (avphead->avp_len[1] << 8) + avphead->avp_len[2];
	
				if(avphead->avp_code == result__code)
				{ //if(avp == result__code)
						
					if(avphead->value == result__diameter__success)
					{
#ifdef _DIA_PROXY_DEBUG					
                                            logString.clear();
                                            logString.str("");
                                            logString << "(HearbeatThread): CER-CEA connection established with Diameter" << endl;
                                            LOG(DEBUG, logString.str());
#endif						
					}
					else
					{
						ok = false;
#ifdef _DIA_PROXY_DEBUG					
						uchar * ptr = (uchar *) &(avphead->value);
						int errorCode = *(ptr);
						errorCode = (errorCode << 8) + (*(ptr+1));
						errorCode = (errorCode << 8) + (*(ptr+2));
						errorCode = (errorCode << 8) + (*(ptr+3));

						switch (avphead->value) 
						{
							case result__diameter__invalid__avp__length:
                                                            logString.clear();
                                                            logString.str("");
                                                            logString << "(HearbeatThread): CER-CEA ERROR. Result_code AVP value: DIAMETER_INVALID_AVP_LENGTH"<< endl ;
                                                            LOG(DEBUG, logString.str());
							    break;
							case result__diameter__no_common__application:
                                                            logString.clear();
                                                            logString.str("");
                                                            logString << "(HearbeatThread): CER-CEA ERROR. Result_code AVP value: DIAMETER_NO_COMMON_APPLICATION"<< endl ;
                                                            LOG(DEBUG, logString.str());
							    break;
							case result__diameter__invalid__avp__value:
                                                            logString.clear();
                                                            logString.str("");
                                                            logString << "(HearbeatThread): CER-CEA ERROR. Result_code AVP value: DIAMETER_INVALID_AVP_VALUE"<< endl ;
                                                            LOG(DEBUG, logString.str());
							    break;
							case result__diameter__unable_to_comply:
                                                            logString.clear();
                                                            logString.str("");
                                                            logString << "(HearbeatThread): CER-CEA ERROR. Result_code AVP value: DIAMETER_UNABLE_TO_COMPLY"<< endl ;
                                                            LOG(DEBUG, logString.str());
							    break;
							default:
                                                            logString.clear();
                                                            logString.str("");
                                                            logString << "(HearbeatThread): CER-CEA ERROR. Result_code AVP value:"<< errorCode << endl ;
                                                            LOG(DEBUG, logString.str());
							    break;
						}
#endif						
					} 

					break;
				} //if(avp == result__code)
				uint t = 0;
				while(((avplen + t)*8) % 32)
				{
					t++;
				}
				offs += avplen + t;
			} //while(offs<received)
		} //if(ok)

	} //if(received > 0)
	else
	{ //else to if(received > 0)
		if(received == -1)
		{
#ifdef _DIA_PROXY_DEBUG					
                    logString.clear();
                    logString.str("");
                    logString << "(HearbeatThread):  Broken Pipe with Diameter"<< endl ;
                    LOG(DEBUG, logString.str());
#endif						
		}
		if(received == 0)
		{
#ifdef _DIA_PROXY_DEBUG					
                    logString.clear();
                    logString.str("");
                    logString << "(HearbeatThread):  Diameter has closed the connection."<< endl ;
                    LOG(DEBUG, logString.str());
#endif						
		}
		
		return false;


	} //else to if(received > 0)
	

	if(!ok){
#ifdef _DIA_PROXY_DEBUG					
            logString.clear();
            logString.str("");
            logString << "(HearbeatThread):  Error during CER-CEA process"<< endl ;
            LOG(DEBUG, logString.str());
#endif						
	    return false;
	}
	return true;
}


void resetExit (int fail)
{
    bool myHaveToExit;
    stringstream logString;

    pthread_mutex_lock(&TOOL_STATUS);
        myHaveToExit = haveToExit;
    pthread_mutex_unlock(&TOOL_STATUS);

    if (hearbeatSockId != -1)	close (hearbeatSockId);	

    if (!myHaveToExit && fail) {
        pthread_mutex_lock(&TOOL_STATUS);
            sigReason = DIA__CONF__ERROR;
        pthread_mutex_unlock(&TOOL_STATUS);
        
        pthread_kill(SignalThreadID ,SIGUSR1);
    }

#ifdef _DIA_PROXY_DEBUG
    logString.clear();
    logString.str("");
    logString << "(HearbeatThread):   .....Terminated"<< endl ;
    LOG(DEBUG, logString.str());
#endif

    pthread_exit(0);
}
