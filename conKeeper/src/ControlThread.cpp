#include "ConnectionKeeper.h"

using namespace std;
extern pthread_t SignalThreadID;

extern vector<Connection> v_connections;
extern vector<Listener> v_listeners;

extern time_t start, stop, lastaction;
extern SignalReason sigReason;
extern pthread_mutex_t sync_mutex;
extern vector <int> conIndex;
extern applicationData dataTool;

void* _ControlThread(void *arg)
{
	int ret, errsv;
        stringstream logString;
 	ConKeeperStatus appStatus;

	vector<Listener> my_v_listeners;
	vector<Connection> my_v_connections;

	if (dataTool.logMask >= LOGMASK_INFO){
       		logString.clear();
		logString.str("");
		logString << "ControlThread: Starting..." <<endl;
		LOG(INFO, logString.str());
        }

	if (dataTool.logMask >= LOGMASK_INFO){
       		logString.clear();
		logString.str("");
		logString << "ControlThread: Start creation of Listeners..." <<endl;
		LOG(INFO, logString.str());
        }

	pthread_attr_t myAttr;
	if (pthread_attr_init(&myAttr)){

			errsv = ret;
			logString.clear();
			logString.str("");
			logString << "ControlThread: Failed to init pthread attr."<< endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(ERROR, logString.str());

			pthread_mutex_lock(&sync_mutex);
	 			dataTool.status = CONKEEPER_HAVE_TO_EXIT;
			pthread_mutex_unlock(&sync_mutex);

            pthread_kill(SignalThreadID ,SIGUSR1);
            pthread_exit(0);
	}

	if (pthread_attr_setstacksize (&myAttr, DEFAULT_STACK_SIZE)){
		errsv = ret;
		logString.clear();
		logString.str("");
		logString << "ControlThread: Failed to change stack size."<< endl;
		logString <<"\tError: " << strerror(errsv) << endl;
		LOG(ERROR, logString.str());

		pthread_mutex_lock(&sync_mutex);
 			dataTool.status = CONKEEPER_HAVE_TO_EXIT;
		pthread_mutex_unlock(&sync_mutex);

        pthread_kill(SignalThreadID ,SIGUSR1);
        pthread_exit(0);
	}

	if (pthread_attr_setdetachstate (&myAttr, PTHREAD_CREATE_DETACHED)){
		errsv = ret;
		logString.clear();
		logString.str("");
		logString << "ControlThread: Failed to change detach state." << endl;
		logString <<"\tError: " << strerror(errsv) << endl;
		LOG(ERROR, logString.str());

		pthread_mutex_lock(&sync_mutex);
 			dataTool.status = CONKEEPER_HAVE_TO_EXIT;
		pthread_mutex_unlock(&sync_mutex);

        pthread_kill(SignalThreadID ,SIGUSR1);
        pthread_exit(0);

	}

	for(;;)	{ 

		sleep(2);
		
		pthread_mutex_lock(&sync_mutex);
 			appStatus = dataTool.status;
		pthread_mutex_unlock(&sync_mutex);
                
                switch (appStatus) {
                        
                        case CONKEEPER_STARTING:{
                                
 				pthread_mutex_lock(&sync_mutex);
					my_v_listeners = v_listeners;
				pthread_mutex_unlock(&sync_mutex);
                                bool listennerPending = false;

				for (unsigned int i = 0; i < my_v_listeners.size(); i++) {

                    			if (my_v_listeners[i].status == LISTENER_TO_BE_STARTED) {
                
						ret = pthread_create(&v_listeners[i].threadID,&myAttr,_ListenerThread,(void *) &(v_listeners[i]));

            					if (ret && (dataTool.logMask >= LOGMASK_ERROR)) {
							errsv = ret;
       							logString.clear();
							logString.str("");
							logString << "ControlThread: ListenerThread creation returned" << ret << endl;
							logString <<"\tError: " << strerror(errsv) << endl;
							LOG(ERROR, logString.str());
                                		}
                                                listennerPending = true;
					}
				} 
                                if (!listennerPending) {
                                        pthread_mutex_lock(&sync_mutex);
 						dataTool.status = CONKEEPER_TO_BE_CONFIGURED;
                                                cout << "ConKeeper up and running" << endl;
					pthread_mutex_unlock(&sync_mutex);
                                }
                                break;
                        }
                                
                        case CONKEEPER_TO_BE_CONFIGURED:{
                                
 				pthread_mutex_lock(&sync_mutex);
					my_v_listeners = v_listeners;
				pthread_mutex_unlock(&sync_mutex);
                                bool listennerPending = false;

				for (unsigned int i = 0; i < my_v_listeners.size(); i++) {

                    			if (my_v_listeners[i].status != LISTENER_ON && my_v_listeners[i].status != LISTENER_NOT_USED) {
                                                listennerPending = true;
					}
					if ((my_v_listeners[i].status == LISTENER_TO_BE_STARTED) && (my_v_listeners[i].threadID == 0)) {
                
						ret = pthread_create(&v_listeners[i].threadID,&myAttr,_ListenerThread,(void *) &(v_listeners[i]));

            					if (ret && (dataTool.logMask >= LOGMASK_ERROR)) {
							errsv = ret;
       							logString.clear();
							logString.str("");
							logString << "ControlThread: ListenerThread creation returned" << ret << endl;
							logString <<"\tError: " << strerror(errsv) << endl;
							LOG(ERROR, logString.str());
                                		}
					}
				} 
                                if (!listennerPending && dataTool.redundancy && dataTool.activeZone != UNKNOWM) {
                                        pthread_mutex_lock(&sync_mutex);
 						dataTool.status = CONKEEPER_READY;
					pthread_mutex_unlock(&sync_mutex);
                                }
                                if (!listennerPending && !dataTool.redundancy && dataTool.activeZone == UNKNOWM) {
                                        pthread_mutex_lock(&sync_mutex);
 						dataTool.status = CONKEEPER_READY;
					pthread_mutex_unlock(&sync_mutex);
                                }
                               break;
                        }
                        
                        case CONKEEPER_READY:{

				pthread_mutex_lock(&sync_mutex);
					my_v_connections = v_connections;
				pthread_mutex_unlock(&sync_mutex);
                
                		unsigned int i ;
        			vector <int>::iterator pos = conIndex.begin();
        			while (pos != conIndex.end()) {
                        		i = *pos;
                                                       
                    			if ((my_v_connections[i].client.status == OFFLINE) && (my_v_connections[i].server.status == OFFLINE)){
                                
						v_connections[i].type = NONE;
						v_connections[i].messageLen = 0;
						strcpy(v_connections[i].type_str, "");
                                
                                		conIndex.erase(pos);
                                		continue;
					} 
                     			if ((my_v_connections[i].client.status == TO_BE_RESTARTED) && (v_connections[i].client.threadID == 0)){
                                
            					if (dataTool.logMask >= LOGMASK_INFO) {
       							logString.clear();
							logString.str("");
							logString << "(ControlThread):Connection client Thread has to be restarted." << endl;
							LOG(INFO, logString.str());
                                		}

						//re-create it
                               			switch (v_connections[i].type) {
							case LOAD:
                         					pthread_mutex_lock(&sync_mutex);
									ret = pthread_create(&v_connections[i].client.threadID,&myAttr,_LoadClientThread,(void *) &v_connections[i]);
								pthread_mutex_unlock(&sync_mutex);
            							if (dataTool.logMask >= LOGMASK_INFO) {
									if (ret) {
										errsv = ret;
       										logString.clear();
										logString.str("");
										logString << "(ControlThread): LOAD Connection client thread creation." << endl;
										logString <<"\tError: " << strerror(errsv) << endl;
										LOG(WARNING, logString.str());
                                                        
									} else {
       										logString.clear();
										logString.str("");
										logString << "(ControlThread): LOAD Connection client thread creation successfully" << endl;
										LOG(INFO, logString.str());
									}
                                                		}
                                                		break;
							case DIAMETER:
                         					pthread_mutex_lock(&sync_mutex);
									ret = pthread_create(&v_connections[i].client.threadID,&myAttr,_DiameterClientThread,(void *) &v_connections[i]);
								pthread_mutex_unlock(&sync_mutex);
            							if (dataTool.logMask >= LOGMASK_INFO) {
									if (ret) {
										errsv = ret;
       										logString.clear();
										logString.str("");
										logString << "(ControlThread): DIAMETER Connection client Thread creation returned" << ret << endl;
										logString <<"\tError: " << strerror(errsv) << endl;
										LOG(WARNING, logString.str());

									} else {
       										logString.clear();
										logString.str("");
										logString << "(ControlThread): DIAMETER Connection client Thread creation successfully" << endl;
										LOG(INFO, logString.str());
									}
                                                		}
                                               			break;
							case LDAP:
                         					pthread_mutex_lock(&sync_mutex);
									ret = pthread_create(&v_connections[i].client.threadID,&myAttr,_LdapClientThread,(void *) &v_connections[i]);
								pthread_mutex_unlock(&sync_mutex);
            							if (dataTool.logMask >= LOGMASK_INFO) {
									if (ret) {
										errsv = ret;
       										logString.clear();
										logString.str("");
										logString << "(ControlThread): LDAP Connection client Thread creation returned" << ret << endl;
										logString <<"\tError: " << strerror(errsv) << endl;
										LOG(WARNING, logString.str());

									} else {
       										logString.clear();
										logString.str("");
										logString << "(ControlThread): LDAP Connection client Thread creation successfully" << endl;
										LOG(INFO, logString.str());
									}
                                                		}
                                                		break;
                                        		default: 
            							if (dataTool.logMask >= LOGMASK_WARNING) {
       									logString.clear();
									logString.str("");
									logString << "(ControlThread): wrong connection type" << endl;
									LOG(WARNING, logString.str());
                                                		}
                                        			break;
                              			} // switch (v_connections[i].type)

					} // if(my_v_connections[i].client.status == TO_BE_RESTARTED)
                       
                        		pos++;

				} //  while (pos != conIndex.end())                                 
                                break;
                        }
                        
                        case CONKEEPER_TO_BE_RESET:{
 				pthread_mutex_lock(&sync_mutex);
					my_v_listeners = v_listeners;
				pthread_mutex_unlock(&sync_mutex);

				for (unsigned int i = 0; i < my_v_listeners.size(); i++) {
                                        
                    			if (my_v_listeners[i].status != LISTENER_TO_BE_CONFIGURED) {
 						pthread_mutex_lock(&sync_mutex);
                                                 	strcpy(v_listeners[i].primary_ip_host, "");
                                                	strcpy(v_listeners[i].secondary_ip_host, "");
                                                       v_listeners[i].status = LISTENER_TO_BE_CONFIGURED;
						pthread_mutex_unlock(&sync_mutex);
					}
				} 
                                
				pthread_mutex_lock(&sync_mutex);
					my_v_connections = v_connections;
				pthread_mutex_unlock(&sync_mutex);
                
                                bool connectionsPending = false;
                		unsigned int i ;
        			vector <int>::iterator pos = conIndex.begin();
        			while (pos != conIndex.end()) {
                        		i = *pos;
                                        if (my_v_connections[i].type != NONE) {
                                                       
                    				if ((my_v_connections[i].client.status == OFFLINE) && (my_v_connections[i].server.status == OFFLINE)){
							pthread_mutex_lock(&sync_mutex);
                                                        
								v_connections[i].type = NONE;
								v_connections[i].messageLen = 0;
								strcpy(v_connections[i].type_str, "");
                                
                                				conIndex.erase(pos);
 							pthread_mutex_unlock(&sync_mutex);
                                			continue;
						}
                                                else {
                                                       connectionsPending = true;
                                                } 
                        
                        			pos++;
                                        }
                                } // while (pos != conIndex.end())
                                
                                if (!connectionsPending) {
                                        pthread_mutex_lock(&sync_mutex);
 						dataTool.status = CONKEEPER_TO_BE_CONFIGURED;
 						dataTool.activeZone = UNKNOWM;
 						dataTool.redundancy = false;
					pthread_mutex_unlock(&sync_mutex);
                                }
                                
                                break;
                        }
                        
                        case CONKEEPER_HAVE_TO_EXIT:
                                pthread_kill(SignalThreadID ,SIGUSR1);

 				if (dataTool.logMask >= LOGMASK_INFO){
       					logString.clear();
					logString.str("");
					logString << "ControlThread: Terminating... " <<endl;
					LOG(INFO, logString.str());
                        	}
				pthread_exit(0);
                               
                                break;
                        
                         default:
                                
                                break;
                        
                       
                }
                
           
                					
	} //for(;;)
}

