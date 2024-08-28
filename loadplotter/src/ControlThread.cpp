#include "loadplotter.h"

using namespace std;
extern pthread_t SignalThreadID;

extern vector<Connection> v_connections;
extern pthread_mutex_t sync_mutex;
extern applicationData dataTool;

void* _ControlThread(void *arg)
{
	int ret, errsv;
        stringstream logString;
	ToolStatus appStatus;

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
	 			dataTool.status = LOADPLOTTER_HAVE_TO_EXIT;
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
 			dataTool.status = LOADPLOTTER_HAVE_TO_EXIT;
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
 			dataTool.status = LOADPLOTTER_HAVE_TO_EXIT;
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
                        
                       case LOADPLOTTER_STARTING:
                       case LOADPLOTTER_TO_BE_CONFIGURED:
                       case LOADPLOTTER_READY:{


                               	for (unsigned int i = 0; i < v_connections.size(); i++) {
                                
                                	if (v_connections[i].status != OFFLINE) continue;
                        
                        		ret = pthread_create(&v_connections[i].threadID,&myAttr,_ConnectionThread_CBA,(void *) &(v_connections[i]));

               				if (ret && (dataTool.logMask >= LOGMASK_ERROR)) {
						errsv = ret;
       						logString.clear();
						logString.str("");
						logString << "ConnectionThread creation returned" << ret << endl;
						logString <<"\tError: " << strerror(errsv) << endl;
						LOG(ERROR, logString.str());
                                        
						pthread_mutex_lock(&sync_mutex);
 							dataTool.status = LOADPLOTTER_HAVE_TO_EXIT;
						pthread_mutex_unlock(&sync_mutex);

        					pthread_kill(SignalThreadID ,SIGUSR1);
					}
					pthread_mutex_lock(&sync_mutex);
 						dataTool.status = LOADPLOTTER_READY;
					pthread_mutex_unlock(&sync_mutex);
				} 
				break;
                        }
                        
                        case LOADPLOTTER_TO_BE_RESET:{
                                break;
                        }
                        
                        case LOADPLOTTER_HAVE_TO_EXIT:
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

