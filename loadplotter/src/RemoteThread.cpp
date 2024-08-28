#include "loadplotter.h"

using namespace std;

extern pthread_t SignalThreadID;
extern pthread_mutex_t sync_mutex;
extern pthread_t RemoteThreadID;

extern vector<Connection> v_connections;
extern applicationData dataTool;
extern RemoteControl remoteControlData;

std::string appStatus[] = {
        "STARTING",
	"TO_BE_CONFIGURED",
       	"READY",
	"TO_BE_RESET",
	"HAVE_TO_EXIT"        
} ;       

std::string conStatus[] = {
        "NOT_USED",
        "OFFLINE",
        "STARTING",
	"TO_BE_CONNECTED",
	"ONLINE",
	"TO_BE_CLOSED" ,
	"FAULTY"       
} ;       

std::string loadType[] = {
        "TOTAL",
	"SYSTEM",
       	"TRAFFIC",
	"OAM"} ;       

void* _RemoteThread(void *)
{ 
        stringstream logString;
 	ToolStatus appStatus;

	pthread_mutex_lock(&sync_mutex);
		appStatus = dataTool.status;
	pthread_mutex_unlock(&sync_mutex);

	if (appStatus == LOADPLOTTER_HAVE_TO_EXIT ){
  		if (dataTool.logMask >= LOGMASK_CONNECTIONS){
       			logString.clear();
			logString.str("");
			logString << "RemoteThread_ : Remote connection shall be closed" <<endl;
			LOG(CONNECTIONS, logString.str());
		}
                        
		pthread_exit(0);
	}
             
       	pthread_mutex_lock(&sync_mutex);
		remoteControlData.status = REMOTE_CONNECTING;
	pthread_mutex_unlock(&sync_mutex);


	int errsv;
	if (dataTool.logMask >= LOGMASK_EVENT) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: Starting up......." <<endl;
		LOG(EVENT, logString.str());
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
	
	if (dataTool.logMask >= LOGMASK_CONNECTIONS) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: listening on port " << remoteControlData.port << endl;
		LOG(CONNECTIONS, logString.str());
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
	unsigned int sent = 0;
        char buff[DEFAULT_BUFFER_SIZE];
        string command = "";
        stringstream commandString;
        string answer = "";
        
        cout << "LoadPlotter up and running" << endl;
        
	while (true){
		pthread_mutex_lock(&sync_mutex);
 			appStatus = dataTool.status;
		pthread_mutex_unlock(&sync_mutex);

		if (appStatus == LOADPLOTTER_HAVE_TO_EXIT){
  			if (dataTool.logMask >= LOGMASK_EVENT){
       				logString.clear();
				logString.str("");
				logString << "RemoteThread_: Terminating... " <<endl;
				LOG(EVENT, logString.str());
			}
                        
			resetRemoteAndExit (0);
		}
                

		tmpset = fds;
		tv.tv_sec = 1;
		tv.tv_usec = 0;

		//passive wait for any activity in the socket
                
		select(remoteControlData.sock+1,&tmpset, NULL, NULL, &tv);

		if(FD_ISSET(remoteControlData.sock, &tmpset)){ 
                        
			received = recvfrom(remoteControlData.sock, buff, DEFAULT_BUFFER_SIZE, 0, (struct sockaddr *) &remote_addr, &len);
                
      			if (received <= 0) {
				if (dataTool.logMask >= LOGMASK_WARNING) {
       					logString.clear();
					logString.str("");
					logString << "RemoteThread_: Received <= 0." << endl;
					LOG(WARNING, logString.str());
				}
				continue;
                        }
			
                        buff[received] = '\0';
                        commandString.clear();
                        commandString.str("");
                         
                        commandString << buff;
			if (dataTool.logMask >= LOGMASK_INFO) {
       				logString.clear();
				logString.str("");
				logString << "RemoteThread_: New command received:" << endl;
				logString <<  "\n\t" <<commandString.str() << endl;
                                LOG(INFO, logString.str());
			}

			commandString >> command ;                        
			transform( command.begin(), command.end(), command.begin(), my_tolower );
                                                
                        if (command == "getstatus" ) {
                                answer = getStatus();                                
                        }
                        else if (command == "getconfig" ) {
                                answer = getConfiguration();                                
                        }
                        else if (command == "getconnection" ) {
                                answer = getConnection();                                
                        }
                         else if (command == "getconnectionindex" ) {
                                answer = getConnectionId(commandString);                                
                        }
                       else if (command == "getload" ) {
                                answer = getLoad(commandString);                                
                        }
                        else if (command == "change" ) {
                                answer = changeDataTool(commandString);                                
                        }
                        else if (command == "addconnection" ) {
                                answer = addConnection(commandString);                                
                        }
                       else if (command == "exit" ) {
                                answer = exitTool();                                
                        }
                        
                        else answer = "UNKNOWN COMMAND" + displayCmdHelp(); 
                      
                        sent = sendto (remoteControlData.sock,answer.c_str(),answer.size(),0, (struct sockaddr *) &remote_addr, len);
                        if (sent == answer.size()) {
				if (dataTool.logMask >= LOGMASK_INFO) {
       					logString.clear();
					logString.str("");
					logString << "RemoteThread_: Anser sent:" << endl;
					logString <<  "\n\t" <<answer << endl;
                                	LOG(INFO, logString.str());
				}
                        }
                        else {
				if (dataTool.logMask >= LOGMASK_WARNING) {
       					logString.clear();
					logString.str("");
					logString << "RemoteThread_: Error trying to send:" << endl;
					logString <<  "\n\t" <<answer << endl;
                                	LOG(WARNING, logString.str());
				}
                        }
		} 
	} 
        
	if (dataTool.logMask >= LOGMASK_EVENT) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: Exiting..." << remoteControlData.port << endl;
		LOG(EVENT, logString.str());
	}

       	return 0;
}

string checkConnectionData(struct Connection * con)
{
        
        stringstream logString;
	string result = "OK";
        string temp = ""; 
        
        if (con->name.empty())
            return result = "ERROR: Name parameter is mandatory"; 
        
 	for (unsigned int index = 0; index < v_connections.size(); index++) {
		if (v_connections[index].status != NOT_USED && v_connections[index].position != con->position) {
                        if (v_connections[index].name == con->name){
	                    if (dataTool.logMask >= LOGMASK_WARNING) {
       		                logString.clear();
		                logString.str("");
		                logString << "RemoteThread_: The existing connection with name " <<  con->name << " will be closed" << endl;
		                LOG(WARNING, logString.str());
	                    }
                            v_connections[index].status = TO_BE_CLOSED;
                            sleep (2);
                            break;
                        }	
                }
	}
            
	if (con->destHostIP.empty())              
            return result = "ERROR: destHostIP parameter is mandatory"; 
                
	if (con->destPort == -1 ) {
            con->destPort = DEFAULT_DEST_PORT_CBA;
        }
        
        if  (con->refreshTime > 0) {
		if (con->scanSize <= 0 )		return result = "ERROR: GraphScanSize must be greater then zero when RefreshTime is set";
        }
               
        return result;
}


std::string addConnection(std::istream& cmd)
{
        stringstream answer;
     	string element, filter;
	bool after;
        
        int con = findConnection();
        if (con == -1) {
		cout << endl << "ERROR:Tehere are not free connections." << endl << endl;
		exit (1);                
	}
                                        
	struct Connection * newConnection = & v_connections[con];
      
        string param ="";
        
        cmd >> param;
        while (!param.empty()) {
                const char * line = param.c_str();
               
		after = false;  
		filter = ":=";
		if (filterLine(line, filter, after, element)) {			
  			if (!strcmp(element.c_str(),"Name")){
				after = true;  
				filter = "Name:=";
				if   (filterLine(line, filter, after, element)) { 
					newConnection->name = element;
					newConnection->dataFileName = element + ".data";
 					newConnection->cmdFileName = "gnuplot_"+element + ".cmd";   
 					newConnection->loopFileName = "loop_forever_"+element + ".gnu";  
				}
			}
 			else if (!strcmp(element.c_str(),"Port")){
				after = true;  
				filter = "Port:=";
				if   (filterLine(line, filter, after, element)) { 
					newConnection->destPort = atoi (element.c_str());
				}
			}
   			else if (!strcmp(element.c_str(),"DestHostIO2")){}
    			else if (!strcmp(element.c_str(),"DestHostIP")){
				after = true;  
				filter = "DestHostIP:=";
				if   (filterLine(line, filter, after, element)) { 
					newConnection->destHostIP = getIpByHostname(element);
				}
			}
                        
			else if (!strcmp(element.c_str(),"RefreshTime")){
				after = true;  
				filter = "RefreshTime:=";
				if   (filterLine(line, filter, after, element)) { 
					newConnection->refreshTime = atoi (element.c_str());
				}
			}
                        
  			else if (!strcmp(element.c_str(),"Platform")){}
                        
  			else if (!strcmp(element.c_str(),"CBA_UserId")){
				after = true;  
				filter = "CBA_UserId:=";
				if   (filterLine(line, filter, after, element)) { 
					newConnection->CBA_userid = element;
				}
			}
                        
  			else if (!strcmp(element.c_str(),"CBA_Password")){
				after = true;  
				filter = "CBA_Password:=";
				if   (filterLine(line, filter, after, element)) { 
					newConnection->CBA_password = element;
				}
			}
                        
			else if (!strcmp(element.c_str(),"GraphScanSize")){
				after = true;  
				filter = "GraphScanSize:=";
				if   (filterLine(line, filter, after, element)) { 
					newConnection->scanSize = atoi (element.c_str());
				}
			}
                        
 			else if (!strcmp(element.c_str(),"MeasureTime")){
				after = true;  
				filter = "MeasureTime:=";
				if   (filterLine(line, filter, after, element)) { 
					newConnection->measureTime = atoi (element.c_str());
				}
			}
                        
			else if (!strcmp(element.c_str(),"ExcludeProcFilter")){
				after = true;  
				filter = "ExcludeProcFilter:=";
				if   (filterLine(line, filter, after, element)) { 
                                     newConnection->excludeProcFilter.push_back(element); 
                                }
			}
			else if (!strcmp(element.c_str(),"ProcFilter")){
				after = true;  
				filter = "ProcFilter:=";
				if   (filterLine(line, filter, after, element)) { 
                                     newConnection->procFilter.push_back(element); 
                                }
			}
 			else if (!strcmp(element.c_str(),"RegulatedloadType")){
				after = true;  
				filter = "RegulatedloadType:=";
				if   (filterLine(line, filter, after, element)) {
                                	if (element == "TRAFFIC" || element == "traffic"){
                                               newConnection->regulatedLoadType = TRAFFIC; 
                                        }
                                        else if (element == "SYSTEM" || element == "system"){
                                               newConnection->regulatedLoadType = SYSTEM; 
                                        }
                                        else if (element == "OAM" || element == "oam"){
                                               newConnection->regulatedLoadType = OAM; 
                                        }
                                        else {
                                               newConnection->regulatedLoadType = TOTAL; 
                                        }
                                }
			}                      
			else if (!strcmp(element.c_str(),"LoadTotalPlot")){
				after = true;  
				filter = "LoadTotalPlot:=";
				if   (filterLine(line, filter, after, element)) { 
                                        if (element == "true" || element == "TRUE"){
                                        	newConnection->LoadTotalPlot = true; 
                                        }                                       
					else {
                                        	newConnection->LoadTotalPlot = false; 
                                	}
                                }
			}
			else {
				answer << "FAIL Param "<< element <<" doesn't exist " << endl;
        			return  answer.str() ;  
			}
               
		}
                        
                                        
               
               param.erase();
               cmd >> param;
        }
        
	string result = checkConnectionData(newConnection);
	if (result != "OK") {
                initConnection(newConnection);
		answer << result ;
		return  answer.str();                
	}
        	
        newConnection->status=OFFLINE;
                                     
	answer << "OK";
        
        return  answer.str() ;  
}

string getConnection()
{
        string answer = "";
	vector<Connection> my_v_connections;
        
	pthread_mutex_lock(&sync_mutex);
		my_v_connections = v_connections;
	pthread_mutex_unlock(&sync_mutex);
                
        bool conFound = false;
	for (unsigned int index = 0;index < my_v_connections.size(); index++) { 
                if (my_v_connections[index].status > NOT_USED ) {
			answer += getConnectionInfo(my_v_connections[index]);
			conFound = true;
                }               
        }
	if (! conFound) 	answer = "There is not active connection.\n";
        return answer;
}
string getConnectionId(std::istream& cmd)
{
        std::stringstream answer;
        string name;
        cmd >> name; 
	vector<Connection> my_v_connections;
        
	pthread_mutex_lock(&sync_mutex);
		my_v_connections = v_connections;
	pthread_mutex_unlock(&sync_mutex);
        
	for (unsigned int index = 0;index < my_v_connections.size(); index++) {
                if (my_v_connections[index].name == name){
                        if (my_v_connections[index].status == ONLINE){
                		answer <<  index; 
                        }
                        else if (my_v_connections[index].status == FAULTY){
                		answer <<  "LOADPLOTTER ERROR"; 
                        }
                        else {
                              answer << "LOADPLOTTER ONGOING";  
                        }
                        return answer.str();      
		
                }                
        }
	
        answer <<  "There is not active connection with Host name: " <<name  ;
        return answer.str();
}

std::string getConnectionInfo(Connection &con)
{
        std::stringstream info;
                
        info << "\n\n";        
        info << "\t"<<con.name<<"\n";         
        info << "\t-----------------------\t\t\n" ;         
        info << "\tConnection:\t"    <<  con.position << "\n";         
        info << "\tState:\t\t"  <<  conStatus[con.status] << "\n";
        info << "\tIp Address:\t"  <<  con.destHostIP << "\n";
        info << "\tPort:\t\t"  <<  con.destPort << "\n";
        info << "\tSocket:\t\t"  <<  con.sock << "\n";
        
        info << "\tUserId:\t\t"  <<  con.CBA_userid << "\n";
        info << "\tPassword:\t"  <<  con.CBA_password << "\n";
               

        
        info << "\tLoadType:\t"  <<  loadType[con.regulatedLoadType] << "\n";
                 
	for (unsigned int index = 0;index <con.procFilter.size(); index++) {                
        	info << "\tProcFilter:\t"  <<  con.procFilter[index] << "\n";
        }
        
        info << "\tScan Size:\t"  <<  con.scanSize << "\n";
        info << "\tMeasure Time:\t"  <<  con.measureTime << "\n";
        info << "\tRefreshTime:\t" <<  con.refreshTime << "\n";  
        
        info << "\n";        
        
 	return info.str();
}

string getLoad(istream& ss)
{
        std::stringstream answer;
        unsigned index;
        std::string loadType;
        ss >> index; 
        if ( !(index >= 0 &&  index < v_connections.size()))
                answer << "Fail wrong connection index\n";
        else {
            ss >> loadType; 
            if (loadType.empty())     answer << v_connections[index].regulatedloadValue;

            else {
        
                if (loadType == "TRAFFIC" || loadType == "traffic"){
                    answer << v_connections[index].trafficloadValue; 
                }
                else if (loadType == "SYSTEM" || loadType == "system"){
                    answer << v_connections[index].systemloadValue;
                }
                else if (loadType == "OAM" || loadType == "oam"){
                    answer << v_connections[index].oamloadValue;
                }
                else if (loadType == "TOTAL" || loadType == "total"){
                    answer << v_connections[index].totalloadValue;
                }
                 else if (loadType == "ALL" || loadType == "all"){
                    answer << "traf=" << v_connections[index].trafficloadValue; 
                    answer << " sys=" << v_connections[index].systemloadValue;
                    answer << " oam=" << v_connections[index].oamloadValue;
                    answer << " total=" << v_connections[index].totalloadValue;
                }
               else {
                    answer << "Fail wrong load type. Allowed values \"TRAFFIC\",\"SYSTEM\", \"OAM\",\"TOTAL\" or\"\"\n"; 
                }
        
            }
        
        }        
 	return answer.str();
}

string getConfiguration()
{
        return  displayAppInfo(); 
}

string getStatus()
{
        return  appStatus[dataTool.status]; 
}


string exitTool()
{
        stringstream logString;
	if (dataTool.logMask >= LOGMASK_EVENT) {
       		logString.clear();
		logString.str("");
		logString << "RemoteThread_: loadPlotter will be finshed by command..." << endl;
		LOG(EVENT, logString.str());
	}
        
	dataTool.status = LOADPLOTTER_HAVE_TO_EXIT; 
        pthread_kill(SignalThreadID ,SIGUSR1);	
        return  "OK" ;  
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
					dataTool.logMask = atoi (element.c_str());
					Log::Instance().set_log_mask(dataTool.logMask);
				}
			}
   			else if (!strcmp(element.c_str(),"LogMode")){
				after = true;  
				filter = "LogMode:=";
				if   (filterLine(line, filter, after, element)) { 
					dataTool.logMode = atoi (element.c_str());
 					Log::Instance().set_log_mode(dataTool.logMode);
				}
			}
                        
  			else if (!strcmp(element.c_str(),"KeepGraphicAfterExecution")){
				after = true;  
				filter = "KeepGraphicAfterExecution:=";
				if   (filterLine(line, filter, after, element)) { 
                                        if (element == "true" || element == "TRUE"){
                                        	dataTool.KeepGraphicAfterExecution = true; 
                                        }                                       
					else {
                                        	dataTool.KeepGraphicAfterExecution = false; 
                                	}
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
        
        help_file = help_file + "/share/loadplotter/load_plotter_help.txt";
              
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


std::string displayAppInfo()
{
        std::stringstream info;
                
        info << "\n\n";        
        info << "\tloadPlotter status:\t" <<  appStatus[dataTool.status] << "\n\n";    
        info << "\tHostname:\t\t" <<  dataTool.hostname << "\n";        
        
        info << "\tLog file:\t\t" <<  Log::Instance().get_log_file() << "\n";        
        info << "\tLog mask:\t\t" <<  dataTool.logMask << "\n";        
        info << "\tLog mode:\t\t" <<  dataTool.logMode << "\n\n";        
 
        if (  dataTool.KeepGraphicAfterExecution )
                info << "\tKeepGraphic:\t\tYES\n";  
        else      
                 info << "\tKeepGraphic:\t\tNO\n";  
       
        info << "\n";        
        
 	return info.str();
}

void resetRemoteAndExit (int fail)
{
	
	if (dataTool.logMask >= LOGMASK_INFO){
        	stringstream logString;
		logString.clear();
		logString.str("");
		logString << "resetRemoteAndExit......"<<endl;
		LOG(INFO, logString.str());
        }
        
	pthread_mutex_lock(&sync_mutex);
		remoteControlData.status = REMOTE_OFF;
	pthread_mutex_unlock(&sync_mutex);

//	if (remoteControlData.sock != -1)	close (remoteControlData.sock);	

	if (fail)
                 {
		pthread_kill(SignalThreadID ,SIGUSR1);
	}
	RemoteThreadID=NULL;
	pthread_exit(0);

}

