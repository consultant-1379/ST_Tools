#include "ConnectionKeeper.h"

using namespace std;

extern pthread_t SignalThreadID;
extern bool haveToExit;
extern vector<Connection> v_connections;
extern vector<Listener> v_listeners;
extern time_t start, stop, lastaction;
extern SignalReason sigReason;
extern pthread_mutex_t sync_mutex;

extern unsigned int nextConnection;
extern vector <int> conIndex;
extern std::string ConStatus[];       
extern std::string ListennerStatus[];       
extern std::string ConType[];
extern applicationData dataTool;

void resetAndExit_Listener (Listener *myListener, ListenerStatus status)
{
        stringstream logString;
	
	pthread_mutex_lock(&sync_mutex);
		if (dataTool.status == CONKEEPER_HAVE_TO_EXIT)	myListener->status = LISTENER_OFF;
		else						myListener->status = status;
                
		if (myListener->sock != -1)	close (myListener->sock);
                	
		myListener->sock = -1;
		myListener->threadID = 0;
	pthread_mutex_unlock(&sync_mutex);
        
  	if (dataTool.logMask >= LOGMASK_INFO){
       		logString.clear();
		logString.str("");
		logString << ConType[myListener->type].c_str()<<" listener: Exit with Status: "<< ListennerStatus[myListener->status] <<endl;
		LOG(INFO, logString.str());
	}
        
	pthread_exit(0);

}


int findConnection(ConnectionType type)
{
	int index = nextConnection;
	unsigned int searches = 1;

	do {
		if (v_connections[index].type == NONE) {
			if (nextConnection < v_connections.size() -1)	nextConnection++;
			else nextConnection = 0;
			
			v_connections[index].type = type;
                       	conIndex.push_back(index);
                        
                        return index;			
		}
		else {
			searches++;
			if (searches > v_connections.size())	return -1;
			else					index++;
		}
	} while (true);
}


void* _ListenerThread(void *arg)
{ 
        
      	Listener	*myListener = (Listener *)arg;
        ListenerStatus myStatus;
        stringstream logString;
 	ConKeeperStatus appStatus;
        
	pthread_mutex_lock(&sync_mutex);
		appStatus = dataTool.status;
	pthread_mutex_unlock(&sync_mutex);
        
        string listenerThreadType = "ListenerThread_" + ConType[myListener->type];

	if (appStatus == CONKEEPER_HAVE_TO_EXIT){
  		if (dataTool.logMask >= LOGMASK_INFO){
       			logString.clear();
			logString.str("");
			logString <<listenerThreadType <<": Terminating... " <<endl;
			LOG(INFO, logString.str());
		}
                        
		pthread_exit(0);
	}

	pthread_mutex_lock(&sync_mutex);
		myListener->status = LISTENER_STARTING;
	pthread_mutex_unlock(&sync_mutex); 
        
        
        int errsv;
	int conFound;
        
	if (dataTool.logMask >= LOGMASK_INFO){
       		logString.clear();
		logString.str("");
		logString <<listenerThreadType <<": Starting..." <<endl;
		LOG(INFO, logString.str());
        }
                                        	
	//creating the server socket
	myListener->sock = socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);

	if (myListener->sock == -1){
		if (dataTool.logMask >= LOGMASK_WARNING) {
			errsv = errno;
 			logString.clear();
			logString.str("");
			logString <<listenerThreadType <<": Create socket returned" << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(WARNING, logString.str());
                }

		resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);
	}

	
	struct sockaddr_in local_addr;
	memset(&local_addr,0,sizeof(local_addr));
	local_addr.sin_family = AF_INET;
	local_addr.sin_addr.s_addr = INADDR_ANY;
	local_addr.sin_port = htons(myListener->port);

	struct sockaddr_in remote_addr;
	memset(&remote_addr,0,sizeof(sockaddr_in));

	//binding the socket to a local port
	if(bind(myListener->sock,(sockaddr*)&local_addr, sizeof(local_addr)) == -1){
		if (dataTool.logMask >= LOGMASK_WARNING) {
			errsv = errno;
 			logString.clear();
			logString.str("");
			logString <<listenerThreadType <<": Failed to bind to local socket." << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(WARNING, logString.str());
                }
		resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);
	}
	
	//the socket stars listening in the local port
	listen(myListener->sock, 5);	//backlog of 5 (number of maximum pending connections for accepting)
	
	if (dataTool.logMask >= LOGMASK_INFO) {
		logString.clear();
		logString.str("");
		logString <<listenerThreadType <<": listening on port " << myListener->port << endl;
		LOG(INFO, logString.str());
        }

	int sock;	//this socket will be initialized when a connection request arrives
	socklen_t len = sizeof(remote_addr);

	fd_set fds;
	fd_set tmpset;
	struct timeval tv;
	tv.tv_sec = 2;
	tv.tv_usec = 0;
        char myIpHost[20];
	
	//subscribing the server socket to the mask to be used in the 'select'
        
	while (true){
                
                strcpy (myIpHost, "");
		pthread_mutex_lock(&sync_mutex);
			myStatus = myListener->status;
			appStatus = dataTool.status;
                        strcpy (myIpHost, myListener->primary_ip_host);
		pthread_mutex_unlock(&sync_mutex); 
                
 		if (appStatus == CONKEEPER_HAVE_TO_EXIT){
  			if (dataTool.logMask >= LOGMASK_WARNING){
       				logString.clear();
				logString.str("");
				logString <<listenerThreadType <<": Terminating... " <<endl;
				LOG(INFO, logString.str());
			}
                        
			resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);
		}
               
		switch (myStatus) {                        
                        
			case LISTENER_STARTING:{
				pthread_mutex_lock(&sync_mutex);
                			if (strcmp(myIpHost,"")) 	myListener->status = LISTENER_ON;
                			else 				myListener->status = LISTENER_TO_BE_CONFIGURED; 
				pthread_mutex_unlock(&sync_mutex);
        
				break;
			}
                        
			case LISTENER_TO_BE_CONFIGURED:{
				sleep(1);
				pthread_mutex_lock(&sync_mutex);
                			if (!strcmp(myIpHost,"0.0.0.0")) 	myListener->status = LISTENER_NOT_USED;
                			else if (strcmp(myIpHost,"")) 		myListener->status = LISTENER_ON;
				pthread_mutex_unlock(&sync_mutex);
        
				break;
			}
                        
			case LISTENER_TO_BE_CLOSED:{
				resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);
        
				break;
			}
                        
			case LISTENER_ON:{
				FD_ZERO(&fds);
				FD_SET(myListener->sock, &fds);
                                
				tmpset = fds;
				tv.tv_sec = 2;
				tv.tv_usec = 0;
                                
// 				if (appStatus != CONKEEPER_READY)	break;
				//passive wait for any activity in the socket
				select(myListener->sock+1,&tmpset, NULL, NULL, &tv);

				if(FD_ISSET(myListener->sock, &tmpset)){ 
		
					sock = accept(myListener->sock,(sockaddr*)&remote_addr,&len);	
					if (dataTool.logMask >= LOGMASK_INFO) {
						logString.clear();
						logString.str("");
						logString <<listenerThreadType <<": Client trying to connect from "<< inet_ntoa(remote_addr.sin_addr) <<":"<< ntohs(remote_addr.sin_port) << endl;
						LOG(INFO, logString.str());
                        		}

                        		pthread_mutex_lock(&sync_mutex);
						conFound = findConnection(myListener->type);
					pthread_mutex_unlock(&sync_mutex);

                        		if (conFound == -1) {
						if (dataTool.logMask >= LOGMASK_WARNING) {
							logString.clear();
							logString.str("");
							logString <<listenerThreadType <<": No connection record available" << endl;
							LOG(WARNING, logString.str());
                        			}
						
						continue;
					}
                                               
					if (dataTool.logMask >= LOGMASK_INFO) {
						logString.clear();
						logString.str("");
						logString <<listenerThreadType <<": Accepted connection " << conFound << " on socket: " << sock << endl;
						LOG(INFO, logString.str());
                        		}
                        
                        		v_connections[conFound].server.status = CONNECTING;
                        		v_connections[conFound].client.status = CONNECTING;
                         		v_connections[conFound].client.connectedTo = UNKNOWM;
                       			v_connections[conFound].server.sock = sock;
                        		v_connections[conFound].client.primary_remote_addr.sin_family = AF_INET;
					v_connections[conFound].client.primary_remote_addr.sin_addr.s_addr = inet_addr(myListener->primary_ip_host);
                         		v_connections[conFound].client.secondary_remote_addr.sin_family = AF_INET;
					v_connections[conFound].client.secondary_remote_addr.sin_addr.s_addr = inet_addr(myListener->secondary_ip_host);
                                       if (myListener->port == 1389) {
                         			v_connections[conFound].client.primary_remote_addr.sin_port = htons(389);
                         			v_connections[conFound].client.secondary_remote_addr.sin_port = htons(389);
                                       }
                                        else {
                        			v_connections[conFound].client.primary_remote_addr.sin_port = htons(myListener->port);
                        			v_connections[conFound].client.secondary_remote_addr.sin_port = htons(myListener->port);
                                        }

					//creating Client Thread
					pthread_attr_t myAttr;
					if (pthread_attr_init(&myAttr)){
						if (dataTool.logMask >= LOGMASK_WARNING) {
                            				errsv = errno;
							logString.clear();
							logString.str("");
							logString <<listenerThreadType <<": Failed to init pthread attr." << endl;
							logString <<"\tError: " << strerror(errsv) << endl;
							LOG(WARNING, logString.str());
                        			}
						resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);
					}
					if (pthread_attr_setstacksize (&myAttr, DEFAULT_STACK_SIZE)){
						if (dataTool.logMask >= LOGMASK_WARNING) {
                            				errsv = errno;
							logString.clear();
							logString.str("");
							logString <<listenerThreadType <<": Failed to change stack size." << endl;
							logString <<"\tError: " << strerror(errsv) << endl;
							LOG(WARNING, logString.str());
                        			}
						resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);
					}

					if (pthread_attr_setdetachstate (&myAttr, PTHREAD_CREATE_DETACHED)){
						if (dataTool.logMask >= LOGMASK_WARNING) {
                           				errsv = errno;
							logString.clear();
							logString.str("");
							logString <<listenerThreadType <<": Failed to change detach state." << endl;
							logString <<"\tError: " << strerror(errsv) << endl;
							LOG(WARNING, logString.str());
                        			}
						resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);

					}

					int ret;
                                                
        				switch (myListener->type) {
                				case LOAD:
							strcpy(v_connections[conFound].type_str, "LOAD");
                        				ret = pthread_create(&v_connections[conFound].client.threadID,&myAttr,_LoadClientThread,&v_connections[conFound]);
                                        		if (ret) {
								if (dataTool.logMask >= LOGMASK_WARNING) {
                                        				errsv = ret;
									logString.clear();
									logString.str("");
									logString <<listenerThreadType <<": Failed during LOAD client thread creation." << endl;
									logString <<"\tError: " << strerror(errsv) << endl;
									LOG(WARNING, logString.str());
                        					}
                                
								resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);
							}
                                        
							ret = pthread_create(&v_connections[conFound].server.threadID,&myAttr,_LoadServerThread,&v_connections[conFound]);
							if (ret) {
								if (dataTool.logMask >= LOGMASK_WARNING) {
                                        				errsv = ret;
									logString.clear();
									logString.str("");
									logString <<listenerThreadType <<": Failed during LOAD server thread creation." << endl;
									logString <<"\tError: " << strerror(errsv) << endl;
									LOG(WARNING, logString.str());
                        					}
                                
								resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);
							}
                                        
                      		 			break; 
               			 		case DIAMETER:

							strcpy(v_connections[conFound].type_str, "DIAMETER");
                       					ret = pthread_create(&v_connections[conFound].client.threadID,&myAttr,_DiameterClientThread,&v_connections[conFound]);
                                        		if (ret) {
								if (dataTool.logMask >= LOGMASK_WARNING) {
                                        				errsv = ret;
									logString.clear();
									logString.str("");
									logString <<listenerThreadType <<": Failed during DIAMETER client thread creation." << endl;
									logString <<"\tError: " << strerror(errsv) << endl;
									LOG(WARNING, logString.str());
                        					}
                                
								resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);
							}
                                        
                                     			ret = pthread_create(&v_connections[conFound].server.threadID,&myAttr,_DiameterServerThread,&v_connections[conFound]);
							if (ret) {
								if (dataTool.logMask >= LOGMASK_WARNING) {
                                        				errsv = ret;
									logString.clear();
									logString.str("");
									logString <<listenerThreadType <<": Failed during DIAMETER server thread creation." << endl;
									logString <<"\tError: " << strerror(errsv) << endl;
									LOG(WARNING, logString.str());
                        					}
                                
								resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);
							}
                                        
                       					break; 
               					case LDAP:
                                        
							strcpy(v_connections[conFound].type_str, "LDAP");
                       					ret = pthread_create(&v_connections[conFound].client.threadID,&myAttr,_LdapClientThread,&v_connections[conFound]);
                                        		if (ret) {
								if (dataTool.logMask >= LOGMASK_WARNING) {
                                        				errsv = ret;
									logString.clear();
									logString.str("");
									logString <<listenerThreadType <<": Failed during LDAP client thread creation." << endl;
									logString <<"\tError: " << strerror(errsv) << endl;
									LOG(WARNING, logString.str());
                        					}
								resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);
							}
                                        
							ret = pthread_create(&v_connections[conFound].server.threadID,&myAttr,_LdapServerThread,&v_connections[conFound]);
							if (ret) {
								if (dataTool.logMask >= LOGMASK_WARNING) {
                                        				errsv = ret;
									logString.clear();
									logString.str("");
									logString <<listenerThreadType <<": Failed during LDAP server thread creation." << endl;
									logString <<"\tError: " << strerror(errsv) << endl;
									LOG(WARNING, logString.str());
                        					}
                                
								resetAndExit_Listener (myListener, LISTENER_TO_BE_STARTED);
							}
                      					break; 
                				default:
							if (dataTool.logMask >= LOGMASK_WARNING) {
								logString.clear();
								logString.str("");
								logString <<listenerThreadType <<": Wrong Listener type." << endl;
								LOG(WARNING, logString.str());
                                        		}
                					break;
                
        				} // switch (myListener->type)
				} //if(FD_ISSET(fd, &tmpset))
                                    
				break;
			}
                        
			default:
				sleep(2);

				break;
                       
		} // switch (myStatus)
        } //while (true)
       
       	return 0;
}



