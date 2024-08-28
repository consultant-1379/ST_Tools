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

#include "cnDiaProxy.h"
#include "DiaThread.h"
#include "ListenerThread.h"

using namespace std;

extern vector<DiaServerConnection> v_connections;
extern vector<Transaction> v_transaction;
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

extern applicationData dataTool;

extern unsigned int numberClientThreads;

void *
_ReportManagerThread(void *)
{
    bool myHaveToExit;
    bool saving_latency_data = false;
    bool saving_DiaErrCounters_data = false;
    ReportDataDeque reportDataToSave;
    ofstream outFile_latency;
    ofstream outFile_DiaErrCounters_percentage;
    ofstream outFile_DiaErrCounters_absolute;
    int sample_DiaErrCounters_index =0;
    int DiaErrCounters_report_timer =0;
    int total_report_timer = 0;
    int sample_latency_index =0;
    char filename[1024];
    stringstream logString;
    
    logString.clear();
    logString.str("");
    logString << "(ReportManagerThread): Thread starting up" <<endl;
    LOG(EVENT, logString.str());
    
    char host_name[100];
    getlocalhostname(host_name);


    for(;;) { 

        sleep(1);
	total_report_timer ++;
        	
        pthread_mutex_lock(&TOOL_STATUS);
            myHaveToExit = haveToExit;
        pthread_mutex_unlock(&TOOL_STATUS);

        if(myHaveToExit){ 
		
            logString.clear();
            logString.str("");
            logString << "(ReportManagerThread): Terminating... " <<endl;
            LOG(EVENT, logString.str());
            
            if (outFile_latency && saving_latency_data) {
                time_t clk= time(NULL);
                string timestamp (ctime(&clk));
                outFile_latency << "Stop capture at "<< timestamp ;
                outFile_latency.flush();
                outFile_latency.close();
            }
			
            if (outFile_DiaErrCounters_percentage && saving_DiaErrCounters_data) {
                time_t clk= time(NULL);
                string timestamp (ctime(&clk));
                outFile_DiaErrCounters_percentage << "Stop capture at "<< timestamp ;
                outFile_DiaErrCounters_percentage.flush();
                outFile_DiaErrCounters_percentage.close();
            }
			
            if (outFile_DiaErrCounters_absolute && saving_DiaErrCounters_data) {
                time_t clk= time(NULL);
                string timestamp (ctime(&clk));
                outFile_DiaErrCounters_absolute << "Stop capture at "<< timestamp ;
                outFile_DiaErrCounters_absolute.flush();
                outFile_DiaErrCounters_absolute.close();
            }
	    pthread_exit(0);
        } 
        
        if (dataTool.latency_report_enabled){
            if (dataTool.latency_report_running){
       
                if (!saving_latency_data) {
                    sprintf(filename,"%s_%s_%d_%d.data",dataTool.latency_report_file,host_name,dataTool.local_port,sample_latency_index);
                    outFile_latency.open (filename);

	            if (!outFile_latency) {
                        logString.clear();
                        logString.str("");
                        logString << "(ReportManagerThread) :Failed to create file: " <<filename <<endl;
                        LOG(ERROR, logString.str());
            
	                dataTool.latency_report_running = false;
                        dataTool.latency_report_enabled = false;
                        
		    }

                    time_t clk= time(NULL);
                    string timestamp (ctime(&clk));
                    outFile_latency << "Start capture at " << timestamp ;
                    
                    outFile_latency << "SessionId\t\t\t\tCmd\tLatency" << endl;
                    saving_latency_data=true;
                }
                
                save_latency_data(outFile_latency);

            }
            else {
                if (saving_latency_data) {
             
                    save_latency_data(outFile_latency);
                
                    time_t clk= time(NULL);
                    string timestamp (ctime(&clk));
                    outFile_latency << "Stop capture at "<< timestamp ;
                    saving_latency_data=false;
                    outFile_latency.flush();
                    outFile_latency.close();
                    sample_latency_index++;
                }
       
            }
        }
         if (dataTool.DiaErrCounters_report_enabled){
            if (dataTool.DiaErrCounters_report_running){
       
                if (!saving_DiaErrCounters_data) {
                    sprintf(filename,"%s_absolute_%s_%d_%d.data",dataTool.DiaErrCounters_report_file,host_name,dataTool.local_port,sample_latency_index);
                    outFile_DiaErrCounters_absolute.open (filename);

	            if (!outFile_DiaErrCounters_absolute) {
                        logString.clear();
                        logString.str("");
                        logString << "(ReportManagerThread): Failed to create file: " <<filename <<endl;
                        LOG(ERROR, logString.str());
                        
	                dataTool.DiaErrCounters_report_running = false;
                        dataTool.DiaErrCounters_report_enabled = false;
		    }

                    sprintf(filename,"%s_percentage_%s_%d_%d.data",dataTool.DiaErrCounters_report_file,host_name,dataTool.local_port,sample_latency_index);
                    outFile_DiaErrCounters_percentage.open (filename);

	            if (!outFile_DiaErrCounters_percentage) {
                        logString.clear();
                        logString.str("");
                        logString << "(ReportManagerThread): Failed to create file: " <<filename <<endl;
                        LOG(ERROR, logString.str());
			
	                dataTool.DiaErrCounters_report_running = false;
                        dataTool.DiaErrCounters_report_enabled = false;
		    }

                    time_t clk= time(NULL);
                    string timestamp (ctime(&clk));
                    outFile_DiaErrCounters_absolute << "Start capture at " << timestamp ;
                    outFile_DiaErrCounters_absolute << "Time\tSucc\tUTC\tBSY\tOth\tReq" << endl;

                    
                    outFile_DiaErrCounters_percentage << "Start capture at " << timestamp ;
                    outFile_DiaErrCounters_percentage << "Time\tSucc\tUTC\tBSY\tOth" << endl;
                    
                    
                    saving_DiaErrCounters_data=true;
                }
               
                if (DiaErrCounters_report_timer >= dataTool.DiaErrCounters_report_timeout) {
                    save_DiaErrCounters_data(outFile_DiaErrCounters_absolute, outFile_DiaErrCounters_percentage, total_report_timer); 
                    DiaErrCounters_report_timer = 0;
                 }
                 else {
                    DiaErrCounters_report_timer++;
                 }      

            }
            else {
                if (saving_DiaErrCounters_data) {
             
                    save_DiaErrCounters_data(outFile_DiaErrCounters_absolute, outFile_DiaErrCounters_percentage, total_report_timer); 
                    DiaErrCounters_report_timer = 0;
                 
                    time_t clk= time(NULL);
                    string timestamp (ctime(&clk));
                    outFile_DiaErrCounters_absolute << "Stop capture at " << timestamp ;
                    outFile_DiaErrCounters_percentage << "Stop capture at " << timestamp ;
                    saving_DiaErrCounters_data=false;
                    outFile_DiaErrCounters_absolute.flush();
                    outFile_DiaErrCounters_percentage.flush();
                    outFile_DiaErrCounters_absolute.close();
                    outFile_DiaErrCounters_percentage.close();
                    sample_DiaErrCounters_index++;
                }
       
            }
        }
       
    }


}

void save_DiaErrCounters_data(ofstream & outFile_absolute, ofstream & outFile_pecentage, int time) 
{

    unsigned int total_Success = 0;
    unsigned int total_Busy = 0;
    unsigned int total_UnableToComply = 0;
    unsigned int total_Other = 0;
    unsigned int total_ReqSent = 0;
                       
    pthread_mutex_lock(&STATISTIC);
        for (unsigned int i = 0; i < v_connections.size(); i++) {
            total_Success +=  v_connections[i].resultCode_Success;
            v_connections[i].resultCode_Success = 0;
                                        
            total_Busy +=  v_connections[i].resultCode_Busy;
            v_connections[i].resultCode_Busy = 0;
                                        
            total_UnableToComply +=  v_connections[i].resultCode_UnableToComply;
            v_connections[i].resultCode_UnableToComply = 0;
                                        
            total_Other +=  v_connections[i].resultCode_Other;
            v_connections[i].resultCode_Other = 0;
                                        
            total_ReqSent +=  v_connections[i].request_Sent;
            v_connections[i].request_Sent = 0;
        }
                        
    pthread_mutex_unlock(&STATISTIC);

    pthread_mutex_lock(&REPORT);
		dataTool.resultcode_request += total_ReqSent;
		dataTool.resultcode_success += total_Success;
		dataTool.resultcode_busy += total_Busy;
		dataTool.resultcode_utc += total_UnableToComply;
		dataTool.resultcode_other += total_Other;
    pthread_mutex_unlock(&REPORT);


    outFile_absolute << time;
    outFile_absolute <<"\t"<< total_Success;
    outFile_absolute <<"\t"<< total_UnableToComply;
    outFile_absolute <<"\t"<< total_Busy;
    outFile_absolute <<"\t"<< total_Other;
    outFile_absolute <<"\t"<< total_ReqSent;
    outFile_absolute << std::endl;
                        
    unsigned int percentage_Success, percentage_Busy, percentage_UnableToComply, percentage_Other;
    unsigned int total_Answer = total_Success + total_Busy + total_UnableToComply + total_Other;
                        
    if (total_Answer) {
        percentage_Success = (100 * total_Success) / total_Answer;
        percentage_Busy = (100 * total_Busy) / total_Answer;
        percentage_UnableToComply = (100 * total_UnableToComply) / total_Answer;
        percentage_Other = (100 * total_Other) / total_Answer;
    }
    else {
        percentage_Success = 0;
        percentage_Busy = 0;
        percentage_UnableToComply = 0;
        percentage_Other = 0;
    }
                      
    outFile_pecentage <<time;
    outFile_pecentage <<"\t"<< percentage_Success;
    outFile_pecentage <<"\t"<< percentage_UnableToComply;
    outFile_pecentage <<"\t"<< percentage_Busy;
    outFile_pecentage <<"\t"<< percentage_Other;
    outFile_pecentage << std::endl;
                                               
}

void save_latency_data(ofstream & outFile) 
{
    ReportDataDeque reportDataToSave;
    
    for (unsigned int i = 0; i < v_connections.size(); i++) {
        reportDataToSave.clear();
        pthread_mutex_lock(&REPORT);
            reportDataToSave.swap(v_connections[i].reportData);
        pthread_mutex_unlock(&REPORT);

        while (! (reportDataToSave.empty())){
                    
            struct reportData sample= reportDataToSave.front();
            reportDataToSave.pop_front();

            outFile << sample.sessionId << "\t";
            outFile << sample.cmd_code << "\t";
            outFile << sample.time_event << endl;
            outFile.flush();
        }               
    }

}
