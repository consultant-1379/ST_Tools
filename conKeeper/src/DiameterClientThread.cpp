#include "ConnectionKeeper.h"

using namespace std;

extern vector<Connection> v_connections;
extern vector<Listener> v_listeners;
extern time_t start, stop, lastaction;
extern pthread_mutex_t sync_mutex;
extern applicationData dataTool;

        
void* _DiameterClientThread(void *arg)
{
       	Connection	*myConnection = (Connection *)arg;         
 	ConnectionStatus myStatus;
        stringstream logString;
	ConKeeperStatus appStatus;
	int localSockId = -1;
	int errsv;
        int value;
	socklen_t value_len;
	char buff[DEFAULT_BUFFER_SIZE];
	fd_set fds, tmpset;
	struct timeval tv;
	int received ;
	struct sockaddr_in local_addr;
	local_addr.sin_family = AF_INET;
	memset(&local_addr,0,sizeof(local_addr));
	local_addr.sin_family = AF_INET;
	local_addr.sin_addr.s_addr = INADDR_ANY;
	int bind_result;
        
	myConnection->client.status = CONNECTING;   
            
	pthread_mutex_lock(&sync_mutex);
		appStatus = dataTool.status;
		myStatus = myConnection->client.status;
	pthread_mutex_unlock(&sync_mutex);

	if (appStatus == CONKEEPER_HAVE_TO_EXIT || appStatus == CONKEEPER_TO_BE_RESET || myStatus == TO_BE_CLOSED){
  		if (dataTool.logMask >= LOGMASK_INFO){
       			logString.clear();
			logString.str("");
			logString << "DiameterClientThread_" << myConnection->position <<": Client connection shall be closed" <<endl;
			LOG(INFO, logString.str());
		}
                        
		resetClientConnectionAndExit (myConnection, OFFLINE);
	}
        
	if (dataTool.logMask >= LOGMASK_INFO){
       		logString.clear();
		logString.str("");
		logString << "DiameterClientThread_" << myConnection->position <<": Starting..." <<endl;
		LOG(INFO, logString.str());
        }
       
	localSockId = socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
        
	if (localSockId == -1){
		errsv = errno;
		logString.clear();
		logString.str("");
		logString << "DiameterClientThread_" << myConnection->position <<": Create socket returned" << endl;
		logString <<"\tError: " << strerror(errsv) << endl;
		LOG(ERROR, logString.str());
                resetClientConnectionAndExit (myConnection, OFFLINE);
	}
                
        struct timeval sendTimer;
                                
	sendTimer.tv_sec = DEFAULT_SEND_TIME;
	value_len = sizeof (value);

        if (setsockopt (localSockId, SOL_SOCKET, SO_SNDTIMEO, &sendTimer, sizeof (sendTimer))) {
		if (dataTool.logMask >= LOGMASK_WARNING) {
			errsv = errno;
 			logString.clear();
			logString.str("");
			logString << "DiameterClientThread_" << myConnection->position <<": Failed step 1 when changing SO_SNDTIMEO" << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(WARNING, logString.str());
                }
	}

	bind_result = bind(localSockId,(struct sockaddr*)&local_addr,sizeof(local_addr));
 
	if( bind_result == -1){
		errsv = errno;
 		logString.clear();
		logString.str("");
		logString << "DiameterClientThread_" << myConnection->position <<": Failed to bind to local socket " << localSockId << endl;
		logString <<"\tError: " << strerror(errsv) << endl;
		LOG(ERROR, logString.str());
                resetClientConnectionAndExit (myConnection, OFFLINE);
	}
        
	struct sockaddr_in remote_addr;
        
	if (dataTool.redundancy){
                
		if (dataTool.activeZone == SECONDARY){
			remote_addr = myConnection->client.secondary_remote_addr;
		} 
		else {
			remote_addr = myConnection->client.primary_remote_addr;
		}
                
	}
	else {
		remote_addr = myConnection->client.primary_remote_addr;
	}
                                        
	int sock_result = connect(localSockId,(sockaddr*)&remote_addr,sizeof(remote_addr));
	if(sock_result == -1){
		if (dataTool.logMask >= LOGMASK_WARNING) {
			errsv = errno;
			logString.clear();
			logString.str("");
			logString << "DiameterClientThread_" << myConnection->position <<": Failing to network connect to remote Server " <<inet_ntoa(remote_addr.sin_addr) <<":"<<ntohs(remote_addr.sin_port) << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(WARNING, logString.str());
		}
		resetClientConnectionAndExit (myConnection, TO_BE_RESTARTED);
	}			

	if (dataTool.logMask >= LOGMASK_INFO) {
		logString.clear();
		logString.str("");
		logString << "DiameterClientThread_" << myConnection->position <<": Connected to remote Server " <<inet_ntoa(remote_addr.sin_addr) <<":"<<ntohs(remote_addr.sin_port) << endl;
		LOG(INFO, logString.str());
	}

	pthread_mutex_lock(&sync_mutex);
                myConnection->client.sock = localSockId;
	pthread_mutex_unlock(&sync_mutex);
        
	FD_ZERO(&fds);
	FD_SET(localSockId, &fds);
        
 	while (true){ 
                
		pthread_mutex_lock(&sync_mutex);
                        myStatus = myConnection->client.status;
			appStatus = dataTool.status;
		pthread_mutex_unlock(&sync_mutex); 
                
 		if (appStatus == CONKEEPER_HAVE_TO_EXIT || appStatus == CONKEEPER_TO_BE_RESET){
  			if (dataTool.logMask >= LOGMASK_INFO){
       				logString.clear();
				logString.str("");
				logString << "DiameterClientThread_" << myConnection->position <<": Client connection shall be closed" <<endl;
				LOG(INFO, logString.str());
			}
                        
			resetClientConnectionAndExit (myConnection, OFFLINE);
		}
                
		switch (myStatus) {                        
                        
			case TO_BE_RESTARTED:{
                                                
				resetClientConnectionAndExit (myConnection, TO_BE_RESTARTED);                                
                                break;
                        }
                        
                        
			case CONNECTING:{
                                        
        			if ((myConnection->messageLen != 0) && (myConnection->firstConnectionOk)){
                			if (!sendFirstDiameterMessage(myConnection)) {
						pthread_mutex_lock(&sync_mutex);
                                        		if (myConnection->client.status == CONNECTING)
								myConnection->client.status = TO_BE_RESTARTED;
						pthread_mutex_unlock(&sync_mutex);
                                                
                                       	break;
                                        }  
         			}
                                
				if (dataTool.logMask >= LOGMASK_INFO) {
 					logString.clear();
					logString.str("");
					logString << "DiameterClientThread_" << myConnection->position <<": Client becomes ready" << endl;
					LOG(INFO, logString.str());
                		}
                                
				pthread_mutex_lock(&sync_mutex);
                                        if (myConnection->client.status == CONNECTING)
						myConnection->client.status = ONLINE;
						myConnection->client.connectedTo = dataTool.activeZone;
                		pthread_mutex_unlock(&sync_mutex);
                                
                                break;
                        }

			case ONLINE:{
                                
                                if (dataTool.redundancy){
                                        if (dataTool.activeZone != myConnection->client.connectedTo) {
						pthread_mutex_lock(&sync_mutex);
                                        		if (myConnection->client.status == ONLINE)
								myConnection->client.status = TO_BE_RESTARTED;
						pthread_mutex_unlock(&sync_mutex);
                                                break;
                                        }
                                }
                                
				//setting the timeout for the select operation
				tv.tv_sec = 2;
				tv.tv_usec = 0;
		
				tmpset = fds;
				//passive wait for any action in any of the socket
				if(myConnection->client.sock == -1) resetClientConnectionAndExit (myConnection, OFFLINE);
				select(myConnection->client.sock+1, &tmpset, NULL, NULL, &tv);

				//if event happened
				if(FD_ISSET(myConnection->client.sock, &tmpset)){ 
					//reading from the socket
					received = recv(myConnection->client.sock,buff,DEFAULT_BUFFER_SIZE,0);

					if(received < 1){
						if (dataTool.logMask >= LOGMASK_EVENT) {
 							logString.clear();
							logString.str("");
							logString << "DiameterClientThread_" << myConnection->position <<": Error reading." << endl;
							logString <<"\tDIAMETER client shall be re-started" << endl;
							LOG(EVENT, logString.str());
                                		}
                                        	if (myConnection->client.status == ONLINE)
							resetClientConnectionAndExit (myConnection, TO_BE_RESTARTED);
                
                                        	break;
					} 
                        		else if (received == 0){
						if (dataTool.logMask >= LOGMASK_EVENT) {
 							logString.clear();
							logString.str("");
							logString << "DiameterClientThread_" << myConnection->position <<":TCP connection closed by peer." << endl;
							logString <<"\tDIAMETER client shall be re-started" << endl;
							LOG(EVENT, logString.str());
                                		}
                
                                        	if (myConnection->client.status == ONLINE)
							resetClientConnectionAndExit (myConnection, TO_BE_RESTARTED);
                
                                        	break;
					}
                        		else {
						// some data received
                                		if (myConnection->server.status == ONLINE) {
							int send_bytes = 0;
                                        		send_bytes = send(myConnection->server.sock,(const char*)buff,received,0); 
							if (dataTool.logMask >= LOGMASK_DEBUG) {
                      						if (send_bytes != received) {
 									logString.clear();
									logString.str("");
									logString << "DiameterClientThread_" << myConnection->position <<":Error sending message" << endl;
									LOG(DEBUG, logString.str());
                      						}
                      						else {
 									logString.clear();
									logString.str("");
									logString << "DiameterClientThread_" << myConnection->position <<":Message sent." << endl;
									LOG(DEBUG, logString.str());
                        					}
             						}
                                                        if ((!myConnection->firstConnectionOk) && (send_bytes == received)) {
                        					pthread_mutex_lock(&sync_mutex);
                        						myConnection->firstConnectionOk = true;
                        					pthread_mutex_unlock(&sync_mutex);
                        				}
                                		}
                                		else {
							if (dataTool.logMask >= LOGMASK_DEBUG) {
 								logString.clear();
								logString.str("");
								logString << "DiameterClientThread_" << myConnection->position <<":Discarded incomming message." << endl;
								LOG(DEBUG, logString.str());
                                        		}
						}
					}
				} //if(FD_ISSET)
                                
				break;
                        } // case ONLINE:
                        
 			case TO_BE_CLOSED:{
                                
				if (dataTool.logMask >= LOGMASK_INFO) {
 					logString.clear();
					logString.str("");
					logString << "DiameterClientThread_" << myConnection->position <<": DIAMETER connection shall be closed" << endl;
					LOG(INFO, logString.str());
                		}
				resetClientConnectionAndExit (myConnection, OFFLINE);
        
				break;
			}
                
                       default:
				if (dataTool.logMask >= LOGMASK_DEBUG) {
 					logString.clear();
					logString.str("");
					logString << "DiameterClientThread_" << myConnection->position <<": Wrong connection state" << endl;
					LOG(DEBUG, logString.str());
                		}
                                pthread_mutex_lock(&sync_mutex);
 					dataTool.status = CONKEEPER_TO_BE_RESET;
				pthread_mutex_unlock(&sync_mutex);
                
				break;
                        
                } //switch (myStatus)                         
	} //while (true)
} 


bool sendFirstDiameterMessage(Connection *myConnection)
{        
	int send_bytes = 0;
        bool sentOk = false;
        stringstream logString;
        
	send_bytes = send(myConnection->client.sock,(const char*)myConnection->message,myConnection->messageLen,0); 
	if (send_bytes != myConnection->messageLen) {
		if (dataTool.logMask  >= LOGMASK_INFO) {
			logString.clear();
			logString.str("");
			logString << "DiameterClientThread_" << myConnection->position <<":Error sending message " << endl;
			LOG(INFO, logString.str());
                }
                
	}
	else {
		if (receive_CEA(myConnection)) {
                       sentOk = true; 
                }
	}
       
        return sentOk;
}

bool receive_CEA (Connection *myConnection) 
{
 	ConnectionStatus myStatus;
 	ConKeeperStatus appStatus;
        stringstream logString;
	
	uchar buff[DEFAULT_BUFFER_SIZE];
	bool receivedOk = false;
		
	DIAMETER_HEADER *head;
	AVP_HEADER *avphead;
	int received = 0;
	struct timeval tv;
	fd_set fds;
	FD_ZERO(&fds);
	FD_SET(myConnection->client.sock, &fds);
					
	int read_retries=0;
	int rest;
	int toread;
	int dp_size;
	fd_set tmpset;
	puchar pbuf;

	while (true){
			
		pthread_mutex_lock(&sync_mutex);
			appStatus = dataTool.status;
			myStatus = myConnection->client.status;
		pthread_mutex_unlock(&sync_mutex);

		if (myStatus == TO_BE_CLOSED || appStatus == CONKEEPER_HAVE_TO_EXIT || appStatus == CONKEEPER_TO_BE_RESET){
  			if (dataTool.logMask  >= LOGMASK_INFO){
       				logString.clear();
				logString.str("");
				logString << "DiameterClientThread_" << myConnection->position <<": Client connection shall be closed" <<endl;
				LOG(INFO, logString.str());
			}
                        
			resetClientConnectionAndExit (myConnection, OFFLINE);
		}
               			
		tv.tv_sec = 4;
		tv.tv_usec = 0;
		tmpset = fds;
		int koll;
		koll = select(myConnection->client.sock +1, &tmpset, NULL, NULL, &tv);
                
		if (dataTool.logMask  >= LOGMASK_INFO) {
 			logString.clear();
			logString.str("");
			logString << "DiameterClientThread_" << myConnection->position <<": Start wait for CEA" <<endl;
			LOG(INFO, logString.str());
                }
                
		if(FD_ISSET(myConnection->client.sock, &tmpset)) { 

			memset(buff,0,DEFAULT_BUFFER_SIZE);

			received = recv(myConnection->client.sock,(LPTSTR)buff,DIAMETER_HEADER_LENGTH,0);

			if(received < DIAMETER_HEADER_LENGTH) { 

				if(received < 1){ 
					if(received == -1){ 
						if (dataTool.logMask  >= LOGMASK_EVENT) {
 							logString.clear();
							logString.str("");
							logString << "DiameterClientThread_" << myConnection->position <<": Error reading." << endl;
							LOG(EVENT, logString.str());
                                                }
						return receivedOk;
					} 
					if(received == 0){ 
						if (dataTool.logMask >= LOGMASK_EVENT) {
 							logString.clear();
							logString.str("");
							logString << "DiameterClientThread_" << myConnection->position <<":TCP connection closed by peer." << endl;
							LOG(EVENT, logString.str());
                                                }
						return receivedOk;
					} 
				} 
                                
				pbuf = buff;
				pbuf += received;
				toread = DIAMETER_HEADER_LENGTH - received;
                                
				while(received < DIAMETER_HEADER_LENGTH) { 
				
					pthread_mutex_lock(&sync_mutex);
						appStatus = dataTool.status;
						myStatus = myConnection->client.status;
					pthread_mutex_unlock(&sync_mutex);

					if (myStatus == TO_BE_CLOSED || appStatus == CONKEEPER_HAVE_TO_EXIT || appStatus == CONKEEPER_TO_BE_RESET){
  						if (dataTool.logMask >= LOGMASK_INFO){
       							logString.clear();
							logString.str("");
							logString << "DiameterClientThread_" << myConnection->position <<": Client connection shall be closed" <<endl;
							LOG(INFO, logString.str());
						}
                        
						resetClientConnectionAndExit (myConnection, OFFLINE);
					}
		
					tmpset = fds;
					tv.tv_sec = 2;
					tv.tv_usec = 0;
					select(myConnection->client.sock + 1, &tmpset, NULL, NULL, &tv);
					if(FD_ISSET(myConnection->client.sock, &tmpset)){ 
						rest = recv(myConnection->client.sock,(LPTSTR)pbuf,toread,0);
                                                
						if(rest == -1){ 
							if (dataTool.logMask >= LOGMASK_EVENT) {
 								logString.clear();
								logString.str("");
								logString << "DiameterClientThread_" << myConnection->position <<": Error reading " << endl;
								LOG(EVENT, logString.str());
                                                	}
							return receivedOk;
						} 
						if(rest == 0){ 
							if (dataTool.logMask >= LOGMASK_EVENT) {
 								logString.clear();
								logString.str("");
								logString << "DiameterClientThread_" << myConnection->position <<":TCP connection closed by peer." << endl;
								LOG(EVENT, logString.str());
                                                	}
							return receivedOk;
						} 
                                                
						toread -= rest;
						received += rest;
						pbuf += rest;
							
					} 
					else { 
						read_retries++;
						if(read_retries == 20){ 
							if (dataTool.logMask >= LOGMASK_EVENT) {
 								logString.clear();
								logString.str("");
								logString << "DiameterClientThread_" << myConnection->position <<":Too many retries reading the compleate diameter packet" << endl;
								logString <<"\tDIAMETER client shall be re-started" << endl;
								LOG(EVENT, logString.str());
                                                	}
							return receivedOk;
							
						} 
					} 
				} //while(received < DIAMETER_HEADER_LENGTH)
			} //if(received < DIAMETER_HEADER_LENGTH)
				
			pbuf = buff;
			if (!read_message_body (myConnection, 0, &pbuf,fds, &dp_size)) {
				if (dataTool.logMask >= LOGMASK_EVENT) {
 					logString.clear();
					logString.str("");
					logString << "DiameterClientThread_" << myConnection->position <<":Error reading message body." << endl;
					logString <<"\tDIAMETER client shall be re-started" << endl;
					LOG(EVENT, logString.str());
				}
				return receivedOk;
                        }
				
			head = (DIAMETER_HEADER*)buff;
			uint cmd_code = (head->cmd_code[0]<<16) + (head->cmd_code[1]<<8) + head->cmd_code[2];
			
			if(cmd_code == cmd__code__cer) {

				int offs = DIAMETER_HEADER_LENGTH;
				while(offs<dp_size){ 
			
					avphead = (AVP_HEADER*)(buff+offs);
					uint avplen = 0;
	
					avplen = (avphead->avp_len[0] << 16) + (avphead->avp_len[1] << 8) + avphead->avp_len[2];
	
					if(avphead->avp_code == result__code){ 
						if(avphead->value == result__diameter__success){
							if (dataTool.logMask >= LOGMASK_EVENT) {
 								logString.clear();
								logString.str("");
								logString << "DiameterClientThread_" << myConnection->position <<": CER-CEA connection established with Diameter Server." << endl;
								LOG(EVENT, logString.str());
                                                	}
                                                        receivedOk = true;
							return receivedOk;
						}
						else {
							if (dataTool.logMask >= LOGMASK_INFO) {
 								logString.clear();
								logString.str("");
								uchar * ptr = (uchar *) &(avphead->value);
								int errorCode = *(ptr);
								errorCode = (errorCode << 8) + (*(ptr+1));
								errorCode = (errorCode << 8) + (*(ptr+2));
								errorCode = (errorCode << 8) + (*(ptr+3));

								switch (avphead->value) {
									case result__diameter__invalid__avp__length:
										logString << "DiameterClientThread_" << myConnection->position <<":CER-CEA ERROR. Result_code AVP value: " <<errorCode <<" DIAMETER_INVALID_AVP_LENGTH" << endl;
										break;
									case result__diameter__no_common__application:
										logString << "DiameterClientThread_" << myConnection->position <<":CER-CEA ERROR. Result_code AVP value: " <<errorCode <<" DIAMETER_NO_COMMON_APPLICATION" << endl;
										break;
									case result__diameter__invalid__avp__value:
										logString << "DiameterClientThread_" << myConnection->position <<":CER-CEA ERROR. Result_code AVP value: " <<errorCode <<" DIAMETER_INVALID_AVP_VALUE" << endl;
										break;
									case result__diameter__unable_to_comply:
										logString << "DiameterClientThread_" << myConnection->position <<":CER-CEA ERROR. Result_code AVP value: " <<errorCode <<" DIAMETER_UNABLE_TO_COMPLY" << endl;
										break;
									default:
										logString << "DiameterClientThread_" << myConnection->position <<":CER-CEA ERROR. Result_code AVP value: " <<errorCode << endl;
										break;
								}
                                                                LOG(INFO, logString.str());
                                                        }
							return receivedOk;
						} 
						break;
					} //if(avp == result__code)
					uint t = 0;
					while(((avplen + t)*8) % 32){
						t++;
					}
					offs += avplen + t;
				} //while(offs<received)

       				return receivedOk;

			} // (cmd_code == cmd__code__cer)
			else {
				if (dataTool.logMask >= LOGMASK_EVENT) {
 					logString.clear();
					logString.str("");
					logString << "DiameterClientThread_" << myConnection->position <<":CEA not received." << endl;
					LOG(EVENT, logString.str());
				}
				return receivedOk;
			}	

		} //if(FD_ISSET(diameter_sock, &tmpset))
		else{
			read_retries++;
			if(read_retries == 2){ 
				if (dataTool.logMask >= LOGMASK_EVENT) {
 					logString.clear();
					logString.str("");
					logString << "DiameterClientThread_" << myConnection->position <<":TIME OUT waiting for CEA." << endl;
					LOG(EVENT, logString.str());
				}
				return receivedOk;
			}
		}
	} //while(true)

	return receivedOk;
} 

bool read_message_body (Connection *myConnection, int bytes_to_read, puchar *p_head,fd_set fds, int *dp_size)
{

 	ConnectionStatus myStatus;
 	ConKeeperStatus appStatus;
        stringstream logString;
	bool readOk = false;
	struct timeval tv;
	int received = -1;
	int rest = -1;
	puchar pbuf;
	DIAMETER_HEADER *l_head = (DIAMETER_HEADER*)(*p_head);
	int l_dp_size = (l_head->length[0]<<16) + (l_head->length[1]<<8) + l_head->length[2];
	int toread = l_dp_size - DIAMETER_HEADER_LENGTH;
	pbuf = (*p_head)+DIAMETER_HEADER_LENGTH;
	fd_set tmpset = fds;
	tv.tv_sec = 2;
	tv.tv_usec = 0;

	do {
		select(myConnection->client.sock + 1, &tmpset, NULL, NULL, &tv);

		pthread_mutex_lock(&sync_mutex);
			appStatus = dataTool.status;
			myStatus = myConnection->client.status;
		pthread_mutex_unlock(&sync_mutex);

		if (myStatus == TO_BE_CLOSED || appStatus == CONKEEPER_HAVE_TO_EXIT || appStatus == CONKEEPER_TO_BE_RESET){
  			if (dataTool.logMask >= LOGMASK_INFO){
       				logString.clear();
				logString.str("");
				logString << "DiameterClientThread_" << myConnection->position <<": Client connection shall be closed" <<endl;
				LOG(INFO, logString.str());
			}
                        
			resetClientConnectionAndExit (myConnection, OFFLINE);
		}

	} while (!FD_ISSET(myConnection->client.sock, &tmpset));

	if(FD_ISSET(myConnection->client.sock, &tmpset)){ 
		received = recv(myConnection->client.sock,(LPTSTR)pbuf,toread,0);

		if(received < toread){ 
			pbuf += received;
			int toread1 = toread - received;
			while(received < toread) { 
				pthread_mutex_lock(&sync_mutex);
					appStatus = dataTool.status;
					myStatus = myConnection->client.status;
				pthread_mutex_unlock(&sync_mutex);

				if (myStatus == TO_BE_CLOSED || appStatus == CONKEEPER_HAVE_TO_EXIT || appStatus == CONKEEPER_TO_BE_RESET){
  					if (dataTool.logMask >= LOGMASK_INFO){
       						logString.clear();
						logString.str("");
						logString << "DiameterClientThread_" << myConnection->position <<": Client connection shall be closed" <<endl;
						LOG(INFO, logString.str());
					}
                        
					resetClientConnectionAndExit (myConnection, OFFLINE);
				}
			
				select(myConnection->client.sock + 1, &tmpset, NULL, NULL, &tv);
				if(FD_ISSET(myConnection->client.sock, &tmpset)){ 
					rest = recv(myConnection->client.sock,(LPTSTR)pbuf,toread1,0);
					if(rest == -1){ 
						if (dataTool.logMask >= LOGMASK_EVENT) {
 							logString.clear();
							logString.str("");
							logString << "DiameterClientThread_" << myConnection->position <<": Error reading " << endl;
							LOG(EVENT, logString.str());
                                                }
							return readOk;
					} 
					if(rest == 0){ 
						if (dataTool.logMask >= LOGMASK_EVENT) {
 							logString.clear();
							logString.str("");
							logString << "DiameterClientThread_" << myConnection->position <<":TCP connection closed by peer." << endl;
							LOG(EVENT, logString.str());
                                                }
							return readOk;
					} 
					toread1 -= rest;
					received += rest;
					pbuf += rest;
				} //if(FD_ISSET(diameter_sock, &tmpset))
			} //while(received < toread)
		} //if(received < toread)
	} //if(FD_ISSET(diameter_sock, &tmpset))
	(*dp_size) = l_dp_size;

        readOk = true;
	return readOk;
}
