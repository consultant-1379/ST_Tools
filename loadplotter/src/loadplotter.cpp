#include "loadplotter.h"

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

// input files
string configFile = "";

using namespace std;
vector<Connection> v_connections;

applicationData dataTool;

vector <string> sub_2_RacksExcludeProc;                
vector <string> sub_3_RacksExcludeProc;   
             
struct RemoteControl remoteControlData;


//main program
int main(int argc, char* argv[])
{
        
	dataTool.status = LOADPLOTTER_STARTING;
        dataTool.logMask = LOGMASK_EVENT;
        dataTool.logMode = FILE_MODE;
        dataTool.KeepGraphicAfterExecution = false;
	remoteControlData.sock = -1;
	remoteControlData.port = REMOTE_PORT;
	remoteControlData.status = REMOTE_OFF;
        
             
       	if (!parseCommandLine(argc, argv)){
		displayHelp();
                return 1;
	} 
               
	char line [1024];
	int ret = 0, errsv = 0;
                   
        gethostname(line,100);
        dataTool.hostname = line;
        
	dataTool.logFile= "loadPlotter.2.0";
        
	string prg(LOG_PRG);
    	Log::Instance().ini(dataTool.logFile, prg); 
	Log::Instance().set_log_mask(dataTool.logMask);
 	Log::Instance().set_log_mode(dataTool.logMode);
        
	stringstream logString;	sigset_t signal_set;
        
 	system ("clear");

	logString.clear();
	logString.str("");
	logString << "loadPlotter running on: " <<dataTool.hostname <<endl;
	LOG(INFO, logString.str());
                
        sub_2_RacksExcludeProc.push_back("Proc_m0_s19");
        sub_2_RacksExcludeProc.push_back("Proc_m0_s23");
        
        sub_3_RacksExcludeProc.push_back("Proc_m0_s19");
        sub_3_RacksExcludeProc.push_back("Proc_m0_s23");
        sub_3_RacksExcludeProc.push_back("Proc_m1_s3");
                               
	struct Connection newConnection;
	v_connections.reserve(MAX_NUMBER_OF_CONNECTIONS);
	v_connections.assign(MAX_NUMBER_OF_CONNECTIONS,newConnection); 
	
	for (unsigned int i = 0; i < v_connections.size(); i++) {
                initConnection(& v_connections[i]);
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
		return 1;
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
        
        dataTool.status =  LOADPLOTTER_TO_BE_CONFIGURED;
        
 	if (! configFile.empty()) readConfigFile(configFile);
        
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


void displayHelp()
{
	cout << endl << "Command line error."<< endl << endl;
				
	cout << "Usage:\t\tloadPlotter [-c <file> | -p <port>]"<< endl<< endl<< endl;
	cout << "\t\t-c <file>\t\tConfiguration file "<< endl ;
	cout << "\t\t-p <port>\t\tRemote cotrol port "<< endl ;
	cout << " "<< endl<< endl;								
}

bool parseCommandLine (int argc, char **argv)
{
	for(int i=1;i<argc;i++){ 
															 
		if(strcmp(argv[i],"-c") == 0){
			i++;
			if(argc == i){ 
				return false;
			}
			configFile = argv [i];      
		}
		else if(strcmp(argv[i],"-p") == 0){
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


void readConfigFile(string nameFile)
{
	char line [1024]; 
	string element, filter;
	bool after;
	ifstream inFile;       
	inFile.open (nameFile.c_str());
				
	if (!inFile) {
		cout << endl << "ERROR:Failed to open file: " << nameFile << endl << endl;
		exit (1);                
	}
        
        
        int con = findConnection();
        if (con == -1) {
		cout << endl << "ERROR:Tehere are not free connections." << endl << endl;
		exit (1);                
	}
                                        
	struct Connection * newConnection = & v_connections[con];
	string result;
        
	while(inFile) {
		inFile.getline(line, 1024);
		purgeLine(line);

		after = false;  
		filter = ":=";
		if (filterLine(line, filter, after, element)) {			
			if (!strcmp(element.c_str(),"Name")){
 				if (!newConnection->name.empty()) {
                                        
                                        result = checkConnectionData(newConnection);
                                        if (result != "OK") {
						cout << endl << result << endl << endl;
						exit (1);                
                                        }	
                                        
                                        newConnection->status=OFFLINE;
                                        con = findConnection();
        				if (con == -1) {
						cout << endl << "ERROR:Tehere are not free connections." << endl << endl;
						exit (1);                
					}
                                        
					newConnection = & v_connections[con];
                                        
                                }
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
					newConnection->destHostIP = element;
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
			else if (!strcmp(element.c_str(),"RefreshTime")){
				after = true;  
				filter = "RefreshTime:=";
				if   (filterLine(line, filter, after, element)) { 
					newConnection->refreshTime = atoi (element.c_str());
				}
			}
			else if (!strcmp(element.c_str(),"LogMask")){
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
		}
				
        }

	if (!newConnection->name.empty()) {
                                        
		result = checkConnectionData(newConnection);
		if (result != "OK") {
			cout << endl << result << endl << endl;
			exit (1);                
		}	
                                        
		newConnection->status=OFFLINE;
	}

	inFile.close();	
        						 
}


bool filterLine (const char * line, string filter, bool after, string & element)
{
	string  myLine(line);  
	int len;
	string::size_type idx;

	idx = myLine.find(filter);
	if (idx == string::npos) {
		return false;

	}
	
	if (after) {
		myLine.erase(0,idx + filter.size());      
	}
	else {
		len = myLine.size();
		myLine.erase(idx, len );  
	}
	element = myLine;
	return  true;
}

void purgeLine(char * line)
{
	char myline[1024];
	strcpy (myline, line);
	int index = 0;
	for (int i = 0; myline[i] != '\0'; i++) {
		if ( myline[i] == '#'){
			line[index] = '\0';
			break;
		} 
		else if ( myline[i] == '\r'){
                        line[index] = '\0';
			break;
		} 
		else if (( myline[i] == '/') && (myline[i+1] == '/')){
			line[index] = '\0';
			break;
		} 
		else if (( myline[i] == ' ') || ( myline[i] == '\t')) {}
		else {
			line[index] = myline[i];
			index++;
		}
	}
	line[index] = '\0';
}



bool isIpFormat(string host)
{
 	string  filter = ".";;  
	string::size_type idx;

	idx = host.find(filter);
	if (idx != string::npos) {
		return true;
	}
        return false;
        
}
bool lookup_host (const char *host, struct in_addr *output_addr)
{
    if (! inet_pton(AF_INET, host, output_addr)){
        struct addrinfo hints, *res;
        void *ptr;

        memset (&hints, 0, sizeof (hints));
        hints.ai_family = AF_INET;

        if (getaddrinfo (host, NULL, &hints, &res) != 0){
            return false;
        }

        char addrstr[100];
        if (res->ai_family != AF_INET) {
            return false;
        }

        ptr = &((struct sockaddr_in *) res->ai_addr)->sin_addr;
        memcpy(output_addr, ptr, sizeof(ptr));

        freeaddrinfo(res);
    }

    return true;
}

string getIpByHostname (string host)
{

    struct in_addr output_addr;
    if (!lookup_host (host.c_str(), &output_addr)){
//         cout << "Error lookup_host " <<endl;
        string ip ="0.0.0.0";
        return ip;
    }
    char buffer[100];
    int errsv;
    if (inet_ntop(AF_INET, &output_addr, buffer, sizeof(buffer)) == NULL){
        errsv=errno;
//         cout << "Error inet_ntop: " << strerror(errsv) <<endl;
        string ip ="0.0.0.0";
        return ip;
    }
    string ip (buffer);
    return   ip; 
}


void initConnection(struct Connection * newConnection)
{        
	newConnection->messageLen = 0;       
  	newConnection->destHostIP.erase();
  	newConnection->dataFileName.erase();
  	newConnection->cmdFileName.erase();
  	newConnection->name.erase() ;
  	newConnection->procFilter.clear() ;
	newConnection->destPort = -1;
   	newConnection->scanSize = DEFAULT_SCAN_SIZE;
  	newConnection->measureTime = DEFAULT_MEASURE_TIME;
	newConnection->sock = -1;
	newConnection->status = NOT_USED;
	newConnection->threadID = NULL;
        
  	newConnection->LoadTotalPlot = true;

  	newConnection->regulatedLoadType = TOTAL;
  	newConnection->regulatedloadValue = 0.0;        
 	newConnection->trafficloadValue = 0.0;
  	newConnection->oamloadValue = 0.0;
  	newConnection->systemloadValue = 0.0;        
  	newConnection->totalloadValue = 0.0;
                       
      	newConnection->refreshTime = DEFAULT_REFRESH_TIME;
             
  	newConnection->acc_systemLoad = 0;
  	newConnection->acc_trafficLoad = 0;
  	newConnection->acc_oamLoad = 0;
        
  	newConnection->CBA_userid = DEFAULT_CBA_USRID;
  	newConnection->CBA_password = DEFAULT_CBA_PASSW;
 	newConnection->cba_firstLoadFilter = NULL;
  	newConnection->cba_acc_Load = 0;
  	newConnection->cba_total_Load = 0;
  	newConnection->cba_load_cnt = 0;
  	newConnection->cba_round_cnt = 0;
        
}
int findConnection()
{
        int result = -1;
 	for (unsigned int index = 0; index < v_connections.size(); index++) {
		if (v_connections[index].status == NOT_USED) 	return index;
	}
        return result;
       
}
