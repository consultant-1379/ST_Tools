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

#include "cnDiaProxy.h"
#include "ClientThread.h"

/*** Declaration of these global variables to be found in the main module ***/
extern pthread_t ListenerThreadID;
extern pthread_t SignalThreadID;
extern bool haveToExit;

extern time_t start, stop, lastaction;
extern applicationData dataTool;

//variable for defining/handling a mutual exclusion zone
extern pthread_mutex_t TRANSACTION_VECTOR;
extern pthread_mutex_t CONNECTION_VECTOR;
extern pthread_mutex_t CLIENT_VECTOR;
extern pthread_mutex_t CLIENT_THREAD_VECTOR;
extern pthread_mutex_t SESSION_MAP;
extern pthread_mutex_t PENDING_MESSAGE_MAP;
extern pthread_mutex_t TOOL_STATUS;
extern pthread_mutex_t STATISTIC;
extern SignalReason sigReason;

extern std::vector<DiaServerConnection> v_connections;
extern std::vector<ClientConnection> v_client;
extern std::vector<Transaction> v_transaction;
extern std::vector<clientThread> v_clientThread;


extern unsigned int nextTransaction;
extern unsigned int numberClientThreads;
extern unsigned int nextConnection;
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
    DIAMETER_HEADER *head;
    puchar pbuf;
    int received;

    struct ClientConnection * currentClient;
    int lastConnectionClient = -1;
    int eventCounter;
    uchar temp_buff[DEFAULT_BUFFER_SIZE];
    bool more_messages ;
    stringstream logString;
    int timeout_msecs = 100;
    int fd_index = -1;
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

        for (int index =0; index < myClient->nfds; index++ ){
            myClient->fds[index].events = (myClient->fds[index].fd != -1) ? POLLIN : 0;
            myClient->fds[index].revents = 0;
        }

        findSocketsWithPendingMessages(myClient);

        eventCounter = poll(myClient->fds, myClient->nfds, timeout_msecs);
        if (eventCounter <=0)     continue;

        for (unsigned int index = 0; (index < myClient->conectionClients.size()) && (eventCounter > 0); index++){
#ifdef _DIA_PROXY_DEBUG
            logString.clear();
            logString.str("");
            logString << "(ClientThread:" << myClient->clientThreadID << "): Poll eventCounter " << eventCounter<<endl;
            LOG(DEBUG, logString.str());
#endif

            if (lastConnectionClient < (int) myClient->conectionClients.size() - 1) lastConnectionClient++;
            else  lastConnectionClient = 0;

            currentClient = &v_client[myClient->conectionClients[lastConnectionClient]];

            if(currentClient->sock == -1){
                closeClient (myClient, currentClient);
                continue;
            }

#ifdef _DIA_PROXY_DEBUG
            logString.clear();
            logString.str("");
            logString << "(Client:" << currentClient->pos << "): revents for fd_index " << currentClient->fd_index <<" is " << myClient->fds[currentClient->fd_index].revents<<endl;
            LOG(DEBUG, logString.str());
#endif


            if(currentClient->fd_index != -1 && (myClient->fds[currentClient->fd_index].revents & POLLOUT)){
#ifdef _DIA_PROXY_DEBUG
                logString.clear();
                logString.str("");
                logString << "(Client:" << currentClient->pos << "): Send event for fd_index " << currentClient->fd_index  <<endl;
                LOG(DEBUG, logString.str());
#endif
                sendPendingMessage(currentClient->net_con);
#ifdef _DIA_PROXY_DEBUG
                logString.clear();
                logString.str("");
                logString << "(Client:" << currentClient->pos << "): Message sent with fd_index " << currentClient->fd_index  <<endl;
                LOG(DEBUG, logString.str());
#endif
                eventCounter--;
            }


            if(currentClient->fd_index != -1 && (myClient->fds[currentClient->fd_index].revents & POLLIN)){
#ifdef _DIA_PROXY_DEBUG
                logString.clear();
                logString.str("");
                logString << "(Client:" << currentClient->pos << "): Read event for fd_index " << currentClient->fd_index  <<endl;
                LOG(DEBUG, logString.str());
#endif
                if (currentClient->received == 0) {
                    memset(temp_buff,0,DEFAULT_BUFFER_SIZE);
                    pbuf = temp_buff;
                }
                else {
                    memcpy(temp_buff, currentClient->client_buff, currentClient->received);
                    pbuf = temp_buff + currentClient->received;
                }

                eventCounter--;
                int pending = DEFAULT_BUFFER_SIZE - currentClient->received;
                received = currentClient->net_con->client_read((LPTSTR)pbuf,DEFAULT_BUFFER_SIZE - currentClient->received);
#ifdef _DIA_PROXY_DEBUG
                    logString.clear();
                    logString.str("");
                    logString << "(Client:" << currentClient->pos << "): pending "<< pending << " received " << received <<endl;
                    LOG(DEBUG, logString.str());
#endif

                time(&lastaction);	//for inactivity monitoring, the lastaction time is updated

                if(received == -1){
                    logString.clear();
                    logString.str("");
                    logString << "(Client:" << currentClient->pos << "): Broken pipe with TTCN client ";
                    logString << currentClient->net_con->get_remote_peer_str() <<endl;
                    LOG(CONNECTIONS, logString.str());

                    closeClient (myClient, currentClient);
                    continue;
                }
                if(received == 0){
                    logString.clear();
                    logString.str("");
                    logString << "(Client:" << currentClient->pos << "): Closed connection by TTCN client ";
                    logString << currentClient->net_con->get_remote_peer_str() <<endl;
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
                    logString << "(Client:" << currentClient->pos << "): Message received from TTCN in socket "<< currentClient->sock <<endl;
                    LOG(DEBUG, logString.str());
#endif
                    uint app_id = (head->cmd_code[3]<<24) + (head->cmd_code[4]<<16) + (head->cmd_code[5]<<8) + head->cmd_code[6];

                    pthread_mutex_lock(&CONNECTION_VECTOR);
                        int conFound = findConnection(app_id);
                    pthread_mutex_unlock(&CONNECTION_VECTOR);

                    if (conFound == -1) {
                        if(find(dataTool.all_appids.begin(), dataTool.all_appids.end(), app_id) == dataTool.all_appids.end()) {
                            logString.clear();
                            logString.str("");
                            logString << "(Client:" << currentClient->pos << "): Not connection to Diameter server configured for "<< app_id <<endl;
                            LOG(ERROR, logString.str());

                            pthread_mutex_lock(&TOOL_STATUS);
                                sigReason = DIA__CONF__ERROR;
                            pthread_mutex_unlock(&TOOL_STATUS);

                            pthread_kill(SignalThreadID ,SIGUSR1);

                            resetAndExit (myClient);

                        }

#ifdef _DIA_PROXY_MONITOR
                        pthread_mutex_lock(&STATISTIC);
                            v_connections[currentClient->diaServerConnection].requestDiscardFromClient++;
                        pthread_mutex_unlock(&STATISTIC);
#endif
                        break;

                    }
                    currentClient->diaServerConnection = conFound;

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

                    head->end2end = ((currentClient->pos+1) * 1000000) + (dataTool.e2e_seed * 10000) + counter_e2e;
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

                        inserted = addMessageAsPending(v_connections[currentClient->diaServerConnection].net_con->get_fd(), message);

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

#ifdef _DIA_PROXY_DEBUG
                        logString.clear();
                        logString.str("");
                        logString << "(Client:" << currentClient->pos << "): Insert pending message for socket " <<  v_connections[currentClient->diaServerConnection].net_con->get_fd();
                        logString << " from fd_index " << currentClient->fd_index <<endl;
                        LOG(DEBUG, logString.str());
#endif
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

                } while (more_messages);

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

    if (myConnection->net_con){
        pthread_mutex_lock(&CLIENT_VECTOR);
            delete myConnection->net_con;
            myConnection->net_con = NULL;
        pthread_mutex_unlock(&CLIENT_VECTOR);

        cleanPendingMessages(myConnection->sock);
    }

    pthread_mutex_lock(&CONNECTION_VECTOR);
        dataTool.activeTTCNConnections--;
    pthread_mutex_unlock(&CONNECTION_VECTOR);
    int sock_bk;
    pthread_mutex_lock(&CLIENT_VECTOR);
        myConnection->waitingAnswer = false;
        sock_bk = myConnection->sock;
        myConnection->sock = -1;
        myConnection->fd_index = -1;
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

    pthread_mutex_unlock(&CLIENT_THREAD_VECTOR);
}

void resetAndExit (clientThread *myClient)
{
    for (unsigned int index = 0; index < myClient->conectionClients.size(); index++){
        closeClient(myClient,&v_client[myClient->conectionClients[index]]);
    }

    pthread_mutex_lock(&CLIENT_THREAD_VECTOR);
        myClient->clientThreadID = 0;
        myClient->nfds = 0;
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

void findSocketsWithPendingMessages(clientThread * myClient)
{
    std::map <int, MessageToSendDeque>::iterator pendingToSendMapIter;
    int socket=0;
    int fd_index=-1;
    for (unsigned int index=0; index < myClient->conectionClients.size();index++) {

        pthread_mutex_lock(&CONNECTION_VECTOR);
            socket = v_client[myClient->conectionClients[index]].sock;
            fd_index = v_client[myClient->conectionClients[index]].fd_index;
        pthread_mutex_unlock(&CONNECTION_VECTOR);

        pthread_mutex_lock(&PENDING_MESSAGE_MAP);
            pendingToSendMapIter = m_pendingToSend.find(socket);
        pthread_mutex_unlock(&PENDING_MESSAGE_MAP);

        if ( ! (pendingToSendMapIter == m_pendingToSend.end())) {

            pthread_mutex_lock(&PENDING_MESSAGE_MAP);
                bool empty = pendingToSendMapIter->second.empty();
            pthread_mutex_unlock(&PENDING_MESSAGE_MAP);
            if (not empty){
                myClient->fds[fd_index].events = myClient->fds[fd_index].events | POLLOUT;
            }
        }
    }
}


bool sendPendingMessage(NetworkConnection *net_con)
{
    stringstream logString;
    int socket = net_con->get_fd();
    int res_sending = 0;
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

                     res_sending = net_con->client_write((const char*)(message.buffer + message.bytes_sent),
                                                         message.message_len - message.bytes_sent);

#ifdef _DIA_PROXY_DEBUG
                    logString.clear();
                    logString.str("");
                    logString << "(sendPendingMessage): Bytes sent for "<<socket<< " socket :" << res_sending << endl;
                    LOG(DEBUG, logString.str());
#endif
                     errsv = net_con->get_errsv();;

                    if ( res_sending == message.message_len-message.bytes_sent ||
                         res_sending == -1 ||
                         (res_sending == 0 && errno==0)) {

#ifdef _DIA_PROXY_MONITOR	
            pthread_mutex_lock(&STATISTIC);
                        switch( message.message_type){
                            case REQUEST_TO_SERVER:
                                if (res_sending > 0 ||(res_sending == 0 && errno==0)){
                                       v_connections[message.diaServerConnection].requestSentToServer++ ;
                                       if (dataTool.DiaErrCounters_report_running) {v_connections[message.diaServerConnection].request_Sent++ ;}
                                       if (dataTool. latency_report_running) {clock_gettime(CLOCK_MONOTONIC, &(v_transaction[message.transaction].request_time));}
                            	}

                                else                v_connections[message.diaServerConnection].requestDiscardFromClient++ ;
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
                                printf("(sendPendingMessage) Error %d in socket %d: %s\n",errsv, socket, strerror(errsv));
                                pthread_mutex_lock(&CONNECTION_VECTOR);
                                    v_connections[message.diaServerConnection].status = BROKEN;
                                pthread_mutex_unlock(&CONNECTION_VECTOR);
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



int findConnection(uint app_id)
{
    int index = nextConnection;
    unsigned int searches = 1;

    do {
        ConnectionStatus status = v_connections[index].status;
        std::vector<int> v_appids = v_connections[index].vendor_specific_application;

        if((std::find(v_appids.begin(), v_appids.end(), app_id) != v_appids.end()) && status == CONNECTED) {
            if (index < v_connections.size() -1)   nextConnection= index + 1;
            else nextConnection = 0;

            return index;

        }
        else {
            searches++;
            if (searches > v_connections.size())    return -1;
            else                    index++;
        }
    } while (true);
}


bool addMessageAsPending(int socket, struct Message message)
{
    bool result = false;

    std::map <int, MessageToSendDeque>::iterator pendingToSendMapIter;
    pthread_mutex_lock(&PENDING_MESSAGE_MAP);
        pendingToSendMapIter = m_pendingToSend.find(socket);
    pthread_mutex_unlock(&PENDING_MESSAGE_MAP);

    if ( ! (pendingToSendMapIter == m_pendingToSend.end())) {
        pthread_mutex_lock(&PENDING_MESSAGE_MAP);
            int size = pendingToSendMapIter->second.size();
        pthread_mutex_unlock(&PENDING_MESSAGE_MAP);

        if(size > dataTool.max_size_message_queue){

#ifdef _DIA_PROXY_MONITOR					
            pthread_mutex_lock(&STATISTIC);
                switch( message.message_type){
                    case REQUEST_TO_SERVER:
                            v_connections[message.diaServerConnection].requestDiscardFromClient++ ;
                        break;
                    case ANSWER_TO_CLIENT:
                            v_connections[message.diaServerConnection].answerDiscardFromServer++ ;
                        break;
                }
            pthread_mutex_unlock(&STATISTIC);
#endif

            printf ("WARNING: Message discarded. TOO MANY MESSAGES (%d) pending to be sent for socket %d.\n\n",
                         size, socket);

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
        pthread_mutex_unlock(&PENDING_MESSAGE_MAP);
            
            
        while (! (queueToRemove.empty())){
                    message= queueToRemove.front();
                    queueToRemove.pop_front();
                    if (message.transaction > -1 && message.transaction < v_transaction.size())
                    pthread_mutex_lock(&TRANSACTION_VECTOR);
                        v_transaction[message.transaction].status = NOTUSED;
                        v_transaction[message.transaction].request_time.tv_sec = 0;
                    pthread_mutex_unlock(&TRANSACTION_VECTOR);
                    delete [] message.buffer;
#ifdef _DIA_PROXY_MONITOR					
            pthread_mutex_lock(&STATISTIC);
                    switch( message.message_type){
                        case REQUEST_TO_SERVER:
                            v_connections[message.diaServerConnection].requestDiscardFromClient++ ;
                            break;
                        case ANSWER_TO_CLIENT:
                            v_connections[message.diaServerConnection].answerDiscardFromServer++ ;
                            break;
                    }
            pthread_mutex_unlock(&STATISTIC);
#endif
            }
            pthread_mutex_lock(&PENDING_MESSAGE_MAP);
                m_pendingToSend.erase(pendingToSendMapIter);
            pthread_mutex_unlock(&PENDING_MESSAGE_MAP);
    }       
}
