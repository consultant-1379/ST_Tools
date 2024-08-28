#include "ConnectionKeeper.h"

/******************************************************************************************
	Global variables for sharing common values between the different modules
*******************************************************************************************/

//variable for defining/handling a mutual exclusion zone
pthread_mutex_t sync_mutex = PTHREAD_MUTEX_INITIALIZER;

//thread handler for Signalling
pthread_t SignalThreadID;

//thread handler for the ProxyThread
pthread_t ControlThreadID;

//thread handler for Remote control
pthread_t RemoteThreadID;

//thread handler for Remote control
pthread_t HeartBeatThreadID;


using namespace std;

unsigned int nextConnection = 0;
vector<Listener> v_listeners;
vector<Connection> v_connections;
vector <int> conIndex;
struct RemoteControl remoteControlData;
struct HeartBeat     heartBeatData;          

applicationData dataTool;

/******************************************************************************************
	END OF Global variables for sharing common values between the different modules
*******************************************************************************************/


//main program
int main(int argc, char* argv[])
{
        
	char line [1024];
	int ret = 0, errsv = 0;
        
	dataTool.status = CONKEEPER_STARTING;
	dataTool.activeZone = UNKNOWM;
        dataTool.redundancy = false;
//      dataTool.logMask = LOGMASK_DEBUG;
        dataTool.logMask = LOGMASK_EVENT;
//      dataTool.logMode = STDOUT_MODE;
//      dataTool.logMode = MIXED_MODE;
        dataTool.logMode = FILE_MODE;
        dataTool.statistic = false;
      	gethostname(line,100);
        dataTool.hostname = line;
	remoteControlData.port = REMOTE_PORT;
        
        std::string ipHost = getIpByHostname(dataTool.hostname);
	strcpy (dataTool.ip_host, ipHost.c_str());
                                        
	dataTool.logFile= "conKeeper";
        
	string prg(LOG_PRG);
    	Log::Instance().ini(dataTool.logFile, prg); 
	Log::Instance().set_log_mask(dataTool.logMask);
 	Log::Instance().set_log_mode(dataTool.logMode);
        
	stringstream logString;
        
	sigset_t signal_set;
	
       	if (!parseCommandLine(argc, argv)){
		displayHelp();
                return 1;
	} 
        
 	system ("clear");

	logString.clear();
	logString.str("");
	logString << "ConKeeper running on: " <<dataTool.hostname <<endl;
	LOG(INFO, logString.str());
        
        
	remoteControlData.sock = -1;
	remoteControlData.status = REMOTE_OFF;
        
	addNewListenner(LOAD, LOAD_PORT);
	addNewListenner(LDAP, LDAP_PORT);
	addNewListenner(DIAMETER, DIA_PORT);
                        
          
	// Prepare Connections information vector   
	struct Connection initialConnection;       
	initialConnection.server.sock = -1;
	initialConnection.server.status = OFFLINE;
	initialConnection.server.threadID = 0;
	initialConnection.client.sock = -1;
	initialConnection.client.status = OFFLINE;
	initialConnection.client.threadID = 0;
	initialConnection.type = NONE;
	initialConnection.messageLen = 0;
	initialConnection.firstConnectionOk = false;
	strcpy(initialConnection.type_str, "");
        
	v_connections.reserve(DEFAULT_NUMBER_CONNECTIONS);
	v_connections.assign(DEFAULT_NUMBER_CONNECTIONS,initialConnection); 
	
	for (unsigned int i = 0; i < v_connections.size(); i++) {
		v_connections[i].position = i;
	}
        		
        /* block all signals */
        sigfillset( &signal_set );
	pthread_sigmask( SIG_BLOCK, &signal_set,NULL);
        
	/*** Threads Spawning ***/			
        ret = pthread_create(&SignalThreadID, NULL,handler, NULL );
       	if (ret) {
		errsv = ret;
		logString.clear();
		logString << "SignalThread creation returned" << ret << endl;
		logString <<"\tError: " << strerror(errsv) << endl;
		LOG(ERROR, logString.str());
		return 0;
	}

       	ret = pthread_create(&RemoteThreadID,NULL,_RemoteThread,NULL);
       	if (ret) {
		errsv = ret;
		logString.clear();
		logString << "RemoteThread creation returned" << ret << endl;
		logString <<"\tError: " << strerror(errsv) << endl;
		LOG(ERROR, logString.str());

		return 0;
	}
        
        
       	ret = pthread_create(&HeartBeatThreadID,NULL,_HeartBeatThread,NULL);
       	if (ret) {
		errsv = ret;
		logString.clear();
		logString << "HeartbeatThread creation returned" << ret << endl;
		logString <<"\tError: " << strerror(errsv) << endl;
		LOG(ERROR, logString.str());

		return 0;
	}
              
 	dataTool.status = CONKEEPER_STARTING;
                               
	ret = pthread_create(&ControlThreadID,NULL,_ControlThread,NULL);        
	if (ret) {
		errsv = ret;
		logString.clear();
		logString << "ControlThread creation returned" << ret << endl;
		logString <<"\tError: " << strerror(errsv) << endl;
		LOG(ERROR, logString.str());

		return 0;
	}

        sleep(2); //go to sleep
        
	if (dataTool.logMask >= LOGMASK_INFO){
       		logString.clear();
		logString.str("");
		logString << "Waiting while the SignalThread is still alive, go on..." << endl;
		LOG(INFO, logString.str());
        }

       	//while the thread is still alive, go on..... 
	void *theThreadStatus;
	pthread_join(SignalThreadID,&theThreadStatus);
	return 0;

        
} //int main(int argc, char* argv[])



bool parseCommandLine (int argc, char **argv)
{
	for(int i=1;i<argc;i++){ 
															 
		if(strcmp(argv[i],"-p") == 0){
			i++;
			if(argc == i){ 
				return false;
			}
			remoteControlData.port = atoi(argv [i]);
		}                
                else {
			return false;                
		}         		
	}
	
	return true;     
}

void displayHelp()
{
	cout << endl << "Command line error."<< endl << endl;
				
	cout << "Usage:\t\tConKeeper [ -p <port>]"<< endl<< endl<< endl;
	cout << "\t\t-p <port>\t\tRemote cotrol port "<< endl ;
	cout << " "<< endl<< endl;								
}



