#include "ConnectionKeeper.h"

using namespace std;

extern vector<Connection> v_connections;
extern vector<Listener> v_listeners;
extern time_t start, stop, lastaction;
extern pthread_mutex_t sync_mutex;

extern unsigned int nextConnection;
extern vector <int> conIndex;
extern applicationData dataTool;

extern string appStatus[];

extern RemoteControl remoteControlData;
extern applicationData dataTool;
extern HeartBeat heartBeatData;


void* _RemoteThread(void *)
{ 
        stringstream logString;
 	ConKeeperStatus appStatus;

	pthread_mutex_lock(&sync_mutex);
		appStatus = dataTool.status;
	pthread_mutex_unlock(&sync_mutex);

	if (appStatus == CONKEEPER_HAVE_TO_EXIT ){
  		if (dataTool.logMask >= LOGMASK_INFO){
       			logString.clear();
			logString.str("");
			logString << "RemoteThread_ : Remote connection shall be closed" <<endl;
			LOG(INFO, logString.str());
		}
                        
		pthread_exit(0);
	}
             
       	pthread_mutex_lock(&sync_mutex);
		remoteControlData.status = REMOTE_CONNECTING;
	pthread_mutex_unlock(&sync_mutex);


	int errsv;
	if (dataTool.logMask >= LOGMASK_INFO) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: Starting up......." <<endl;
		LOG(INFO, logString.str());
	}
                                	
	//creating the server socket
	remoteControlData.sock = socket(AF_INET, SOCK_DGRAM, 0);

	if (remoteControlData.sock == -1){
		if (dataTool.logMask >= LOGMASK_ERROR) {
			errsv = errno;
 			logString.clear();
			logString.str("");
			logString << "RemoteThread_: Create socket returned" << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(ERROR, logString.str());
                }
		resetRemoteAndExit (1);
	}
/*
	int optval = 1;
	if (setsockopt(remoteControlData.sock, SOL_SOCKET, SO_REUSEADDR, &optval, sizeof optval)){
		if (dataTool.logMask >= LOGMASK_ERROR) {
			errsv = errno;
 			logString.clear();
			logString.str("");
			logString << "RemoteThread_: Setting  SO_REUSEADDR returned" << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(ERROR, logString.str());
                }
		resetRemoteAndExit (1);
        }
*/	
	struct sockaddr_in local_addr;
	memset(&local_addr,0,sizeof(local_addr));
	local_addr.sin_family = AF_INET;
	local_addr.sin_addr.s_addr = INADDR_ANY;
	local_addr.sin_port = htons(remoteControlData.port);

	struct sockaddr_in remote_addr;
	memset(&remote_addr,0,sizeof(sockaddr_in));

	//binding the socket to a local port
	if(bind(remoteControlData.sock,(sockaddr*)&local_addr, sizeof(local_addr)) == -1){
		if (dataTool.logMask >= LOGMASK_ERROR) {
			errsv = errno;
 			logString.clear();
			logString.str("");
			logString << "RemoteThread_: Failed to bind socket on port: " << remoteControlData.port  << endl;
			logString <<"\tError: " << strerror(errsv) << endl;
			LOG(ERROR, logString.str());
                }

		resetRemoteAndExit (1);
	}
	
	if (dataTool.logMask >= LOGMASK_INFO) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: listening on port " << remoteControlData.port << endl;
		LOG(INFO, logString.str());
	}
                
       	pthread_mutex_lock(&sync_mutex);
		remoteControlData.status = REMOTE_ON;
	pthread_mutex_unlock(&sync_mutex);
	
	socklen_t len = sizeof(remote_addr);

	fd_set fds;
	fd_set tmpset;
	struct timeval tv;
	tv.tv_sec = 2;
	tv.tv_usec = 0;
	
	//subscribing the server socket to the mask to be used in the 'select'
	FD_ZERO(&fds);
	FD_SET(remoteControlData.sock, &fds);
	int received = 0;
        char buff[DEFAULT_BUFFER_SIZE];
        string command = "";
        stringstream commandString;
        string answer = "";
                
	while (true){
		pthread_mutex_lock(&sync_mutex);
 			appStatus = dataTool.status;
		pthread_mutex_unlock(&sync_mutex);

		if (appStatus == CONKEEPER_HAVE_TO_EXIT){
  			if (dataTool.logMask >= LOGMASK_INFO){
       				logString.clear();
				logString.str("");
				logString << "RemoteThread_: Terminating... " <<endl;
				LOG(INFO, logString.str());
			}
                        
			resetRemoteAndExit (0);
		}
                

		tmpset = fds;
		tv.tv_sec = 2;
		tv.tv_usec = 0;

		//passive wait for any activity in the socket
		select(remoteControlData.sock+1,&tmpset, NULL, NULL, &tv);

		if(FD_ISSET(remoteControlData.sock, &tmpset)){ 
		
      			if ( (received = recvfrom(remoteControlData.sock, buff, DEFAULT_BUFFER_SIZE, 0, (struct sockaddr *) &remote_addr, &len)) <= 0) {
				if (dataTool.logMask >= LOGMASK_WARNING) {
       					logString.clear();
					logString.str("");
					logString << "RemoteThread_: Received <= 0. Thread shall be closed." << endl;
					LOG(WARNING, logString.str());
				}
				resetRemoteAndExit (0);
                        }
			
                        buff[received] = '\0';
                        commandString.clear();
                        commandString.str("");
                         
                        commandString << buff;
			if (dataTool.logMask >= LOGMASK_INFO) {
       				logString.clear();
				logString.str("");
				logString << "RemoteThread_: New command received:" << endl;
				logString <<  "\t" <<commandString.str() << endl;
                                LOG(INFO, logString.str());
			}

			commandString >> command ;                        
			transform( command.begin(), command.end(), command.begin(), my_tolower );
                                                
                        if (command == "add" ){
                                answer = addListenner(commandString);                                
                        }
                        else if (command == "setdesthost" ) {
                                answer = setdesthost(commandString);                                
                        }
                        else if (command == "getstatus" ) {
                                answer = getStatus();                                
                        }
                        else if (command == "getconfig" ) {
                                answer = getConfiguration();                                
                        }
                        else if (command == "getlistener" ) {
                                answer = getListenner(commandString);                                
                        }
                        else if (command == "getconnection" ) {
                                answer = getConnection(commandString);                                
                        }
                        else if (command == "change" ) {
                                answer = changeDataTool(commandString);                                
                        }
                        else if (command == "reset" ) {
                                answer = resetTool();                                
                        }
                        else if (command == "exit" ) {
                                answer = exitTool();                                
                        }
                        
                        else answer = "UNKNOWN COMMAND" + displayCmdHelp(); 
                      
                        sendto (remoteControlData.sock,answer.c_str(),answer.size(),0, (struct sockaddr *) &remote_addr, len);
		} 
	} 
        
	if (dataTool.logMask >= LOGMASK_INFO) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: Exiting..." << remoteControlData.port << endl;
		LOG(INFO, logString.str());
	}

       	return 0;
}

string getConfiguration()
{
        return  displayAppInfo(); 
}

string getStatus()
{

    if (dataTool.status == CONKEEPER_TO_BE_RESET)  {
        for (unsigned int i = 0; i < v_listeners.size(); i++) {
                                
            if (v_listeners[i].status != LISTENER_TO_BE_CONFIGURED) {
                return  appStatus[dataTool.status]; 
            }
        }
        
        dataTool.status= CONKEEPER_TO_BE_CONFIGURED ;
    }

    return  appStatus[dataTool.status]; 
}

string resetTool()
{
        stringstream logString;
	if (dataTool.logMask >= LOGMASK_INFO) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: conKeeper will be reset by command..." << endl;
		LOG(INFO, logString.str());
	}
        
	dataTool.status = CONKEEPER_TO_BE_RESET; 
        return  "OK"; 
}

string exitTool()
{
        stringstream logString;
	if (dataTool.logMask >= LOGMASK_INFO) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: conKeeper will be finshed by command..." << endl;
		LOG(INFO, logString.str());
	}
        
	dataTool.status = CONKEEPER_HAVE_TO_EXIT; 
        return  "OK" ;  
}

string changeDataTool(istream& ss)
{
        // Parameters for command add are
        //    type hostname
        stringstream logString;
        string answer = "";
        string configParam = "";        
                        
        ss >> configParam;   
	transform( configParam.begin(), configParam.end(), configParam.begin(), my_toupper );
        
        if (configParam == "STATISTIC") {
                string value ="";
                ss >> value;
		transform( value.begin(), value.end(), value.begin(), my_toupper );
                if (value == "ENABLE") {
        		dataTool.statistic = true;
                }
                else if (value == "DISABLE") {
        		dataTool.statistic = false;
                }
                else {
        		answer = "COMMAND FAILED: Value for " + configParam + " shall be enable|disable";
        		return answer;
                }
	}
                
        else if (configParam == "LOGMASK") {
                unsigned int mask;
        	ss >> mask;
                if (mask < 1) {
        		answer = "COMMAND FAILED: Value for " + configParam + " shall be > 0";
        		return answer;
                }
                dataTool.logMask = mask;
		Log::Instance().set_log_mask(dataTool.logMask);
	}
                
        else if (configParam == "LOGMODE") {
                int mode;
        	ss >> mode;
                if ((mode < 0) || (mode > 2)) {
        		answer = "COMMAND FAILED: Value for " + configParam + " shall be on range 0-2";
        		return answer;
                }
                dataTool.logMode = mode;
		Log::Instance().set_log_mode(dataTool.logMode);
	}
	else {
             answer = "COMMAND FAILED: Configuration parameter " + configParam + " not valid";
             return answer;                   
        }
                       
	if (dataTool.logMask >= LOGMASK_DEBUG) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: change done successfully" << endl;
		LOG(DEBUG, logString.str());
	}

        answer = "OK";
        return answer;
}

string getListenner(istream& ss)
{
        // Parameters for command add are
        //    type 
        stringstream logString;
        string answer = "";
        string type = "";        
        ConnectionType searchedType;
                        
        ss >> type;   
       	transform( type.begin(), type.end(), type.begin(), my_toupper );
        
	if (dataTool.logMask >= LOGMASK_DEBUG) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: Parameters for command..." << endl;
		logString <<  "\ttype: " << type << endl;
		LOG(DEBUG, logString.str());
	}
                
        if (type == "LOAD")		searchedType = LOAD;
        else if (type == "DIAMETER")	searchedType = DIAMETER;
        else if (type == "LDAP")	searchedType = LDAP;
        else if (type == "ALL")		searchedType = NONE;
	else {
             answer = "COMMAND FAILED: Type " + type + " not valid";
             return answer;                   
        }
               
        
	for (unsigned int i = 0; i < v_listeners.size(); i++) {
                                
                if ((v_listeners[i].type == searchedType) || type == "ALL")
                        answer += getListennerInfo(v_listeners[i], i);
	}

        return answer;
}

string getConnection(istream& ss)
{
        // Parameters for command add are
        //    type 
        stringstream logString;
        string answer = "";
        string type = "";        
        ConnectionType searchedType;
                        
        ss >> type;   
       	transform( type.begin(), type.end(), type.begin(), my_toupper );
        
	if (dataTool.logMask >= LOGMASK_DEBUG) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: Parameters for command..." << endl;
		logString <<  "\ttype: " << type << endl;
		LOG(DEBUG, logString.str());
	}
                
        if (type == "LOAD")		searchedType = LOAD;
        else if (type == "DIAMETER")	searchedType = DIAMETER;
        else if (type == "LDAP")	searchedType = LDAP;
        else if (type == "ALL")		searchedType = NONE;
	else {
             answer = "COMMAND FAILED: Type " + type + " not valid";
             return answer;                   
        }

	vector <int> my_conIndex;
	vector<Connection> my_v_connections;
        
	pthread_mutex_lock(&sync_mutex);
        	my_conIndex = conIndex;
		my_v_connections = v_connections;
	pthread_mutex_unlock(&sync_mutex);
                
	unsigned int i ;
        bool conFound = false;
	vector <int>::iterator pos = my_conIndex.begin();
	while (pos != my_conIndex.end()) {                
                i = *pos;
                                                       
                if ((my_v_connections[i].type == searchedType) || type == "ALL"){
                        answer += getConnectionInfo(my_v_connections[i], i);
                        conFound = true;
		} 
		pos++;
        }
	if (! conFound) 	answer = "There is not active connection for " + type + " type.\n";
        return answer;
}

string setdesthost(istream& ss)
{
        // Parameters for command add are
        //    type hostname port
        stringstream logString;
        string answer = "";
        string primary_hostname = "";        
        string secondary_hostname = "";        
        string primary_ip = "";        
        string secondary_ip = "";        
        string type = "";
        ConnectionType searchedType;
        int port = 0;
        bool not_used = false;
        
        ss >> type >> primary_hostname >> port >> secondary_hostname;   
                        
	transform( type.begin(), type.end(), type.begin(), my_toupper );
        
	if (dataTool.logMask >= LOGMASK_DEBUG) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: Parameters for command..." << endl;
		logString <<  "\ttype: " << type << endl;
		logString <<  "\tprimary hostname: " << primary_hostname << endl;
		logString <<  "\tsecondary hostname: " << secondary_hostname << endl;
		LOG(DEBUG, logString.str());
	}

        
        if (primary_hostname == "0.0.0.0") {
                not_used = true;
        }
        else {
        	primary_ip = getIpByHostname(primary_hostname);
        
        	if (primary_ip.empty()) {
			answer = "COMMAND FAILED: Destination " + primary_hostname + " not valid";
			return answer;                   
        	}
        
        	if (!secondary_hostname.empty()) {
        		secondary_ip = getIpByHostname(secondary_hostname);
                
        		if (secondary_ip.empty()) {
             			answer = "COMMAND FAILED: Destination " + secondary_hostname + " not valid";
             			return answer;                   
        		}
        	}
                
        }
                
                
        if (type == "LOAD")		searchedType = LOAD;
        else if (type == "DIAMETER")	searchedType = DIAMETER;
        else if (type == "LDAP")	searchedType = LDAP;
        else if (type == "ALL")		searchedType = NONE;
	else {
             answer = "COMMAND FAILED: Type " + type + " not valid";
             return answer;                   
        }
                       
        pthread_mutex_lock(&sync_mutex);                       
        
        for (unsigned int i = 0; i < v_listeners.size(); i++) {
                
                if ((v_listeners[i].type == searchedType) && (v_listeners[i].status == LISTENER_TO_BE_CONFIGURED)) {
                        
                	if (not_used){
				v_listeners[i].status = LISTENER_NOT_USED;
                                break;
                        } 
                        
                        if (v_listeners[i].port != port) {
				v_listeners[i].port = port;
				v_listeners[i].status = LISTENER_TO_BE_CLOSED;
			}
			strcpy (v_listeners[i].primary_ip_host, primary_ip.c_str());
                               
			if (!secondary_ip.empty()){
				strcpy (v_listeners[i].secondary_ip_host, secondary_ip.c_str());
				if (searchedType == DIAMETER) {
					dataTool.redundancy = true;
					heartBeatData.port = port;
					strcpy (heartBeatData.secondary_ip_host, secondary_ip.c_str());
					strcpy (heartBeatData.primary_ip_host, primary_ip.c_str());
				}
			}
                }
	}
	pthread_mutex_unlock(&sync_mutex);

        answer = "OK";
        return answer;
}


string addListenner(istream& ss)
{
        // Parameters for command add are
        //    type port hostname
        stringstream logString;
        string answer = "";
        string hostname = "";        
        string type = "";        
        int port = 0;
        
        ss >> type >> port >> hostname;   
	transform( type.begin(), type.end(), type.begin(), my_toupper );
                     
	if (dataTool.logMask >= LOGMASK_DEBUG) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: Parameters for command..." << endl;
		logString <<  "\ttype: " << type << endl;
		logString <<  "\thostname: " << hostname << endl;
		logString <<  "\tport: " << port << endl;
		LOG(DEBUG, logString.str());
	}
        
	// Prepare Listeners information vector   
        struct Listener myListener;
	myListener.sock = -1;
	myListener.port = port;
	
	myListener.threadID = 0;

        
        if (hostname.empty())
                myListener.status = LISTENER_TO_BE_CONFIGURED;
        else {
        	string ip = getIpByHostname(hostname);
        
		if (ip.empty()) {
             		answer = "COMMAND FAILED: Destination " + hostname + " not valid";
             		return answer;                   
        	}
		strcpy(myListener.primary_ip_host,ip.c_str());        
		myListener.status = LISTENER_TO_BE_STARTED;
		cout << "Destination Host Load: " << myListener.primary_ip_host << endl;		
		if (dataTool.logMask >= LOGMASK_DEBUG) {
       			logString.clear();
			logString.str("");
			logString << "RemoteThread_: Destination Host Load: " << myListener.primary_ip_host << endl;
			LOG(DEBUG, logString.str());
		}
        }
        
        if (type == "LOAD")		myListener.type = LOAD;
        else if (type == "DIAMETER")	myListener.type = DIAMETER;
        else if (type == "LDAP")	myListener.type = LDAP;
	else {
             answer = "COMMAND FAILED: Type " + type + " not valid";
             return answer;                   
        }

        v_listeners.push_back(myListener);
        
        answer = "OK";
        return answer;
}


void addNewListenner(ConnectionType type, int port)
{
                    
        struct Listener myListener;
	myListener.sock = -1;
	myListener.port = port;
        myListener.type = type;
	myListener.status = LISTENER_TO_BE_STARTED;
	myListener.threadID = 0;
	strcpy(myListener.primary_ip_host,"");        
	strcpy(myListener.secondary_ip_host,"");        

        v_listeners.push_back(myListener);
                
}


