#include "loadplotter.h"

#define SSH_PERIOD  "var"
#define SSH_NODE 	"node"
#define EXIT_CMD "exit"
#define QUIT_CMD "quit"
#define LOGOUT_CMD "logout"

using namespace std;

extern pthread_t SignalThreadID;
extern pthread_mutex_t sync_mutex;

extern vector<Connection> v_connections;

extern applicationData dataTool;
UtilsLoadMeas utils;


void* _ConnectionThread_CBA(void *arg)
{
    Connection	*myConnection = (Connection *)arg;
 	ConnectionStatus myStatus;
    stringstream logString;
	ToolStatus appStatus;
	CUtilsSsh sshCnct;
    auto_ptr <CUtilsSsh> ptrShCnct;
        
    string command = "";
    stringstream commandString;
    std::ofstream outFile;
    double runningTime = 0;
    char cmd[1024];
    char line [1024];
    int slot_without_data = 0;
    int max_slot_without_data = 50;
       
    bool connected_at_least_once = false;
    string get_PL_data=myConnection->name +"_CBA_get_PL.data";
    string get_PL_log=myConnection->name +"_CBA_get_PL.log";
    myConnection->status= STARTING;
    
    if ( myConnection->procFilter.empty()){
        sprintf(cmd,"CBA_get_PL -v --node %s --user %s 1>%s 2>%s ",myConnection->destHostIP.c_str(),myConnection->CBA_userid.c_str(), get_PL_data.c_str(), get_PL_log.c_str());
        if(system(cmd)!=0){
                logString.clear();
                logString.str("");
                logString << "ConnectionThread_" << myConnection->name <<": Failed during command execution: " <<cmd << endl;
                LOG(ERROR, logString.str());
                                
                resetConnectionAndExit_CBA (myConnection, ptrShCnct);
        }
                                
        ifstream inFile;       
        inFile.open (get_PL_data.c_str());
                        
        if (!inFile) {
                logString.clear();
                logString.str("");
                logString << "ConnectionThread_" << myConnection->name <<"ERROR: CBA_get_PL failed " << endl;
                LOG(ERROR, logString.str());
                                
                resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
        }

        string line;
        while (getline(inFile, line)){
            myConnection->procFilter.push_back(line);
        }
                
        if ( myConnection->procFilter.empty()){ 
            logString.clear();
            logString.str("");
            logString << "ConnectionThread_" << myConnection->name <<"ERROR: List of PL proccessors is empty" << endl;
            LOG(ERROR, logString.str());
                            
            resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
        }
        else{
                        
            if (dataTool.logMask >= LOGMASK_INFO) {
                    logString.clear();
                    logString.str("");
                    logString << "ConnectionThread_" << myConnection->name <<": " <<myConnection->procFilter.size() << " PL proccessors found"<< endl;
                    LOG(INFO, logString.str());
            }
            
            inFile.close(); 
       }
        
    } //  if ( myConnection->procFilter.empty()   
    else{
        if (dataTool.logMask >= LOGMASK_INFO) {
            logString.clear();
            logString.str("");
            logString << "ConnectionThread_" << myConnection->name <<": " <<myConnection->procFilter.size() << " PL proccessors set by user"<< endl;
            LOG(INFO, logString.str());
        }
    }
                      
    myConnection->status= TO_BE_CONNECTED;
    struct timespec event_time;
    struct timespec start_time;
    clock_gettime( CLOCK_MONOTONIC, &start_time );
                    
    while (true){ 

        pthread_mutex_lock(&sync_mutex);
            myStatus = myConnection->status;
            appStatus = dataTool.status;
        pthread_mutex_unlock(&sync_mutex); 
        
        if (appStatus == LOADPLOTTER_HAVE_TO_EXIT){
            if (dataTool.logMask >= LOGMASK_EVENT) {
                logString.clear();
                logString.str("");
                logString << "ConnectionThread_" << myConnection->name <<": Client connection shall be closed" <<endl;
                LOG(EVENT, logString.str());
            }
            resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
        }
                
        switch (myStatus) { 
            case TO_BE_CONNECTED:{
                if (dataTool.logMask >= LOGMASK_CONNECTIONS) {
                    logString.clear();
                    logString.str("");
                    logString << "ConnectionThread_" << myConnection->name <<": Starting..." <<endl;
                    LOG(CONNECTIONS, logString.str());
                }
                        
                if (dataTool.logMask >= LOGMASK_CONNECTIONS) {
                        logString.clear();
                        logString.str("");
                        logString << "ConnectionThread_" << myConnection->name <<": Connecting to remote Server " <<myConnection->destHostIP <<":"<< myConnection->destPort << " using " << myConnection->CBA_userid.c_str()<<":"<<myConnection->CBA_password.c_str()<< endl;
                        LOG(CONNECTIONS, logString.str());
                }
                ptrShCnct = auto_ptr <CUtilsSsh> (new CUtilsSsh);
        
				if (!ptrShCnct->Connect(myConnection->destHostIP.c_str(), myConnection->destPort, myConnection->CBA_userid.c_str(), myConnection->CBA_password.c_str())){
                	if (connected_at_least_once){
						if (dataTool.logMask >= LOGMASK_CONNECTIONS) {
							logString.clear();
							logString.str("");
							logString << "ConnectionThread_" << myConnection->name <<": Failing to network re-connect to remote Server " <<myConnection->destHostIP <<":"<< myConnection->destPort << endl;
                            LOG(CONNECTIONS, logString.str());
        				}

 	    				outFile <<get_timestamp();
	    				outFile <<",0";
	    				outFile << std::endl;
	       				outFile.flush();
                        sleep (1 * myConnection->scanSize);
                        continue;
                   }
                   else {
 						logString.clear();
						logString.str("");
						logString << "ConnectionThread_" << myConnection->name <<": Failing to network connect to remote Server " <<myConnection->destHostIP <<":"<< myConnection->destPort << endl;
						LOG(ERROR, logString.str());

						resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
                   }
				} // if (!sshCnct.Connect
                                
                myConnection->sock = ptrShCnct->getSshfd();
                                
				if (dataTool.logMask >= LOGMASK_CONNECTIONS) {
					logString.clear();
					logString.str("");
					logString << "ConnectionThread_" << myConnection->name <<": Connected to remote Server " <<myConnection->destHostIP <<":"<< myConnection->destPort << endl;
					LOG(CONNECTIONS, logString.str());
        		}

				if (connected_at_least_once == false && myConnection->scanSize > 0){

					if (connected_at_least_once == false && myConnection->refreshTime > 0){
						outFile.open(myConnection->loopFileName.c_str());
						if (!outFile) {
							logString.clear();
							logString.str("");
							logString << "Failed to create file: " <<myConnection->loopFileName << endl;
							LOG(ERROR, logString.str());

							resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
						}

						outFile << "pause " << myConnection->refreshTime << ";replot;reread;";
						outFile.close();
					}

					outFile.open(myConnection->dataFileName.c_str());
					if (!outFile) {
						logString.clear();
						logString.str("");
						logString << "ConnectionThread_" << myConnection->name <<": Failed to open file:" <<myConnection->dataFileName << endl;
						LOG(ERROR, logString.str());
                                        
						myConnection->status = FAULTY;
                                        	resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
					}
                                
					outFile <<get_timestamp();
					outFile <<",0";
					outFile << std::endl;
					outFile.flush();
                    outFile.close();
                    sleep (2);
                                
                    if (connected_at_least_once == false && myConnection->refreshTime > 0){
                        outFile.open(myConnection->cmdFileName.c_str());
						if (!outFile) {
							logString.clear();
							logString.str("");
							logString << "ConnectionThread_" << myConnection->name <<": Failed to open file:" <<myConnection->cmdFileName << endl;
							LOG(ERROR, logString.str());
                                        
							myConnection->status = FAULTY;
                            resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
						}

                        outFile <<"set term x11 font \"arial,15,italic\"" << endl;
						outFile <<"set title \""<<myConnection->name <<"\"" << " noenhanced"<< endl;
                        outFile <<"set key outside "<< endl;
                        outFile <<"set ylabel \"HSS load (%)\""<< endl;
                        outFile <<"set xlabel \"Time\""<< endl;

                        outFile <<"set datafile separator \",\""<< endl;
                        outFile <<"set xdata time"<< endl;
						outFile <<"set timefmt \"%Y-%m-%d %H:%M:%S\""<< endl;
						outFile <<"set format x \"%m-%d %H:%M:%S\""<< endl;
						outFile <<"set xtics rotate by -45"<< endl;

                        outFile <<"set grid layerdefault"<< endl;
                        outFile <<"set border 3"<< endl;
                        outFile << "plot \""<<myConnection->dataFileName<<"\" using 1:2 title \"Total\" noenhanced with lines lt 1";
                                         
                        outFile << "\0" << endl;
                        outFile <<"load \""<<myConnection->loopFileName<<"\"\0" << endl;
                        outFile.flush();
                        outFile.close();
                                
						sprintf(cmd,"chmod 755 %s",myConnection->cmdFileName.c_str());
						if(system(cmd)!=0){
							logString.clear();
							logString.str("");
							logString << "ConnectionThread_" << myConnection->name <<": Failed during command execution: " <<cmd << endl;
							LOG(ERROR, logString.str());
                                        
							myConnection->status = FAULTY;
                            resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
						}
                              
						sprintf(cmd,"chmod 755 %s",myConnection->loopFileName.c_str());
						if(system(cmd)!=0){
							logString.clear();
							logString.str("");
							logString << "ConnectionThread_" << myConnection->name <<": Failed during command execution: " <<cmd << endl;
							LOG(ERROR, logString.str());
                                        
							myConnection->status = FAULTY;
                            resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
						}
                                        
                        if (myConnection->refreshTime > 0) {
// 							sprintf(cmd,"gnuplot -noraise %s >& /dev/null &",myConnection->cmdFileName.c_str());
                            sprintf(cmd,"gnuplot -noraise %s > /dev/null 2>&1 &",myConnection->cmdFileName.c_str());
							if(system(cmd)!=0){
								logString.clear();
								logString.str("");
								logString << "ConnectionThread_" << myConnection->name <<": Failed during command execution: " <<cmd << endl;
								LOG(ERROR, logString.str());
                                        
								myConnection->status = FAULTY;
                                resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
							}
                        }
                    }
                                                               
 					outFile.open(myConnection->dataFileName.c_str(),ios::app );
					if (!outFile) {
						logString.clear();
						logString.str("");
						logString << "ConnectionThread_" << myConnection->name <<": Failed to open file:" <<myConnection->dataFileName << endl;
						LOG(ERROR, logString.str());
                                        
						myConnection->status = FAULTY;
                                        	resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
					}
                                } //if (connected_at_least_once == false)
                                
                            const char msg[] = "(ssh node \"sar -u var | sed -u \'s/^/node_LOAD/\'\" & echo $! >&3) 3>>pids_load.txt | grep -vi linux &";
 
				logString.clear();
                                logString.str("");
                                logString << myConnection->measureTime;
                                
	                        string bufferCmd = utils.replaceAll(msg, SSH_PERIOD, logString.str().c_str()); // set period
	                        int res ;
                            res = utils.sendCmd("rm pids_load.txt", myConnection->sock);
	                        for (unsigned int i=0;i<myConnection->procFilter.size();i++)
	                        {
		                        string bufferString = " "; //repeat full command for each filter
		                        bufferString=bufferString + utils.replaceAll(bufferCmd, SSH_NODE, myConnection->procFilter[i].c_str()) + "\n";

		                        char *bufToChar = new char [bufferString.size()+1];
		                        bufToChar[bufferString.size()]=0;
		                        memcpy(bufToChar,bufferString.c_str(), bufferString.size());

		                        res = utils.sendCmd(bufToChar, myConnection->sock);
		                        if (res !=0){
						logString.clear();
						logString.str("");
						logString << "ConnectionThread_" << myConnection->name <<": Failed to send trigger cmd:"<< bufferString<< endl;
						LOG(ERROR, logString.str());
                                        
                                        	resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
		                        }
                                        
					if (dataTool.logMask >= LOGMASK_EVENT) {
       						logString.clear();
						logString.str("");
						logString << "ConnectionThread_" << myConnection->name << " Command sent: " << endl;
						logString <<  "\n\t" <<bufToChar << endl;
                                		LOG(EVENT, logString.str());
					}
//		                        res = utils.sendCmd("CHILD_LIST=$CHILD_LIST' '$!", myConnection->sock);

	                        } // for
        
                                connected_at_least_once = true;
				myConnection->status = ONLINE;

				break;
                        } // TO_BE_CONNECTED
                        
			case TO_BE_CLOSED:{
                                
				if (dataTool.logMask >= LOGMASK_INFO) {
 					logString.clear();
					logString.str("");
					logString << "ConnectionThread_" << myConnection->name <<": connection shall be closed" << endl;
					LOG(INFO, logString.str());
                }
                                
                outFile.close();
				resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
        
				break;
			}
                
			case FAULTY:{
				if (dataTool.logMask >= LOGMASK_INFO) {
 					logString.clear();
					logString.str("");
					logString << "ConnectionThread_" << myConnection->name <<": FAULTY connection shall be closed" << endl;
					LOG(INFO, logString.str());
                }
				resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
				break;
			}
                
			case ONLINE:{
 				if(myConnection->sock == -1) {
					logString.clear();
					logString.str("");
					logString << "ConnectionThread_" << myConnection->name <<": Invalid file descriptor fd."<< endl;
					LOG(ERROR, logString.str());
                                        
                    resetConnectionAndExit_CBA (myConnection, ptrShCnct);;
				}

                char buff[BUFFLEN];
				int res = 0;

				res = utils.recvLine(myConnection->sock, buff, 250);

				if(res == -2){
				    if (dataTool.logMask >= LOGMASK_EVENT) {
 				        logString.clear();
 				        logString.str("");
                    	logString << "ConnectionThread_" << myConnection->name <<": Error reading." <<endl;
                    	logString <<"\tConnection shall be re-started" << endl;
                    	LOG(EVENT, logString.str());
                    }
				    slot_without_data = 0;
				    myConnection->status = TO_BE_CONNECTED;
			    }
 
				else if(res == -1){
				    if (dataTool.logMask >= LOGMASK_INFO) {
				    	logString.clear();
				    	logString.str("");
				    	logString << "ConnectionThread_" << myConnection->name <<": No data received " <<endl;
				    	LOG(EVENT, logString.str());
                     }
				     slot_without_data ++;
				     if (slot_without_data >= max_slot_without_data){
				    	 slot_without_data = 0;
						 if (dataTool.logMask >= LOGMASK_EVENT) {
		 				 	logString.clear();
		 				 	logString.str("");
		                  	logString << "ConnectionThread_" << myConnection->name <<": Too much time without data." <<endl;
		                  	logString <<"\tConnection shall be re-started" << endl;
		                 	LOG(EVENT, logString.str());
		                 }
				    	 myConnection->status = TO_BE_CONNECTED;
				     }
			    }
                else if (res == 0){
				    if (dataTool.logMask >= LOGMASK_EVENT) {
				    	logString.clear();
				    	logString.str("");
				    	logString << "ConnectionThread_" << myConnection->name <<":TCP connection closed by peer." << endl;
				    	logString <<"\tConnection shall be re-started" << endl;
				    	LOG(EVENT, logString.str());
                    }
				    slot_without_data = 0;
				    myConnection->status = TO_BE_CONNECTED;
				}
                else {
                	buff[res] = '\0';
            		clock_gettime( CLOCK_MONOTONIC, &event_time );
            		double seconds = event_time.tv_sec - start_time.tv_sec;
                    if (runningTime > seconds){
 						logString.clear();
						logString.str("");
						logString << "ConnectionThread_" << myConnection->name <<"Wrong execution time." << endl;
						logString <<"\event_time.tv_sec: " << event_time.tv_sec << "\trunningTime: " << runningTime << endl;
						LOG(ERROR, logString.str());
                                                         
                        continue;
                    }
                                                
                    slot_without_data = 0;
                    runningTime = seconds;
                    parseLoadRead_CBA(buff, myConnection);

					if (myConnection->cba_round_cnt == myConnection->scanSize && myConnection->scanSize){
 	    				outFile <<get_timestamp();
	    				outFile <<","<< myConnection->cba_total_Load / myConnection->cba_round_cnt;
	    				outFile << std::endl;
	       				outFile.flush();
	       				myConnection->cba_round_cnt = 0;
	       				myConnection->cba_total_Load = 0;
                    }
 				}
                                
				break;
           } // case ONLINE:
                        
           default:
				if (dataTool.logMask >= LOGMASK_DEBUG) {
 					logString.clear();
					logString.str("");
					logString << "ConnectionThread_" << myConnection->name <<": Wrong connection state" << endl;
					LOG(DEBUG, logString.str());
                }
                                
                pthread_mutex_lock(&sync_mutex);
 					dataTool.status = LOADPLOTTER_TO_BE_RESET;
				pthread_mutex_unlock(&sync_mutex);
                
				break;
                        
          } //switch (myStatus)
	} //while (true)
} 
        
        
void resetConnectionAndExit_CBA(Connection *myConnection, auto_ptr <CUtilsSsh> ptrShCnct)
{
	stringstream logString;
	if (dataTool.logMask >= LOGMASK_INFO){
		logString.clear();
		logString.str("");
		logString << "ConnectionThread_" << myConnection->name <<": resetConnectionAndExit_CBA SocketId "<< myConnection->sock <<", ThreadId "<< myConnection->threadID<<endl;
		LOG(INFO, logString.str());
    }
       
    if (myConnection->status < TO_BE_CONNECTED) {
 		pthread_mutex_lock(&sync_mutex);
			myConnection->threadID = 0;
			if (dataTool.status != LOADPLOTTER_HAVE_TO_EXIT)	pthread_kill(SignalThreadID ,SIGUSR1);
		pthread_mutex_unlock(&sync_mutex);
        
        pthread_exit(0);
	}
        
    char cmd[1024];
    
    if (myConnection->status == FAULTY) {
		myConnection->threadID = 0;
        int socket = ptrShCnct->getSshfd();
        if (socket  != -1 ) {
            int res;
            sprintf(cmd,"CBA_run_command \"xargs kill -KILL <pids_load.txt\" -v --node %s --user %s  1>cmd_1.data 2>cmd_1.log  ",myConnection->destHostIP.c_str(),myConnection->CBA_userid.c_str());
            if(system(cmd)!=0){
                logString.clear();
                logString.str("");
                logString << "ConnectionThread_" << myConnection->name <<": Failed during command execution: " <<cmd << endl;
                LOG(ERROR, logString.str());
            }
            else if (dataTool.logMask >= LOGMASK_EVENT) {
                logString.clear();
                logString.str("");
                logString << "ConnectionThread_" << myConnection->name << " Command sent: " << endl;
                logString <<  "\n\t" <<cmd << endl;
                LOG(EVENT, logString.str());
            }
            sprintf(cmd,"CBA_run_command \"rm pids_load.txt\" -v --node %s --user %s 1>cmd_2.data 2>cmd_2.log  ",myConnection->destHostIP.c_str(),myConnection->CBA_userid.c_str());
            if(system(cmd)!=0){
                logString.clear();
                logString.str("");
                logString << "ConnectionThread_" << myConnection->name <<": Failed during command execution: " <<cmd << endl;
                LOG(ERROR, logString.str());
            }
            else if (dataTool.logMask >= LOGMASK_EVENT) {
                logString.clear();
                logString.str("");
                logString << "ConnectionThread_" << myConnection->name << " Command sent: " << endl;
                logString <<  "\n\t" <<cmd << endl;
                LOG(EVENT, logString.str());
            }
            res = ptrShCnct->sendCmd(EXIT_CMD);
			res = ptrShCnct->sendCmd(LOGOUT_CMD);
            shutdown(socket, SHUT_RDWR);
			close (socket);
        }
        ptrShCnct.release();
        pthread_exit(0);
	}	
		
    if (myConnection->status >= ONLINE) {
    	int socket = ptrShCnct->getSshfd();
        if (socket  != -1 ) {
        	int res;
             sprintf(cmd,"CBA_run_command \"xargs kill -KILL <pids_load.txt\" -v --node %s --user %s  1>cmd_1.data 2>cmd_1.log  ",myConnection->destHostIP.c_str(),myConnection->CBA_userid.c_str());
             if(system(cmd)!=0){
                logString.clear();
                logString.str("");
                logString << "ConnectionThread_" << myConnection->name <<": Failed during command execution: " <<cmd << endl;
                LOG(ERROR, logString.str());
            }
            else if (dataTool.logMask >= LOGMASK_EVENT) {
                logString.clear();
                logString.str("");
                logString << "ConnectionThread_" << myConnection->name << " Command sent: " << endl;
                logString <<  "\n\t" <<cmd << endl;
                LOG(EVENT, logString.str());
            }

            sprintf(cmd,"CBA_run_command \"rm pids_load.txt\" -v --node %s --user %s 1>cmd_2.data 2>cmd_2.log ",myConnection->destHostIP.c_str(),myConnection->CBA_userid.c_str());
            if(system(cmd)!=0){
                logString.clear();
                logString.str("");
                logString << "ConnectionThread_" << myConnection->name <<": Failed during command execution: " <<cmd << endl;
                LOG(ERROR, logString.str());
            }
            else if (dataTool.logMask >= LOGMASK_EVENT) {
                logString.clear();
                logString.str("");
                logString << "ConnectionThread_" << myConnection->name << " Command sent: " << endl;
                logString <<  "\n\t" <<cmd << endl;
                LOG(EVENT, logString.str());
            }

			res = ptrShCnct->sendCmd(EXIT_CMD);
			res = ptrShCnct->sendCmd(LOGOUT_CMD);
            shutdown(socket, SHUT_RDWR);
			close (socket);
        }
                
    }

    ptrShCnct.release();

	pthread_mutex_lock(&sync_mutex);
		myConnection->status = OFFLINE;
		myConnection->sock = -1;
	pthread_mutex_unlock(&sync_mutex);
        
        char file[1024];
        
        if (myConnection->refreshTime > 0) {
		sprintf(cmd,"ps -eaf | grep \"gnuplot -noraise %s\" | grep -v \"grep\" | awk '{print $2}' | xargs kill -9",myConnection->cmdFileName.c_str());
       
		if(system(cmd)!=0){
			if (dataTool.logMask >= LOGMASK_INFO){
				logString.clear();
				logString.str("");
				logString << "ConnectionThread_" << myConnection->name <<": Failed during command execution: "<<cmd<<endl;
				LOG(INFO, logString.str());
			}
        	}
        }
        
        if (myConnection->scanSize) {
		ofstream outFile;
		outFile.open(myConnection->cmdFileName.c_str());
		if (!outFile) {
			logString.clear();
			logString.str("");
			logString << "ConnectionThread_" << myConnection->name <<": Failed to open file:" <<myConnection->cmdFileName << endl;
			LOG(ERROR, logString.str());
		}
        
		outFile <<"set term x11 font \"arial,15,italic\"" << endl;		
		outFile <<"set title \""<<myConnection->name <<"\"" << " noenhanced" << endl;
		outFile <<"set ylabel \"HSS load (%)\""<< endl;
		outFile <<"set xlabel \"Time\""<< endl;

        outFile <<"set datafile separator \",\""<< endl;
        outFile <<"set xdata time"<< endl;
		outFile <<"set timefmt \"%Y-%m-%d %H:%M:%S\""<< endl;
		outFile <<"set format x \"%m-%d %H:%M:%S\""<< endl;
		outFile <<"set xtics rotate by -45"<< endl;

        outFile <<"set key outside "<< endl;
        outFile <<"set grid layerdefault"<< endl;
        outFile <<"set border 3"<< endl;
		outFile << "plot \""<<myConnection->dataFileName<<"\" using 1:2 title \"Total\" noenhanced with lines lt 1\0";
                                        
		outFile.flush();
		outFile.close();  
        
		if(dataTool.KeepGraphicAfterExecution){
                  
			sprintf(cmd,"gnuplot -persist %s > /dev/null 2>&1 &",myConnection->cmdFileName.c_str());

			if(system(cmd)!=0){
				logString.clear();
				logString.str("");
				logString << "ConnectionThread_" << myConnection->name <<": Failed during command execution: " <<cmd << endl;
				LOG(ERROR, logString.str());
			}
        	} 
           
		sprintf(file,"generate_gif_%s",myConnection->name.c_str());
		outFile.open(file);
		if (!outFile) {
			logString.clear();
			logString.str("");
			logString << "ConnectionThread_" << myConnection->name <<": Failed to open file: generate_gif_xxxxxx.cmd" << endl;
			LOG(ERROR, logString.str());
		}

		outFile <<"set term gif" << endl;
		outFile <<"set title \""<<myConnection->name <<"\"" << " noenhanced"  << endl;
		outFile <<"set output \"load_"<<myConnection->name <<".gif\"" << endl;
		outFile <<"set ylabel \"HSS load (%)\""<< endl;
		outFile <<"set xlabel \"Time\""<< endl;

        outFile <<"set datafile separator \",\""<< endl;
        outFile <<"set xdata time"<< endl;
		outFile <<"set timefmt \"%Y-%m-%d %H:%M:%S\""<< endl;
		outFile <<"set format x \"%m-%d %H:%M:%S\""<< endl;
		outFile <<"set xtics rotate by -45"<< endl;

        outFile <<"set key outside "<< endl;
        outFile <<"set grid layerdefault"<< endl;
        outFile <<"set border 3"<< endl;
		outFile << "plot \""<<myConnection->dataFileName<<"\" using 1:2 title \"Total\" noenhanced with lines lt 1\0" << endl;
                                        
		outFile.flush();
		outFile.close();  
       
		sprintf(cmd,"gnuplot %s > /dev/null 2>&1 ",file);

		if(system(cmd)!=0){
			logString.clear();
			logString.str("");
			logString << "ConnectionThread_" << myConnection->name <<": Failed during command execution: " <<cmd << endl;
			LOG(ERROR, logString.str());
		}
                         
 		sprintf(cmd,"rm %s",file);

		if(system(cmd)!=0){
			logString.clear();
			logString.str("");
			logString << "ConnectionThread_" << myConnection->name <<": Failed during command execution: " <<cmd << endl;
			LOG(ERROR, logString.str());
		}
        }
                         
 	pthread_mutex_lock(&sync_mutex);
		myConnection->threadID = 0;
		myConnection->status = NOT_USED;
//                if (dataTool.status != LOADPLOTTER_HAVE_TO_EXIT)	pthread_kill(SignalThreadID ,SIGUSR1);
	pthread_mutex_unlock(&sync_mutex);
        
        pthread_exit(0);
}

void parseLoadRead_CBA(char * buf, Connection *myConnection)
{
        
	stringstream logString;
	const char loadSuffix[7] = "_LOAD";
	char *substr = NULL;
	char *substrL = NULL;
	char *substrCmd = NULL;
	float load = 0;
        string addInfo;
        addInfo = buf;
               
	if (dataTool.logMask >= LOGMASK_DEBUG) {
 		logString.clear();
		logString.str("");
		logString << "ConnectionThread_" << myConnection->name <<": Received message "<< addInfo  << endl;
		LOG(DEBUG, logString.str());
        }

	if (!utils.confGetHeaderParams(buf)){
                
            if(utils.parCount(buf, " ")>5 && (substr = strstr(buf,"PL-")) != NULL  && ((substrCmd = strstr(buf, "/")) == NULL )){

                if ((substrL = strstr(buf, loadSuffix)) != NULL){

                    char *substr_save = substr;
                    char *tmp = (char *)calloc(128, 1);

                    while (!(*substr == '\n' || *substr == '\0')){
                        //printf("%c", *substr);
                        tmp[substr-substr_save] = (char)*substr;
                        substr++;
                    }


                    if (substrL != NULL){ //Load
                        //pl-4_LOAD09:51:02 CPU %user %nice %system %iowait %steal %idle : pl-3_LOAD095102 all 1.42 0.00 0.75 0.00 0.00 97.82
                        load = (100.0 - utils.getFloatLoad(buf));
                        myConnection->cba_acc_Load += load;
                        myConnection->cba_load_cnt++;
						
                        if (myConnection->cba_load_cnt == myConnection->procFilter.size()) {
                            myConnection->totalloadValue = myConnection->cba_acc_Load/myConnection->cba_load_cnt;
                            myConnection->regulatedloadValue = myConnection->cba_acc_Load/myConnection->cba_load_cnt;
                            myConnection->cba_total_Load += myConnection->cba_acc_Load/myConnection->cba_load_cnt;
                            myConnection->cba_round_cnt++;
                            myConnection->cba_load_cnt = 0;
                            myConnection->cba_acc_Load = 0;
                        }
//printf("cba_load_cnt: %d    cba_round_cnt: %d   cba_acc_Load: %f  cba_total_Load: %f   regulatedloadValue: %f \n", myConnection->cba_load_cnt,myConnection->cba_round_cnt,myConnection->cba_acc_Load,myConnection->cba_total_Load, myConnection->regulatedloadValue);
                                                
		    }
		    free(tmp);

                } //if load mem loadcmd memcmd
            } //if substring filter

	} //if (!utils.confGetHeaderParams(buf))
 }
