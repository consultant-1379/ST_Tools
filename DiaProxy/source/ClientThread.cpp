//==============================================================================
//#****h* src/ClientThread.cpp
//# MODULE
//#   DiaProxy.capp
//#
//# AUTHOR    
//#   TV 
//#
//# VERSION
//#   1.0.0
//#   	Ckecked by: -
//#	Aproved by: -
//#
//# DATE
//#   September, 2005
//#
//# DESCRIPTION
//# 	
//#   
//# IMPORTS
//#   
//# REFERENCES
//#	[1]	NONE
//#
//# -----------------------------------------------------------------------------
//# HISTORY
//#   Olov Marklund		   	2005/06/10    Creation
//#   Jose Manuel Santos	   	2005/09/26    Comments added
//#   Jose Manuel Santos		2005/11/22    Avoid '0x00000000' end2end ID
//#******
//==============================================================================
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
#include <sys/time.h>
#include <algorithm>
#include <errno.h>

#include <iostream>
#include <fstream>
#include <sstream>

#include "DiaProxy.h"
#include "ClientThread.h"
#include "Logger.h"

/*** Declaration of these global variables to be found in the main module ***/
extern pthread_t ListenerThreadID;
extern pthread_t SignalThreadID;
extern bool haveToExit;

extern time_t start, stop, lastaction;
extern CER_DATA cer_data;

//variable for defining/handling a mutual exclusion zone
extern pthread_mutex_t TRANSACTION_VECTOR;
extern pthread_mutex_t CONNECTION_VECTOR;
extern pthread_mutex_t CLIENT_VECTOR;
extern pthread_mutex_t CLIENT_THREAD_VECTOR;
extern pthread_mutex_t SESSION_MAP;
extern pthread_mutex_t PENDING_MESSAGE_MAP;
extern pthread_mutex_t TOOL_STATUS;
extern pthread_mutex_t STATISTIC;

extern std::vector<DiaServerConnection> v_connections;
extern std::vector<ClientConnection> v_client;
extern std::vector<Transaction> v_transaction;
extern std::map<std::string, Session> m_session;
extern std::vector<clientThread> v_clientThread;


extern unsigned int nextTransaction;
extern unsigned int numberClientThreads;

extern PendingToSendMap  m_pendingToSend;

using namespace std;

//function executed when ProxyThread is created
void* _ClientThread(void *arg)
{
    bool myHaveToExit;
    int counter_e2e = 0;
        
    bool fd_set_result = false;
		
    pthread_mutex_lock(&TOOL_STATUS);
	myHaveToExit = haveToExit;
    pthread_mutex_unlock(&TOOL_STATUS);

    if (myHaveToExit)  	pthread_exit(0);

    clientThread * myClient = (clientThread * )arg;

    //variable declaration
    char logline[1024];
    DIAMETER_HEADER *head;
    puchar pbuf;
    int received;
    fd_set readfdset, writefdset;
    struct timeval tv;
    std::string cmd_code_str;

    struct ClientConnection * currentClient;
    int lastConnectionClient = -1;
    int eventCounter;
    uchar temp_buff[DEFAULT_BUFFER_SIZE];
    bool more_messages ;
    int maxFd_write;
    int maxFd_write_read;
    stringstream logString;   
              
    while (true){ 
	
        pthread_mutex_lock(&TOOL_STATUS);
            myHaveToExit = haveToExit;
        pthread_mutex_unlock(&TOOL_STATUS);

        if(myHaveToExit){ 
            logString.clear();
            logString.str("");
            logString << "(ClientThread:" << myClient->clientThreadID << "): Terminating... "<<endl;
            LOG(EVENT, logString.str());
                        
            resetAndExit (myClient);
        } 
            
        if (myClient->conectionClients.size() == 0) {
            logString.clear();
            logString.str("");
            logString << "(ClientThread:" << myClient->clientThreadID << "): No clients connection...terminating... "<<endl;
            LOG(EVENT, logString.str());
                        
            resetAndExit (myClient);
        }

        //setting the timeout for the select operation
        tv.tv_sec = 0;
        tv.tv_usec = 5000;		
        readfdset = myClient->fds;

        maxFd_write = findSocketsWithPendingMessages(&writefdset, myClient);

        pthread_mutex_lock(&CLIENT_THREAD_VECTOR);
            if (maxFd_write> myClient->maxFd)   maxFd_write_read = maxFd_write +1;
            else                                maxFd_write_read = myClient->maxFd;
        pthread_mutex_unlock(&CLIENT_THREAD_VECTOR);

        eventCounter = select(maxFd_write_read, &readfdset,&writefdset, NULL, &tv);

        for (unsigned int index = 0; (index < myClient->conectionClients.size()) && (eventCounter > 0); index++){

            if (lastConnectionClient < (int) myClient->conectionClients.size() - 1) lastConnectionClient++;
            else  lastConnectionClient = 0;

            currentClient = &v_client[myClient->conectionClients[lastConnectionClient]];

            if(currentClient->sock == -1){
                closeClient (myClient, currentClient);
                continue;
            }

            fd_set_result = FD_ISSET(currentClient->sock, &writefdset);

            if(fd_set_result){
                sendPendingMessage(currentClient->sock);
            }

            fd_set_result = FD_ISSET(currentClient->sock, &readfdset);
                            
            if(fd_set_result){
                if (currentClient->received == 0) {

                    memset(temp_buff,0,DEFAULT_BUFFER_SIZE);
                    pbuf = temp_buff;
                }
                else {
                    memcpy(temp_buff, currentClient->client_buff, currentClient->received);
                    pbuf = temp_buff + currentClient->received;
                }

                eventCounter--;
                received = recv(currentClient->sock,(LPTSTR)pbuf,DEFAULT_BUFFER_SIZE - currentClient->received,0);
                time(&lastaction);	//for inactivity monitoring, the lastaction time is updated

                if(received == -1){
                    logString.clear();
                    logString.str("");
                    logString << "(Client:" << currentClient->pos << "): Broken pipe with TTCN client ";
                    logString <<inet_ntoa(currentClient->remote_addr.sin_addr)<<":"<< htons(currentClient->remote_addr.sin_port) <<endl;
                    LOG(CONNECTIONS, logString.str());
                    closeClient (myClient, currentClient);
                    continue;
                }
                if(received == 0){
                    logString.clear();
                    logString.str("");
                    logString << "(Client:" << currentClient->pos << "): Closed connection by TTCN client ";
                    logString <<inet_ntoa(currentClient->remote_addr.sin_addr)<<":"<< htons(currentClient->remote_addr.sin_port) <<endl;
                    LOG(CONNECTIONS, logString.str());
                    closeClient (myClient, currentClient);
                    continue;
                }

                pbuf = temp_buff;
                received += currentClient->received;

                do {
                    head = (DIAMETER_HEADER*)pbuf;
                    //extracting the DIAMETER message length from the header
                    currentClient->toreceive = (head->length[0]<<16) + (head->length[1]<<8) + head->length[2];

                    //determining how many bytes are left for having the full message
                    more_messages = false;

                    if(currentClient->toreceive > received)  {
                        currentClient->received = received;
                        memcpy(currentClient->client_buff, pbuf, currentClient->received);

                        break;
                    }

                    //once the message is read, the end2end is stored in the proxy
                    //and replaced for the id of the client
                    //this way, the answer could be routed back to the client
#ifdef _DIA_PROXY_DEBUG
                    logString.clear();
                    logString.str("");
                    logString << "(Client:" << currentClient->pos << "): Message received from TTCN" <<endl;
                    LOG(DEBUG, logString.str());

#endif
                    uint cmd_code = (head->cmd_code[0]<<16) + (head->cmd_code[1]<<8) + head->cmd_code[2];
                    std::string myAvp;

                    if (cer_data.ism_port) {
                        uint app_id = (head->cmd_code[3]<<24) + (head->cmd_code[4]<<16) + (head->cmd_code[5]<<8) + head->cmd_code[6];

                        switch (app_id) {
                            case applicationId_zx:
                            case applicationId_sh:
                            case applicationId_zh:
                            case applicationId_cx: {
                                currentClient->diaServerConnection = currentClient->ismServerConnection;
#ifdef _DIA_PROXY_DEBUG
                                logString.clear();
                                logString.str("");
                                logString << "(Client:" << currentClient->pos << "): ISM applicationId" <<endl;
                                LOG(DEBUG, logString.str());                            
#endif
                                break;
                            }

                            case applicationId_slh: {
                                if (extractAVP ((const char *)pbuf, currentClient->toreceive, DESTINATIONHOST_CODE, myAvp) ) {
                                    if (myAvp == "hss.ericsson.se"){
                                        currentClient->diaServerConnection = currentClient->ismServerConnection;
                                    }
                                    else{
                                        currentClient->diaServerConnection = currentClient->esmServerConnection;
                                    }
                                }
                                break;
                            }

                            case applicationId_s6a: 
                            case applicationId_s6t: 
                            case applicationId_s6m: 
                            case applicationId_swx: {
                                currentClient->diaServerConnection = currentClient->esmServerConnection;
#ifdef _DIA_PROXY_DEBUG
                                logString.clear();
                                logString.str("");
                                logString << "(Client:" << currentClient->pos << "): ESM applicationId" <<endl;
                                LOG(DEBUG, logString.str());
#endif
                                break;
                            }
                            default: {
#ifdef _DIA_PROXY_DEBUG
                                logString.clear();
                                logString.str("");
                                logString << "(Client:" << currentClient->pos << "): Wrong applicationId" <<endl;
                                LOG(DEBUG, logString.str());
#endif
                                break;
                            }
                        }// switch (app_id)
                    }// if (cer_data.ism_port)

                    switch (cmd_code) {
                        case cmd__clr_rfe5:
                        case cmd__clr:
                        cmd_code_str = "CL";
                            break;
                        case cmd__idr_rfe5:
                        case cmd__idr:
                            cmd_code_str = "ID";
                            break;
                        case cmd__dsr_rfe5:
                            cmd_code_str = "DS";
                            break;
                        default:
                            cmd_code_str = "XX";
                            break;
                    }

                    switch (cmd_code) {
                        case cmd__code__cer: {
                            if (!extractAVP ((const char *)pbuf, currentClient->toreceive, USERNAME_CODE, myAvp) ) {
                                logString.clear();
                                logString.str("");
                                logString << "(Client:" << currentClient->pos << "):Received an CER without a valid UserName" <<endl;
                                LOG(DEBUG, logString.str());

                                if (!extractAVP ((const char *)pbuf, currentClient->toreceive, ORIGINHOST_CODE, myAvp) ) {
                                    logString.clear();
                                    logString.str("");
                                    logString << "(Client:" << currentClient->pos << "):Received an CER without a valid OriginHost " << myAvp <<endl;
                                    LOG(DEBUG, logString.str());

                                    break;
                                }
                            }

                            std::map<std::string,Session>::iterator mapIter;
                            pthread_mutex_lock(&SESSION_MAP);
                                mapIter = m_session.find(myAvp);
                            pthread_mutex_unlock(&SESSION_MAP);

                            if ( mapIter != m_session.end()) {
                                pthread_mutex_lock(&SESSION_MAP);
                                    mapIter->second.client =  currentClient->pos;
                                    mapIter->second.status = ESTABLISHED;
                                    mapIter->second.diaServerConnection = currentClient->diaServerConnection;
                                pthread_mutex_unlock(&SESSION_MAP);
                            }
                            else {
                                Session mySession;
                                mySession.status = ESTABLISHED;
                                mySession.client =  currentClient->pos;
                                mySession.diaServerConnection = currentClient->diaServerConnection;
                                pthread_mutex_lock(&SESSION_MAP);
                                            bool inserted = m_session.insert(std::make_pair(myAvp, mySession)).second;
                                pthread_mutex_unlock(&SESSION_MAP);

                                if (not inserted) {
                                    logString.clear();
                                    logString.str("");
                                    logString << "(Client:" << currentClient->pos << "):OUT_MESSAGES: ERROR when insert UserName in map" <<endl;
                                    LOG(CONNECTIONS, logString.str());
                                    break;
                                }
                            }
                            head->flags = head->flags & 0x7f;   // convert received CER to answer CEA
                            int res_sending = send(currentClient->sock,(const char*)pbuf,currentClient->toreceive,0);
                            break;
                        }//case cmd__code__cer

                        case cmd__clr_rfe5:
                        case cmd__clr:
                        case cmd__idr_rfe5:
                        case cmd__idr:
                        case cmd__dsr_rfe5: {
                            uint hop2hop = head->hop2hop;
                            hop2hop = hop2hop - 1;
                            //the value of hop2hop is checked in order to avoid Segmentation Fault
                            if (hop2hop > v_transaction.size() - 1) {
                                logString.clear();
                                logString.str("");
                                logString << "(Client:" << currentClient->pos << "):Received end2endid out of range" <<endl;
                                LOG(WARNING, logString.str());
                                closeClient (myClient, currentClient);
                                break;
                            }
                            uint conIndex = v_transaction[hop2hop].answerToDiaServerConnection;
                            if (conIndex < 0) {
                                logString.clear();
                                logString.str("");
                                logString << "(Client:" << currentClient->pos << "):Connection index for outgoing messages out of range" <<endl;
                                LOG(WARNING, logString.str());
                                closeClient (myClient, currentClient);
                                break;
                            }
#ifdef _DIA_PROXY_MONITOR
                            pthread_mutex_lock(&STATISTIC);
                                v_connections[v_transaction[hop2hop].answerToDiaServerConnection].answerReceivedFromClient++;
                            pthread_mutex_unlock(&STATISTIC);
#endif
                            //Storing the message to be sent towards the Diameter server
                            head->end2end =  v_transaction[hop2hop].end2end;
                            head->hop2hop =  v_transaction[hop2hop].hopByHop;;

                            bool inserted = false;

                            if (v_connections[conIndex].status == CONNECTED){
                                struct Message message;
                                message.message_len = currentClient->toreceive;
                                message.bytes_sent = 0;
                                message.message_type = ANSWER_TO_SERVER;
                                message.transaction = -1;
                                message.diaServerConnection = conIndex;
                                message.buffer = new unsigned char [currentClient->toreceive];
                                memcpy(message.buffer, pbuf, currentClient->toreceive);

                                inserted = addMessageAsPending(v_connections[conIndex].sockId, message);

                                if (not inserted){ delete [] message.buffer; }
                            }
                            if (not inserted){
#ifdef _DIA_PROXY_MONITOR
                            pthread_mutex_lock(&STATISTIC);
                                v_connections[conIndex].answerDiscardFromClient++;
                            pthread_mutex_unlock(&STATISTIC);
#endif
                            }
                            pthread_mutex_lock(&TRANSACTION_VECTOR);
                                v_transaction[hop2hop].status = NOTUSED;
                            pthread_mutex_unlock(&TRANSACTION_VECTOR);

                            break;
                        } // 

                        default: {
#ifdef _DIA_PROXY_MONITOR	
                            pthread_mutex_lock(&STATISTIC);
                                v_connections[currentClient->diaServerConnection].requestReceivedFromClient++;
                            pthread_mutex_unlock(&STATISTIC);
#endif
                            int transId = findTransaction();
                            if (transId == -1) {
                                logString.clear();
                                logString.str("");
                                logString << "(Client:" << currentClient->pos << "):There are not Free transaction record" <<endl;
                                LOG(WARNING, logString.str());
#ifdef _DIA_PROXY_MONITOR
                                pthread_mutex_lock(&STATISTIC);
                                    v_connections[currentClient->diaServerConnection].requestDiscardFromClient++;
                                pthread_mutex_unlock(&STATISTIC);												
#endif
                                break;
                            }
                            v_transaction[transId].end2end = head->end2end;
                            v_transaction[transId].hopByHop = head->hop2hop;
                            v_transaction[transId].client = currentClient->pos;
                            head->end2end = ((currentClient->pos+1) * 1000000) + (cer_data.e2e_seed * 10000) + counter_e2e;
                            if (counter_e2e == 7295)    counter_e2e = 0;
                            else                        counter_e2e++;
                            head->hop2hop = transId+1;

                            bool inserted = false;
                            if (v_connections[currentClient->diaServerConnection].status == CONNECTED){
                                struct Message message;
                                message.message_len = currentClient->toreceive;
                                message.bytes_sent = 0;
                                message.message_type = REQUEST_TO_SERVER;
                                message.transaction = transId;
                                message.diaServerConnection = currentClient->diaServerConnection;
                                message.buffer = new unsigned char [currentClient->toreceive];
                                memcpy(message.buffer, pbuf, currentClient->toreceive);

                                inserted = addMessageAsPending(v_connections[currentClient->diaServerConnection].sockId, message);
                                if (not inserted){ delete [] message.buffer; }
                            } 
                            if (not inserted){ 
                                pthread_mutex_lock(&TRANSACTION_VECTOR);
                                    v_transaction[transId].status = NOTUSED;
                                pthread_mutex_unlock(&TRANSACTION_VECTOR);
#ifdef _DIA_PROXY_MONITOR
                                pthread_mutex_lock(&STATISTIC);
                                    v_connections[currentClient->diaServerConnection].requestDiscardFromClient++;
                                pthread_mutex_unlock(&STATISTIC);
#endif
                            }
                            break;
                        } //default
                    } //switch cmd_code

                    if (received > currentClient->toreceive){
                        pbuf += currentClient->toreceive;
                        received -=  currentClient->toreceive;
                        currentClient->toreceive = 0;
                        more_messages = true;
                    }
                    else{
                        currentClient->received = 0;
                        currentClient->toreceive = 0;
                        received = 0;
                        more_messages = false;
                    }

                }while (more_messages);
            }// if(fd_set_result read)
        } // for
    } //while (true)

    logString.clear();
    logString.str("");
    logString << "(Client:" << currentClient->pos << "): Before:Pthread_exit Exiting..." <<endl;
    LOG(INFO, logString.str());
    resetAndExit (myClient);

} //void* _ClientThread(void *arg)


void closeClient (clientThread *myClient, ClientConnection *myConnection)
{
    stringstream logString;

    logString.clear();
    logString.str("");
    logString << "(ClientThread:" << myClient->clientThreadID << "): Exiting..."<<endl;
    LOG(INFO, logString.str());
                            
    pthread_mutex_lock(&CLIENT_VECTOR);
        myConnection->status = OFFLINE;
    pthread_mutex_unlock(&CLIENT_VECTOR);
   
     if (myConnection->sock != -1){
        pthread_mutex_lock(&CLIENT_VECTOR);
           close(myConnection->sock);
        pthread_mutex_unlock(&CLIENT_VECTOR);
        cleanPendingMessages(myConnection->sock);
      }
      
   pthread_mutex_lock(&CONNECTION_VECTOR);
	v_connections[myConnection->diaServerConnection].numberOfClients--;
   pthread_mutex_unlock(&CONNECTION_VECTOR);
   
   pthread_mutex_lock(&CLIENT_VECTOR);
	myConnection->waitingAnswer = false;
	myConnection->sock = -1;
	myConnection->clientThreadID = 0;
	myConnection->diaServerConnection = -1;
    pthread_mutex_unlock(&CLIENT_VECTOR);
        

    std::vector<int>::iterator pos;
    pthread_mutex_lock(&CLIENT_THREAD_VECTOR);
        pos = find (myClient->conectionClients.begin(),myClient->conectionClients.end(), myConnection->pos);
        if (pos != myClient->conectionClients.end()){
            myClient->conectionClients.erase(pos);
        }
        myConnection->pos = -1;

        FD_ZERO(&myClient->fds);
        myClient->maxFd = 0;
    pthread_mutex_unlock(&CLIENT_THREAD_VECTOR);
    
    for (unsigned int index = 0; index < myClient->conectionClients.size(); index++){
        pthread_mutex_lock(&CLIENT_VECTOR);
	    int sock = v_client[myClient->conectionClients[index]].sock;
        pthread_mutex_unlock(&CLIENT_VECTOR);
        
        pthread_mutex_lock(&CLIENT_THREAD_VECTOR);
            FD_SET(sock, &myClient->fds);
            if (sock > myClient->maxFd)
                myClient->maxFd = sock + 1;
        pthread_mutex_unlock(&CLIENT_THREAD_VECTOR);
    }
}

void resetAndExit (clientThread *myClient)
{
    
    for (unsigned int index = 0; index < myClient->conectionClients.size(); index++){
        closeClient(myClient,&v_client[myClient->conectionClients[index]]);
    }

    pthread_mutex_lock(&CLIENT_THREAD_VECTOR);
        FD_ZERO(&myClient->fds);
        myClient->maxFd = -1;
        myClient->clientThreadID = 0;
        myClient->conectionClients.clear();
    pthread_mutex_unlock(&CLIENT_THREAD_VECTOR);
    
    pthread_mutex_lock(&TOOL_STATUS);
        numberClientThreads--;
    pthread_mutex_unlock(&TOOL_STATUS);
    
    pthread_exit(0);
}

               
int findTransaction()
{
	int index;
	unsigned int searches = 1;

	do {
            pthread_mutex_lock(&TRANSACTION_VECTOR);
                TransactionStatus status = v_transaction[nextTransaction].status;
            
	    if (status == NOTUSED) {

	        v_transaction[nextTransaction].status = USED;

	        index = nextTransaction;
                        
	        if (nextTransaction < v_transaction.size() -1)	nextTransaction++;
		else nextTransaction = 0;
                
		pthread_mutex_unlock(&TRANSACTION_VECTOR);
                return index;
	    }
	    else {
	        searches++;
		if (searches > v_transaction.size()){
                    pthread_mutex_unlock(&TRANSACTION_VECTOR);
                    return -1;
                }
		else {
		    if (nextTransaction < v_transaction.size() -1)	nextTransaction++;
		    else nextTransaction = 0;
                }
	    }
            pthread_mutex_unlock(&TRANSACTION_VECTOR);
	} while (true);
}                

int findSocketsWithPendingMessages(fd_set * fd_write, clientThread * myClient)
{
 
    std::map <int, MessageToSendDeque>::iterator pendingToSendMapIter;
    FD_ZERO(fd_write);
    int socket=0, maxFd=0;
    for (unsigned int index=0; index < myClient->conectionClients.size();index++) {
    
        pthread_mutex_lock(&CONNECTION_VECTOR);
            socket = v_client[myClient->conectionClients[index]].sock;
        pthread_mutex_unlock(&CONNECTION_VECTOR);
        
        pthread_mutex_lock(&PENDING_MESSAGE_MAP);
            pendingToSendMapIter = m_pendingToSend.find(socket);
        pthread_mutex_unlock(&PENDING_MESSAGE_MAP);
        
        if ( ! (pendingToSendMapIter == m_pendingToSend.end())) {
        
            pthread_mutex_lock(&PENDING_MESSAGE_MAP);
                bool empty = pendingToSendMapIter->second.empty();
            pthread_mutex_unlock(&PENDING_MESSAGE_MAP);
            if (not empty){
                FD_SET(socket, fd_write);
                if (socket >= maxFd)
		    maxFd = socket + 1;        
            }
        }
    
    }
    return maxFd;
}


bool sendPendingMessage(int socket)
{
    int res_sending = 0;
    stringstream logString;
    int errsv;
    bool keep_sending = true;
    std::map <int, MessageToSendDeque>::iterator pendingToSendMapIter;

    pthread_mutex_lock(&PENDING_MESSAGE_MAP);
        pendingToSendMapIter = m_pendingToSend.find(socket);
    pthread_mutex_unlock(&PENDING_MESSAGE_MAP);

    if ( ! (pendingToSendMapIter == m_pendingToSend.end())) {

        pthread_mutex_lock(&PENDING_MESSAGE_MAP);
            bool empty = pendingToSendMapIter->second.empty();
        pthread_mutex_unlock(&PENDING_MESSAGE_MAP);

        while (not empty && keep_sending){

            pthread_mutex_lock(&PENDING_MESSAGE_MAP);
                struct Message message = pendingToSendMapIter->second.front();
            pthread_mutex_unlock(&PENDING_MESSAGE_MAP);

            if (message.message_len > 0){
                res_sending = send(socket,
                                (const char*)(message.buffer + message.bytes_sent),
                                message.message_len - message.bytes_sent, 0);
                errsv = errno;
                if ( res_sending == message.message_len-message.bytes_sent ||
                        res_sending == -1 ||
                        (res_sending == 0 && errno==0)) {

#ifdef _DIA_PROXY_MONITOR
                    pthread_mutex_lock(&STATISTIC);
                        switch( message.message_type){
                            case REQUEST_TO_SERVER:
                                if (res_sending > 0 ||(res_sending == 0 && errno==0)){
                                       v_connections[message.diaServerConnection].requestSentToServer++ ;
                                       if (cer_data.DiaErrCounters_report_running) {v_connections[message.diaServerConnection].request_Sent++ ;}
                                       if (cer_data. latency_report_running) {clock_gettime(CLOCK_MONOTONIC, &(v_transaction[message.transaction].request_time));}
                            	}
                                else                v_connections[message.diaServerConnection].requestDiscardFromClient++ ;
                                break;
                             case REQUEST_TO_CLIENT:
                                if (res_sending > 0 ||(res_sending == 0 && errno==0))    v_connections[message.diaServerConnection].requestSentToClient++ ;
                                else                v_connections[message.diaServerConnection].requestDiscardFromServer++ ;
                                break;
                            case ANSWER_TO_SERVER:
                                if (res_sending > 0 ||(res_sending == 0 && errno==0))    v_connections[message.diaServerConnection].answerSentToServer++ ;
                                else                v_connections[message.diaServerConnection].answerDiscardFromClient++ ;
                                break;
                            case ANSWER_TO_CLIENT:
                                if (res_sending > 0 ||(res_sending == 0 && errno==0))    v_connections[message.diaServerConnection].answerSentToClient++ ;
                                else                v_connections[message.diaServerConnection].answerDiscardFromServer++ ;
                                break;
                        }
                    pthread_mutex_unlock(&STATISTIC);
#endif
                    if (res_sending == -1 ) {
                        if (errsv == EAGAIN) {
                                return true;
                        }
                        else {
                            logString.clear();
                            logString.str("");
                            logString << "(sendPendingMessage) Error in socket "<< socket <<" : "<<  strerror(errsv)<< endl;
                            LOG(CONNECTIONS, logString.str());
                            if (message.message_type == REQUEST_TO_SERVER || message.message_type == ANSWER_TO_SERVER){
                                pthread_mutex_lock(&CONNECTION_VECTOR);
                                    v_connections[message.diaServerConnection].status = BROKEN;
                                pthread_mutex_unlock(&CONNECTION_VECTOR);
                            }
                            keep_sending = false;
                        }
                    }
                    pthread_mutex_lock(&PENDING_MESSAGE_MAP);
                        delete [] message.buffer;                        
                        pendingToSendMapIter->second.pop_front();
                    pthread_mutex_unlock(&PENDING_MESSAGE_MAP);
                }
                else  {
                        pendingToSendMapIter->second.front().bytes_sent += res_sending;
                        keep_sending = false;
                }
            }
            pthread_mutex_lock(&PENDING_MESSAGE_MAP);
                empty = pendingToSendMapIter->second.empty();
            pthread_mutex_unlock(&PENDING_MESSAGE_MAP);
        }// end while
    }

    return   res_sending>0?true:false;    
 }

 
bool addMessageAsPending(int socket, struct Message message)
{
   static unsigned int sample = 0;
   stringstream logString;

   bool result = false;
    
    std::map <int, MessageToSendDeque>::iterator pendingToSendMapIter;
    pthread_mutex_lock(&PENDING_MESSAGE_MAP);
        pendingToSendMapIter = m_pendingToSend.find(socket);
    pthread_mutex_unlock(&PENDING_MESSAGE_MAP);
    
    if ( ! (pendingToSendMapIter == m_pendingToSend.end())) {
        pthread_mutex_lock(&PENDING_MESSAGE_MAP);
            int size = pendingToSendMapIter->second.size();
        pthread_mutex_unlock(&PENDING_MESSAGE_MAP);


// sample++;
// if (socket==5){
//     if (sample++>1000) {
//         sample = 0;
//         printf ("WARNING:  (%d) pending to be sent for socket %d\n",size, socket);
//     }
// }

        if(size > cer_data.max_size_message_queue){

#ifdef _DIA_PROXY_MONITOR
            pthread_mutex_lock(&STATISTIC);
                        switch( message.message_type){
                            case REQUEST_TO_SERVER:
                                    v_connections[message.diaServerConnection].requestDiscardFromClient++ ;
                                break;
                             case REQUEST_TO_CLIENT:
                                    v_connections[message.diaServerConnection].requestDiscardFromServer++ ;
                                break;
                            case ANSWER_TO_SERVER:
                                    v_connections[message.diaServerConnection].answerDiscardFromClient++ ;
                                break;
                            case ANSWER_TO_CLIENT:
                                    v_connections[message.diaServerConnection].answerDiscardFromServer++ ;
                                break;
                        }
            pthread_mutex_unlock(&STATISTIC);
#endif

            logString.clear();
            logString.str("");
            logString << "(addMessageAsPending) Message discarded. TOO MANY MESSAGES ( "<< size <<") pending to be sent for socket "<<  socket <<endl;
            LOG(CONNECTIONS, logString.str());

 //           discardPendingMessages(socket,size/2);

        }
        else {
            pthread_mutex_lock(&PENDING_MESSAGE_MAP);
                pendingToSendMapIter->second.push_back(message);
            pthread_mutex_unlock(&PENDING_MESSAGE_MAP);
            result = true;
        }
    }
    return result; 
}

void discardPendingMessages(int socket, int nofmessages)
{
    stringstream logString;
    std::map <int, MessageToSendDeque>::iterator pendingToSendMapIter;
    struct Message message;
    pthread_mutex_lock(&PENDING_MESSAGE_MAP);
        pendingToSendMapIter = m_pendingToSend.find(socket);
    pthread_mutex_unlock(&PENDING_MESSAGE_MAP);

    if ( ! (pendingToSendMapIter == m_pendingToSend.end())) {

        logString.clear();
        logString.str("");
        logString << "(discardPendingMessages) Discarding "<< nofmessages <<" pending messages to be sent for socket "<<  socket <<endl;
        LOG(CONNECTIONS, logString.str());
        
        for (int counter = 0; counter < nofmessages; counter++){
            
            pthread_mutex_lock(&PENDING_MESSAGE_MAP);
                message= pendingToSendMapIter->second.front();
                delete [] message.buffer;
                pendingToSendMapIter->second.pop_front();
            pthread_mutex_unlock(&PENDING_MESSAGE_MAP);

            if (message.transaction > -1 && message.transaction < v_transaction.size())
                pthread_mutex_lock(&TRANSACTION_VECTOR);
                    v_transaction[message.transaction].status = NOTUSED;
                    v_transaction[message.transaction].request_time.tv_sec = 0;
                pthread_mutex_unlock(&TRANSACTION_VECTOR);

            
#ifdef _DIA_PROXY_MONITOR					
                pthread_mutex_lock(&STATISTIC);
                        switch( message.message_type){
                            case REQUEST_TO_SERVER:
                                v_connections[message.diaServerConnection].requestDiscardFromClient++ ;
                                break;
                            case REQUEST_TO_CLIENT:
                                v_connections[message.diaServerConnection].requestDiscardFromServer++ ;
                                break;
                            case ANSWER_TO_SERVER:
                                v_connections[message.diaServerConnection].answerDiscardFromClient++ ;
                                break;
                            case ANSWER_TO_CLIENT:
                                v_connections[message.diaServerConnection].answerDiscardFromServer++ ;
                                break;
                        }
                pthread_mutex_unlock(&STATISTIC);
#endif

            }
        }
}


void cleanPendingMessages(int socket)
{
    std::map <int, MessageToSendDeque>::iterator pendingToSendMapIter;
    struct Message message;
    pthread_mutex_lock(&PENDING_MESSAGE_MAP);
        pendingToSendMapIter = m_pendingToSend.find(socket);
    pthread_mutex_unlock(&PENDING_MESSAGE_MAP);

    if ( ! (pendingToSendMapIter == m_pendingToSend.end())) {

        MessageToSendDeque queueToRemove = MessageToSendDeque();
            
        pthread_mutex_lock(&PENDING_MESSAGE_MAP);
            queueToRemove.swap(pendingToSendMapIter->second);
            m_pendingToSend.erase(pendingToSendMapIter);
        pthread_mutex_unlock(&PENDING_MESSAGE_MAP);
            
            
        while (! (queueToRemove.empty())){
                    message= queueToRemove.front();
                    if (message.transaction > -1 && message.transaction < v_transaction.size())
                    pthread_mutex_lock(&TRANSACTION_VECTOR);
                        v_transaction[message.transaction].status = NOTUSED;
                        v_transaction[message.transaction].request_time.tv_sec = 0;
                    pthread_mutex_unlock(&TRANSACTION_VECTOR);
                    delete [] message.buffer;
                    queueToRemove.pop_front();
#ifdef _DIA_PROXY_MONITOR                   
            pthread_mutex_lock(&STATISTIC);
                    switch( message.message_type){
                        case REQUEST_TO_SERVER:
                            v_connections[message.diaServerConnection].requestDiscardFromClient++ ;
                            break;
                        case REQUEST_TO_CLIENT:
                            v_connections[message.diaServerConnection].requestDiscardFromServer++ ;
                            break;
                        case ANSWER_TO_SERVER:
                            v_connections[message.diaServerConnection].answerDiscardFromClient++ ;
                            break;
                        case ANSWER_TO_CLIENT:
                            v_connections[message.diaServerConnection].answerDiscardFromServer++ ;
                            break;
                    }
            pthread_mutex_unlock(&STATISTIC);
#endif
            }
    }       
}
