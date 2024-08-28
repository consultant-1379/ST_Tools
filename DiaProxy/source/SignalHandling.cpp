#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <signal.h>
#include <pthread.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <net/if.h>
#include <stropts.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <unistd.h>
#include <netdb.h>
#include <sys/timeb.h>
#include <vector>
#include <map>
#include <iostream>
#include <fstream>
#include <sstream>

#include "DiaProxy.h"
#include "DiaThread.h"
#include "ListenerThread.h"

#include "Logger.h"
using namespace std;

extern vector<DiaServerConnection> v_connections;
extern map<string, Session> m_session;
extern vector<Transaction> v_transaction;
extern map<string, Session> m_session;
extern PendingToSendMap  m_pendingToSend;

extern SignalReason sigReason;
extern DiaProxyStatus diaProxyState;
extern bool haveToExit;
extern bool couldBeCleaned;
extern pthread_mutex_t TOOL_STATUS;
extern pthread_mutex_t REPORT;
extern pthread_mutex_t STATISTIC;

extern pthread_t ProxyThreadID;
extern pthread_t ListenerThreadID;
extern pthread_t DiaThreadID;

extern CER_DATA cer_data;

extern unsigned int numberClientThreads;

void printState()
{
    string answer = "";
    answer = get_status_info() + get_configuration_info() ;
    LOG(DISPLAY, answer);
}



void *
handler(void *)
{
    stringstream logString;
    string logInfo;
    logString.clear();
    logString.str("");
    int signal;
    DiaProxyStatus myDiaProxyState; 	
    sigset_t signal_set;

    logString.clear();
    logString.str("");
    logString << "(SignalThread): Thread starting up" <<endl;
    LOG(EVENT, logString.str());
        

	for(;;){
		sigfillset( &signal_set );
		sigwait(&signal_set, &signal);
		switch (signal) {
			case SIGINT:
			case SIGTERM:
    	                        logString.clear();
    	                        logString.str("");
	                        logString << endl << "***********************************************************" << endl;
				logString <<         "\tUser have pressed CTRL-C Exiting........." << endl;
	                        logString <<         "***********************************************************" << endl;
                                LOG(DISPLAY, logString.str());
                               
                                if (cer_data.latency_report_running) {cer_data.latency_report_running = false;} 
                                if (cer_data.DiaErrCounters_report_running) {cer_data.DiaErrCounters_report_running = false;} 
                                
                                pthread_mutex_lock(&TOOL_STATUS);
					myDiaProxyState = diaProxyState;
					diaProxyState = DIAPROXY_SHUTINGDOWN;
				pthread_mutex_unlock(&TOOL_STATUS);
                                
				printState();
                                
				pthread_mutex_lock(&TOOL_STATUS);
					haveToExit = true;
				pthread_mutex_unlock(&TOOL_STATUS);

				sleep (5);
				close_server_socket();

				if (myDiaProxyState == DIAPROXY_PROCESSING ) {
                                        
    	                            logString.clear();
    	                            logString.str("");
                                    logString << endl << "\tFINAL STATISTIC REPORT" << endl;
	                            logString <<         "\t**********************" << endl;
                                    LOG(DISPLAY, logString.str());
                                    
                                    logInfo = "";

				    for (unsigned int i = 0; i < v_connections.size(); i++) {
					logInfo += get_connection_info(&v_connections[i], i);
                                        logInfo += get_connection_statistic(&v_connections[i], i);
				    }
                                        
                                    LOG(DISPLAY, logInfo);
				}

    	                        logString.clear();
    	                        logString.str("");
				logString << "(SignalThread): ....Terminated" << endl;
                                LOG(DISPLAY, logString.str());

				exit (0);		
				break;
				
			case SIGTSTP:
                                
    	                        logString.clear();
    	                        logString.str("");
	                        logString << endl << "**********************************************" << endl;
				logString <<         "\tUser have pressed CTRL-Z........." << endl;
	                        logString <<         "**********************************************" << endl;
                                LOG(DISPLAY, logString.str());
                                
				printState();
				
    	                       logString.clear();
    	                       logString.str("");
                               logString << endl << "\tSTATISTIC REPORT" << endl;
	                       logString <<         "\t**********************" << endl;
                               LOG(DISPLAY, logString.str());
                                    
    	                       logString.clear();
    	                       logString.str("");
                               logInfo = "";

			       for (unsigned int i = 0; i < v_connections.size(); i++) {
				    logInfo += get_connection_info(&v_connections[i], i);
                                    logInfo += get_connection_statistic(&v_connections[i], i);
			       }
                                        
                               LOG(DISPLAY, logInfo);

			       break;
				
			case SIGUSR1: {
			
				switch (sigReason) {
					case MAX__INACTIVE__REACHED: {

    	                                    logString.clear();
    	                                    logString.str("");
	                                    logString << endl << "*******************************************" << endl;
				            logString <<         "\tNot active TTCN connections" << endl;
	                                    logString <<         "******************************************" << endl;
                                            LOG(DISPLAY, logString.str());
                                 
					    int activeTTCNConnections = 0;
					    pthread_mutex_lock(&TOOL_STATUS);
					    sigReason = NO_REASON;
                                
                                            if (cer_data.latency_report_running) {cer_data.latency_report_running = false;} 
                                            if (cer_data.DiaErrCounters_report_running) {cer_data.DiaErrCounters_report_running = false;} 
                                
					    printState();

    	                                    logString.clear();
    	                                    logString.str("");
                                            logString << endl << "\tFINAL STATISTIC REPORT" << endl;
	                                    logString <<         "\t**********************" << endl;
                                            LOG(DISPLAY, logString.str());
                                    
    	                                    logString.clear();
    	                                    logString.str("");
                                            logInfo = "";

			                    for (unsigned int i = 0; i < v_connections.size(); i++) {
				                logInfo += get_connection_info(&v_connections[i], i);
                                                logInfo += get_connection_statistic(&v_connections[i], i);
			                    }
                                        
                                            LOG(DISPLAY, logInfo);
				
					    if (activeTTCNConnections) {
	                                        logString.clear();
	                                        logString.str("");
	                                        logString << "(SignalThread): Number of TTCN connections should be zero not " << activeTTCNConnections <<endl;
	                                        LOG(WARNING, logString.str());
					    }
				
					    diaProxyState = DIAPROXY_CLEANNING;

	                                    logString.clear();
	                                    logString.str("");
	                                    logString << "(SignalThread): DiaProxy start cleaning ....." << endl;
	                                    LOG(INFO, logString.str());
                                                
 					    int numberOfSession = m_session.size();
					    if (numberOfSession) {
	                                        logString.clear();
	                                        logString.str("");
	                                        logString << "(SignalThread): Cleaning session map" << endl;
	                                        LOG(INFO, logString.str());
                                                
						m_session.clear();
					    }
					    else {
	                                        logString.clear();
	                                        logString.str("");
	                                        logString << "(SignalThread): Sessions map was empty" << endl;
	                                        LOG(INFO, logString.str());
					    }
					
					    int numberTrans = 0;
					    for (int index = 0; index < v_transaction.size() -1; index++) {
						if (v_transaction[index].status == USED ){
						    v_transaction[index].status = NOTUSED;
						    numberTrans++;
						}
					    }
				
	                                    logString.clear();
	                                    logString.str("");
	                                    logString << "(SignalThread): " <<numberTrans<< " pending Transactions has been cleaned" << endl;
	                                    LOG(INFO, logString.str());
                                            
					    map <int, MessageToSendDeque>::iterator pendingToSendMapIter;
					    struct Message message;
					    int numOfSock=0;
					    int numOfMessages=0;
    
					    for (pendingToSendMapIter = m_pendingToSend.begin();pendingToSendMapIter != m_pendingToSend.end();++pendingToSendMapIter){
					        numOfSock++;
					        while (! (pendingToSendMapIter->second.empty())){
						        message= pendingToSendMapIter->second.front();
						        pendingToSendMapIter->second.pop_front();
						        delete [] message.buffer;
						        numOfMessages++;
					        }
					        pendingToSendMapIter->second.clear();
   
					    }
				
	                                    logString.clear();
	                                    logString.str("");
	                                    logString << "(SignalThread): " <<numOfMessages<< " pending messages to send for "<< numOfSock<< " sockets has been cleaned." << endl;
	                                    LOG(INFO, logString.str());
                                            
					    for (unsigned int i = 0; i < v_connections.size(); i++) {
					        v_connections[i].numberOfClients = 0;
						v_connections[i].totalNumberOfClients = 0;
						v_connections[i].requestSentToServer = 0;
						v_connections[i].requestReceivedFromServer = 0;
						v_connections[i].requestSentToClient = 0;
						v_connections[i].requestReceivedFromClient = 0;
						v_connections[i].requestDiscardFromClient = 0;
						v_connections[i].requestDiscardFromServer = 0;

						v_connections[i].answerSentToServer = 0;
						v_connections[i].answerReceivedFromServer = 0;
						v_connections[i].answerSentToClient = 0;
						v_connections[i].answerReceivedFromClient = 0;
						v_connections[i].answerDiscardFromClient = 0;
						v_connections[i].answerDiscardFromServer = 0;

	                                        logString.clear();
	                                        logString.str("");
	                                        logString << "(SignalThread): Counters for connection "<< i<< " has been cleaned" << endl;
	                                        LOG(INFO, logString.str());
					    }

				
	                                    logString.clear();
	                                    logString.str("");
	                                    logString << "(SignalThread): DiaProxy cleanning finished" << endl;
	                                    LOG(INFO, logString.str());

					    couldBeCleaned = false;
					    diaProxyState = DIAPROXY_STANDBY;
					    printState();
					    pthread_mutex_unlock(&TOOL_STATUS);
					    break;					
					
					}
                                        
                                        
  			                case DIA_EXIT_REQ_BY_USER:
    	                                    logString.clear();
    	                                    logString.str("");
	                                    logString << endl << "***********************************************************" << endl;
				            logString <<         "\tUser has sent exit command. Exiting........." << endl;
	                                    logString <<         "***********************************************************" << endl;
                                            LOG(DISPLAY, logString.str());
                                
                                            if (cer_data.latency_report_running) {cer_data.latency_report_running = false;} 
                                            if (cer_data.DiaErrCounters_report_running) {cer_data.DiaErrCounters_report_running = false;} 
                                
                                            pthread_mutex_lock(&TOOL_STATUS);
					        myDiaProxyState = diaProxyState;
					        diaProxyState = DIAPROXY_SHUTINGDOWN;
				            pthread_mutex_unlock(&TOOL_STATUS);
                                
				            printState();
                                              
				            pthread_mutex_lock(&TOOL_STATUS);
					        haveToExit = true;
				            pthread_mutex_unlock(&TOOL_STATUS);

				            sleep (5);
				            close_server_socket();

				            if (myDiaProxyState == DIAPROXY_PROCESSING ) {
                                        
    	                                        logString.clear();
    	                                        logString.str("");
                                                logString << endl << "\tFINAL STATISTIC REPORT" << endl;
	                                        logString <<         "\t**********************" << endl;
                                                LOG(DISPLAY, logString.str());
                                    
    	                                        logString.clear();
    	                                        logString.str("");
                                                logInfo = "";

				                for (unsigned int i = 0; i < v_connections.size(); i++) {
					            logInfo += get_connection_info(&v_connections[i], i);
                                                    logInfo += get_connection_statistic(&v_connections[i], i);
				                }
                                        
                                                LOG(DISPLAY, logInfo);
				            }

    	                                    logString.clear();
    	                                    logString.str("");
				            logString << "(SignalThread): ....Terminated" << endl;
                                            LOG(DISPLAY, logString.str());

				            exit (0);		
				            break;
                                      
 					case DIA__CONF__ERROR: {
    	                                    logString.clear();
    	                                    logString.str("");
	                                    logString << endl << "*******************************************************************" << endl;
				            logString <<         "\tDiaProxy Shutting down due to configuration/execution error" << endl;
	                                    logString <<         "*******************************************************************" << endl;
                                            LOG(DISPLAY, logString.str());
                                
                                            if (cer_data.latency_report_running) {cer_data.latency_report_running = false;} 
                                            if (cer_data.DiaErrCounters_report_running) {cer_data.DiaErrCounters_report_running = false;} 
                                            
					    pthread_mutex_lock(&TOOL_STATUS);
						haveToExit = true;
					    pthread_mutex_unlock(&TOOL_STATUS);

					    sleep (5);
				
					    close_server_socket();
                                            
    	                        	    logString.clear();
    	                        	    logString.str("");
					    logString << "(SignalThread): ....Terminated" << endl;
                                	    LOG(DISPLAY, logString.str());
		
					    exit (0);		
					
					}
					case PTHREAD_ERROR: {
   	                                    logString.clear();
    	                                    logString.str("");
	                                    logString << endl << "*******************************************************************" << endl;
				            logString <<         "\tDiaProxy Shutting down due to an error in pthread library." << endl;
	                                    logString <<         "*******************************************************************" << endl;
                                            LOG(DISPLAY, logString.str());

					    pthread_mutex_lock(&TOOL_STATUS);
						haveToExit = true;
					    pthread_mutex_unlock(&TOOL_STATUS);

					    sleep (5);
					    close_server_socket();
    	                        	    logString.clear();
    	                        	    logString.str("");
					    logString << "(SignalThread): ....Terminated" << endl;
                                	    LOG(DISPLAY, logString.str());
		
					    exit (0);		
					}
				
					case DIA__CONRETRIES__REACHED: {
   	                                    logString.clear();
    	                                    logString.str("");
	                                    logString << endl << "*******************************************************************" << endl;
				            logString <<         "\tDiaProxy Shutting down due to max initial connections tries reached." << endl;
	                                    logString <<         "*******************************************************************" << endl;
                                            LOG(DISPLAY, logString.str());

					    pthread_mutex_lock(&TOOL_STATUS);
						haveToExit = true;
					    pthread_mutex_unlock(&TOOL_STATUS);

					    sleep (5);
					    close_server_socket();
    	                        	    logString.clear();
    	                        	    logString.str("");
					    logString << "(SignalThread): ....Terminated" << endl;
                                	    LOG(DISPLAY, logString.str());
		
					    exit (0);		
					}
					default:				
   	                                    logString.clear();
    	                                    logString.str("");
				            logString << "(SignalThread): Received internal signal" << endl;
                                            LOG(DEBUG, logString.str());
				} //end switch sigReason
			
				break;
			} // end case SIGUSR1

			case SIGUSR2:
   	                    logString.clear();
    	                    logString.str("");
			    logString << "(SignalThread): Received SIGUSR2 signal" << endl;
                            LOG(DEBUG, logString.str());
			    break;

			default:
   	                    logString.clear();
    	                    logString.str("");
			    logString << "(SignalThread): Received external signal" << signal << endl;
                            LOG(DEBUG, logString.str());
				break;
		}
    
    	}
    
}
