#include "CpsMonitor.h"

using namespace std;
extern struct MonitorData monitorData;
extern pthread_t MonitorThreadID;
extern pthread_mutex_t sync_mutex;

void *
handler(void *)
{
    int signal;
    sigset_t signal_set;
    stringstream logString;
        
    for(;;){
               
        sigfillset( &signal_set );
        sigwait(&signal_set, &signal);
        switch (signal) {
            case SIGINT:
            case SIGTERM:{
                if (monitorData.logMask >= LOGMASK_INFO){
                    logString.clear();
                    logString.str("");
                    logString << "SignalThread: user press ctrl-C.Terminating... "<< endl;
                    LOG(INFO, logString.str());
                }
                monitorData.status = MONITOR_HAVE_TO_EXIT;
                if (monitorData.logMask >= LOGMASK_WARNING){
       		    logString.clear();
		    logString.str("");
		    logString << "SignalThread: Waiting for Monitorthread to finish... " <<endl;
		    LOG(INFO, logString.str());
                }
                                
                while (	MonitorThreadID!=NULL) {};
                if (monitorData.logMask >= LOGMASK_WARNING){
       		    logString.clear();
		    logString.str("");
		    logString << "SignalThread: Monitorthread has finished." <<endl;
		    LOG(INFO, logString.str());
                }
                                
                exit (0);		
                break;
            }	
            case SIGUSR1: {
                pthread_mutex_lock(&sync_mutex);
		    monitorData.status = MONITOR_HAVE_TO_EXIT;
	        pthread_mutex_unlock(&sync_mutex);
            
                if (monitorData.logMask >= LOGMASK_WARNING){
       		    logString.clear();
		    logString.str("");
		    logString << "SignalThread: Terminating... ... " <<endl;
		    LOG(INFO, logString.str());
                }
            
                exit (0);		
                break;
            
            }
            case SIGTSTP:
            case SIGUSR2:
            default:
                if (monitorData.logMask >= LOGMASK_INFO){
                    logString.clear();
                    logString.str("");
                    logString << "SignalThread: received signal: "<< signal <<endl;
                    LOG(DEBUG, logString.str());
                }
            break;
        }
    }
}
