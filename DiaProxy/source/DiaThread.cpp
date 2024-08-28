//==============================================================================
//#****h* src/DiaThread.cpp
//# MODULE
//#   DiaProxy.capp
//#
//# AUTHOR    
//#   TV 
//#
//# VERSION
//#   2.0
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
//#   Jose Manuel Santos		2006/01/10    Adding the support for PNR messages
//#******
//==============================================================================
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <signal.h>
#include <pthread.h>

#include <sys/types.h>
#include <sys/ioctl.h>
#include <netinet/in.h>

#include <sys/socket.h>
#include <netinet/tcp.h>
#include <net/if.h>
#include <stropts.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <unistd.h>
#include <netdb.h>
#include <sys/timeb.h>
#include <sys/time.h>
#include <vector>
#include <map>

#include "DiaThread.h"
#include "ClientThread.h"
#include "DiaMessage.h"
#include "Logger.h"

#include <unistd.h>
#include <fcntl.h>

extern time_t start, stop, lastaction;
extern CER_DATA cer_data;
extern pthread_t ProxyThreadID;
extern pthread_t SignalThreadID;
extern SignalReason sigReason;
extern bool haveToExit;
//extern char diameter_host[20];
extern int local_port;
//extern int server_port;

//variable for defining/handling a mutual exclusion zone
extern pthread_mutex_t TRANSACTION_VECTOR;
extern pthread_mutex_t CONNECTION_VECTOR;
extern pthread_mutex_t CLIENT_VECTOR;
extern pthread_mutex_t SESSION_MAP;
extern pthread_mutex_t PENDING_MESSAGE_MAP;
extern pthread_mutex_t TOOL_STATUS;
extern pthread_mutex_t STATISTIC;
extern pthread_mutex_t REPORT;



extern std::vector<DiaServerConnection> v_connections;
extern std::vector<ClientConnection> v_client;
extern std::vector<Transaction> v_transaction;
extern std::map<std::string, Session> m_session;
extern DiaProxyStatus diaProxyState;
extern PendingToSendMap  m_pendingToSend;

extern unsigned int nextClient;
using namespace std;

int findUsedClient()
{
    int result = findUsedClientWaitingAnswer();
        
        if (result != -1){
                return result;
        }
                
    int index;
    unsigned int searches = 1;

    do {
        
            pthread_mutex_lock(&CLIENT_VECTOR);
                ClientStatus status = v_client[nextClient].status;
            pthread_mutex_unlock(&CLIENT_VECTOR);                                
        
        if (status == ONLINE) {
                        
                        index = nextClient;

            if (nextClient < v_client.size() -1)	nextClient++;
            else nextClient = 0;
            
            return index;
            
        }
        else {
            searches++;
            if (searches > v_client.size()){
                                return -1;
                        }
            else {
                if (nextClient < v_client.size() -1)	nextClient++;
                else nextClient = 0;
                        }
        }
    } while (true);
}

int findUsedClientWaitingAnswer()
{
        int index;
    unsigned int searches = 1;

    do {
            pthread_mutex_lock(&CLIENT_VECTOR);
                ClientStatus status = v_client[nextClient].status;
                bool waitingAnswer = v_client[nextClient].waitingAnswer;
            pthread_mutex_unlock(&CLIENT_VECTOR);
            
        if (status == ONLINE && waitingAnswer) {
                        
                index = nextClient;

        if (nextClient < v_client.size() -1)	nextClient++;
        else nextClient = 0;
            
        return index;
            
        }
        else {
            searches++;
            if (searches > v_client.size()){
                    return -1;
                }
        else {
            if (nextClient < v_client.size() -1)	nextClient++;
            else nextClient = 0;
                }
        }
            
    } while (true);
}

bool receive_CEA (DiaServerConnection *myConnection) 
{
    bool myHaveToExit;
    bool result = false;
    uchar buff[DEFAULT_BUFFER_SIZE];
    bool ok = false;
    stringstream logString;		
    DIAMETER_HEADER *head;
    AVP_HEADER *avphead;
    int received;
    struct timeval tv;
    int localSockId = myConnection->sockId;
    fd_set fds;
    FD_ZERO(&fds);
    FD_SET(localSockId, &fds);

    int read_retries=0;
    int rest;
    int toread;
    int dp_size;
    fd_set tmpset;
    puchar pbuf;

    while (true){

        pthread_mutex_lock(&TOOL_STATUS);
            myHaveToExit = haveToExit;
        pthread_mutex_unlock(&TOOL_STATUS);

        if(myHaveToExit){ 
            logString.clear();
            logString.str("");
            logString << "(DiaThread:" << myConnection->threadID << "): Terminating... "<<endl;
            LOG(EVENT, logString.str());

            resetAndExit (myConnection, OFF);
        }

        if (myConnection->status == BROKEN) {
            logString.clear();
            logString.str("");
            logString << "(DiaThread:" << myConnection->threadID << "): Connection broken waiting for CEA. Terminating... "<<endl;
            LOG(EVENT, logString.str());

            pthread_mutex_lock(&CONNECTION_VECTOR);
                myConnection->status = TOBECONNECTED;
            pthread_mutex_unlock(&CONNECTION_VECTOR);
            return result;
        } 

        tv.tv_sec = 2;
        tv.tv_usec = 0;
        tmpset = fds;
        int koll;
        koll = select(localSockId+1, &tmpset, NULL, NULL, &tv);

        if(FD_ISSET(localSockId, &tmpset)) { 
            memset(buff,0,DEFAULT_BUFFER_SIZE);
            received = recv(localSockId,(LPTSTR)buff,DIAMETER_HEADER_LENGTH,0);
            if(received < DIAMETER_HEADER_LENGTH) { 
                if(received < 1){ 
                    if(received == -1){ 
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Broken pipe with Diameter server waiting for CEA. Restarting"<<endl;
                        LOG(CONNECTIONS, logString.str());
                    } 
                    if(received == 0){ 
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Diameter server has closed the connection waiting for CEA. Restarting"<<endl;
                        LOG(CONNECTIONS, logString.str());
                    } 

                    sleep (cer_data.reconnectTime);

                    pthread_mutex_lock(&CONNECTION_VECTOR);
                        myConnection->status = TOBECONNECTED;
                    pthread_mutex_unlock(&CONNECTION_VECTOR);

                    return result;
                } 
                pbuf = buff;
                pbuf += received;
                toread = DIAMETER_HEADER_LENGTH - received;
                read_retries = 0;
                while(received < DIAMETER_HEADER_LENGTH) { 

                    pthread_mutex_lock(&TOOL_STATUS);
                        myHaveToExit = haveToExit;
                    pthread_mutex_unlock(&TOOL_STATUS);

                    if(myHaveToExit){ 
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Terminating... "<<endl;
                        LOG(EVENT, logString.str());

                        sleep (cer_data.reconnectTime);
                        resetAndExit (myConnection, OFF);
                    } 
                    if (myConnection->status == BROKEN) {
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Connection broken waiting for CEA. Terminating... "<<endl;
                        LOG(EVENT, logString.str());

                        sleep (cer_data.reconnectTime);

                        pthread_mutex_lock(&CONNECTION_VECTOR);
                            myConnection->status = TOBECONNECTED;
                        pthread_mutex_unlock(&CONNECTION_VECTOR);

                        return result;
                    } 
            
                    tmpset = fds;
                    tv.tv_sec = 2;
                    tv.tv_usec = 0;
                    select(localSockId+1, &tmpset, NULL, NULL, &tv);
                    if(FD_ISSET(localSockId, &tmpset)){ 
                        rest = recv(localSockId,(LPTSTR)pbuf,toread,0);
                        if(rest == -1){ 
                            logString.clear();
                            logString.str("");
                            logString << "(DiaThread:" << myConnection->threadID << "): Broken pipe with Diameter server waiting for CEA. Restarting"<<endl;
                            LOG(CONNECTIONS, logString.str());

                            sleep (cer_data.reconnectTime);

                            pthread_mutex_lock(&CONNECTION_VECTOR);
                                myConnection->status = TOBECONNECTED;
                            pthread_mutex_unlock(&CONNECTION_VECTOR);

                            return result;
                        } 
                        if(rest == 0){ 
                            logString.clear();
                            logString.str("");
                            logString << "(DiaThread:" << myConnection->threadID << "): Diameter server has closed the connection waiting for CEA. Restarting "<<endl;
                            LOG(CONNECTIONS, logString.str());

                            sleep (cer_data.reconnectTime);

                            pthread_mutex_lock(&CONNECTION_VECTOR);
                                myConnection->status = TOBECONNECTED;
                            pthread_mutex_unlock(&CONNECTION_VECTOR);

                            return result;
                        } 

                        toread -= rest;
                        received += rest;
                        pbuf += rest;
                    } 
                    else { 
                        read_retries++;
                        if(read_retries == 20){ 
                            logString.clear();
                            logString.str("");
                            logString << "(DiaThread:" << myConnection->threadID << "): Too many retries reading the compleate diameter packet. Restart..."<<endl;
                            LOG(CONNECTIONS, logString.str());

                            sleep (cer_data.reconnectTime);

                            pthread_mutex_lock(&CONNECTION_VECTOR);
                                myConnection->status = TOBECONNECTED;
                            pthread_mutex_unlock(&CONNECTION_VECTOR);

                            return result;

                        } 
                    } 
                } //while(received < DIAMETER_HEADER_LENGTH)
            } //if(received < DIAMETER_HEADER_LENGTH)
/////////////////////////////////////////////////////////////////////////////

            pbuf = buff;
            received = read_message_body (myConnection, 0, &pbuf,fds, &dp_size);
            if (myConnection->status != CONNECTING)   return false;

            head = (DIAMETER_HEADER*)buff;
            uint cmd_code = (head->cmd_code[0]<<16) + (head->cmd_code[1]<<8) + head->cmd_code[2];

            if(cmd_code == cmd__code__cer) {

                int offs = DIAMETER_HEADER_LENGTH;
                while(offs<dp_size){ 
                    avphead = (AVP_HEADER*)(buff+offs);
                    uint avplen = 0;
                    avplen = (avphead->avp_len[0] << 16) + (avphead->avp_len[1] << 8) + avphead->avp_len[2];
                    if(avphead->avp_code == result__code){ 
#ifdef _DIA_PROXY_DEBUG
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): CER-CEA Result code: "<< avphead->value <<endl;
                        LOG(DEBUG, logString.str());
#endif
                        if(avphead->value == result__diameter__success){
                            ok = true;
                            logString.clear();
                            logString.str("");
                            logString << "(DiaThread:" << myConnection->threadID << "): CER-CEA connection established with Diameter."<<endl;
                            LOG(CONNECTIONS, logString.str());
                        }
                        else {
                            ok = false;
                            uchar * ptr = (uchar *) &(avphead->value);
                            int errorCode = *(ptr);
                            errorCode = (errorCode << 8) + (*(ptr+1));
                            errorCode = (errorCode << 8) + (*(ptr+2));
                            errorCode = (errorCode << 8) + (*(ptr+3));

                            switch (avphead->value) {
                                case result__diameter__invalid__avp__length:
                                    logString.clear();
                                    logString.str("");
                                    logString << "(DiaThread:" << myConnection->threadID << "): CER-CEA ERROR. Result_code AVP value: DIAMETER_INVALID_AVP_LENGTH"<<endl;
                                    LOG(ERROR, logString.str());
                                    break;
                                case result__diameter__no_common__application:
                                    logString.clear();
                                    logString.str("");
                                    logString << "(DiaThread:" << myConnection->threadID << "): CER-CEA ERROR. Result_code AVP value: DIAMETER_NO_COMMON_APPLICATION"<<endl;
                                    LOG(ERROR, logString.str());
                                    break;
                                case result__diameter__invalid__avp__value:
                                    logString.clear();
                                    logString.str("");
                                    logString << "(DiaThread:" << myConnection->threadID << "): CER-CEA ERROR. Result_code AVP value: DIAMETER_INVALID_AVP_VALUE"<<endl;
                                    LOG(ERROR, logString.str());
                                    break;
                                case result__diameter__unable_to_comply:
                                    logString.clear();
                                    logString.str("");
                                    logString << "(DiaThread:" << myConnection->threadID << "): CER-CEA ERROR. Result_code AVP value: DIAMETER_UNABLE_TO_COMPLY"<<endl;
                                    LOG(ERROR, logString.str());
                                    break;
                                default:
                                    logString.clear();
                                    logString.str("");
                                    logString << "(DiaThread:" << myConnection->threadID << "): CER-CEA ERROR. Result_code AVP value: "<< errorCode <<endl;
                                    LOG(ERROR, logString.str());
                                    break;
                            } // end switch (avphead->value)
                        } 
                        break;
                    } //if(avp == result__code)
                    uint t = 0;
                    while(((avplen + t)*8) % 32){
                        t++;
                    }
                    offs += avplen + t;
                } //while(offs<received)


                if(!ok){
                    logString.clear();
                    logString.str("");
                    logString << "(DiaThread:" << myConnection->threadID << "): Error during CER-CEA process." <<endl;
                    LOG(ERROR, logString.str());

                    sleep (cer_data.reconnectTime);

                    pthread_mutex_lock(&CONNECTION_VECTOR);
                        myConnection->status = CONFIGURATIONERROR;
                    pthread_mutex_unlock(&CONNECTION_VECTOR);

                    return false;
                }
                return true;

            } // (cmd_code == cmd__code__cer)
            else {
                logString.clear();
                logString.str("");
                logString << "(DiaThread:" << myConnection->threadID << "): CEA not received. Restart..." <<endl;
                LOG(CONNECTIONS, logString.str());

                sleep (cer_data.reconnectTime);

                pthread_mutex_lock(&CONNECTION_VECTOR);
                    myConnection->status = TOBECONNECTED;
                pthread_mutex_unlock(&CONNECTION_VECTOR);
                return result;
            }

        } //if(FD_ISSET(diameter_sock, &tmpset))
        else{
            read_retries++;
            if(read_retries == 2){ 
                logString.clear();
                logString.str("");
                logString << "(DiaThread:" << myConnection->threadID << "): TIME OUT waiting for CEA. Restart..." <<endl;
                LOG(CONNECTIONS, logString.str());

                sleep (cer_data.reconnectTime);
                pthread_mutex_lock(&CONNECTION_VECTOR);
                    myConnection->status = TOBECONNECTED;
                pthread_mutex_unlock(&CONNECTION_VECTOR);
                return result;
            }
        }
    } //while(true)

    return true;
} 


int read_message_body (DiaServerConnection *myConnection, int bytes_to_read, puchar *p_head,fd_set fds, int *dp_size)
{
    int localSockId = myConnection->sockId;
    stringstream logString;
    bool myHaveToExit;
    int  errsv ;

    struct timeval tv;
    int received = -1;
    int rest = -1;
    puchar pbuf;
    DIAMETER_HEADER *l_head = (DIAMETER_HEADER*)(*p_head);
    int l_dp_size = (l_head->length[0]<<16) + (l_head->length[1]<<8) + l_head->length[2];
    int toread = l_dp_size - DIAMETER_HEADER_LENGTH;
    pbuf = (*p_head)+DIAMETER_HEADER_LENGTH;
    fd_set tmpset = fds;
    tv.tv_sec = 2;
    tv.tv_usec = 0;

    do {
        select(localSockId+1, &tmpset, NULL, NULL, &tv);

        pthread_mutex_lock(&TOOL_STATUS);
            myHaveToExit = haveToExit;
        pthread_mutex_unlock(&TOOL_STATUS);

        if(myHaveToExit){ 
            logString.clear();
            logString.str("");
            logString << "(DiaThread:" << myConnection->threadID << "): Terminating... " <<endl;
            LOG(EVENT, logString.str());

            resetAndExit (myConnection, OFF);
        }

        if (myConnection->status == BROKEN) {
            logString.clear();
            logString.str("");
            logString << "(DiaThread:" << myConnection->threadID << "): Broken pipe with Diameter server waiting for message body. Restarting... " <<endl;
            LOG(EVENT, logString.str());

            return -1;
        } 

    } while (!FD_ISSET(localSockId, &tmpset));

    if(FD_ISSET(localSockId, &tmpset)) {

        received = recv(localSockId,(LPTSTR)pbuf,toread,0);
        if(received < toread){ 
            pbuf += received;
            int toread1 = toread - received;
            while(received < toread) {
                pthread_mutex_lock(&TOOL_STATUS);
                    myHaveToExit = haveToExit;
                pthread_mutex_unlock(&TOOL_STATUS);

                if(myHaveToExit){ 
                    logString.clear();
                    logString.str("");
                    logString << "(DiaThread:" << myConnection->threadID << "): Terminating... " <<endl;
                    LOG(EVENT, logString.str());

                    resetAndExit (myConnection, OFF);
                } 
                if (myConnection->status == BROKEN) {
                    logString.clear();
                    logString.str("");
                    logString << "(DiaThread:" << myConnection->threadID << "): Broken pipe with Diameter server waiting for message body. Restarting ... " <<endl;
                    LOG(EVENT, logString.str());

                    return -1;
                } 

                tmpset = fds;
                tv.tv_sec = 2;
                tv.tv_usec = 0;
                select(localSockId+1, &tmpset, NULL, NULL, &tv);
                if(FD_ISSET(localSockId, &tmpset)) {
                    rest = recv(localSockId,(LPTSTR)pbuf,toread1,0);
                    errsv = errno;
                    if(rest < 1){ 
                        if(rest == -1){ 

                            logString.clear();
                            logString.str("");
                            logString << "(DiaThread:" << myConnection->threadID << "): Broken pipe from Diameter server waiting for message body. Restarting..." <<endl;
                            LOG(EVENT, logString.str());

                            pthread_mutex_lock(&CONNECTION_VECTOR);
                                myConnection->status = TOBECONNECTED;
                            pthread_mutex_unlock(&CONNECTION_VECTOR);
                            return -1;

                        } 
                        if(rest == 0) { 
                            logString.clear();
                            logString.str("");
                            logString << "(DiaThread:" << myConnection->threadID << "): Diameter server has closed the connection waiting for message body. Restarting..." <<endl;
                            LOG(EVENT, logString.str());

                            pthread_mutex_lock(&CONNECTION_VECTOR);
                                myConnection->status = TOBECONNECTED;
                            pthread_mutex_unlock(&CONNECTION_VECTOR);
                            return -1;
                        } //if(rest == 0)
                    } //if(rest < 1)
                    toread1 -= rest;
                    received += rest;
                    pbuf += rest;
                } //if(FD_ISSET(diameter_sock, &tmpset))
            } //while(received < toread)
        } //if(received < toread)
    } //if(FD_ISSET(diameter_sock, &tmpset))
    (*dp_size) = l_dp_size;

    return received;
}


void cleanDiaConnection (DiaServerConnection *myConnection)
{
    stringstream logString;
    logString.clear();
    logString.str("");
    logString << "(DiaThread:" << myConnection->threadID << "): Close and Clean data connection" <<endl;
    LOG(CONNECTIONS, logString.str());

    if (myConnection->sockId != -1){
        if (myConnection->status == CONNECTED){
            uchar dpr_msg[DEFAULT_BUFFER_SIZE];
            int dpr_len = createDPR(dpr_msg,&cer_data,myConnection);
            int res = send(myConnection->sockId,(const char*)dpr_msg,dpr_len,0);
            if (res == dpr_len){
                uchar buff[DEFAULT_BUFFER_SIZE];
                memset(buff,0,DEFAULT_BUFFER_SIZE);
                struct timeval tv;
                fd_set fds;
                FD_ZERO(&fds);
                FD_SET(myConnection->sockId, &fds);
                fd_set tmpset = fds;
                tv.tv_sec = 2;
                tv.tv_usec = 0;
                select(myConnection->sockId+1, &tmpset, NULL, NULL, &tv);
                if(FD_ISSET(myConnection->sockId, &tmpset)){
                    int received = recv(myConnection->sockId,(LPTSTR)buff,DIAMETER_HEADER_LENGTH,0);

                    DIAMETER_HEADER *head = (DIAMETER_HEADER*)buff;
                    //extracting the DIAMETER message length from the header
                    int toreceive = (head->length[0]<<16) + (head->length[1]<<8) + head->length[2];
                    received = recv(myConnection->sockId,(LPTSTR)buff,toreceive,0);
                }
            }
        }

        cleanPendingMessages(myConnection->sockId);

        pthread_mutex_lock(&CONNECTION_VECTOR);
            close(myConnection->sockId);
        pthread_mutex_unlock(&CONNECTION_VECTOR);
    }

    pthread_mutex_lock(&CONNECTION_VECTOR);
        myConnection->sockId = -1;
        myConnection->pendingWatchDog = 0;
    pthread_mutex_unlock(&CONNECTION_VECTOR);

}

void resetAndExit (DiaServerConnection *myConnection, ConnectionStatus status )
{

    cleanDiaConnection (myConnection);

    unsigned int numberOfRetries = myConnection->conexionRetries++;
    bool myHaveToExit = haveToExit;
    DiaProxyStatus myDiaProxyState = diaProxyState;

    if ((!myHaveToExit) && (myDiaProxyState == DIAPROXY_STARTING)) {
        pthread_mutex_lock(&TOOL_STATUS);
        myConnection->threadID = 0;
        myConnection->pendingWatchDog = 0;
        numberOfRetries = myConnection->conexionRetries++;
        pthread_mutex_unlock(&TOOL_STATUS);
        if(numberOfRetries < cer_data.maxReconnections) {
            sleep(2);
        } 
        else {
            pthread_mutex_lock(&TOOL_STATUS);
                myConnection->status = MAXCONEXIONREACHED;
                sigReason = DIA__CONRETRIES__REACHED;
            pthread_mutex_unlock(&TOOL_STATUS);

            pthread_kill(SignalThreadID ,SIGUSR1);
        }
    }

    pthread_exit(0);
}


void* _DiaThread(void *arg)
{ 
    DiaServerConnection	*myConnection = (DiaServerConnection *)arg;;
    int localSockId = -1;
    bool myHaveToExit;
    struct sockaddr_in diameter_addr;
    struct sockaddr_in6 diameter_addr_v6;
    struct sockaddr_in loc_addr;
    struct sockaddr_in6 loc_addr_v6;
    stringstream logString;

    pthread_mutex_lock(&TOOL_STATUS);
        myHaveToExit = haveToExit;
    pthread_mutex_unlock(&TOOL_STATUS);

    if (myHaveToExit)   pthread_exit(0);

    pthread_mutex_lock(&CONNECTION_VECTOR);
        myConnection->status = CONNECTING;
        myConnection->sockId = -1;
    pthread_mutex_unlock(&CONNECTION_VECTOR);

    uchar cer_msg[DEFAULT_BUFFER_SIZE];
    uchar buff[DEFAULT_BUFFER_SIZE];

    int cer_len = createCER(cer_msg,&cer_data,myConnection);
    int sock_result;
    int errsv;
    std::map <int, MessageToSendDeque>::iterator pendingToSendMapIter;
 
    long long value;
    struct timeval sendTimer;
    DIAMETER_HEADER *head;
    int received;
    fd_set fds;
    struct timeval tv;
    int read_retries=0;
    int rest;
    int toread;
    int dp_size;
    fd_set readfdset, writefdset;
    puchar pbuf;
    int wdrCount = 0;
    std::string cmd_code_str;
    bool  messageToSend ;

    while (true){
        switch (myConnection->status){
            case CONFIGURATIONERROR:
            case BROKEN:
            case TOBECONNECTED:{
                if (myConnection->firstConnectionTry) {
                    resetAndExit (myConnection, CONFIGURATIONERROR);
                }
                cleanDiaConnection (myConnection);
                pthread_mutex_lock(&CONNECTION_VECTOR);
                    myConnection->status = CONNECTING;
                pthread_mutex_unlock(&CONNECTION_VECTOR);

            }
            case CONNECTING: {
                pthread_mutex_lock(&CONNECTION_VECTOR);
                    if  (myConnection->type != SPECIFIC)
                        strcpy((char*)myConnection->diameter_server,(char*)cer_data.diameter_host);
                pthread_mutex_unlock(&CONNECTION_VECTOR);

                if (cer_data.ipv6) {
                    if(myConnection->use_sctp){
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): (IPv6) Trying to establish connection to Diameter server " ;
                        logString << myConnection->diameter_server << " : " <<myConnection->serv_port<< " using SCTP" <<endl;
                        LOG(CONNECTIONS, logString.str());

                        pthread_mutex_lock(&CONNECTION_VECTOR);
                            localSockId = socket(AF_INET6,SOCK_STREAM,IPPROTO_SCTP);
                        pthread_mutex_unlock(&CONNECTION_VECTOR);
                    }
                    else {
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): (IPv6) Trying to establish connection to Diameter server " ;
                        logString << myConnection->diameter_server << " : " <<myConnection->serv_port<< " using TCP" <<endl;
                        LOG(CONNECTIONS, logString.str());

                        pthread_mutex_lock(&CONNECTION_VECTOR);
                            localSockId = socket(AF_INET6,SOCK_STREAM,IPPROTO_TCP);
                        pthread_mutex_unlock(&CONNECTION_VECTOR);
                    }
                }
                else {  // IPv4
                    if(myConnection->use_sctp){
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): (IPv4) Trying to establish connection to Diameter server " ;
                        logString << myConnection->diameter_server << " : " <<myConnection->serv_port<< " using SCTP" <<endl;
                        LOG(CONNECTIONS, logString.str());

                        pthread_mutex_lock(&CONNECTION_VECTOR);
                            localSockId = socket(AF_INET,SOCK_STREAM,IPPROTO_SCTP);
                        pthread_mutex_unlock(&CONNECTION_VECTOR);
                    }
                    else {
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): (IPv4) Trying to establish connection to Diameter server " ;
                        logString << myConnection->diameter_server << " : " <<myConnection->serv_port<< " using TCP" <<endl;
                        LOG(CONNECTIONS, logString.str());

                        pthread_mutex_lock(&CONNECTION_VECTOR);
                            localSockId = socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
                        pthread_mutex_unlock(&CONNECTION_VECTOR);
                    }
                }

                if(localSockId == -1) { 
                    errsv = errno;
                    logString.clear();
                    logString.str("");
                    logString << "(DiaThread:" << myConnection->threadID << "): Failed to create socket" <<endl;
                    logString <<"\tError: " << strerror(errsv) << endl;
                    LOG(ERROR, logString.str());

                    sleep (cer_data.reconnectTime);
                    pthread_mutex_lock(&CONNECTION_VECTOR);
                        myConnection->status = TOBECONNECTED;
                    pthread_mutex_unlock(&CONNECTION_VECTOR);
                    break;
                } 

                if(localSockId > 1023) { 
                    errsv = errno;
                    logString.clear();
                    logString.str("");
                    logString << "(DiaThread:" << myConnection->threadID << "): Returned fd higher than 1023. Messages for this connection wont be processed." <<endl;
                    logString <<"\tError: " << strerror(errsv) << endl;
                    LOG(WARNING, logString.str());
                }

                sendTimer.tv_sec = DEFAULT_SEND_TIME;
                sendTimer.tv_usec = 0;

                if (setsockopt (localSockId, SOL_SOCKET, SO_SNDTIMEO, &sendTimer, sizeof (sendTimer))) {
                    errsv = errno;
                    logString.clear();
                    logString.str("");
                    logString << "(DiaThread:" << myConnection->threadID << "): Failed when changing SO_SNDTIMEO" <<endl;
                    logString <<"\tError: " << strerror(errsv) << endl;
                    LOG(ERROR, logString.str());

                    resetAndExit (myConnection, CONFIGURATIONERROR);
                }

                value = cer_data.socketbuffersize;
                if (setsockopt (localSockId, SOL_SOCKET, SO_RCVBUF, &value, sizeof (value))) {
                    errsv = errno;
                    logString.clear();
                    logString.str("");
                    logString << "(DiaThread:" << myConnection->threadID << "): Failed when changing SO_RCVBUF" <<endl;
                    logString <<"\tError: " << strerror(errsv) << endl;
                    LOG(ERROR, logString.str());

                    resetAndExit (myConnection, CONFIGURATIONERROR);
                }

                if (setsockopt (localSockId, SOL_SOCKET, SO_SNDBUF, &value, sizeof (value))) {
                    errsv = errno;
                    logString.clear();
                    logString.str("");
                    logString << "(DiaThread:" << myConnection->threadID << "): Failed when changing SO_SNDBUF" <<endl;
                    logString <<"\tError: " << strerror(errsv) << endl;
                    LOG(ERROR, logString.str());

                    resetAndExit (myConnection, CONFIGURATIONERROR);
                }

                if (cer_data.ipv6) {
                    memset(&diameter_addr_v6,0,sizeof(diameter_addr_v6));
                    diameter_addr_v6.sin6_family = AF_INET6;
                    diameter_addr_v6.sin6_port = htons(myConnection->serv_port);

                    if (inet_pton(AF_INET6,myConnection->diameter_server, &diameter_addr_v6.sin6_addr.s6_addr) !=1){
                        errsv = errno;
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): (IPv6) Failed to get sockaddr_in6 for "<< myConnection->diameter_server << endl;
                        logString <<"\tError: " << strerror(errsv) << endl;
                        LOG(ERROR, logString.str());

                        resetAndExit (myConnection, CONFIGURATIONERROR);
                    }

                    memset(&loc_addr_v6,0,sizeof(loc_addr_v6));
                    loc_addr_v6.sin6_family = AF_INET6;

                    if(myConnection->use_sctp) 
                            if (inet_pton(AF_INET6, cer_data.diaproxy_host, &loc_addr_v6.sin6_addr) !=1){
                            errsv = errno;
                            logString.clear();
                            logString.str("");
                            logString << "(DiaThread:" << myConnection->threadID << "): (IPv6) Failed to get sockaddr_in6 for "<< cer_data.diaproxy_host << endl;
                            logString <<"\tError: " << strerror(errsv) << endl;
                            LOG(ERROR, logString.str());

                            resetAndExit (myConnection, CONFIGURATIONERROR);
                        }

                    socklen_t len = sizeof(diameter_addr_v6);

                    if(bind(localSockId,(struct sockaddr*)&loc_addr_v6,sizeof(loc_addr_v6)) < 0){
                        errsv = errno;
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): (IPv6) Failed to bind local socket " << endl;
                        logString <<"\tError: " << strerror(errsv) << endl;
                        LOG(ERROR, logString.str());

                        resetAndExit (myConnection, CONFIGURATIONERROR);
                    }

                    sock_result = connect(localSockId,(sockaddr*)&diameter_addr_v6,len);

                    if (sock_result == -1 && errno != 115){
                        errsv = errno;
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Failing to network connect (socked id " <<localSockId << ")" ;
                        if(myConnection->use_sctp)
                            logString << " from " << cer_data.diaproxy_host;

                        logString << " to " <<myConnection->diameter_server<< " : " << myConnection->serv_port << endl;
                        logString <<"\tError: " << strerror(errsv) << endl;
                        LOG(ERROR, logString.str());

                        sleep (cer_data.reconnectTime);
                        pthread_mutex_lock(&CONNECTION_VECTOR);
                            close(localSockId);
                            myConnection->status = TOBECONNECTED;
                        pthread_mutex_unlock(&CONNECTION_VECTOR);
                        break;
                    }
                }
                else{  // IPv4
                    memset(&diameter_addr,0,sizeof(sockaddr_in));
                    diameter_addr.sin_family = AF_INET;
                    diameter_addr.sin_port = htons(myConnection->serv_port);

                    struct hostent *he;
                    he = gethostbyname(myConnection->diameter_server); 
                    if (he == 0) {
                            logString.clear();
                            logString.str("");
                            logString << "(DiaThread:" << myConnection->threadID << "): (IPv4) Destination host not valid " << myConnection->diameter_server <<endl;
                            LOG(ERROR, logString.str());

                            resetAndExit (myConnection, CONFIGURATIONERROR);
                    }

                    bcopy(he->h_addr_list[0], &diameter_addr.sin_addr.s_addr, he->h_length);
                    memset(&loc_addr,0,sizeof(sockaddr_in));
                    loc_addr.sin_family = AF_INET;

                    if(myConnection->use_sctp) 
                        loc_addr.sin_addr.s_addr = inet_addr(cer_data.diaproxy_host);

                    socklen_t len = sizeof(diameter_addr);

                    if(bind(localSockId,(struct sockaddr*)&loc_addr,sizeof(loc_addr)) < 0){
                        errsv = errno;
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): (IPv4) Failed to bind local socket " << endl;
                        logString <<"\tError: " << strerror(errsv) << endl;
                        LOG(ERROR, logString.str());

                        resetAndExit (myConnection, CONFIGURATIONERROR);
                    }

                    sock_result = connect(localSockId,(sockaddr*)&diameter_addr,len);

                    if (sock_result == -1 && errno != 115){
                        errsv = errno;
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Failing to network connect (socked id " <<localSockId << ")";
                        if(myConnection->use_sctp)
                            logString << " from " << cer_data.diaproxy_host;
                        logString << " to " <<myConnection->diameter_server<< " : " << myConnection->serv_port << endl;
                        logString <<"\tError: " << strerror(errsv) << endl;
                        LOG(ERROR, logString.str());

                        sleep (cer_data.reconnectTime);
                        pthread_mutex_lock(&CONNECTION_VECTOR);
                            close(localSockId);
                            myConnection->status = TOBECONNECTED;
                        pthread_mutex_unlock(&CONNECTION_VECTOR);
                        break;
                    }
                }

                if(localSockId != -1) { 
                    tv.tv_sec = 2;
                    tv.tv_usec = 0;
                    int localSockId_port = 0;
                    char localSockId_ip[100]="";
                    if (!cer_data.ipv6) {
                        struct sockaddr_in sin;
                        socklen_t len2 = sizeof(sin);
                        if (getsockname(localSockId, (struct sockaddr *)&sin, &len2) != -1){
                            localSockId_port = ntohs(sin.sin_port);
                            strcpy(localSockId_ip,inet_ntoa(sin.sin_addr));
                        }
                    }
                    FD_ZERO(&writefdset);
                    FD_SET(localSockId, &writefdset);
                    int temp = select(localSockId+1, NULL, &writefdset, NULL, &tv);
                    if( FD_ISSET(localSockId, &writefdset)) { 
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Network connection (socked id " <<localSockId << ")";
                        if(!cer_data.ipv6)
                            logString << " from " << localSockId_ip << " : " << localSockId_port;
                        logString << "    to   " <<myConnection->diameter_server<< " : " << myConnection->serv_port<<" established" <<endl;
                        LOG(CONNECTIONS, logString.str());
                    }
                    else {
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Timeout during network connection (socked id " <<localSockId << ")";
                        if(!cer_data.ipv6)
                            logString << " from " << localSockId_ip << " : " << localSockId_port;
                        logString << "   to   " <<myConnection->diameter_server<< " : " << myConnection->serv_port << endl;
                        LOG(ERROR, logString.str());

                        sleep (cer_data.reconnectTime);
                        pthread_mutex_lock(&CONNECTION_VECTOR);
                            close(localSockId);
                            myConnection->status = TOBECONNECTED;
                        pthread_mutex_unlock(&CONNECTION_VECTOR);
                        break;

                    }
                    FD_ZERO(&fds);
                    FD_SET(localSockId, &fds);

                    int res = send(localSockId,(const char*)cer_msg,cer_len,0);

                    if(res > 0) { 
#ifdef _DIA_PROXY_DEBUG
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): CER sent " << endl ;
                        LOG(DEBUG, logString.str());
#endif
                        pthread_mutex_lock(&CONNECTION_VECTOR);
                            myConnection->sockId = localSockId;
                        pthread_mutex_unlock(&CONNECTION_VECTOR);

                    receive_CEA(myConnection);
                    } 
                    else { 
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Failed to send CER to Diameter" << endl ;
                        LOG(ERROR, logString.str());

                        sleep (cer_data.reconnectTime);
                        pthread_mutex_lock(&CONNECTION_VECTOR);
                            close(localSockId);
                            myConnection->status = TOBECONNECTED;
                        pthread_mutex_unlock(&CONNECTION_VECTOR);
                        break;
                    } 

                    if (myConnection->status != CONNECTING)     break;  

                    pthread_mutex_lock(&CONNECTION_VECTOR);
                        myConnection->status = CONNECTED;
                        myConnection->firstConnectionTry = false;
                    pthread_mutex_unlock(&CONNECTION_VECTOR);

                    MessageToSendDeque pendingMessages;
                    pthread_mutex_lock(&PENDING_MESSAGE_MAP);
                        bool insert_result = m_pendingToSend.insert(std::make_pair(localSockId , pendingMessages)).second;
                    pthread_mutex_unlock(&PENDING_MESSAGE_MAP);

                    if (!insert_result) {
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Failing to insert socket " <<localSockId << " in m_pendingToSend" <<endl;
                        LOG(ERROR, logString.str());

                        resetAndExit (myConnection, OFF);
                    }

                    int status = fcntl(localSockId, F_SETFL, fcntl(localSockId, F_GETFL, 0) | O_NONBLOCK);

                    if (status == -1){
                        errsv = errno;
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Failing to setting O_NONBLOCK" << endl;
                        logString <<"\tError: " << strerror(errsv) << endl;
                        LOG(ERROR, logString.str());
                    }
                }
                break;
            }
            case CONNECTED: {

                pthread_mutex_lock(&TOOL_STATUS);
                    myHaveToExit = haveToExit;
                pthread_mutex_unlock(&TOOL_STATUS);

                if(myHaveToExit){ 
                    logString.clear();
                    logString.str("");
                    logString << "(DiaThread:" << myConnection->threadID << "): Terminating... " << endl;
                    LOG(EVENT, logString.str());

                    resetAndExit (myConnection, OFF);
                } 

                tv.tv_sec = 0;
                tv.tv_usec = 5000;
                FD_ZERO(&readfdset);
                FD_SET(localSockId, &readfdset);
                messageToSend = false;

                FD_ZERO(&writefdset);
                pendingToSendMapIter = m_pendingToSend.find(localSockId);
                if ( ! (pendingToSendMapIter == m_pendingToSend.end())) {
                    if (! (pendingToSendMapIter->second.empty())){
                        FD_SET(localSockId, &writefdset);
                        messageToSend = true;
                    }
                }

                int koll;
                struct timespec event_time;

                koll = select(localSockId+1, &readfdset, &writefdset, NULL, &tv);
                if(FD_ISSET(localSockId, &writefdset) && messageToSend) { 
                    if (sendPendingMessage(localSockId)) {
                        wdrCount = 0;
                        myConnection->pendingWatchDog = 0;
                    }
                    else if (myConnection->status != CONNECTED){
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Problem sending messages to Diameter server. Restarting..." << endl;
                        LOG(CONNECTIONS, logString.str());
                        break;
                    }
                }

                if(FD_ISSET(localSockId, &readfdset)) {
                    if (cer_data.latency_report_running) {clock_gettime( CLOCK_MONOTONIC, &event_time );}

                    wdrCount = 0;
                    myConnection->pendingWatchDog = 0;
                    memset(buff,0,DEFAULT_BUFFER_SIZE);

                    received = recv(localSockId,(LPTSTR)buff,DIAMETER_HEADER_LENGTH,0);
                    if(received < DIAMETER_HEADER_LENGTH) { 
                        if(received < 1){ 
                            if(received == -1){ 
                                logString.clear();
                                logString.str("");
                                logString << "(DiaThread:" << myConnection->threadID << "): Broken pipe with Diameter server reading message header. Restarting..." << endl;
                                LOG(CONNECTIONS, logString.str());
                                } 
                            if(received == 0){ 
                                logString.clear();
                                logString.str("");
                                logString << "(DiaThread:" << myConnection->threadID << "): Diameter server has closed the connection reading message header. Restarting... " << endl;
                                LOG(CONNECTIONS, logString.str());
                            } 

                            pthread_mutex_lock(&CONNECTION_VECTOR);
                                myConnection->status = TOBECONNECTED;
                            pthread_mutex_unlock(&CONNECTION_VECTOR);
                            break;
                        } 
                        pbuf = buff;
                        pbuf += received;
                        toread = DIAMETER_HEADER_LENGTH - received;
                        read_retries = 0;

                        while(received < DIAMETER_HEADER_LENGTH){ 
                            pthread_mutex_lock(&TOOL_STATUS);
                                myHaveToExit = haveToExit;
                            pthread_mutex_unlock(&TOOL_STATUS);

                            if(myHaveToExit){ 
                                logString.clear();
                                logString.str("");
                                logString << "(DiaThread:" << myConnection->threadID << "): Terminating... " << endl;
                                LOG(EVENT, logString.str());

                                resetAndExit (myConnection, OFF);
                            } 
                            if (myConnection->status == BROKEN) {
                                logString.clear();
                                logString.str("");
                                logString << "(DiaThread:" << myConnection->threadID << "): Broken pipe with Diameter server reading message header. Restarting..." << endl;
                                LOG(EVENT, logString.str());

                                pthread_mutex_lock(&CONNECTION_VECTOR);
                                    myConnection->status = TOBECONNECTED;
                                pthread_mutex_unlock(&CONNECTION_VECTOR);

                                break;
                            } 

                            FD_ZERO(&readfdset);
                            FD_SET(localSockId, &readfdset);

                            tv.tv_sec = 2;
                            tv.tv_usec = 0;
                            select(localSockId+1, &readfdset, NULL, NULL, &tv);
                            if(FD_ISSET(localSockId, &readfdset)){ 
                                rest = recv(localSockId,(LPTSTR)pbuf,toread,0);

                                if(rest == -1){ 
                                    logString.clear();
                                    logString.str("");
                                    logString << "(DiaThread:" << myConnection->threadID << "): Broken pipe with Diameter server reading message header. Restarting..." << endl;
                                    LOG(CONNECTIONS, logString.str());

                                    pthread_mutex_lock(&CONNECTION_VECTOR);
                                        myConnection->status = TOBECONNECTED;
                                    pthread_mutex_unlock(&CONNECTION_VECTOR);

                                    break;
                                } 
                                if(rest == 0){ 
                                    logString.clear();
                                    logString.str("");
                                    logString << "(DiaThread:" << myConnection->threadID << "): Diameter server has closed the connection reading message header. Restarting... " << endl;
                                    LOG(CONNECTIONS, logString.str());

                                    pthread_mutex_lock(&CONNECTION_VECTOR);
                                        myConnection->status = TOBECONNECTED;
                                    pthread_mutex_unlock(&CONNECTION_VECTOR);
    
                                    break;
                                } 

                                toread -= rest;
                                received += rest;
                                pbuf += rest;
                            } //if(FD_ISSET(diameter_sock, &readfdset1))
                            else { 
                                read_retries++;
                                if(read_retries == 20){ //if(read_retries == 20)
                                    logString.clear();
                                    logString.str("");
                                    logString << "(DiaThread:" << myConnection->threadID << "): Too many retries reading the compleate diameter packet. Restarting..." << endl;
                                    LOG(CONNECTIONS, logString.str());

                                    pthread_mutex_lock(&CONNECTION_VECTOR);
                                        myConnection->status = TOBECONNECTED;
                                    pthread_mutex_unlock(&CONNECTION_VECTOR);
                                    break;
                                } //if(read_retries == 20)
                            } //else to if(FD_ISSET(diameter_sock, &readfdset))
                        } //while(received < DIAMETER_HEADER_LENGTH)
                    } //if(received < DIAMETER_HEADER_LENGTH)
     /////////////////////////////////////////////////////////////////////////////
     
                    if ( myConnection->status != CONNECTED)    break;

                    pbuf = buff;
                    received = read_message_body (myConnection, 0, &pbuf,fds, &dp_size);
                     if ( myConnection->status != CONNECTED)    break;

                    head = (DIAMETER_HEADER*)buff;
                    uint cmd_code = (head->cmd_code[0]<<16) + (head->cmd_code[1]<<8) + head->cmd_code[2];

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
                        case cmd__watchdog:
                            if(head->flags == 0x80){
#ifdef _DIA_PROXY_DEBUG
                                logString.clear();
                                logString.str("");
                                logString << "(DiaThread:" << myConnection->threadID << "): Received watchdog request message from Diameter server" << endl;
                                LOG(DEBUG, logString.str());
#endif
                                send_WDR_or_DPR_Answer (myConnection,(uchar*)buff);
                            }
                            else {
#ifdef _DIA_PROXY_DEBUG
                                logString.clear();
                                logString.str("");
                                logString << "(DiaThread:" << myConnection->threadID << "): Received watchdog answer message from Diameter server" << endl;
                                LOG(DEBUG, logString.str());
#endif
                            }
                            break;

                        case cmd__dpr:
                            logString.clear();
                            logString.str("");
                            logString << "(DiaThread:" << myConnection->threadID << "): Received a Disconnect Request message from Diameter server" << endl;
                            LOG(CONNECTIONS, logString.str());

                            send_WDR_or_DPR_Answer (myConnection,(uchar*)buff);
                            pthread_mutex_lock(&CONNECTION_VECTOR);
                                myConnection->status = DISCONNECTED;
                            pthread_mutex_unlock(&CONNECTION_VECTOR);

                            resetAndExit (myConnection, OFF);
                            break;

                        case cmd__rsr_rfe5:
                            logString.clear();
                            logString.str("");
                            logString << "(DiaThread:" << myConnection->threadID << "): Received a Reset mme Request message from Diameter server" << endl;
                            LOG(CONNECTIONS, logString.str());

                            break;

                        case cmd__clr_rfe5: 
                        case cmd__clr:
                        case cmd__idr_rfe5: 
                        case cmd__idr:	
                        case cmd__dsr_rfe5:	{
#ifdef _DIA_PROXY_MONITOR
                            myConnection->requestReceivedFromServer++;;
#endif
                            time(&lastaction);	//for inactivity monitoring
                            std::string myAvp;
                            if (!extractAVP ((const char *)buff, dp_size, USERNAME_CODE, myAvp) ) {
                                logString.clear();
                                logString.str("");
                                logString << "(DiaThread:" << myConnection->threadID << "): Received a request without a valid UserName" << endl;
                                LOG(EVENT, logString.str());
#ifdef _DIA_PROXY_MONITOR
                                myConnection->requestDiscardFromServer++;
#endif
                                break;
                            }

                            std::string myDestHostAvp;
                            if (!extractAVP ((const char *)buff, dp_size, DESTINATIONHOST_CODE, myDestHostAvp) ) {
                                logString.clear();
                                logString.str("");
                                logString << "(DiaThread:" << myConnection->threadID << "): Received a request without a valid DestHost" << endl;
                                LOG(EVENT, logString.str());
#ifdef _DIA_PROXY_MONITOR
                                myConnection->requestDiscardFromServer++;
#endif
                                break;
                            }

                            std::map<std::string,Session>::iterator mapIter;
                            int client = -1;

                            pthread_mutex_lock(&SESSION_MAP);
                                mapIter = m_session.find(myDestHostAvp);
                            pthread_mutex_unlock(&SESSION_MAP);

                            if ( mapIter == m_session.end()) {
                                logString.clear();
                                logString.str("");
                                logString << "(DiaThread:" << myConnection->threadID << "): Received a request with a non existing DestHost: " <<myDestHostAvp<< endl;
                                LOG(DEBUG, logString.str());

                                pthread_mutex_lock(&SESSION_MAP);
                                    mapIter = m_session.find(myAvp);
                                pthread_mutex_unlock(&SESSION_MAP);

                                if ( mapIter == m_session.end()) {
                                    logString.clear();
                                    logString.str("");
                                    logString << "(DiaThread:" << myConnection->threadID << "): Received a request with a non existing UserName: " <<myAvp<< endl;
                                    LOG(EVENT, logString.str());

                                    client = findUsedClient();
                                    if (client == -1 ) {
#ifdef _DIA_PROXY_MONITOR
                                        myConnection->requestDiscardFromServer++;
#endif
                                        break;
                                    }
                                }
                                else {
                                    client = mapIter->second.client;
                                }
                            }
                            else {
                                client = mapIter->second.client;
                            } 
                            int transId = findTransaction();

                            if (transId == -1) {
                                logString.clear();
                                logString.str("");
                                logString << "(DiaThread:" << myConnection->threadID << "): There are not Free transaction record" << endl;
                                LOG(EVENT, logString.str());

#ifdef _DIA_PROXY_MONITOR
                                myConnection->requestDiscardFromServer++;
#endif
                                break;
                            }
                            v_transaction[transId].end2end = head->end2end;
                            v_transaction[transId].hopByHop = head->hop2hop;
                            v_transaction[transId].client = client;
                            v_transaction[transId].answerToDiaServerConnection = myConnection->pos;
                            head->hop2hop = transId+1;

                            bool inserted = false;

                            if(v_client[client].status == ONLINE) {
                                struct Message message;
                                message.message_len = dp_size;
                                message.bytes_sent = 0;
                                message.message_type = REQUEST_TO_CLIENT;
                                message.transaction = transId;
                                message.diaServerConnection = myConnection->pos;
                                message.buffer = new unsigned char [dp_size];
                                memcpy(message.buffer, buff, dp_size);

                                inserted = addMessageAsPending(v_client[client].sock, message);

                                if (not inserted){  delete [] message.buffer;}
                            }
                            if (not inserted){  
#ifdef _DIA_PROXY_MONITOR
                                myConnection->requestDiscardFromServer++;
#endif
                                v_transaction[transId].status = NOTUSED;
                                v_transaction[transId].request_time.tv_sec = 0;
                            }
                            break;
                        }
                        default: {
#ifdef _DIA_PROXY_DEBUG
                            logString.clear();
                            logString.str("");
                            logString << "(DiaThread:" << myConnection->threadID << "): Received message from Diameter server" << endl;
                            LOG(DEBUG, logString.str());
#endif
#ifdef _DIA_PROXY_MONITOR
                            myConnection->answerReceivedFromServer++;;
#endif
                            time(&lastaction);	//for inactivity monitoring
                            //normal operation
                            uint h2h = head->hop2hop;
                            h2h = h2h - 1;

                            //the value of h2h is checked in order to avoid Segmentation Fault
                            if (h2h > v_transaction.size() - 1) {
                                logString.clear();
                                logString.str("");
                                logString << "(DiaThread:" << myConnection->threadID << "): Mesaage with hopbyhop out of range" << endl;
                                LOG(WARNING, logString.str());

                                myConnection->answerDiscardFromServer++;
                                break;
                            }

                             if (cer_data.DiaErrCounters_report_running) {
                                int resultCodeValue;
                                if (extractResultCodeAVP ((const char *)buff, dp_size, resultCodeValue) ) {
                                    switch (resultCodeValue){
                                        case DIAMETER_SUCCESS:{
                                            pthread_mutex_lock(&STATISTIC);
                                                myConnection->resultCode_Success++;
                                            pthread_mutex_unlock(&STATISTIC);
                                             break;
                                        }
                                        case DIAMETER_UNABLE_TO_COMPLY:{
                                            pthread_mutex_lock(&STATISTIC);
                                                myConnection->resultCode_UnableToComply++;
                                            pthread_mutex_unlock(&STATISTIC);
                                            break;
                                        }
                                        case DIAMETER_TOO_BUSY:{
                                            pthread_mutex_lock(&STATISTIC);
                                                myConnection->resultCode_Busy++;
                                            pthread_mutex_unlock(&STATISTIC);
                                            break;
                                        }
                                        default:{
                                            if (resultCodeValue > 2001 && resultCodeValue<3000){
                                                pthread_mutex_lock(&STATISTIC);
                                                    myConnection->resultCode_Success++;
                                                pthread_mutex_unlock(&STATISTIC);
                                            }
                                            else{
                                                pthread_mutex_lock(&STATISTIC);
                                                    myConnection->resultCode_Other++;
                                                pthread_mutex_unlock(&STATISTIC);
                                            }
                                            break;
                                        }
                                    }
                                }
                                else {
                                    pthread_mutex_lock(&STATISTIC);
                                        myConnection->resultCode_Other++;
                                    pthread_mutex_unlock(&STATISTIC);
                                }
                            } 
                            if (cer_data.latency_report_running && v_transaction[h2h].request_time.tv_sec) {
                                struct reportData sample;

                                sample.time_event = double (event_time.tv_sec - v_transaction[h2h].request_time.tv_sec) * 1000;
                                sample.time_event = sample.time_event + double (event_time.tv_nsec - v_transaction[h2h].request_time.tv_nsec) / 1000000;

                                sample.cmd_code =  cmd_code;
                                extractAVP ((const char *)buff, dp_size, SESSIONID_CODE, sample.sessionId);

                                if (sample.time_event < 0) {
                                    logString.clear();
                                    logString.str("");
                                    logString << "(DiaThread:" << myConnection->threadID << "): Wrong negative time for sessionId " ;
                                    logString << sample.sessionId << " CmdCode " <<cmd_code << endl;
                                    LOG(WARNING, logString.str());
                                }
                                else {
                                    pthread_mutex_lock(&REPORT);
                                        myConnection->reportData.push_back(sample);
                                    pthread_mutex_unlock(&REPORT);
                                }
                            }

                            int client = v_transaction[h2h].client;
                            bool inserted = false;
                            if(v_client[client].status == ONLINE) { 

                                head->end2end = v_transaction[h2h].end2end;
                                head->hop2hop = v_transaction[h2h].hopByHop;

                                struct Message message;
                                message.message_len = dp_size;
                                message.bytes_sent = 0;
                                message.message_type = ANSWER_TO_CLIENT;
                                message.transaction = -1;
                                message.diaServerConnection = myConnection->pos;
                                message.buffer = new unsigned char [dp_size];
                                memcpy(message.buffer, buff, dp_size);

                                inserted = addMessageAsPending(v_client[client].sock, message);

                                if (inserted) {
                                    v_client[client].waitingAnswer = false;
                                }
                                else {
                                    delete[] message.buffer;
                                }
                                
                            }

                            if ( not inserted ) {
#ifdef _DIA_PROXY_MONITOR
                                myConnection->answerDiscardFromServer++;
#endif                                     
                            }

                            pthread_mutex_lock(&TRANSACTION_VECTOR);
                                v_transaction[h2h].status = NOTUSED;
                                v_transaction[h2h].request_time.tv_sec = 0;
                            pthread_mutex_unlock(&TRANSACTION_VECTOR);

                            break;

                        } //default	
                    } //switch cmd_code 

                } //if(FD_ISSET(diameter_sock, &readfdset))

                else {
                    if(myConnection->pendingWatchDog >= MAX_WDR_PENDING){ 
                        logString.clear();
                        logString.str("");
                        logString << "(DiaThread:" << myConnection->threadID << "): Too many Watchdog Request without answer. Restart Diathread " << endl ;
                        LOG(CONNECTIONS, logString.str());
                    
                        pthread_mutex_lock(&CONNECTION_VECTOR);
                            myConnection->status = TOBECONNECTED;
                        pthread_mutex_unlock(&CONNECTION_VECTOR);
                        break;
                    } 

                    if (not cer_data.skip_wd){
                        //Send wdr evry WDR_TIME  seconds
                        wdrCount++;

                        if (wdrCount > WDR_TIME) {
#ifdef _DIA_PROXY_DEBUG
                            logString.clear();
                            logString.str("");
                            logString << "(DiaThread:" << myConnection->threadID << "): sending Watchdog Request" << endl ;
                            LOG(DEBUG, logString.str());
#endif
                            send_Watchdog_Request(myConnection);
                            wdrCount = 0;
                            myConnection->pendingWatchDog++;
                        }
                    }
                }

                break;
            }   // end myConnection->status == CONNECTED
            default:
                break;
        } // end switch (myConnection->status)
    } //while(true)

    if(localSockId != -1){
        close(localSockId);
    }

    logString.clear();
    logString.str("");
    logString << "(DiaThread:" << myConnection->threadID << "):  Exiting..." << endl ;
    LOG(EVENT, logString.str());

    resetAndExit (myConnection, OFF);
    return 0;

} //void* _DiaThread(void *arg)

void send_WDR_or_DPR_Answer (DiaServerConnection *myConnection, uchar *buff)
{
    int localSockId = myConnection->sockId;
    int res_sending;
    DIAMETER_HEADER *head;
    head = (DIAMETER_HEADER*)buff;
    puchar pb = buff + DIAMETER_HEADER_LENGTH;
    int len = add_response(pb);
    int ts = len + DIAMETER_HEADER_LENGTH;
    head->flags = 0x00;
    head->length[0] = (ts >> 16) & 0xff;
    head->length[1] = (ts >> 8) & 0xff;
    head->length[2] = ts & 0xff;

    res_sending = send(localSockId,buff,ts,0);

    if (res_sending < 1) {
        pthread_mutex_lock(&CONNECTION_VECTOR);
            myConnection->status = TOBECONNECTED;
        pthread_mutex_unlock(&CONNECTION_VECTOR);

    }
}

void send_Watchdog_Request (DiaServerConnection *myConnection) 
{

    int localSockId = myConnection->sockId;
    int res_sending;

    DIAMETER_HEADER *head;
    uchar buff[DEFAULT_BUFFER_SIZE];
    
    head = (DIAMETER_HEADER*)buff;
    generatehae(head);
    puchar pb = buff + DIAMETER_HEADER_LENGTH;
    int wdrs = generate_wdr(pb);
    int ts = wdrs + DIAMETER_HEADER_LENGTH;
    head->ver  = 0x01;
    head->cmd_code[0] = 0x00;
    head->cmd_code[1] = 0x01;
    head->cmd_code[2] = 0x18;
    head->vendor_id = 0;
    head->flags = 0x80;
    head->length[0] = (ts>>16) & 0xff;
    head->length[1] = (ts>>8) & 0xff;
    head->length[2] = ts & 0xff;

    res_sending = send(localSockId,buff,ts,0);

    if (res_sending < 1) {
        pthread_mutex_lock(&CONNECTION_VECTOR);
            myConnection->status = TOBECONNECTED;
        pthread_mutex_unlock(&CONNECTION_VECTOR);
    }
}

int add_response(puchar pb)
{
    stop = clock();
    int toret = 0;
    AVP_HEADER avph;
    memcpy(pb,WDA,WDA_SIZE);
    pb += WDA_SIZE;
    toret += WDA_SIZE;
    
    
    int len = strlen((char*)cer_data.origin_host);
    int plen = len + topad(len);
    
    int avplen = len + WDA_AVPS_GENERIC_LENGTH;
    memset(&avph,0,WDA_AVPS_GENERIC_LENGTH);
    avph.avp_code = origin__host;
    avph.avp_len[0] = ((avplen) >> 16) & 0xff;
    avph.avp_len[1] = (avplen >> 8) & 0xff;
    avph.avp_len[2] = avplen & 0xff;
    avph.flags = 0x40;
    memcpy(pb,&avph,WDA_AVPS_GENERIC_LENGTH);
    
    pb += WDA_AVPS_GENERIC_LENGTH;
    toret += WDA_AVPS_GENERIC_LENGTH;
    memset(pb,0,plen);
    memcpy(pb,cer_data.origin_host,len);
    pb += plen;
    toret += plen;

    len = strlen((char*)cer_data.origin_realm);
    avplen = len + WDA_AVPS_GENERIC_LENGTH;
    plen = len + topad(len);
    memset(&avph,0,WDA_AVPS_GENERIC_LENGTH);
    avph.avp_code = origin__realm;
    avph.avp_len[0] = (avplen >> 16) & 0xff;
    avph.avp_len[1] = (avplen >> 8) & 0xff;
    avph.avp_len[2] = avplen & 0xff;
    avph.flags = 0x40;

    memcpy(pb,&avph,WDA_AVPS_GENERIC_LENGTH);
    pb += WDA_AVPS_GENERIC_LENGTH;

    toret += WDA_AVPS_GENERIC_LENGTH;
    memset(pb,0,plen);
    memcpy(pb,cer_data.origin_realm,len);
    toret += plen;
    return toret;
}

void generatehae(DIAMETER_HEADER *head)
{
    srand((unsigned)time(NULL));
    head->hop2hop = rand();
    head->end2end = rand();
}

int generate_wdr(puchar pb)
{
    stop= clock();
    int toret = 0;
    AVP_HEADER avph;

    memset(&avph,0,sizeof(avph));
    avph.avp_code = origin__host;
    int len = strlen((char*)cer_data.origin_host);
    int plen = len + topad(len);
    //int avplen = len + sizeof(avph);
    int avplen = len + 8;
    avph.avp_len[0] = (avplen>>16) & 0xff;
    avph.avp_len[1] = (avplen>>8) & 0xff;
    avph.avp_len[2] = avplen & 0xff;
    avph.flags = 0x40;
    memcpy(pb,&avph,sizeof(avph));
    //pb += sizeof(avph);
    pb += 8;
    
    //toret += sizeof(avph);
    toret += 8;
    memset(pb,0,plen);
    memcpy(pb,cer_data.origin_host,len);
    pb += plen;
    toret += plen;

    memset(&avph,0,sizeof(avph));
    avph.avp_code = origin__realm;
    len = strlen((char*)cer_data.origin_realm);
    plen = len + topad(len);
    //avplen = len + sizeof(avph);
    avplen = len + 8;
    avph.avp_len[0] = (avplen>>16) & 0xff;
    avph.avp_len[1] = (avplen>>8) & 0xff;
    avph.avp_len[2] = avplen & 0xff;
    avph.flags = 0x40;
    memcpy(pb,&avph,sizeof(avph));
    //pb += sizeof(avph);
    pb += 8;
    //toret += sizeof(avph);
    toret += 8;
    memset(pb,0,plen);
    memcpy(pb,cer_data.origin_realm,len);
    pb += plen;
    toret += plen;

    return toret;
}



int createCER(uchar *cermsg, struct CER_DATA *cerdata, DiaServerConnection *connection )
{ //int createCER(uchar *cermsg, struct CER_DATA *cerdata)

    int version=RFC__VERSION;
    char firmware_value[4];

    DiaMessage CERMessage = DiaMessage();
    uchar cmd_code[3];
    cmd_code[1]=0x01;
    cmd_code[2]=0x01;

    CERMessage.set_cmd_code(cmd_code);
    AVP *avp;
    //Origin-Host
                
    avp = new AVP (origin__host,0x40,connection->origin_host,version);
    CERMessage.addAVP (avp);
    free (avp);	
                
    //Origin-Realm
    avp = new AVP (origin__realm,0x40,cer_data.origin_realm,version);
    CERMessage.addAVP (avp);
    free (avp);
    
    //Host-IP-Address
    if (cer_data.ipv6) {
        avp = new AVP (host__ip__address,0x40, (puchar)cer_data.localaddr_v6.sin6_addr.s6_addr, cer_data.ipv6, version, true);
        CERMessage.addAVP (avp);
        free (avp);
                
    }
    else {
        avp = new AVP (host__ip__address,0x40, cer_data.host_ip_address, version, true);
        CERMessage.addAVP (avp);
        free (avp);
    }
        
    //Vendor-ID
    avp = new AVP (vendor__id, 0x40, 4, cerdata->vendor_id,version);
    CERMessage.addAVP (avp);
    free (avp);
    
    //Product-Name
    avp = new AVP (product__name, (uchar)0x00,cerdata->product_name,version);
    CERMessage.addAVP (avp);
    free (avp);

    
    int sub_attr_len=0;	
        
    int index;
    for (index=0;index!=cer_data.number_of_supported_vendor_ids;index++) {
        puchar hex_value[4];  
        int current_vendor_id = cer_data.list_of_supported_vendor_ids[index];
            
        int2hex ((char*)hex_value,current_vendor_id,4);
        avp = new AVP (supported__vendor__id, (uchar)0x40, 4, (puchar)hex_value, version);
        CERMessage.addAVP (avp);
        free (avp);
    }
        
    for (index=0;index!=cer_data.number_of_auth_application_ids;index++) {
        puchar hex_value[4];  
        int current_vendor_id = cer_data.list_of_auth_application_ids[index];
            
        int2hex ((char*)hex_value,current_vendor_id,4);
        avp = new AVP (auth__application__id, (uchar)0x40, 4,(puchar)hex_value,version);
        CERMessage.addAVP (avp);
        free (avp);
    }
        
    for (index=0;index < 2 * cer_data.number_of_vendor_specific_application_ids;index++) {
        char hex_value[4];  

        //Supported-Vendor-ID
        int current_vendor_id = cer_data.list_of_vendor_specific_application_ids[index];
        int2hex (hex_value,current_vendor_id,4);
        AVP *sub_avp1 = new AVP (vendor__id,0x40, 4, (uchar*)hex_value, version);
        sub_attr_len = sub_avp1->get_length();
            
        //Auth-Application-ID
        int2hex(hex_value, cer_data.list_of_vendor_specific_application_ids[++index],4);
        AVP *sub_avp2 = new AVP (auth__application__id,0x40, 4, (uchar*)hex_value, version);
        sub_attr_len += sub_avp2->get_length();
    
        //Vendor-Specific-Application-Id
        AVP *parent_avp = new AVP (vendor__specific__application__id,0x40, version,sub_attr_len);
            
        parent_avp->add_sub_attribute(sub_avp1);
        parent_avp->add_sub_attribute(sub_avp2);
                    
        free (sub_avp1);
        free (sub_avp2);
                
        CERMessage.addAVP (parent_avp);
        free (parent_avp);
    }
        
    //firmware revision
    int2hex (firmware_value, DEFAULT_FIRMWARE_REVISION, 4);
    avp = new AVP (firmware__revision, (uchar)0x00, 4, (uchar*)firmware_value,version);
    CERMessage.addAVP (avp);
    free (avp);

    //finishing the message
    CERMessage.message(cermsg);
    return CERMessage.get_size();
} //int createCER(uchar *cermsg, struct CER_DATA *cerdata)

 bool SetSocketBlockingEnabled(int fd, bool blocking)
{
   if (fd < 0) return false;

   int flags = fcntl(fd, F_GETFL, 0);
   if (flags < 0) return false;
   flags = blocking ? (flags&O_NONBLOCK) : (flags|O_NONBLOCK);
   return (fcntl(fd, F_SETFL, flags) == 0) ? true : false;
}       

 int createDPR(uchar *dprmsg, struct CER_DATA *cerdata, DiaServerConnection *connection )
 {

    int version=RFC__VERSION;

    DiaMessage DPRMessage = DiaMessage();
    uchar cmd_code[3];
    cmd_code[1] = 0x01;
    cmd_code[2] = 0x1a;
    DPRMessage.set_cmd_code(cmd_code);
    AVP *avp;
    //Origin-Host

    avp = new AVP (origin__host,0x40,connection->origin_host,version);
    DPRMessage.addAVP (avp);
    free (avp);

    //Origin-Realm
    avp = new AVP (origin__realm,0x40,cer_data.origin_realm,version);
    DPRMessage.addAVP (avp);
    free (avp);

    //Disconnect cause = 2
    char hex_value[4];
    int2hex (hex_value,2,4);
    avp = new AVP (disconnect__cause, 0x40,4, (uchar*)hex_value, version);
    DPRMessage.addAVP (avp);
    free (avp);

    //finishing the message
    DPRMessage.message(dprmsg);
    return DPRMessage.get_size();
 }
 
