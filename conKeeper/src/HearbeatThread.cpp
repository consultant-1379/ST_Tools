#include "ConnectionKeeper.h"
#include "DiaMessage.h"

using namespace std;
extern pthread_t SignalThreadID;

extern vector<Connection> v_connections;
extern vector<Listener> v_listeners;

extern time_t start, stop, lastaction;
extern SignalReason sigReason;
extern pthread_mutex_t sync_mutex;
extern vector <int> conIndex;
extern applicationData dataTool;
extern HeartBeat  heartBeatData; 

int cer_len;
uchar cer_msg[DEFAULT_BUFFER_SIZE];


void* _HeartBeatThread(void *arg)
{ 
	char remote_ip[20];
                       	
       	cer_len = create_heartbeat_CER(cer_msg);
        
        stringstream logString;
 	ConKeeperStatus appStatus;
                        
	if (dataTool.logMask >= LOGMASK_INFO){
       		logString.clear();
		logString.str("");
		logString << "HearbeatThread: Starting..." <<endl;
		LOG(INFO, logString.str());
        }
        
       	ActiveZone TryToconnecTo = PRIMARY;

	for(;;)	{ 

		pthread_mutex_lock(&sync_mutex);
 			appStatus = dataTool.status;
		pthread_mutex_unlock(&sync_mutex);
                
 		if (appStatus == CONKEEPER_HAVE_TO_EXIT || appStatus == CONKEEPER_TO_BE_RESET){
  			if (dataTool.logMask >= LOGMASK_INFO){
       				logString.clear();
				logString.str("");
				logString << "HearbeatThread: Terminating... " <<endl;
				LOG(INFO, logString.str());
			}
                        
			resetHeartBeatAndExit (0);
		}

                if (!dataTool.redundancy) {
      			dataTool.activeZone = UNKNOWM;
                        sleep(10);
                        continue;
                }
                
      		sleep(5);
                
		switch (dataTool.activeZone) {
			case UNKNOWM:{
                                if (TryToconnecTo == PRIMARY) {
                        		strcpy (remote_ip, heartBeatData.primary_ip_host);
                                	if (checkConnection(remote_ip)) {
						if (dataTool.logMask >= LOGMASK_DEBUG) {
							logString.clear();
							logString.str("");
							logString << "HearbeatThread: Connected to PRIMARY zone."<< endl;
							LOG(DEBUG, logString.str());
						}
                
						pthread_mutex_lock(&sync_mutex);
                					dataTool.activeZone = PRIMARY;
						pthread_mutex_unlock(&sync_mutex);
                                	}
                                        else {
                                               TryToconnecTo = SECONDARY; 
                                        }
                                        
                                }
                                else {
                        		strcpy (remote_ip, heartBeatData.secondary_ip_host);
                                	if (checkConnection(remote_ip)) {
						if (dataTool.logMask >= LOGMASK_DEBUG) {
							logString.clear();
							logString.str("");
							logString << "HearbeatThread: Connected to SECONDARY zone."<< endl;
							LOG(DEBUG, logString.str());
						}
						pthread_mutex_lock(&sync_mutex);
                					dataTool.activeZone = SECONDARY;
						pthread_mutex_unlock(&sync_mutex);
                                	}
                                        else {
                                               TryToconnecTo = PRIMARY; 
                                        }
                                }
                                
				break;
			}
			case PRIMARY:{
                       	strcpy (remote_ip, heartBeatData.secondary_ip_host);
                                if (checkConnection(remote_ip)) {
					pthread_mutex_lock(&sync_mutex);
                				dataTool.activeZone = SECONDARY;
					pthread_mutex_unlock(&sync_mutex);
                                }
                                
                                break;
                        }
        
                         case SECONDARY:{
                        	strcpy (remote_ip, heartBeatData.primary_ip_host);
                                if (checkConnection(remote_ip)) {
					pthread_mutex_lock(&sync_mutex);
                				dataTool.activeZone = PRIMARY;
					pthread_mutex_unlock(&sync_mutex);
                                }
                                
                                break;
                        }
                }
         }//for(;;)

}


bool checkConnection(char * connection_host)
{
	bool result = false;
	struct sockaddr_in remote_addr;
	struct sockaddr_in local_addr;
	int sock_result;
	int errsv;
        stringstream logString;
        
     	heartBeatData.sock = socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);

	if (heartBeatData.sock == -1){
		if (dataTool.logMask >= LOGMASK_WARNING) {
			errsv = errno;
 			logString.clear();
			logString.str("");
			logString << "HearbeatThread : Create socket returned" << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(WARNING, logString.str());
                }
                                                        
		resetHeartBeatAndExit (1);
	}
        	
	memset(&remote_addr,0,sizeof(sockaddr_in));
	remote_addr.sin_family = AF_INET;
	remote_addr.sin_port = htons(heartBeatData.port);
	remote_addr.sin_addr.s_addr = inet_addr(connection_host);
	
	memset(&local_addr,0,sizeof(sockaddr_in));
	local_addr.sin_family = AF_INET;

	socklen_t len = sizeof(remote_addr);

	if(bind(heartBeatData.sock,(struct sockaddr*)&local_addr,sizeof(local_addr)) < 0)
	{
		if (dataTool.logMask >= LOGMASK_ERROR) {
			errsv = errno;
			logString.clear();
			logString.str("");
			logString << "HearbeatThread: Failed to bind to local socket: " << heartBeatData.sock << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(ERROR, logString.str());
		}
		resetHeartBeatAndExit (1);
	}

	sock_result = connect(heartBeatData.sock,(sockaddr*)&remote_addr,len);
		
	if (sock_result == -1 && errno != 115){
                
		if (dataTool.logMask >= LOGMASK_DEBUG) {
			errsv = errno;
			logString.clear();
			logString.str("");
			logString << "HearbeatThread: Failing to network connect to remote Server: " <<inet_ntoa(remote_addr.sin_addr) <<":"<<ntohs(remote_addr.sin_port) << endl;
			LOG(DEBUG, logString.str());
		}
                
		if(heartBeatData.sock != -1){
			close(heartBeatData.sock);
		}

		return false;
	}	
        		
	if(heartBeatData.sock != -1) { 
		
		fd_set fds;
		struct timeval tv;
		tv.tv_sec = 2;
		tv.tv_usec = 0;
		FD_ZERO(&fds);
		FD_SET(heartBeatData.sock, &fds);
			
		int res = send(heartBeatData.sock,(const char*)cer_msg,cer_len,0);

		if(res > 0) { 
			
			fd_set tmpset = fds;
			tv.tv_sec = 4;
			tv.tv_usec = 0;
					
			select(heartBeatData.sock+1, &tmpset, NULL, NULL, &tv);

			if(FD_ISSET(heartBeatData.sock, &tmpset)){ 
				result = receive_heartbeat_CEA();
				if(heartBeatData.sock != -1){
					close(heartBeatData.sock);
				}
																		
				return result;				
			} 
			else {
				if(heartBeatData.sock != -1){
					close(heartBeatData.sock);
				}
				return false;
			}

		} 
		else { 
			if(heartBeatData.sock != -1){
				close(heartBeatData.sock);
			}
			return false;
		} 
				
		
	} //if(diameter_sock != INVALID_SOCKET)

	if(heartBeatData.sock != -1){
		close(heartBeatData.sock);
	}
	resetHeartBeatAndExit (1);
        
        return true;

} //bool checkConnection(char *arg)


int create_heartbeat_CER(unsigned char *cermsg)
{ 
	int version=RFC__VERSION;
	int sub_attr_len=0;			
	char hex_value[4];  
        
	unsigned char	origin_host[] = "conkeeper.ericsson.se";
	unsigned char	origin_realm[] = "ericsson.se";
	unsigned char	product_name[] = "Ericsson Diameter";
        
	unsigned char	host_ip_address[4];
	unsigned char	vendor_id[4];
	char		conkeeper_host[100];
                
        getlocalhostname (conkeeper_host);

      	string IpHost = getIpByHostname (conkeeper_host);
	ip2oct(host_ip_address,IpHost.c_str());

	DiaMessage CERMessage = DiaMessage();
	AVP *avp;
	//Origin-Host

	avp = new AVP (origin__host,0x40,origin_host,version);
	CERMessage.addAVP (avp);
	free (avp);

	//Origin-Realm
	avp = new AVP (origin__realm,0x40,origin_realm,version);
	CERMessage.addAVP (avp);
	free (avp);
	
	//Host-IP-Address
	avp = new AVP (host__ip__address,0x40, host_ip_address, version, true);
	CERMessage.addAVP (avp);
	free (avp);

	//Vendor-ID
	int2oct(vendor_id,"0");
	avp = new AVP (vendor__id, 0x40, 4, vendor_id,version);
	CERMessage.addAVP (avp);
	free (avp);
	
	//Product-Name
	avp = new AVP (product__name, (uchar)0x00,product_name,version);
	CERMessage.addAVP (avp);
	free (avp);

	//Supported-Vendor-ID
	int2hex (hex_value,10415,4);
	AVP *sub_avp1 = new AVP (vendor__id,0x40, 4, (unsigned char*)hex_value, version);
	sub_attr_len = sub_avp1->get_length();
			
	//Auth-Application-ID
	int2hex(hex_value, 16777216,4);
	AVP *sub_avp2 = new AVP (auth__application__id,0x40, 4, (unsigned char*)hex_value, version);
	sub_attr_len += sub_avp2->get_length();
	
	//Vendor-Specific-Application-Id
	AVP *parent_avp = new AVP (vendor__specific__application__id,0x40, version,sub_attr_len);
			
	parent_avp->add_sub_attribute(sub_avp1);
	parent_avp->add_sub_attribute(sub_avp2);
					
	free (sub_avp1);
	free (sub_avp2);
				
	CERMessage.addAVP (parent_avp);
		
	//firmware revision
	int2hex (hex_value, 1, 4);
	avp = new AVP (firmware__revision, (unsigned char)0x00, 4, (unsigned char*)hex_value,version);
	CERMessage.addAVP (avp);
	free (avp);

	//finishing the message
	CERMessage.message(cermsg);
	return CERMessage.get_size();
} 

bool receive_heartbeat_CEA () 
{

	DIAMETER_HEADER *head;
	AVP_HEADER *avphead;
        stringstream logString;
	
	bool ok = false;
	uchar buff[DEFAULT_BUFFER_SIZE];
	int received;
	
	memset(buff,0,DEFAULT_BUFFER_SIZE);
						
	received = recv(heartBeatData.sock,(LPTSTR)buff,DEFAULT_BUFFER_SIZE,0);

	if(received > 0)
	{ 
		if(received > DIAMETER_HEADER_LENGTH)
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
			while(offs<received){ 
				avphead = (AVP_HEADER*)(buff+offs);
				uint avplen = 0;
	
				avplen = (avphead->avp_len[0] << 16) + (avphead->avp_len[1] << 8) + avphead->avp_len[2];
	
				if(avphead->avp_code == result__code){ 
						
					if(avphead->value == result__diameter__success){
						if (dataTool.logMask >= LOGMASK_DEBUG) {
 							logString.clear();
							logString.str("");
							logString << "HearbeatThread: CER-CEA connection established with Diameter." << endl;
							LOG(DEBUG, logString.str());
                                		}
					}
					else{
						ok = false;
						if (dataTool.logMask >= LOGMASK_DEBUG) {
                                                        
 							logString.clear();
							logString.str("");
                                                        
							uchar * ptr = (uchar *) &(avphead->value);
							int errorCode = *(ptr);
							errorCode = (errorCode << 8) + (*(ptr+1));
							errorCode = (errorCode << 8) + (*(ptr+2));
							errorCode = (errorCode << 8) + (*(ptr+3));

							switch (avphead->value){
								case result__diameter__invalid__avp__length:
									logString << "HearbeatThread: CER-CEA ERROR. Result_code AVP value: DIAMETER_INVALID_AVP_LENGTH." << endl;
 									LOG(DEBUG, logString.str());
									break;
								case result__diameter__no_common__application:
									logString << "HearbeatThread: CER-CEA ERROR. Result_code AVP value: DIAMETER_NO_COMMON_APPLICATION." << endl;
 									LOG(DEBUG, logString.str());
									break;
								case result__diameter__invalid__avp__value:
									logString << "HearbeatThread: CER-CEA ERROR. Result_code AVP value: DIAMETER_INVALID_AVP_VALUE." << endl;
 									LOG(DEBUG, logString.str());
									break;
								case result__diameter__unable_to_comply:
									logString << "HearbeatThread: CER-CEA ERROR. Result_code AVP value: DIAMETER_UNABLE_TO_COMPLY." << endl;
 									LOG(DEBUG, logString.str());
									break;
								default:
									logString << "HearbeatThread: CER-CEA ERROR. Result_code AVP value: "<< errorCode << endl;
 									LOG(DEBUG, logString.str());
									break;
							}
                                                }
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
	else{ 
		if(received == -1){
			if (dataTool.logMask >= LOGMASK_EVENT) {                
 				logString.clear();
				logString.str("");
				logString << "HearbeatThread : TCP connection Broken Pipe." << endl;
				LOG(EVENT, logString.str());
                        }
		}
		if(received == 0){
			if (dataTool.logMask >= LOGMASK_EVENT) {                
 				logString.clear();
				logString.str("");
				logString << "HearbeatThread : TCP connection closed by peer." << endl;
				LOG(EVENT, logString.str());
                        }
		}
		
		return false;


	} //else to if(received > 0)
	

	if(!ok){
		if (dataTool.logMask >= LOGMASK_DEBUG) {
			logString.clear();
			logString.str("");
			logString << "HearbeatThread: Error during CER-CEA process." << endl;
			LOG(DEBUG, logString.str());
		}
		return false;
	}
	return true;
}


