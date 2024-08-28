#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <errno.h>
#include <time.h>
#include <signal.h>
#include <pthread.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <net/if.h>
#include <stropts.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <unistd.h>
#include <netdb.h>
#include <sys/timeb.h>
#include <syslog.h>
#include <vector>
#include <sys/time.h>

#include "cnDiaProxy.h"
#include "DiaThread.h"
#include "ListenerThread.h"

extern pthread_t ListenerThreadID;
extern pthread_t SignalThreadID;

extern bool haveToExit;
extern bool couldBeCleaned;

extern std::vector<DiaServerConnection> v_connections;

extern time_t start, stop, lastaction;
extern applicationData dataTool;

extern ListennerStatus listennerState;
extern DiaProxyStatus diaProxyState;
extern SignalReason sigReason;

struct DiaServerConnection	*param = NULL;


//extern bool ext_connection_ready;
extern pthread_mutex_t STATISTIC;
extern pthread_mutex_t CONNECTION_VECTOR;
extern pthread_mutex_t TOOL_STATUS;

using namespace std;

//this thread is a kind of main-thread, as it is one of the few actions
//performed by the main function
//this thread will spawn different threads:
//	* DiaThread: responsible of the communication with the Diameter ServerVendor
//  	* ListenerThread: its goal is listening in the local interface and accept
//					  connection request coming from the clients (PTCs)
//
//Apart from the actions described above, the thread will look after the spawned 
//threads and will respawn them in case any error happends
void* _ProxyThread(void *arg)
{
    int ret, errsv;
    bool myHaveToExit;
    stringstream logString;

	diaProxyState = DIAPROXY_STARTING;

    logString.clear();
    logString.str("");
    logString << endl << "*************************************************" << endl;
    logString << "(ProxyThread) : CONNECTING......"<<endl;
    logString << "*************************************************" << endl;
    LOG(DISPLAY, logString.str());
    		

#ifdef _DIA_PROXY_DEBUG
    logString.clear();
    logString.str("");
    logString << "(ProxyThread) :Creating Diameter Thread"<<endl;
    LOG(DEBUG, logString.str());
#endif

	//creating the Diameter Thread; it will execute the _DiaThread routine
	
	for (unsigned int i = 0; i < v_connections.size(); i++) {
		ret = pthread_create(&v_connections[i].threadID,NULL,_DiaThread,(void *) &(v_connections[i]));
		if (ret) {
			errsv = ret;
 			logString.clear();
			logString.str("");
			logString << "(ProxyThread) : DiaThread creation returned " << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(ERROR, logString.str());

			pthread_mutex_lock(&TOOL_STATUS);
				sigReason = PTHREAD_ERROR;
			pthread_mutex_unlock(&TOOL_STATUS);
			pthread_kill(SignalThreadID ,SIGUSR1);
			pthread_exit(0);
		}
	}
	
	bool have_to_wait;
	
	do {

		sleep (1);
		have_to_wait = false;
		//if there is any connection to be established, we wait for it
		for (unsigned int i = 0; i < v_connections.size(); i++) {

			if (v_connections[i].threadID == 0) {
			
				if (v_connections[i].status == CONFIGURATIONERROR) {
 			            logString.clear();
			            logString.str("");
			            logString << "(ProxyThread) : DiaProxy Shutting down due to configuration error" << endl;
			            LOG(ERROR, logString.str());
                                    
				    pthread_mutex_lock(&TOOL_STATUS);
					sigReason = DIA__CONF__ERROR;
				    pthread_mutex_unlock(&TOOL_STATUS);
                                    
				    pthread_kill(SignalThreadID ,SIGUSR1);
				    pthread_exit(0);
				}
			
 			        logString.clear();
			        logString.str("");
			        logString << "(ProxyThread) : re_creating DiaThread..... " << endl;
			        LOG(DEBUG, logString.str());
                                
				ret = pthread_create(&v_connections[i].threadID,NULL,_DiaThread,(void *) &(v_connections[i]));
				if (ret) {

			            errsv = ret;
 			            logString.clear();
			            logString.str("");
			            logString << "(ProxyThread) : DiaThread creation returned " << endl;
			            logString <<"\tError: " << strerror(errsv) << endl;
			            LOG(ERROR, logString.str());

				    pthread_mutex_lock(&TOOL_STATUS);
					sigReason = DIA__CONF__ERROR;
				    pthread_mutex_unlock(&TOOL_STATUS);
                                        
				    pthread_kill(SignalThreadID ,SIGUSR1);
				    pthread_exit(0);
				}
				have_to_wait = true;
				continue;
			}
				
			if (v_connections[i].status != CONNECTED) {
				have_to_wait = true;
				break;
			}
			
		}

	//while the connection is ready to go on
	} while (have_to_wait);
	

#ifdef _DIA_PROXY_DEBUG
    logString.clear();
    logString.str("");
    logString << "(ProxyThread) :Creating Listener Thread"<<endl;
    LOG(DEBUG, logString.str());
#endif

	//creating the Listener Thread; it will execute the _ListenerThread routine
	ret = pthread_create(&ListenerThreadID,NULL,_ListenerThread,NULL);

	ListennerStatus	mylistennerState;
	pthread_mutex_lock(&TOOL_STATUS);
		mylistennerState = listennerState;
	pthread_mutex_unlock(&TOOL_STATUS);

	while (mylistennerState <= LISTENNER_CONNECTING) {
		sleep(1);
		pthread_mutex_lock(&TOOL_STATUS);
			mylistennerState = listennerState;
		pthread_mutex_unlock(&TOOL_STATUS);
	}

	if (mylistennerState != LISTENNER_READY) {
            logString.clear();
            logString.str("");
            logString << "(ProxyThread) : DiaProxy Shutting down due to configuration error" << endl;
            LOG(ERROR, logString.str());
            
	    pthread_mutex_lock(&TOOL_STATUS);
		sigReason = DIA__CONF__ERROR;
	    pthread_mutex_unlock(&TOOL_STATUS);
            
	    pthread_kill(SignalThreadID ,SIGUSR1);
	    pthread_exit(0);
	}
        
	diaProxyState = DIAPROXY_STANDBY;

	//telling the system log (syslog) that the proxy is up&running
	syslog (LOG_NOTICE, "DiaProxy up & running\n");

    logString.clear();
    logString.str("");
    logString << endl<< "*************************************************" << endl;
    logString <<        "*************************************************" << endl;
    logString <<        "(ProxyThread) :   DIAPROXY UP & RUNNING" << endl;
    logString <<        "*************************************************" << endl;
    logString <<        "*************************************************" << endl;

    cout <<logString.str(); 
	
#ifdef _DIA_PROXY_DEBUG
	printf ("(ProxyThread) : Warning: You're running the DEBUG version\n");
#endif

	sleep(2);

	time(&start);
	stop = start;
	lastaction = stop;
	int TotalmonitorCount = 0;
	int monitorCount = 0;
	for(;;)	{ 

		sleep(2);
		
		pthread_mutex_lock(&TOOL_STATUS);
			myHaveToExit = haveToExit;
		pthread_mutex_unlock(&TOOL_STATUS);

		if(myHaveToExit){ 
                    logString.clear();
                    logString.str("");
                    logString << "(ProxyThread) : Terminating... " << endl;
                    LOG(EVENT, logString.str());
		
		    pthread_exit(0);
		} 

		time(&stop);  //should be better called 'now' 
		monitorCount++;

		if (!is_process_alive(&ListenerThreadID)) 
		{
                    logString.clear();
                    logString.str("");
                    logString << "(ProxyThread) :  Listener Thread has terminated. Restart it" << endl;
                    LOG(WARNING, logString.str());
                    
		    ret = pthread_create(&ListenerThreadID,NULL,_ListenerThread,NULL);
		}
		
		//if there is any connection to be established, we wait for it

		bool restart;
                
		for (unsigned int i = 0; i < v_connections.size(); i++) {
			restart = false;
		
			if (v_connections[i].threadID == NULL) {
				restart = true;
			} else if (!is_process_alive(&v_connections[i].threadID))	restart = true;
				
			if (restart) {
                logString.clear();
                logString.str("");
                logString << "(ProxyThread) :  DiaThread Thread has terminated. Restart it" << endl;
                LOG(WARNING, logString.str());

				//re-create it
				pthread_mutex_lock(&CONNECTION_VECTOR);
					ret = pthread_create(&v_connections[i].threadID,NULL,_DiaThread,(void *) &(v_connections[i]));
				pthread_mutex_unlock(&CONNECTION_VECTOR);
				if (ret) {
			            errsv = ret;
 			            logString.clear();
			            logString.str("");
			            logString << "(ProxyThread) : DiaThread creation returned " << endl;
			            logString <<"\tError: " << strerror(errsv) << endl;
			            LOG(ERROR, logString.str());

				} else {
                                    logString.clear();
                                    logString.str("");
                                    logString << "(ProxyThread) :  DiaThread Thread created successfully" << endl;
                                    LOG(DEBUG, logString.str());
				}
			}
				
		}
        if (dataTool.activeTTCNConnections<=0 && diaProxyState != DIAPROXY_STANDBY) {
            logString.clear();
            logString.str("");
            logString << "(ProxyThread) : There are not active TTCN connections. DiaProxy cleaning" << endl;
            LOG(EVENT, logString.str());
                        
            pthread_mutex_lock(&TOOL_STATUS);
            sigReason = MAX__INACTIVE__REACHED;
            pthread_mutex_unlock(&TOOL_STATUS);
            
            pthread_kill(SignalThreadID ,SIGUSR1);
        }
            
	} //for(;;)
}


bool is_process_alive(pthread_t* process_id) 
{

	if (*process_id)	return (pthread_kill((*process_id),0) == 0);
	else 			return false;
}
