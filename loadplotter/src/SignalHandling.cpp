#include "SignalHandling.h"
#include "loadplotter.h"

using namespace std;
extern pthread_t SignalThreadID;
extern vector<Connection> v_connections;
extern time_t start, stop, lastaction;
extern pthread_mutex_t sync_mutex;

extern applicationData dataTool;
extern RemoteControl remoteControlData;
       
extern pthread_t RemoteThreadID;

void *
handler(void *)
{
	int signal;
	sigset_t signal_set;
	vector<Connection> my_v_connections;
        stringstream logString;
        
	for(;;){
               
                sigfillset( &signal_set );
		sigwait(&signal_set, &signal);
		switch (signal) {
			case SIGINT:
			case SIGTERM:{
  				if (dataTool.logMask >= LOGMASK_WARNING){
       					logString.clear();
					logString.str("");
					logString << "(SignalThread): user press ctrl-C.Terminating... " <<endl;
					LOG(WARNING, logString.str());
                        	}

                            	pthread_mutex_lock(&sync_mutex);
					dataTool.status = LOADPLOTTER_HAVE_TO_EXIT;
				pthread_mutex_unlock(&sync_mutex);
                                
         			bool pending = true;                       
         			while (pending){                        
					for (unsigned int index = 0;index < v_connections.size(); index++) {                
						if (v_connections[index].threadID == 0)
		    					pending = false;
                				else {
		    					pending = true;
                               			 break;
                        			}
        				}
                			if (v_connections.empty()) pending = false;
				}
                               
  				if (dataTool.logMask >= LOGMASK_WARNING){
       					logString.clear();
					logString.str("");
					logString << "(SignalThread): Waiting for Remotethread to finish... " <<endl;
					LOG(WARNING, logString.str());
                        	}
                                
                                while (	RemoteThreadID!=NULL) {};

                                
				if (remoteControlData.sock != -1){
                                        int result = close (remoteControlData.sock);
                                        if (result != 0)	perror("remote");
                                }

        			cout << "LoadPlotter finished"<<endl;
				exit (0);		
				break;
                        }	
			case SIGUSR1: {
			
cout <<"señal SIGUSR1"<<endl;
                            	pthread_mutex_lock(&sync_mutex);
					dataTool.status = LOADPLOTTER_HAVE_TO_EXIT;
				pthread_mutex_unlock(&sync_mutex);
                                

  				if (dataTool.logMask >= LOGMASK_INFO){
       					logString.clear();
					logString.str("");
					logString << "(SignalThread): Terminating... " <<endl;
					LOG(INFO, logString.str());
                        	}
                                
         			bool pending = true;                       
         			while (pending){                        
					for (unsigned int index = 0;index < v_connections.size(); index++) {                
						if (v_connections[index].threadID == 0)
		    					pending = false;
                				else {
		    					pending = true;
                                			break;
                        			}
                        
                            
        				}
                			if (v_connections.empty()) pending = false;
				}
        
                                while (	RemoteThreadID!=NULL) {};

                                
				if (remoteControlData.sock != -1){
                                        int result = close (remoteControlData.sock);
                                        if (result != 0)	perror("remote");
                                }

        			cout << "LoadPlotter finished"<<endl;
				exit (0);		
				break;
			} // end case SIGUSR1

			case SIGTSTP:
			case SIGUSR2:
			default:
 				if (dataTool.logMask >= LOGMASK_DEBUG){
       					logString.clear();
					logString.str("");
					logString << "(SignalThread): received signal: "<< signal <<endl;
					LOG(DEBUG, logString.str());
                        	}
				break;
		}
    	}
}
