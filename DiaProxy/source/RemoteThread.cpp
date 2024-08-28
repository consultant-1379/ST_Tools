#include "DiaProxy.h"
#include "Logger.h"

using namespace std;

extern pthread_t SignalThreadID;
extern pthread_t RemoteThreadID;
extern DiaProxyStatus diaProxyState;
extern SignalReason sigReason;
extern bool haveToExit;
extern bool couldBeCleaned;
extern CER_DATA cer_data;
extern std::vector<DiaServerConnection> v_connections;

//variable for defining/handling a mutual exclusion zone
extern pthread_mutex_t TRANSACTION_VECTOR;
extern pthread_mutex_t CONNECTION_VECTOR;
extern pthread_mutex_t CLIENT_VECTOR;
extern pthread_mutex_t CLIENT_THREAD_VECTOR;
extern pthread_mutex_t SESSION_MAP;
extern pthread_mutex_t PENDING_MESSAGE_MAP;
extern pthread_mutex_t TOOL_STATUS;
extern pthread_mutex_t STATISTIC;
extern pthread_mutex_t REPORT;

extern RemoteControl remoteControlData;
extern unsigned int numberClientThreads;

void* _RemoteThread(void *)
{ 
        stringstream logString;
        
	bool myHaveToExit;
	
	pthread_mutex_lock(&TOOL_STATUS);
		myHaveToExit = haveToExit;
		remoteControlData.status = REMOTE_CONNECTING;
	pthread_mutex_unlock(&TOOL_STATUS);

	if (myHaveToExit)  	pthread_exit(0);
	int errsv;

	logString.clear();
	logString.str("");
	logString << "(RemoteThread): Thread starting up" <<endl;
	LOG(EVENT, logString.str());

	//creating the server socket
	remoteControlData.sock = socket(AF_INET, SOCK_DGRAM, 0);

	if (remoteControlData.sock == -1)	//if error in socket creation
	{
	    errsv = errno;

	    logString.clear();
	    logString.str("");
	    logString << "(RemoteThread): Failed to create UDP server socket" <<endl;
	    logString <<"\tError: " << strerror(errsv) << endl;
	    LOG(ERROR, logString.str());

	    resetRemoteAndExit (1);
	}
       
	struct sockaddr_in local_addr;
	memset(&local_addr,0,sizeof(local_addr));
	local_addr.sin_family = AF_INET;
	local_addr.sin_addr.s_addr = INADDR_ANY;
	local_addr.sin_port = htons(remoteControlData.port);

	struct sockaddr_in remote_addr;
	memset(&remote_addr,0,sizeof(sockaddr_in));

	//binding the socket to a local port
	if(bind(remoteControlData.sock,(sockaddr*)&local_addr, sizeof(local_addr)) == -1){
            errsv = errno;

	    logString.clear();
	    logString.str("");
	    logString << "(RemoteThread): Failed to bind socket on port " << remoteControlData.port <<endl;
	    logString <<"\tError: " << strerror(errsv) << endl;
	    LOG(ERROR, logString.str());

    	    resetRemoteAndExit (1);
	}
	
        logString.clear();
        logString.str("");
        logString << "(RemoteThread): listening on port " << htons(local_addr.sin_port) <<endl;
        LOG(INFO, logString.str());
            
	pthread_mutex_lock(&TOOL_STATUS);
            remoteControlData.status = REMOTE_ON;
	pthread_mutex_unlock(&TOOL_STATUS);
        
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
	unsigned int sent = 0;
        char buff[DEFAULT_BUFFER_SIZE];
        string command = "";
        stringstream commandString;
        string answer = "";
                
	while (true){
		pthread_mutex_lock(&TOOL_STATUS);
			myHaveToExit = haveToExit;
		pthread_mutex_unlock(&TOOL_STATUS);

		if(myHaveToExit){ 
	            logString.clear();
	            logString.str("");
	            logString <<"(RemoteThread): Terminating... "<<endl;
	            LOG(EVENT, logString.str());
			
		    resetRemoteAndExit (0);
		} 
                

		tmpset = fds;
		tv.tv_sec = 1;
		tv.tv_usec = 0;

		//passive wait for any activity in the socket
                
		select(remoteControlData.sock+1,&tmpset, NULL, NULL, &tv);

		if(FD_ISSET(remoteControlData.sock, &tmpset)){ 
                        
			received = recvfrom(remoteControlData.sock, buff, DEFAULT_UDP_BUFFER_SIZE, 0, (struct sockaddr *) &remote_addr, &len);
                
      			if (received <= 0) {
	                    logString.clear();
	                    logString.str("");
	                    logString << "(RemoteThread): Received <= 0"<<endl;
	                    LOG(CONNECTIONS, logString.str());
                            
			    continue;
                        }
			
                        buff[received] = '\0';
                        commandString.clear();
                        commandString.str("");
                         
                        commandString << buff;
                        
	                logString.clear();
	                logString.str("");
	                logString << "(RemoteThread): New command received:"<< commandString.str()<< endl;
	                LOG(DEBUG, logString.str());
                            
			commandString >> command ;                        
			transform( command.begin(), command.end(), command.begin(), my_tolower );
                                                
                        if (command == "help" ) {
                                answer = displayCmdHelp();                                
                        }
                        else if (command == "get_status" ) {
                                answer = getStatus();
                        }
                        else if (command == "get_connection" ) {
                                
				for (unsigned int i = 0; i < v_connections.size(); i++) {
					answer += get_connection_info(&v_connections[i], i);
				}
                        }
                        else if (command == "get_statistic" ) {
                                
				for (unsigned int i = 0; i < v_connections.size(); i++) {
					answer += get_connection_info(&v_connections[i], i);
                                        answer += get_connection_statistic(&v_connections[i], i);
				}
                        }
                        else if (command == "get_config" ) {
                                answer = getConfiguration();                                
                        }
                        else if (command == "enable_report" ) {
                                answer = enable_report(commandString);                                
                        }
                        else if (command == "change_file_report" ) {
                                answer = change_file_report(commandString);                                
                        }
                        else if (command == "change_result_codes_period" ) {
                                answer = change_result_codes_period(commandString);                                
                        }
                        else if (command == "start_report" ) {
                                answer = start_report(commandString);                                
                        }
                        else if (command == "stop_report" ) {
                                answer = stop_report(commandString);                                
                        }
                        else if (command == "get_result_code_counter" ) {
                                answer = get_result_code_counter(commandString);
                        }
                        else if (command == "get_and_reset_result_code_counter" ) {
                                answer = get_and_reset_result_code_counter(commandString);
                        }
                        else if (command == "reset_result_code_counter" ) {
                                answer = reset_result_code_counter(commandString);
                        }
                        else if (command == "check_connections_up" ) {
                                answer = check_connections_up(commandString);
                        }
                        else if (command == "change" ) {
                                answer = changeDataTool(commandString);                                
                        }
                        else if (command == "exit" ) {
                                answer = exitTool();                                
                        }
                        
                        else answer = "UNKNOWN COMMAND" + displayCmdHelp(); 
                      
                        sent = sendto (remoteControlData.sock,answer.c_str(),answer.size(),0, (struct sockaddr *) &remote_addr, len);
                        if (sent == answer.size()) {
                                               
	                    logString.clear();
	                    logString.str("");
	                    logString << "(RemoteThread): Answer sent:"<< answer << endl;
	                    LOG(DEBUG, logString.str());
                        
                        }
                        else {
	                    logString.clear();
	                    logString.str("");
	                    logString << "(RemoteThread): Error trying to send: "<< answer << endl;
	                    LOG(WARNING, logString.str());
                            
                        }
                        answer="";
		} 
	} 
        
        logString.clear();
        logString.str("");
        logString << "(RemoteThread): Exiting..."<< endl;
        LOG(INFO, logString.str());

       	return 0;
}

string getStatus()
{
    return get_status_info();
}

string getConfiguration()
{
    return get_configuration_info();
}

string enable_report(std::istream& cmd)
{
    stringstream answer;
    string report ="";
    string file ="";
        
    cmd >> report >> file;
    if (file.empty())  {
        answer << endl<< "ERROR: file name is empty "<< endl;
        return  answer.str(); 
    }
    
    if (report == "latency") {
        cer_data.latency_report_enabled = true;
        strcpy((char*)cer_data.latency_report_file,file.c_str()); 

    }
    else if (report == "result_codes") {
        cer_data.DiaErrCounters_report_enabled = true;
        strcpy((char*)cer_data.DiaErrCounters_report_file,file.c_str()); 
    }
    else {
        answer << endl<< "ERROR: Wrong report value: "<< report << endl;
        answer << "\t Allowed values :  latency result_codes"<< endl;
        return  answer.str(); 
    }
    answer << "SUCCESS " << endl;       
    return  answer.str() ;  
    
}
string change_file_report(std::istream& cmd)
{
    stringstream answer;
    string report ="";
    string file ="";
        
    cmd >> report >> file;
    
    if (file.empty())  {
        answer << endl<< "ERROR: file name is empty "<< endl;
        return  answer.str(); 
    }
    
    if (report == "latency") {
        if (!cer_data.latency_report_enabled) {
            answer << endl<< "ERROR: "<< report <<" report is not enabled."<< endl;
            return  answer.str(); 
        }
        if (cer_data.DiaErrCounters_report_running) {
            answer << endl<< "ERROR: "<< report <<" report is already running"<< endl;
            answer << "\t Stop report before changing file name"<< endl;
            return  answer.str();        
        }
        
        strcpy((char*)cer_data.latency_report_file,file.c_str()); 

    }
    else if (report == "result_codes") {
        if (!cer_data.DiaErrCounters_report_enabled) {
            answer << endl<< "ERROR: "<< report <<" report is not enabled."<< endl;
            return  answer.str();        
        }
        if (cer_data.DiaErrCounters_report_running) {
            answer << endl<< "ERROR: "<< report <<" report is already running"<< endl;
            answer << "\t Stop report before changing file name"<< endl;
            return  answer.str();        
        }
        
        strcpy((char*)cer_data.DiaErrCounters_report_file,file.c_str()); 
    }
    else {
        answer << endl<< "ERROR: Wrong report value: "<< report << endl;
        answer << "\t Allowe values :  latency result_codes"<< endl;
        return  answer.str(); 
    }
    answer << "SUCCESS " << endl;       
    return  answer.str() ;  
    
}
string change_result_codes_period(std::istream& cmd)
{
    stringstream answer;
    string period ="";
        
    cmd >> period ;
    
    if (period.empty())  {
        answer << endl<< "ERROR: period is empty "<< endl;
        return  answer.str(); 
    }
    
    int seconds = atoi(period.c_str()); 
    if(seconds < 1){						
        answer << endl<< "ERROR: period shall be > 1 "<< endl;
        return  answer.str(); 
    }	
    
    cer_data.DiaErrCounters_report_timeout = seconds;			
    answer << "SUCCESS " << endl;       
    return  answer.str() ;  
    
}

string start_report(std::istream& cmd)
{
    stringstream answer;
    string report ="";
        
    cmd >> report ;
    if (report == "latency") {
        if (!cer_data.latency_report_enabled) {
            answer << endl<< "ERROR: "<< report <<" report is not enabled."<< endl;
            return  answer.str(); 
        }
        if (cer_data.latency_report_running) {
            answer << endl<< "ERROR: "<< report <<" report is already running"<< endl;
            return  answer.str();        
        }
        cer_data.latency_report_running = true;

    }
    else if (report == "result_codes") {
        if (!cer_data.DiaErrCounters_report_enabled) {
            answer << endl<< "ERROR: "<< report <<" report is not enabled."<< endl;
            return  answer.str();        
        }
        if (cer_data.DiaErrCounters_report_running) {
            answer << endl<< "ERROR: "<< report <<" report is already running"<< endl;
            return  answer.str();        
        }
        cer_data.DiaErrCounters_report_running = true;
    }
    else {
        answer << endl<< "ERROR: Wrong report value: "<< report << endl;
        answer << "\t Allowe values :  latency result_codes"<< endl;
        return  answer.str(); 
    }
    answer << "SUCCESS " << endl;       
    return  answer.str() ;  
    
}

string stop_report(std::istream& cmd)
{
    stringstream answer;
    string report ="";
        
    cmd >> report ;
    if (report == "latency") {
        if (!cer_data.latency_report_enabled) {
            answer << endl<< "ERROR: "<< report <<" report is not enabled."<< endl;
            return  answer.str(); 
        }
        if (!cer_data.latency_report_running) {
            answer << endl<< "ERROR: "<< report <<" report is not running"<< endl;
            return  answer.str();        
        }
        cer_data.latency_report_running = false;

    }
    else if (report == "result_codes") {
        if (!cer_data.DiaErrCounters_report_enabled) {
            answer << endl<< "ERROR: "<< report <<" report is not enabled."<< endl;
            return  answer.str();        
        }
        if (!cer_data.DiaErrCounters_report_running) {
            answer << endl<< "ERROR: "<< report <<" report is not running"<< endl;
            return  answer.str();        
        }
        cer_data.DiaErrCounters_report_running = false;
    }
    else {
        answer << endl<< "ERROR: Wrong report value: "<< report << endl;
        answer << "\t Allowe values :  latency result_codes"<< endl;
        return  answer.str(); 
    }
    answer << "SUCCESS " << endl;       
    return  answer.str() ;  
    
}

string get_and_reset_result_code_counter(std::istream& cmd)
{
    string answer = get_result_code_info();
    reset_result_code_info();
    return answer;

}

string get_result_code_counter(std::istream& cmd)
{
    return  get_result_code_info() ;
}

string reset_result_code_counter(std::istream& cmd)
{
    string answer ("SUCCESS");
    reset_result_code_info();
    return  answer;
}
string check_connections_up(std::istream& cmd)
{
    string answer;
    bool all_up = true;
    for (unsigned int i = 0; i < v_connections.size(); i++) {
    	all_up &= check_connection(&v_connections[i]);
    }
    if (all_up) answer = "SUCCESS";
    else        answer = "FAILED";
    return  answer;
}

string changeDataTool(std::istream& cmd)
{
        stringstream answer;
	string element, filter;
	bool after;
        
        string param ="";
        
        cmd >> param;
        while (!param.empty()) {
                const char * line = param.c_str();
               
		after = false;  
		filter = ":=";
		if (filterLine(line, filter, after, element)) {			
			if (!strcmp(element.c_str(),"LogMask")){
				after = true;  
				filter = "LogMask:=";
				if   (filterLine(line, filter, after, element)) { 
			            int lmask = atoi(element.c_str()); //conversion to an integer number
			            if(lmask > 0){						
				        cer_data.log_mask = lmask;			
				        Log::Instance().set_log_mask(cer_data.log_mask); 
                                    }	
				}
			}
   			else if (!strcmp(element.c_str(),"LogMode")){
				after = true;  
				filter = "LogMode:=";
				if   (filterLine(line, filter, after, element)) { 
					int logMode = atoi (element.c_str());
 					Log::Instance().set_log_mode(logMode);
				}
			}
                        
			else {
				answer << "FAIL Param "<< element <<" doesn't exist " << endl;
        			return  answer.str() ;  
			}
		}
                else {
			answer << "FAIL Worong syntax"<< param << endl;
			return  answer.str() ;  
                        
                }
                        
               param.erase();
               cmd >> param;
        }
        
        answer << "SUCCESS " << endl;       
        return  answer.str() ;  

}


std::string displayCmdHelp()
{
        std::stringstream info;
	char line [1024]; 
	ifstream inFile; 
        
        char * path = getenv("ST_TOOL_PATH");
        
	if (path == NULL) {
		info << endl << "ERROR: Env variable ST_TOOL_PATH not defined "<< endl << endl;
 		return info.str();
	}
        
        string help_file (path);
        
        help_file = help_file + "/share/DiaProxy/DiaProxy_help.txt";
              
	inFile.open (help_file.c_str());
				
	if (!inFile) {
		info << endl << "ERROR:Failed to open " << help_file << endl << endl;
 		return info.str();
	}
        
	info << endl;
                
	while(inFile) {
		inFile.getline(line, 1024);
		info << line << endl;
        }
        
 	return info.str();
}

void resetRemoteAndExit (int fail)
{
	
    pthread_mutex_lock(&TOOL_STATUS);
        remoteControlData.status = REMOTE_OFF;
    pthread_mutex_unlock(&TOOL_STATUS);

    if (fail){
        pthread_kill(SignalThreadID ,SIGUSR1);
    }
    RemoteThreadID=NULL;
    pthread_exit(0);

}


string exitTool()
{
    stringstream logString;
                        
    logString.clear();
    logString.str("");
    logString << "(RemoteThread): Diaproxy will be finshed by command..."<< endl;
    LOG(DEBUG, logString.str());
        
    
    pthread_mutex_lock(&TOOL_STATUS);
        sigReason = DIA_EXIT_REQ_BY_USER;
    pthread_mutex_unlock(&TOOL_STATUS);
    
    pthread_kill(SignalThreadID ,SIGUSR1);	
    return  "OK" ;  
}
string get_status_info() 
{
    stringstream logString;
    logString.clear();
    logString.str("");
    logString <<  endl ;
    switch (diaProxyState) {
        case DIAPROXY_STARTING:
            logString << "\tState : Starting\n" <<endl;			
            break;
        case DIAPROXY_STANDBY:
            logString << "\tState : Standby, waiting for TTCN clients connections\n" <<endl;			
            break;
        case DIAPROXY_PROCESSING:
            logString << "\tState : Processing diameter traffic\n" <<endl;			
            break;
        case DIAPROXY_CLEANNING:
            logString << "\tState : Cleaning resources\n" <<endl;			
            break;
        case DIAPROXY_OFF:
            logString << "\tState : Configuring\n" <<endl;			
            break;
        case DIAPROXY_SHUTINGDOWN:
            logString << "\tState : Shutting down\n" <<endl;			
            break;
        default:
            logString << "\tState : Wrong state\n" <<endl;			
        break;
    }
    
    return logString.str();
}  

string get_configuration_info() 
{
    stringstream logString;
    logString.clear();
    logString.str("");
    logString <<  endl;
    
    logString <<         "\tMain configuration parameters" << endl;
    logString << endl << "\t\tDiameter Server                        : " << cer_data.diameter_host << endl;
    logString << "\t\tNumber of Diameter Server connections  : "<< cer_data.numberOfConnections << endl;
    logString << "\t\tNumber of Client Threads (max)         : "<< numberClientThreads << " (" << cer_data.maxNumberClientThreads << ")" << endl;
    logString << "\t\tDiaProxy port                          : "<< cer_data.serv_port<< endl;
    logString << endl;
    
    logString <<         "\tlatency report configuration" << endl;
    logString << endl << "\t\tEnabled                        : " <<(cer_data.latency_report_enabled ? "True" : "False")<< endl;
    logString <<         "\t\tRunning                        : " <<(cer_data.latency_report_running ? "True" : "False")<< endl;
    logString <<         "\t\tFile Name Prefix               : " << cer_data.latency_report_file << endl;
    logString << endl;


    logString <<         "\tresult_codes report configuration" << endl;
    logString << endl << "\t\tEnabled                        : " <<(cer_data.DiaErrCounters_report_enabled ? "True" : "False")<< endl;
    logString <<         "\t\tRunning                        : " <<(cer_data.DiaErrCounters_report_running ? "True" : "False")<< endl;
    logString <<         "\t\tFile Name Prefix               : " << cer_data.DiaErrCounters_report_file << endl;
    logString <<         "\t\tSaving period                  : " << cer_data.DiaErrCounters_report_timeout << endl;
    logString << endl;
    
    return logString.str();
} 

string get_result_code_info()
{
    stringstream logString;
    logString.clear();
    logString.str("");

    logString << "request=" << cer_data.resultcode_request;
    logString << " success=" << cer_data.resultcode_success;
    logString << " busy=" << cer_data.resultcode_busy;
    logString << " utc=" << cer_data.resultcode_utc;
    logString << " other=" << cer_data.resultcode_other;

    return logString.str();
}

void reset_result_code_info()
{
	pthread_mutex_lock(&REPORT);
		cer_data.resultcode_request = 0;
		cer_data.resultcode_success = 0;
		cer_data.resultcode_busy = 0;
		cer_data.resultcode_utc = 0;
		cer_data.resultcode_other = 0;
	pthread_mutex_unlock(&REPORT);

}

bool check_connection(void *connection)
{
    DiaServerConnection *myConnection = (DiaServerConnection *)connection;;
	if (myConnection->status == CONNECTED)		return true;
	else 										return false;

}
string get_connection_info(void *connection, int index)
{

    DiaServerConnection *myConnection = (DiaServerConnection *)connection;;
    stringstream logString;
    logString.clear();
    logString.str("");
    logString <<  endl <<  endl;

    char * status[]={"OFF","TOBECONNECTED","CONNECTING","CONNECTED","BROKEN","MAXCONEXIONREACHED","CONFIGURATIONERROR"};

    logString << endl << "\t-------------------------------------" << endl;
    logString <<         "\tCONNECTION NUMBER " << index <<  endl;
    logString <<         "\t-------------------------------------" << endl;

    logString <<         "\t\tThread Id                           " << myConnection->threadID << endl;
    logString <<         "\t\tSocket Id                           " << myConnection->sockId << endl;

    logString <<         "\t\tDiameter server                     " << myConnection->diameter_server << endl;
    logString <<         "\t\tDiameter server port                " << myConnection->serv_port << endl;
    logString <<         "\t\tProtocol                            " << (myConnection->use_sctp ? "SCTP" : "TCP") << endl;
    logString <<         "\t\tUsed origin host                    " << myConnection->origin_host << endl;
             
    logString <<         "\t\tConnection to server retries        " << myConnection->conexionRetries << endl;
    logString <<         "\t\tNumber of TTCN Clients              " << myConnection->totalNumberOfClients << endl;
    logString <<         "\t\tNumber of active TTCN Clients       " << myConnection->numberOfClients << endl;
    logString <<         "\t\tConnection Status                   " << status[myConnection->status] << endl;

    return logString.str();
}
 
string get_connection_statistic(void *connection, int index)
{
    DiaServerConnection *myConnection = (DiaServerConnection *)connection;;
    stringstream logString;
    logString.clear();
    logString.str("");
    logString <<  endl;

    logString <<         "\t\tRequests received from Clients      " << myConnection->requestReceivedFromClient << endl;
    logString <<         "\t\tRequests sent to Server             " << myConnection->requestSentToServer << endl;
    logString <<         "\t\tRequests discarded from Clients     " << myConnection->requestDiscardFromClient << endl;
    logString <<         "\t\tAnswers received from Clients       " << myConnection->answerReceivedFromClient << endl;
    logString <<         "\t\tAnswers sent to Server              " << myConnection->answerSentToServer << endl;
    logString <<         "\t\tAnswers discarded from Clients      " << myConnection->answerDiscardFromClient << endl;
    logString <<  endl;
		
    logString <<         "\t\tRequests received from Server       " << myConnection->requestReceivedFromServer << endl;
    logString <<         "\t\tRequests sent to Clients            " << myConnection->requestSentToClient << endl;
    logString <<         "\t\tRequests discarded from Server      " << myConnection->requestDiscardFromServer << endl;
    logString <<         "\t\tAnswers received from Server        " << myConnection->answerReceivedFromServer << endl;
    logString <<         "\t\tAnswers sent to Clients             " << myConnection->answerSentToClient << endl;
    logString <<         "\t\tAnswers discarded from Server       " << myConnection->answerDiscardFromServer << endl;

    logString <<  endl;

    return logString.str();
}
