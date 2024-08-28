#include "CpsMonitor.h"

using namespace std;
struct MonitorData monitorData;
pthread_t SignalThreadID;
pthread_t MonitorThreadID;

//variable for defining/handling a mutual exclusion zone
pthread_mutex_t sync_mutex = PTHREAD_MUTEX_INITIALIZER;

string configFile;
StepDeque q_stepLoad;
StepDeque q_stepPre;
StepDeque q_stepPost;


int main(int argc, char* argv[])
{

    monitorData.sock = -1;
    monitorData.server="";
    monitorData.port = DEFAULT_PORT;
    monitorData.dataFileName="";
    monitorData.cmdFileName="";
    monitorData.loopFileName="";
    monitorData.refreshTime = DEFAULT_REFRESH;
    monitorData.scan = DEFAULT_SCAN;
    monitorData.measureTime = DEFAULT_MEASURETIME;
    monitorData.acc_currentCPS = 0;
    monitorData.acc_targetCPS = 0;
    monitorData.noAnswerCounter = 0;
     
    monitorData.hostname = "";
    monitorData.logFile = "CPS_Monitor";
    monitorData.logMask = LOGMASK_INFO;
    monitorData.logMode=FILE_MODE;
    
    monitorData.status = MONITOR_OFF;
    monitorData.display_active = false;
    monitorData.schedulingEnabled  = false; 
     
    stringstream logString;
    int errsv;
    
    // read only cfg parameter
    parseCommandLine(argc, argv, true);
    if (!configFile.empty()) readConfigFile(configFile);        
    
    // read rest of parameter
    if (!parseCommandLine(argc, argv, false)){
        displayHelp();
        return 1;
    }
     
       
    string prg(LOG_PRG);
    Log::Instance().ini(monitorData.logFile, prg); 
    Log::Instance().set_log_mask(monitorData.logMask);
    Log::Instance().set_log_mode(monitorData.logMode);


    /* block all signals */
    sigset_t signal_set;
    sigfillset( &signal_set );
    pthread_sigmask( SIG_BLOCK, &signal_set,NULL);
        
    /*** Threads Spawning ***/			
    int ret = pthread_create(&SignalThreadID, NULL,handler, NULL );

    if (ret) {
        errsv = ret;
        logString.clear();
        logString << "MonitorData: SignalThread creation returned" << ret << endl;
        logString <<"\tError: " << strerror(errsv) << endl;
        LOG(ERROR, logString.str());
        return 1;
    }
    ret = pthread_create(&MonitorThreadID,NULL,_MonitorThread,NULL);
    if (ret) {
        errsv = ret;
        logString.clear();
        logString << "_MonitorThread creation returned" << ret << endl;
        logString <<"\tError: " << strerror(errsv) << endl;
        LOG(ERROR, logString.str());

        return 0;
    }
        
    sleep(2); //go to sleep
        
    if (monitorData.logMask >= LOGMASK_INFO){
        logString.clear();
        logString.str("");
        logString << "Waiting while the SignalThread is still alive, go on..." << endl;
        LOG(INFO, logString.str());
    }

    //while the thread is still alive, go on..... 
    void *theThreadStatus;
    pthread_join(SignalThreadID,&theThreadStatus);

    return 0;

}

void* _MonitorThread(void *arg)
{
    stringstream logString;
        
    struct sockaddr_in local_addr;
    string command = "";
    stringstream commandString;
    std::ofstream outFile;
    int accTimes = 0;
    char cmd[1024];
    int errsv;
    

    pthread_mutex_lock(&sync_mutex);
        monitorData.status = MONITOR_STARTING;
    pthread_mutex_unlock(&sync_mutex);

    monitorData.sock = socket(AF_INET,SOCK_DGRAM,0);
        
    if (monitorData.sock == -1){
        if (monitorData.logMask >= LOGMASK_WARNING) {
            errsv = errno;
 	    logString.clear();
	    logString.str("");
	    logString << "MonitorData: Create socket returned" << endl;
	    logString <<"\tError: " << strerror(errsv) << endl;
	    LOG(WARNING, logString.str());
        }

        exitMonitor ();
    }
        
    if (monitorData.logMask >= LOGMASK_DEBUG) {
        logString.clear();
        logString.str("");
        logString << "MonitorData: SocketId: "<< monitorData.sock <<endl;
        LOG(DEBUG, logString.str());
    }

    memset(&local_addr,0,sizeof(sockaddr_in));
    local_addr.sin_family = AF_INET;

    if(bind(monitorData.sock,(struct sockaddr*)&local_addr,sizeof(local_addr)) == -1){
        if (monitorData.logMask >= LOGMASK_WARNING) {
            errsv = errno;
            logString.clear();
            logString.str("");
            logString << "MonitorData: Failed to bind to local socket " << monitorData.sock << endl;
            logString <<"\tError: " << strerror(errsv) << endl;
            LOG(WARNING, logString.str());
        }

        exitMonitor ();
    }
            
    memset(&monitorData.remote_addr,0,sizeof(sockaddr_in));
    monitorData.remote_addr.sin_family = AF_INET;                
    monitorData.remote_addr.sin_port = htons(monitorData.port);                
    monitorData.remote_addr.sin_addr.s_addr = inet_addr(monitorData.serverIP.c_str());
                                                                                                
    outFile.open(monitorData.dataFileName.c_str());
                                        
    if (!outFile) {
        logString.clear();
        logString.str("");
        logString << "MonitorData: Failed to open file:" <<monitorData.dataFileName << endl;
        LOG(ERROR, logString.str());
                                        
        exitMonitor ();
    }
                                
    outFile <<"0\t0\t0" << endl;
    outFile.flush();
    outFile.close();
    sleep (2);
    
    outFile.open(monitorData.cmdFileName.c_str());
    if (!outFile) {
        logString.clear();
        logString.str("");
        logString << "MonitorData: Failed to open file:" <<monitorData.cmdFileName << endl;
        LOG(ERROR, logString.str());
                                        
        exitMonitor ();
    }

    outFile <<"set term x11 font \"arial,15,italic\"" << endl;
    outFile <<"set title \"CPS "<<monitorData.server <<"\"" << endl;
    outFile <<"set key outside "<< endl;
    outFile <<"set ylabel \"CPS\""<< endl;
    outFile <<"set xlabel \"Time (s)\""<< endl;
    outFile <<"set grid layerdefault"<< endl;
       
    outFile <<"set border 3"<< endl;
    outFile << "plot \""<<monitorData.dataFileName<<"\" using 1:2 title \"Target\" with lines 1, \""<<monitorData.dataFileName<<"\" using 1:3 title \"Current\" with lines 3";
    outFile << "\0" << endl;
    outFile <<"load \""<<monitorData.loopFileName<<"\"\0" << endl;
    outFile.flush();
    outFile.close();
                                
    sprintf(cmd,"chmod 755 %s",monitorData.cmdFileName.c_str());
    if(system(cmd)!=0){
        logString.clear();
        logString.str("");
        logString << "MonitorData: Failed during command execution: " <<cmd << endl;
        LOG(ERROR, logString.str());
                                        
        exitMonitor ();
    }
                              
    if ( monitorData.refreshTime > 0) {
        outFile.open(monitorData.loopFileName.c_str());
        if (!outFile) {
            logString.clear();
            logString.str("");
            logString << "Failed to create file: " <<monitorData.loopFileName << endl;
            LOG(INFO, logString.str());
        }

        outFile << "pause " << monitorData.refreshTime << ";replot;reread;";
        outFile.close();
                                        
        sprintf(cmd,"chmod 755 %s",monitorData.loopFileName.c_str());
        if(system(cmd)!=0){
            logString.clear();
            logString.str("");
            logString << "MonitorData: Failed during command execution: " <<cmd << endl;
            LOG(ERROR, logString.str());
                                        
            exitMonitor ();
        }

    }
                                                               
    outFile.open(monitorData.dataFileName.c_str(),ios::app );
    if (!outFile) {
        logString.clear();
        logString.str("");
        logString << "MonitorData: Failed to open file:" <<monitorData.dataFileName << endl;
        LOG(ERROR, logString.str());
                                        
        exitMonitor ();
    }
    string target, current ;
    
    struct timespec event_time;
    struct timespec start_time;
    double step_time_stop = 0;
    clock_gettime( CLOCK_MONOTONIC, &start_time );
    bool trafficIsrunning = false;   
    while (true) {
    
        if ( monitorData.status == MONITOR_HAVE_TO_EXIT) exitMonitor ();
        
        sleep (monitorData.measureTime);
        command = "get targetCps";
        target = sendCommand(command);
        if (target.empty()) {
            monitorData.noAnswerCounter++;
            if (monitorData.noAnswerCounter >= MAX_NO_ANSWER && monitorData.status == MONITOR_ON ) {
                logString.clear();
                logString.str("");
                logString << "MonitorData: Too many messages no answered."<< endl;
                LOG(ERROR, logString.str());
                                        
                exitMonitor ();
            }
            continue;
        }
        monitorData.noAnswerCounter = 0;
        monitorData.acc_targetCPS += atoi(target.c_str());
        
        command = "get currentCps";
        current = sendCommand(command);
        if (current.empty()) {
            monitorData.noAnswerCounter++;
            if (monitorData.noAnswerCounter >= MAX_NO_ANSWER && monitorData.status == MONITOR_ON ) {
                logString.clear();
                logString.str("");
                logString << "MonitorData: Too many messages no answered."<< endl;
                LOG(ERROR, logString.str());
                                        
                exitMonitor ();
            }
            continue;
        }
        
        pthread_mutex_lock(&sync_mutex);
            if ( monitorData.status != MONITOR_HAVE_TO_EXIT) monitorData.status = MONITOR_ON;
        pthread_mutex_unlock(&sync_mutex);

        monitorData.noAnswerCounter = 0;
        
        if (monitorData.display_active == false && monitorData.refreshTime > 0) {
        
            sprintf(cmd,"gnuplot -noraise %s >& /dev/null &",monitorData.cmdFileName.c_str());
            if(system(cmd)!=0){
                logString.clear();
                logString.str("");
                logString << "MonitorData: Failed during command execution: " <<cmd << endl;
                LOG(ERROR, logString.str());
                                        
                exitMonitor ();
            }
            monitorData.display_active = true;
        }
        
        monitorData.acc_currentCPS += atoi(current.c_str());
        
        accTimes++;

        if (accTimes == monitorData.scan && monitorData.scan){
            clock_gettime( CLOCK_MONOTONIC, &event_time );
            double seconds = event_time.tv_sec - start_time.tv_sec;
            outFile <<seconds;
            outFile <<"\t"<< monitorData.acc_targetCPS / accTimes;
            outFile <<"\t"<< monitorData.acc_currentCPS / accTimes;
            outFile << std::endl;
            outFile.flush();
            accTimes = 0;
            monitorData.acc_currentCPS = 0;
            monitorData.acc_targetCPS = 0;
        }
        
        if (monitorData.schedulingEnabled){
      
            stringstream command;
            string answer;
            command << "get ScGrpStatus";
            answer = sendCommand(command.str());
            string::size_type idx;

            idx = answer.find("RUNNING");
            if (idx == string::npos) {
                trafficIsrunning = false;
                step_time_stop = 0;
                continue;
            }
            trafficIsrunning = true;
            
            StepDeque * q_stepPtr; 
            idx = answer.find("preexec");
            if (idx != string::npos) {
                q_stepPtr = &q_stepPre;
            }
            else {
                idx = answer.find("loadgen");
                if (idx != string::npos) {
                    q_stepPtr = &q_stepLoad;
                }
                else {
                    idx = answer.find("postexec");
                    if (idx != string::npos) {
                        q_stepPtr = &q_stepPost;
                    }
                    else {
                        continue;
                    }   
                }
            }
                
            if (event_time.tv_sec > step_time_stop && !q_stepPtr->empty()) {
                struct Step tempStep = q_stepPtr->front();
                
                if (tempStep.time == 0) { 
                        continue;
                }   
                q_stepPtr->pop_front();

                stringstream command;
                string answer;
                command << "set targetCps " << tempStep.cps;
                answer = sendCommand(command.str());
                if (answer.empty()) {
                    monitorData.noAnswerCounter++;
                    if (monitorData.noAnswerCounter >= MAX_NO_ANSWER && monitorData.status == MONITOR_ON ) {
                        logString.clear();
                        logString.str("");
                        logString << "MonitorData: Too many messages no answered."<< endl;
                        LOG(ERROR, logString.str());
                                        
                        exitMonitor ();
                    }
                    continue;
                }
                
                step_time_stop = event_time.tv_sec + tempStep.time ;
            }
        }
        
    }
        
}
void exitMonitor ()
{
    if (monitorData.sock !=-1)  close(monitorData.sock);
    if (!monitorData.display_active) {
        MonitorThreadID= NULL;
        pthread_exit(0);
    }
    stringstream logString;
    char cmd[1024];
    char file[1024];

    if (monitorData.refreshTime > 0) {
        sprintf(cmd,"ps -eaf | grep \"gnuplot -noraise %s\" | grep -v \"grep\" | awk '{print $2}' | xargs kill -9",monitorData.cmdFileName.c_str());                
       
        if(system(cmd)!=0){
            if (monitorData.logMask >= LOGMASK_INFO) {
                logString.clear();
                logString.str("");
                logString << "MonitorData: Failed during command execution: "<<cmd<<endl;
                LOG(INFO, logString.str());
            }
        }
    }

    if (monitorData.scan) {
        ofstream outFile;
        outFile.open(monitorData.cmdFileName.c_str());
        if (!outFile) {
            logString.clear();
            logString.str("");
            logString << "MonitorData: Failed to open file:" <<monitorData.cmdFileName << endl;
            LOG(ERROR, logString.str());
        }
        
        outFile <<"set term x11 font \"arial,15,italic\"" << endl;
        outFile <<"set title \"CPS "<<monitorData.server <<"\"" << endl;
        outFile <<"set key outside "<< endl;
        outFile <<"set ylabel \"CPS\""<< endl;
        outFile <<"set xlabel \"Time (s)\""<< endl;
        outFile <<"set grid layerdefault"<< endl;
       
        outFile <<"set border 3"<< endl;
        outFile << "plot \""<<monitorData.dataFileName<<"\" using 1:2 title \"Target\" with lines 1, \""<<monitorData.dataFileName<<"\" using 1:3 title \"Current\" with lines 3";
        outFile << "\0" << endl;
        outFile.flush();
        outFile.close();
 
        sprintf(file,"generate_gif_%s",monitorData.server.c_str());
        outFile.open(file);
        if (!outFile) {
            logString.clear();
            logString.str("");
            logString << "MonitorData: Failed to open file: generate_gif_xxxxxx.cmd" << endl;
            LOG(ERROR, logString.str());
        }
        
        
        outFile <<"set term gif" << endl;
        outFile <<"set title \"CPS "<<monitorData.server <<"\"" << endl;
	outFile <<"set output \"load_"<<monitorData.server <<".gif\"" << endl;
        outFile <<"set key outside "<< endl;
        outFile <<"set ylabel \"CPS\""<< endl;
        outFile <<"set xlabel \"Time (s)\""<< endl;
        outFile <<"set grid layerdefault"<< endl;
       
        outFile <<"set border 3"<< endl;
        outFile << "plot \""<<monitorData.dataFileName<<"\" using 1:2 title \"Target\" with lines 1, \""<<monitorData.dataFileName<<"\" using 1:3 title \"Current\" with lines 3";
        outFile << "\0" << endl;
        outFile.flush();
        outFile.close();
        
        sprintf(cmd,"gnuplot %s >& /dev/null",file);

        if(system(cmd)!=0){
            logString.clear();
            logString.str("");
            logString << "MonitorData: Failed during command execution: " <<cmd << endl;
            LOG(ERROR, logString.str());
        }
                         
        sprintf(cmd,"rm %s",file);

        if(system(cmd)!=0){
            logString.clear();
            logString.str("");
            logString << "MonitorData: Failed during command execution: " <<cmd << endl;
            LOG(ERROR, logString.str());
        }
     }
     
    pthread_mutex_lock(&sync_mutex);
        if (monitorData.status != MONITOR_HAVE_TO_EXIT)	pthread_kill(SignalThreadID ,SIGUSR1);
    pthread_mutex_unlock(&sync_mutex);

    MonitorThreadID= NULL;
    pthread_exit(0);
}
bool parseCommandLine (int argc, char **argv, bool onlyCfg)
{
    for(int i=1;i<argc;i++){ 
															 
        if(strcmp(argv[i],"-server") == 0){
            i++;
            if(argc == i){ 
                return false;
            }
            if (!onlyCfg) {
                monitorData.server = argv [i]; 
                monitorData.dataFileName = monitorData.server + "_CPS.data";
                monitorData.cmdFileName = "gnuplot_CPS_"+monitorData.server + ".cmd";   
                monitorData.loopFileName = "loop_forever_CPS_"+monitorData.server + ".gnu";  
                monitorData.serverIP = getIpByHostname(monitorData.server);     
           }                      
        }
        else if(strcmp(argv[i],"-port") == 0){
            i++;
            if(argc == i){ 
                return false;
            }
            if (!onlyCfg) {
                monitorData.port = atoi(argv [i]);
            }
        }                
        else if(strcmp(argv[i],"-logMask") == 0){
            i++;
            if(argc == i){ 
                return false;
            }
            if (!onlyCfg) {
                monitorData.logMask = atoi(argv [i]);
            }
        }                
        else if(strcmp(argv[i],"-logMode") == 0){
            i++;
            if(argc == i){ 
                return false;
            }
            if (!onlyCfg) {
                monitorData.logMode = atoi(argv [i]);
            }
            
        }                
        else if((strcmp(argv[i],"-scan") == 0)){
            
            i++;
            if(argc == i){ 
                return false;
            }

            if (!onlyCfg) {
                monitorData.scan = atoi(argv [i]);
            }
        }                
        else if(strcmp(argv[i],"-refreshTime") == 0){
            i++;
            if(argc == i){ 
                return false;
            }
            if (!onlyCfg) {
                monitorData.refreshTime = atoi(argv [i]);
            }
            
        }                
        else if(strcmp(argv[i],"-measureTime") == 0){
            i++;
            if(argc == i){ 
                return false;
            }
            if (!onlyCfg) {
                monitorData.measureTime = atoi(argv [i]);
            }
            
        }                
        else if(strcmp(argv[i],"-cfg") == 0){
            i++;
            if(argc == i){ 
                return false;
            }
            if (onlyCfg) {
                configFile = argv [i];
            }
                  
        }                
        else if(strcmp(argv[i],"-h") == 0){
            displayHelp();
            exitMonitor ();
            
        }                
        else {
            cout << endl << "\tSyntax ERROR: Unknown parameter "<< argv[i]<< endl ;
            return false; 
        }         		
    }

    return true;     
}

void displayHelp()
{
        cout << endl << "CpsMonitor command line options"<< endl << endl;
				        
        cout << "-cfg <file>                   Specify the configuration file." << endl;
        cout << "-server <hostname>            Specify the hostname where the ttcn_monitor is running" << endl;
        cout << "-port <int>                   Specify the UDP port where the ttcn_monitor is waiting for clients." << endl;
        cout << "-measureTime <time(sec)>      Base time for reading CPS. Default 2 sec" << endl;
        cout << "-scan <int>                   Number of scans for average calculation. Default 10" << endl;
        cout << "-refreshTime <time(sec)>      Base time for plotting data. Default 10 sec" << endl;
        cout << "                              If 0 plotting is disabled" << endl;
        cout << "-logMask  <int>               Set log mask." << endl;
        cout << "                              Value summing what to log" << endl;
        cout << "                                      Errors        1" << endl;
        cout << "                                      Warnings      2" << endl;
        cout << "                                      Connections   4" << endl;
        cout << "                                      Events        8" << endl;
        cout << "                                      Info          16" << endl;
        cout << "                                      Debug         32" << endl;
        cout << "                                      Log all       63" << endl;
        cout << "" << endl;
        cout << "-logMode  <int>               Set log mode." << endl;
        cout << "                              value:  0       FILE_MODE" << endl;
        cout << "                                      1       STDOUT_MODE" << endl;
        cout << "                                      2       MIXED_MODE  " << endl;                                                      
	cout << " "<< endl<< endl;								
}

string getIpByHostname (string host)
{
    string  filter = ".";;  
    string::size_type idx;

    idx = host.find(filter);
    if (idx != string::npos) {
        return host;
    }

    struct hostent *he;
    he = gethostbyname(host.c_str()); 
    if (he == 0) {
        string ip ="0.0.0.0";
        return ip;
    }   

    if (he->h_addr_list[0] == NULL) {
        string ip ="0.0.0.0";
        return ip;
    }   

    string ip (inet_ntoa( (struct in_addr) *((struct in_addr *) he->h_addr_list[0])));

    return   ip; 
}

string sendCommand(string command)
{
    stringstream logString;
    stringstream answerString;
    string answer = "";
    struct timeval tv;
    tv.tv_sec = 5;
    tv.tv_usec = 0;
        
    fd_set tmpset, fds;
    int received;
    char buff[DEFAULT_BUFFER_SIZE];
    socklen_t len = sizeof(monitorData.remote_addr);
    
    unsigned int sent = sendto (monitorData.sock,command.c_str(),command.size(),0, (struct sockaddr *) &monitorData.remote_addr, len);

    if (sent != command.size()){                
        logString.clear();
        logString.str("");
        logString << "MonitorData: Failed to send command \"" << command << "\" to ("<<monitorData.serverIP <<":"<<monitorData.port << ") .Only "  <<sent <<" of " << command.size() << " bytes have been sent."<< endl;   
        LOG(ERROR, logString.str());
                                        
        exitMonitor ();
    }
    
    if (monitorData.logMask >= LOGMASK_DEBUG) {
            logString.clear();
            logString.str("");
            logString << "MonitorData: Command sent to ("<<monitorData.serverIP <<":"<<monitorData.port << ") is " << command << endl;
            LOG(DEBUG, logString.str());
    }

    FD_ZERO(&fds);
    FD_SET(monitorData.sock, &fds);
    tmpset = fds;

    //passive wait for any activity in the socket
    select(monitorData.sock+1,&tmpset, NULL, NULL, &tv);

    if(FD_ISSET(monitorData.sock, &tmpset)){ 
		
        if ( (received = recvfrom(monitorData.sock, buff, DEFAULT_BUFFER_SIZE, 0, (struct sockaddr *) &monitorData.remote_addr, &len)) <= 0) {
            logString.clear();
            logString.str("");
            logString << "MonitorData: Received <= 0" << endl;
            LOG(ERROR, logString.str());
                                        
            exitMonitor ();
        }
			
        buff[received] = '\0';
        answerString.clear();
        answerString.str("");                        
        answerString << buff;
        
        if (monitorData.logMask >= LOGMASK_DEBUG) {
            logString.clear();
            logString.str("");
            logString << "MonitorData: Answer received: "<<answerString.str()  << endl;
            LOG(DEBUG, logString.str());
        }
        
        answerString >> answer ;                        
        transform( answer.begin(), answer.end(), answer.begin(), my_tolower );
        
        if (answer == "error:" ) {
            if (monitorData.logMask >= LOGMASK_DEBUG) {
                logString.clear();
                logString.str("");
                logString << "MonitorData: ERROR received " << command << endl;
                LOG(DEBUG, logString.str());
            }
            exitMonitor ();                            
        }
    } 
    else {
        if (monitorData.logMask >= LOGMASK_DEBUG) {
            logString.clear();
            logString.str("");
            logString << "MonitorData: No Answer received for " << command << endl;
            LOG(DEBUG, logString.str());
        }
    
    }  
    return answerString.str();
}

bool filterLine (char * line, string filter, bool after, string & element)
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
        
        
	while(inFile) {
		inFile.getline(line, 1024);
		purgeLine(line);

		after = false;  
		filter = ":=";
		if (filterLine(line, filter, after, element)) {			
			if (!strcmp(element.c_str(),"Server")){
				after = true;  
				filter = "Server:=";
				if (filterLine(line, filter, after, element)) {
                                        monitorData.server = element; 
                                        monitorData.dataFileName = monitorData.server + "_CPS.data";
                                        monitorData.cmdFileName = "gnuplot_CPS_"+monitorData.server + ".cmd";   
                                        monitorData.loopFileName = "loop_forever_CPS_"+monitorData.server + ".gnu";  
                                        monitorData.serverIP = getIpByHostname(monitorData.server);                           
				}
			}
 			else if (!strcmp(element.c_str(),"Port")){
				after = true;  
				filter = "Port:=";
				if   (filterLine(line, filter, after, element)) { 
					monitorData.port = atoi (element.c_str());
				}
			}
			else if (!strcmp(element.c_str(),"GraphScanSize")){
				after = true;  
				filter = "GraphScanSize:=";
				if   (filterLine(line, filter, after, element)) { 
					monitorData.scan = atoi (element.c_str());
				}
			}
                        
 			else if (!strcmp(element.c_str(),"MeasureTime")){
				after = true;  
				filter = "MeasureTime:=";
				if   (filterLine(line, filter, after, element)) { 
					monitorData.measureTime = atoi (element.c_str());
				}
			}
			else if (!strcmp(element.c_str(),"RefreshTime")){
				after = true;  
				filter = "RefreshTime:=";
				if   (filterLine(line, filter, after, element)) { 
					monitorData.refreshTime = atoi (element.c_str());
				}
			}
			else if (!strcmp(element.c_str(),"LogMask")){
				after = true;  
				filter = "LogMask:=";
				if   (filterLine(line, filter, after, element)) { 
                                     monitorData.logMask = atoi (element.c_str());
                                }
			}
			else if (!strcmp(element.c_str(),"LogMode")){
				after = true;  
				filter = "LogMode:=";
				if   (filterLine(line, filter, after, element)) { 
                                     monitorData.logMode = atoi (element.c_str());
                                }
			}
			else if (!strcmp(element.c_str(),"SchedulerStep")){
				after = true;  
				filter = "SchedulerStep:=";
				if (filterLine(line, filter, after, element)) { 
                                
                                    struct Step tempStep;
                                    std::vector<std::string> schedulerStep = split(element, ':');
                                    if (schedulerStep.size() != 3){
		                        cout << endl << "ERROR:Wrong SchedulerStep syntax in file: " << nameFile << endl << endl;
		                        exit (1);                
                                    }
                                   
                                    string phase = schedulerStep[0];
                                    tempStep.time = atoi (schedulerStep[1].c_str());
                                    tempStep.cps = atoi (schedulerStep[2].c_str());
                                    monitorData.schedulingEnabled  = true; 
                                  
                                    if (phase == "pre") {
                                        q_stepPre.push_back(tempStep); 
                                    }
                                    else if (phase == "load") {
                                        q_stepLoad.push_back(tempStep); 
                                    }
                                     else if (phase == "post") {
                                        q_stepPost.push_back(tempStep); 
                                    }
                                    else {
		                        cout << endl << "ERROR:Wrong SchedulerStep syntax in file: " << nameFile << endl << endl;
		                        exit (1);                
                                    }
                                   
				}
			}
		}

        }

	inFile.close();	
        						 
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

std::vector<std::string> &split(const std::string &s, char delim, std::vector<std::string> &elems) {
    std::stringstream ss(s);
    std::string item;
    while (std::getline(ss, item, delim)) {
        elems.push_back(item);
    }
    return elems;
}


std::vector<std::string> split(const std::string &s, char delim) {
    std::vector<std::string> elems;
    split(s, delim, elems);
    return elems;
}
