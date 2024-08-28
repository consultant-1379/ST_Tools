#include "ConnectionKeeper.h"

using namespace std;

extern vector<Connection> v_connections;
extern vector<Listener> v_listeners;
extern time_t start, stop, lastaction;
extern pthread_mutex_t sync_mutex;
extern applicationData dataTool;


void* _LoadClientThread(void *arg)
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
			logString << "LoadClientThread_" << myConnection->position <<": Client connection shall be closed" <<endl;
			LOG(INFO, logString.str());
		}
                        
		resetClientConnectionAndExit (myConnection, OFFLINE);
	}

	if (dataTool.logMask >= LOGMASK_INFO){
       		logString.clear();
		logString.str("");
		logString << "LoadClientThread_" << myConnection->position <<": Starting..." <<endl;
		LOG(INFO, logString.str());
        }

	localSockId = socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
        
	if (localSockId == -1){
		errsv = errno;
		logString.clear();
		logString.str("");
		logString << "LoadClientThread_" << myConnection->position <<": Create socket returned" << endl;
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
			logString << "LoadClientThread_" << myConnection->position <<": Failed step 1 when changing SO_SNDTIMEO" << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(WARNING, logString.str());
                }
	}

	bind_result = bind(localSockId,(struct sockaddr*)&local_addr,sizeof(local_addr));
 
	if( bind_result == -1){
		errsv = errno;
 		logString.clear();
		logString.str("");
		logString << "LoadClientThread_" << myConnection->position <<": Failed to bind to local socket " << localSockId << endl;
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
			logString << "LoadClientThread_" << myConnection->position <<": Failing to network connect to remote Server " <<inet_ntoa(remote_addr.sin_addr) <<":"<<ntohs(remote_addr.sin_port) << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(WARNING, logString.str());
		}
		resetClientConnectionAndExit (myConnection, TO_BE_RESTARTED);
	}			

	if (dataTool.logMask >= LOGMASK_INFO) {
		logString.clear();
		logString.str("");
		logString << "LoadClientThread_" << myConnection->position <<": Connected to remote Server " <<inet_ntoa(remote_addr.sin_addr) <<":"<<ntohs(remote_addr.sin_port) << endl;
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
				logString << "LoadClientThread_" << myConnection->position <<": Client connection shall be closed" <<endl;
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
						if (dataTool.logMask  >= LOGMASK_EVENT) {
 							logString.clear();
							logString.str("");
							logString << "LoadClientThread_" << myConnection->position <<": Error reading." << endl;
							logString <<"\tLOAD client shall be re-started" << endl;
							LOG(EVENT, logString.str());
                                		}
                                                
                                        	if (myConnection->client.status == ONLINE)
							resetClientConnectionAndExit (myConnection, TO_BE_RESTARTED);
                
                                        	break;
					} 
                        		else if (received == 0){
						if (dataTool.logMask  >= LOGMASK_EVENT) {
 							logString.clear();
							logString.str("");
							logString << "LoadClientThread_" << myConnection->position <<":TCP connection closed by peer." << endl;
							logString <<"\tLOAD client shall be re-started" << endl;
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
									logString << "LoadClientThread_" << myConnection->position <<":Error sending message" << endl;
									LOG(DEBUG, logString.str());
                      						}
                      						else {
 									logString.clear();
									logString.str("");
									logString << "LoadClientThread_" << myConnection->position <<":Message sent." << endl;
									LOG(DEBUG, logString.str());
                        					}
                                        		}
                                		}
                                		else {
							if (dataTool.logMask >= LOGMASK_DEBUG) {
 								logString.clear();
								logString.str("");
								logString << "LoadClientThread_" << myConnection->position <<":Discarded incomming message." << endl;
								LOG(DEBUG, logString.str());
                                        		}
                                		}
					}
				} //if(FD_ISSET)
                                
				break;
                        } // case ONLINE:
                        
			case TO_BE_CLOSED:{
                                
				if (dataTool.logMask  >= LOGMASK_INFO) {
 					logString.clear();
					logString.str("");
					logString << "LoadClientThread_" << myConnection->position <<": LOAD connection shall be closed" << endl;
					LOG(INFO, logString.str());
                		}
				resetClientConnectionAndExit (myConnection, OFFLINE);
        
				break;
			}
                
                        default:
				if (dataTool.logMask >= LOGMASK_DEBUG) {
 					logString.clear();
					logString.str("");
					logString << "LoadClientThread_" << myConnection->position <<": Wrong connection state" << endl;
					LOG(DEBUG, logString.str());
                		}
                                pthread_mutex_lock(&sync_mutex);
 					dataTool.status = CONKEEPER_TO_BE_RESET;
				pthread_mutex_unlock(&sync_mutex);
                
				break;
                        
                } //switch (myStatus)                         
	} //while (true)
} 

