#include "ConnectionKeeper.h"

using namespace std;
extern pthread_t SignalThreadID;
extern vector<Connection> v_connections;
extern vector<Listener> v_listeners;
extern time_t start, stop, lastaction;
extern pthread_mutex_t sync_mutex;

extern std::string ConStatus[];       
extern std::string ListennerStatus[];       
extern std::string ConType[];
extern applicationData dataTool;
        


void *
handler(void *)
{
	int signal;
	sigset_t signal_set;
	vector<Connection> my_v_connections;
	vector<Listener> my_v_listeners;
	ConKeeperStatus appStatus;
        stringstream logString;
        
	for(;;){
               
		sleep(1);
               
                sigfillset( &signal_set );
		sigwait(&signal_set, &signal);
		switch (signal) {
			case SIGINT:
			case SIGTERM:
				if (appStatus == CONKEEPER_HAVE_TO_EXIT){
  					if (dataTool.logMask >= LOGMASK_WARNING){
       						logString.clear();
						logString.str("");
						logString << "(SignalThread): user press ctrl-C.Terminating... " <<endl;
						LOG(WARNING, logString.str());
                        		}
                                }

                            	pthread_mutex_lock(&sync_mutex);
					dataTool.status = CONKEEPER_HAVE_TO_EXIT;
				pthread_mutex_unlock(&sync_mutex);

				sleep (5);
        			cout << "ConKeeper finished"<<endl;
				exit (0);		
				break;
				
			case SIGUSR1: {
			
				pthread_mutex_lock(&sync_mutex);
					appStatus = dataTool.status;
				pthread_mutex_unlock(&sync_mutex);


				if (appStatus == CONKEEPER_HAVE_TO_EXIT){
  					if (dataTool.logMask >= LOGMASK_INFO){
       						logString.clear();
						logString.str("");
						logString << "(SignalThread): Terminating... " <<endl;
						LOG(INFO, logString.str());
                        		}
                                }
                                
                            	pthread_mutex_lock(&sync_mutex);
					dataTool.status = CONKEEPER_HAVE_TO_EXIT;
				pthread_mutex_unlock(&sync_mutex);

				sleep (5);
                                
        			cout << "ConKeeper finished"<<endl;
					
				exit (0);		
					
			
				break;
			} // end case SIGUSR1

			case SIGTSTP:
			case SIGUSR2:
 				if (dataTool.logMask >= LOGMASK_DEBUG){
       					logString.clear();
					logString.str("");
					logString << "(SignalThread): received signal: "<< signal <<endl;
					LOG(DEBUG, logString.str());
                        	}
				break;
			default:
				break;
		}
    	}
}
