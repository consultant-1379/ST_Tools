#include "ConnectionKeeper.h"

using namespace std;

extern vector<Connection> v_connections;
extern vector<Listener> v_listeners;
extern time_t start, stop, lastaction;
extern pthread_mutex_t sync_mutex;
extern applicationData dataTool;
      
void* _LdapClientThread(void *arg)
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
	memset(&local_addr,0,sizeof(local_addr));
	local_addr.sin_family = AF_INET;
	local_addr.sin_addr.s_addr = INADDR_ANY;
	int bind_result;
        
	myConnection->client.status = CONNECTING;   

	pthread_mutex_lock(&sync_mutex);
		appStatus = dataTool.status;
		myStatus = myConnection->client.status;
	pthread_mutex_unlock(&sync_mutex);

	if (appStatus == CONKEEPER_HAVE_TO_EXIT || appStatus == CONKEEPER_TO_BE_RESET || myStatus == TO_BE_CLOSED) {
                if (dataTool.logMask >= LOGMASK_INFO) {
			logString.clear();
			logString.str("");
			logString << "LdapClientThread_" << myConnection->position <<": Client connection shall be closed" <<endl;
			LOG(INFO, logString.str());
                }
                       
		resetClientConnectionAndExit (myConnection, OFFLINE);
	}
        
	if (dataTool.logMask >= LOGMASK_INFO) {
       		logString.clear();
		logString.str("");
		logString << "LdapClientThread_" << myConnection->position <<": Starting..." <<endl;
		LOG(INFO, logString.str());
        }
       
	localSockId = socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
        
	if (localSockId == -1){
		errsv = errno;
		logString.clear();
		logString.str("");
		logString << "LdapClientThread_" << myConnection->position <<": Create socket returned" << endl;
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
			logString << "LdapClientThread_" << myConnection->position <<": Failed when changing SO_SNDTIMEO" << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(WARNING, logString.str());
                }
	}

        bind_result = bind(localSockId,(struct sockaddr*)&local_addr,sizeof(local_addr));
 
	if( bind_result == -1){
		errsv = errno;
 		logString.clear();
		logString.str("");
		logString << "LdapClientThread_" << myConnection->position <<": Failed to bind to local socket " << localSockId << endl;
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
			logString << "LdapClientThread_" << myConnection->position <<": Failing to network connect to remote Server " <<inet_ntoa(remote_addr.sin_addr) <<":"<<ntohs(remote_addr.sin_port) << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(WARNING, logString.str());
		}
		resetClientConnectionAndExit (myConnection, TO_BE_RESTARTED);
	}			

	if (dataTool.logMask >= LOGMASK_INFO) {
		logString.clear();
		logString.str("");
		logString << "LdapClientThread_" << myConnection->position <<": Connected to remote Server " <<inet_ntoa(remote_addr.sin_addr) <<":"<<ntohs(remote_addr.sin_port) << endl;
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
			if (dataTool.logMask >= LOGMASK_INFO) {
       				logString.clear();
				logString.str("");
				logString << "LdapClientThread_" << myConnection->position <<": Client connection shall be closed" <<endl;
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
                			if (!sendFirstLdapMessage(myConnection)) {
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
					logString << "LdapClientThread_" << myConnection->position <<": Client becomes ready" << endl;
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
				if(myConnection->client.sock == -1) 	resetClientConnectionAndExit (myConnection, OFFLINE);
				select(myConnection->client.sock+1, &tmpset, NULL, NULL, &tv);

				//if event happened
				if(FD_ISSET(myConnection->client.sock, &tmpset)){ 
					//reading from the socket
					received = recv(myConnection->client.sock,buff,DEFAULT_BUFFER_SIZE,0);

					if(received < 1){
						if (dataTool.logMask >= LOGMASK_EVENT) {
 							logString.clear();
							logString.str("");
							logString << "LdapClientThread_" << myConnection->position <<": Error reading." << endl;
							logString <<"\tLDAP client shall be re-started" << endl;
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
							logString << "LdapClientThread_" << myConnection->position <<": TCP connection closed by peer." << endl;
							logString <<"\tLDAP client shall be re-started" << endl;
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
									logString << "LdapClientThread_" << myConnection->position <<": Error sending message" << endl;
									LOG(DEBUG, logString.str());
                      						}
                      						else {
 									logString.clear();
									logString.str("");
									logString << "LdapClientThread_" << myConnection->position <<": Message sent." << endl;
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
								logString << "LdapClientThread_" << myConnection->position <<": Discarded incomming message." << endl;
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
					logString << "LdapClientThread_" << myConnection->position <<": LDAP connection shall be closed" << endl;
					LOG(INFO, logString.str());
                                }
                                
				resetClientConnectionAndExit (myConnection, OFFLINE);
        
				break;
			}
                
                        default:
				if (dataTool.logMask >= LOGMASK_DEBUG) {
 					logString.clear();
					logString.str("");
					logString << "LdapClientThread_" << myConnection->position <<": Wrong connection state" << endl;
					LOG(DEBUG, logString.str());
                                }
                                
                                pthread_mutex_lock(&sync_mutex);
 					dataTool.status = CONKEEPER_TO_BE_RESET;
				pthread_mutex_unlock(&sync_mutex);
                
				break;
                        
                } //switch (myStatus)                         
	} //while (true)
} 

bool sendFirstLdapMessage(Connection *myConnection)
{
        
	int send_bytes = 0;
	int received = 0;
	fd_set fds, tmpset;
	struct timeval tv;
        bool sentOk = false;
	char buff[DEFAULT_BUFFER_SIZE];
 	ConnectionStatus myStatus;
 	ConKeeperStatus appStatus;
        stringstream logString;
        LDAP_MESSAGE *head;
        
	send_bytes = send(myConnection->client.sock,(const char*)myConnection->message,myConnection->messageLen,0); 
	if (send_bytes != myConnection->messageLen) {
		if (dataTool.logMask >= LOGMASK_INFO) {
			logString.clear();
			logString.str("");
			logString << "LdapClientThread_" << myConnection->position <<": Error sending message " << endl;
			LOG(INFO, logString.str());
                }
	}
	else {
		if (dataTool.logMask >= LOGMASK_INFO) {                
			logString.clear();
			logString.str("");
			logString << "LdapClientThread_" << myConnection->position <<": First message sent OK " << endl;
			LOG(INFO, logString.str());
                }
                
		while (true){
			
			pthread_mutex_lock(&sync_mutex);
				appStatus = dataTool.status;
				myStatus = myConnection->client.status;
			pthread_mutex_unlock(&sync_mutex);

			if (myStatus == TO_BE_CLOSED || appStatus == CONKEEPER_HAVE_TO_EXIT || appStatus == CONKEEPER_TO_BE_RESET){
  				if (dataTool.logMask  >= LOGMASK_INFO){
       					logString.clear();
					logString.str("");
					logString << "LdapClientThread_" << myConnection->position <<": Client connection shall be closed" <<endl;
					LOG(INFO, logString.str());
				}
                        
				resetClientConnectionAndExit (myConnection, OFFLINE);
			}
                
                	//setting the timeout for the select operation
			tv.tv_sec = 4;
			tv.tv_usec = 0;
			FD_ZERO(&fds);
			FD_SET(myConnection->client.sock, &fds);
		
			tmpset = fds;
			//passive wait for any action in any of the socket
			select(myConnection->client.sock+1, &tmpset, NULL, NULL, &tv);
                
 			//if event happened
			if(FD_ISSET(myConnection->client.sock, &tmpset)){ 
				//reading from the socket
				received = recv(myConnection->client.sock,buff,DEFAULT_BUFFER_SIZE,0);
                        
				if(received < 1){
					if (dataTool.logMask >= LOGMASK_EVENT) {                
 						logString.clear();
						logString.str("");
						logString << "LdapClientThread_" << myConnection->position <<": Error reading." << endl;
						LOG(EVENT, logString.str());
                                	}
                                        
					return sentOk;
 				} 
                        	else if (received == 0){
					if (dataTool.logMask >= LOGMASK_EVENT) {                
 						logString.clear();
						logString.str("");
						logString << "LdapClientThread_" << myConnection->position <<": TCP connection closed by peer." << endl;
						LOG(EVENT, logString.str());
                                	}
                                        
					return sentOk;
				}
                       		else {
					// some data received                                                
                                	buff[received]='\0';
                                        
                                	head = (LDAP_MESSAGE*)buff;
                                	char cmd = head->cmd_code[0];
					uint res_code = (head->result_code[0]<<16) + (head->result_code[1]<<8) + head->result_code[2];
                                
					if (dataTool.logMask >= LOGMASK_EVENT) {                
 						logString.clear();
						logString.str("");
						logString << "LdapClientThread_" << myConnection->position <<": Answer to first message OK." << endl;
						logString << "\tldap command code: " << cmd <<", ldap result code: "<< res_code << endl;
						LOG(EVENT, logString.str());
                                	}
                                           
                                	if (res_code == success_bind) {
                                		return true;
                                	}
				}
			} //if(FD_ISSET)
                }// end while (true)
	}
       
        return sentOk;
        
}
