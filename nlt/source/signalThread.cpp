#include "networkLayerTranslator.h"
#include <vector>

using namespace std;
extern pthread_t SignalThreadID;
extern SignalReason sigReason;

extern ToolData toolData;
extern vector<Listener> v_listeners;
extern vector<Connection> v_connections;
 
void * _SignalThread(void *)
{
    int signal;
    sigset_t signal_set;
    
    for(;;){
               
        sleep(1);
               
        sigfillset( &signal_set );
        sigwait(&signal_set, &signal);
        switch (signal) {
            case SIGINT:
            case SIGTERM:
                toolData.status = HAVE_TO_EXIT;
                sleep (5);
                cout << "(SignalThread): networkLayerTranslator finished"<<endl;
                exit (0);		
                break;
                
            case SIGUSR1: 
                toolData.status = HAVE_TO_EXIT;
                sleep (5);
                cout << "(SignalThread): networkLayerTranslator finished"<<endl;
                exit (0);		
                break;

            case SIGTSTP:
            case SIGUSR2:
                    cout << "(SignalThread): received signal: "<< signal <<endl;
                    break;
            default:
                    break;
        }
    }
}
