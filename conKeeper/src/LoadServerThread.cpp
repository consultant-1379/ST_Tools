#include "ConnectionKeeper.h"

using namespace std;

extern vector<Connection> v_connections;
extern vector<Listener> v_listeners;

extern time_t start, stop, lastaction;
extern pthread_mutex_t sync_mutex;
extern applicationData dataTool;


void* _LoadServerThread(void *arg)
{
       	Connection	*myConnection = (Connection *)arg;
        
 	ConnectionStatus myStatus;
        stringstream logString;
	ConKeeperStatus appStatus;
        
	pthread_mutex_lock(&sync_mutex);
		appStatus = dataTool.status;
	pthread_mutex_unlock(&sync_mutex);

	if (appStatus == CONKEEPER_HAVE_TO_EXIT){
  		if (dataTool.logMask >= LOGMASK_INFO){
       			logString.clear();
			logString.str("");
			logString << "LoadServerThread_" << myConnection->position <<": Server connection shall be closed." <<endl;
			LOG(INFO, logString.str());
		}
                        
		pthread_exit(0);
	}

  	if (dataTool.logMask >= LOGMASK_INFO){
       		logString.clear();
		logString.str("");
		logString << "LoadServerThread_" << myConnection->position <<": Starting..." <<endl;
		LOG(INFO, logString.str());
	}

	if (dataTool.logMask >= LOGMASK_DEBUG) {
       		logString.clear();
		logString.str("");
		logString << "LoadServerThread_" << myConnection->position <<": SocketId: "<< myConnection->server.sock <<", ThreadId: "<< myConnection->server.threadID<<endl;
		LOG(DEBUG, logString.str());
        }
       
	pthread_mutex_lock(&sync_mutex);
		myConnection->server.status = ONLINE;;
	pthread_mutex_unlock(&sync_mutex);
        

	//variable declaration
	char buff[DEFAULT_BUFFER_SIZE];
	fd_set fds, tmpset;
	struct timeval tv;
	int received ;
	//initializing file descriptor
	FD_ZERO(&fds);
	FD_SET(myConnection->server.sock, &fds);
	
	while (true){ 
                
		pthread_mutex_lock(&sync_mutex);
                        myStatus = myConnection->server.status;
			appStatus = dataTool.status;
		pthread_mutex_unlock(&sync_mutex); 
                
 		if (appStatus == CONKEEPER_HAVE_TO_EXIT || appStatus == CONKEEPER_TO_BE_RESET){
  			if (dataTool.logMask >= LOGMASK_INFO){
       				logString.clear();
				logString.str("");
				logString << "LoadServerThread_" << myConnection->position <<": Server connection shall be closed" <<endl;
				LOG(INFO, logString.str());
			}
                        
			resetServerConnectionAndExit (myConnection);
		}
                
		switch (myStatus) {                        
                        
			case ONLINE:{
		
				//setting the timeout for the select operation
				tv.tv_sec = 2;
				tv.tv_usec = 0;
		
				tmpset = fds;
				//passive wait for any action in any of the socket
				if(myConnection->server.sock == -1) resetServerConnectionAndExit (myConnection);
				select(myConnection->server.sock+1, &tmpset, NULL, NULL, &tv);

				//if event happened
				if(FD_ISSET(myConnection->server.sock, &tmpset)){ 
					//reading from the socket
					received = recv(myConnection->server.sock,buff,DEFAULT_BUFFER_SIZE,0);
					if (dataTool.logMask >= LOGMASK_DEBUG) {
 						logString.clear();
						logString.str("");
						logString << "LoadServerThread_" << myConnection->position <<": Incomming message with "<< received <<" bytes."<<endl;
						LOG(INFO, logString.str());
                			}


					if(received < 1){
						if (dataTool.logMask >= LOGMASK_WARNING) {
 							logString.clear();
							logString.str("");
							logString << "LoadServerThread_" << myConnection->position <<": Error by reading" <<endl;
							logString <<"\tLOAD connection shall be closed" << endl;
							LOG(WARNING, logString.str());
                				}
						resetServerConnectionAndExit (myConnection);
                                
					}
                        		else if (received == 0){
                                
						if (dataTool.logMask >= LOGMASK_WARNING) {
 							logString.clear();
							logString.str("");
							logString << "LoadServerThread_" << myConnection->position <<": TCP connection closed by peer." <<endl;
							logString <<"\tLOAD connection shall be closed" << endl;
							LOG(WARNING, logString.str());
                				}
						resetServerConnectionAndExit (myConnection);
                                
					}
                        		else {
						// some data received
                                		while (myConnection->client.status == CONNECTING) {
                                                        
 							pthread_mutex_lock(&sync_mutex);
                        					myStatus = myConnection->server.status;
								appStatus = dataTool.status;
							pthread_mutex_unlock(&sync_mutex); 
                
 							if (appStatus == CONKEEPER_HAVE_TO_EXIT){
  								if (dataTool.logMask >= LOGMASK_INFO){
       									logString.clear();
									logString.str("");
									logString << "LoadServerThread_" << myConnection->position <<": Server connection shall be closed" <<endl;
									LOG(INFO, logString.str());
								}
                        
								resetServerConnectionAndExit (myConnection);
							}
                                                }
                                		if (myConnection->client.status == ONLINE) {
							int send_bytes = 0;
                                        		send_bytes = send(myConnection->client.sock,(const char*)buff,received,0); 
                      					if (send_bytes != received) {
								pthread_mutex_lock(&sync_mutex);
									myConnection->client.status = TO_BE_RESTARTED;
								pthread_mutex_unlock(&sync_mutex);
								if (dataTool.logMask >= LOGMASK_WARNING) {
 									logString.clear();
									logString.str("");
									logString << "LoadServerThread_" << myConnection->position <<": Error sending message." <<endl;
									logString <<"\tLOAD client  shall be re-started" << endl;
									LOG(WARNING, logString.str());
                						}
                      					}
                      					else {
								if (dataTool.logMask >= LOGMASK_DEBUG) {
 									logString.clear();
									logString.str("");
									logString << "LoadServerThread_" << myConnection->position <<": Message sent." <<endl;
									LOG(DEBUG, logString.str());
                						}
                        				}
                                            
                                		}
                               		 	else {
							if (dataTool.logMask >= LOGMASK_INFO) {
 								logString.clear();
								logString.str("");
								logString << "LoadServerThread_" << myConnection->position <<": Incomming message discarded." <<endl;
								LOG(INFO, logString.str());
                					}
						}		
					}
				} //if(FD_ISSET)
 				break;
			}
                
			case TO_BE_CLOSED:{
				if (dataTool.logMask >= LOGMASK_INFO) {
 					logString.clear();
					logString.str("");
					logString << "LoadServerThread_" << myConnection->position <<": LOAD connection shall be closed" << endl;
					LOG(INFO, logString.str());
                		}
				resetServerConnectionAndExit (myConnection);
        
				break;
			}
                
			case TO_BE_RESTARTED:
                        default:
				if (dataTool.logMask >= LOGMASK_INFO) {
 					logString.clear();
					logString.str("");
					logString << "LoadServerThread_" << myConnection->position <<": Wrong connection state" << endl;
					LOG(INFO, logString.str());
                		}
                                pthread_mutex_lock(&sync_mutex);
 					dataTool.status = CONKEEPER_TO_BE_RESET;
				pthread_mutex_unlock(&sync_mutex);
                
				break;
                                
		} // switch (myStatus)
	} //while (true)	
} 





