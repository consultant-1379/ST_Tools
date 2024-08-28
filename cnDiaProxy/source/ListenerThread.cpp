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


#include "cnDiaProxy.h"
#include "ClientThread.h"
#include "DiaThread.h"
#include "ListenerThread.h"
#include <fcntl.h>

extern ListennerStatus listennerState;
extern DiaProxyStatus diaProxyState;
DiaProxyStatus myDiaProxyState;
extern SignalReason sigReason;

extern pthread_t ListenerThreadID;
extern pthread_t SignalThreadID;
extern bool haveToExit;
extern bool couldBeCleaned;

extern time_t start, stop, lastaction;
extern applicationData dataTool;

extern std::vector<DiaServerConnection> v_connections;
extern std::vector<ClientConnection> v_client;
extern std::vector<clientThread> v_clientThread;
extern PendingToSendMap  m_pendingToSend;

struct DiaServerConnection *servCon = NULL;

NetworkConnection *server_connection;

extern unsigned int numberClientThreads;
extern int nextClientThread;

//variable for defining/handling a mutual exclusion zone
extern pthread_mutex_t TRANSACTION_VECTOR;
extern pthread_mutex_t CONNECTION_VECTOR;
extern pthread_mutex_t CLIENT_VECTOR;
extern pthread_mutex_t CLIENT_THREAD_VECTOR;
extern pthread_mutex_t SESSION_MAP;
extern pthread_mutex_t PENDING_MESSAGE_MAP;
extern pthread_mutex_t TOOL_STATUS;
extern pthread_mutex_t STATISTIC;

using namespace std;

void resetAndExit (int fail)
{
    bool myHaveToExit;
    stringstream logString;

    pthread_mutex_lock(&TOOL_STATUS);
        myHaveToExit = haveToExit;
        listennerState = LISTENNER_FAULTY;
    pthread_mutex_unlock(&TOOL_STATUS);

    if (server_connection)  delete server_connection;

    if (!myHaveToExit && fail) {
        pthread_mutex_lock(&TOOL_STATUS);
            sigReason = DIA__CONF__ERROR;
        pthread_mutex_unlock(&TOOL_STATUS);

        pthread_kill(SignalThreadID ,SIGUSR1);
    }

#ifdef _DIA_PROXY_DEBUG
    logString.clear();
    logString.str("");
    logString << "(ListenerThread): Terminated... " << endl;
    LOG(EVENT, logString.str());
#endif

    pthread_exit(0);

}

//this thread is responsible of handling the server socket used for listening and
//accepting the connection requests coming from the PTCs.
void* _ListenerThread(void *arg)
{ 

    bool myHaveToExit;
        stringstream logString;

    pthread_mutex_lock(&TOOL_STATUS);
        myHaveToExit = haveToExit;
        listennerState = LISTENNER_CONNECTING;
    pthread_mutex_unlock(&TOOL_STATUS);

    if (myHaveToExit)  	pthread_exit(0);

    int errsv, rc;
    logString.clear();
    logString.str("");
    logString << "(ListenerThread): Thread starting up" << endl;
    LOG(EVENT, logString.str());

    server_connection = new TCP_NetworkConnection();

    //creating the server socket
    int srv_sock = server_connection->get_fd();

    if (srv_sock == -1) {
        logString.clear();
        logString.str("");
        logString << "(ListenerThread):  Failed to create TCP server socket" <<endl;
        LOG(ERROR, logString.str());

        resetAndExit (1);
    }

    if (!server_connection->openListener(NULL, dataTool.local_port)){
        logString.clear();
        logString.str("");
        logString << "(ListenerThread):  Failed to open server in "<< dataTool.local_port<<endl;
        logString <<"\tError: " << server_connection->get_error_str() << endl;
        LOG(ERROR, logString.str());

        resetAndExit (1);
    }

    logString.clear();
    logString.str("");
    logString << "(ListenerThread): Server side is listening on "<< server_connection->get_local_peer_str()<<endl;
    LOG(INFO, logString.str());

    pthread_mutex_lock(&TOOL_STATUS);
        listennerState = LISTENNER_READY;
    pthread_mutex_unlock(&TOOL_STATUS);

    struct pollfd fds[1];
    int timeout_msecs = 1000;
    fds[0].fd = srv_sock;
    fds[0].events = POLLIN ;

    NetworkConnection * client_connection;
    int client_index;
    while (true){
        pthread_mutex_lock(&TOOL_STATUS);
            myHaveToExit = haveToExit;
        pthread_mutex_unlock(&TOOL_STATUS);

        if(myHaveToExit){ 
                logString.clear();
            logString.str("");
            logString << "(ListenerThread): Terminating... " <<endl;
            LOG(EVENT, logString.str());

            resetAndExit (0);
        } 

         //passive wait for any activity in the socket
        rc = poll(fds, 1, timeout_msecs);
        if (rc > 0 && (fds[0].revents & POLLIN)) {
            fds[0].revents = 0;

#ifdef _DIA_PROXY_DEBUG
            logString.clear();
            logString.str("");
            logString << "(ListenerThread): TTTCN-client trying to connect. " <<endl;
            LOG(DEBUG, logString.str());
#endif
            time(&lastaction);
            client_index = get_free_client();
            if (client_index == -1){
                logString.clear();
                logString.str("");
                logString << "(ListenerThread): Connection refused. Number of clients exceeded. " <<endl;
                LOG(ERROR, logString.str());

                continue;
            }

            v_client[client_index].net_con = server_connection->accept_client();
            if (!v_client[client_index].net_con){
                logString.clear();
                logString.str("");
                logString << "(ListenerThread): Failed to accept connection try" <<endl;
                logString <<"\tError: " << server_connection->get_error_str() << endl;
                LOG(ERROR, logString.str());

                free_client(client_index);
                continue;
             }

            pthread_mutex_lock(&TOOL_STATUS);
                myDiaProxyState = diaProxyState;
            pthread_mutex_unlock(&TOOL_STATUS);

            if((myDiaProxyState < DIAPROXY_STANDBY) || (myDiaProxyState > DIAPROXY_PROCESSING) ){ 
                v_client[client_index].net_con->client_write(MSG_MAX_CLIENTS_REACHED,strlen(MSG_MAX_CLIENTS_REACHED));

                free_client(client_index);
                continue;
            } 

            long long value;
            value = DEFAULT_RCVBUF;
            int client_fd = v_client[client_index].net_con->get_fd();
            if (setsockopt (client_fd, SOL_SOCKET, SO_RCVBUF, &value, sizeof (value))) {
                errsv = errno;
                logString.clear();
                logString.str("");
                logString << "(ListenerThread): Failed step 1 when changing SO_RCVBUF " << endl;
                logString <<"\tError: " << strerror(errsv) << endl;
                LOG(WARNING, logString.str());
            }

            if (setsockopt (client_fd, SOL_SOCKET, SO_SNDBUF, &value, sizeof (value))) {
                errsv = errno;
                logString.clear();
                logString.str("");
                logString << "(ListenerThread): Failed step 1 when changing SO_SNDBUF " << endl;
                logString <<"\tError: " << strerror(errsv) << endl;
                LOG(WARNING, logString.str());
            }

            logString.clear();
            logString.str("");
            logString << "(ListenerThread): incoming client (socket Id "<< client_fd <<") connecting from ";
            logString << v_client[client_index].net_con->get_remote_peer_str()<< endl;
            LOG(CONNECTIONS, logString.str());

            //once the slot has been identified (client_index), the information is copied
            v_client[client_index].sock = client_fd;
            v_client[client_index].pos = client_index;

            int clientThreadPos;
            if (dataTool.clientsSharingThreads && (numberClientThreads >= dataTool.maxNumberClientThreads)) {
                clientThreadPos = addConnectionToClientThread(client_index);
            }
            else {
                //creating Client Thread
                pthread_attr_t myAttr;
                if (pthread_attr_init(&myAttr)){
                    errsv = errno;
                    logString.clear();
                    logString.str("");
                    logString << "(ListenerThread): Failed to init pthread attr." << endl;
                    logString <<"\tError: " << strerror(errsv) << endl;
                    LOG(ERROR, logString.str());

                    free_client(client_index);
                    resetAndExit (1);
                }
                if (pthread_attr_setstacksize (&myAttr, DEFAULT_STACK_SIZE)){
                    errsv = errno;
                    logString.clear();
                    logString.str("");
                    logString << "(ListenerThread): Failed to change stack size" << endl;
                    logString <<"\tError: " << strerror(errsv) << endl;
                    LOG(ERROR, logString.str());

                    free_client(client_index);
                    resetAndExit (1);
                }
                if (pthread_attr_setdetachstate (&myAttr, PTHREAD_CREATE_DETACHED)){
                    errsv = errno;
                    logString.clear();
                    logString.str("");
                    logString << "(ListenerThread): Failed to change detach state" << endl;
                    logString <<"\tError: " << strerror(errsv) << endl;
                    LOG(ERROR, logString.str());

                    free_client(client_index);
                    resetAndExit (1);

                }
                clientThreadPos = addConnectionToClientThread(client_index);

                if (clientThreadPos == -1) {
                    logString.clear();
                    logString.str("");
                    logString << "(ListenerThread): Error : Too many connections. The max is " << MAX_CLIENTS_THREADS<< endl;
                    LOG(ERROR, logString.str());

                    free_client(client_index);
                    resetAndExit (1);
                }

                int ret = pthread_create(&v_clientThread[clientThreadPos].clientThreadID,&myAttr,_ClientThread,(void*)&v_clientThread[clientThreadPos]);
                if (ret) {
                    errsv = ret;
                    logString.clear();
                    logString.str("");
                    logString << "(ListenerThread): pthread_create returned" << endl;
                    logString <<"\tError: " << strerror(errsv) << endl;
                    LOG(ERROR, logString.str());

                    free_client(client_index);
                    resetAndExit (1);
                }
                pthread_mutex_lock(&TOOL_STATUS);
                    numberClientThreads++;
                pthread_mutex_unlock(&TOOL_STATUS);

                pthread_detach(v_clientThread[clientThreadPos].clientThreadID);

            }
            pthread_mutex_lock(&TOOL_STATUS);
                diaProxyState = DIAPROXY_PROCESSING;
            pthread_mutex_unlock(&TOOL_STATUS);

            couldBeCleaned = true;
            usleep(500);

        } 
    } //while(true)

    if (server_connection)  delete server_connection;

    logString.clear();
    logString.str("");
    logString << "(ListenerThread): Exiting..." << endl;
    LOG(EVENT, logString.str());

    return 0;
} //void* _ListenerThread(void *arg)


int get_free_client()
{
    for(unsigned int index = 0; index < v_client.size(); index++) {
        if (v_client[index].status == OFFLINE){
            v_client[index].status = ONGOING;
            return index;
        }
    }
    return -1;
}
void free_client(int index)
{
    if (v_client[index].net_con)    delete v_client[index].net_con;
    v_client[index].status = OFFLINE;
    v_client[index].net_con = NULL;
    v_client[index].sock = -1;
    v_client[index].status = OFFLINE;
    v_client[index].waitingAnswer = false;
    v_client[index].pos = -1;
    v_client[index].diaServerConnection = -1;
    v_client[index].clientThreadID = 0;
    v_client[index].toreceive = 0;
    v_client[index].received = 0;

}

int addConnectionToClientThread(int clientConnection)
{

    if (dataTool.clientsSharingThreads)	{
        if (nextClientThread < (dataTool.maxNumberClientThreads - 1)) {
            nextClientThread++;
        }
        else nextClientThread = 0;
    }
    else {
        int max = v_clientThread.size() -1;
        if (nextClientThread < max) {
            nextClientThread++;
        }
        else return -1;
    }

    pthread_mutex_lock(&CLIENT_THREAD_VECTOR);
        v_clientThread[nextClientThread].conectionClients.push_back(clientConnection);
    pthread_mutex_unlock(&CLIENT_THREAD_VECTOR);

    pthread_mutex_lock(&CLIENT_VECTOR);
        int sock = v_client[clientConnection].sock;
        v_client[clientConnection].fd_index = v_clientThread[nextClientThread].nfds;
    pthread_mutex_unlock(&CLIENT_VECTOR);

    pthread_mutex_lock(&CLIENT_THREAD_VECTOR);
        v_clientThread[nextClientThread].fds[v_clientThread[nextClientThread].nfds] = {sock, 0, 0};
        (v_clientThread[nextClientThread].nfds)++;

    pthread_mutex_unlock(&CLIENT_THREAD_VECTOR);

    pthread_mutex_lock(&CLIENT_VECTOR);
        v_client[clientConnection].status = ONLINE;
        v_client[clientConnection].clientThreadID = v_clientThread[nextClientThread].clientThreadID ;
    pthread_mutex_unlock(&CLIENT_VECTOR);

    MessageToSendDeque pendingMessages;
    pthread_mutex_lock(&PENDING_MESSAGE_MAP);
        bool inserted = m_pendingToSend.insert(std::make_pair(sock , pendingMessages)).second;
    pthread_mutex_unlock(&PENDING_MESSAGE_MAP);

    if (not inserted) { return -1;}

    dataTool.activeTTCNConnections++;
    return nextClientThread;

}

int setNonblocking(int fd)
{
 int flags, s;

  flags = fcntl (fd, F_GETFL, 0);
  if (flags == -1)
    {
      perror ("fcntl");
      return -1;
    }

  flags |= O_NONBLOCK;
  s = fcntl (fd, F_SETFL, flags);
  if (s == -1)
    {
      perror ("fcntl");
      return -1;
    }

  return 0;

}
int setBlocking(int fd)
{
 int flags, s;

  flags = fcntl (fd, F_GETFL, 0);
  if (flags == -1)
    {
      perror ("fcntl");
      return -1;
    }

  flags ^= O_NONBLOCK;
  s = fcntl (fd, F_SETFL, flags);
  if (s == -1)
    {
      perror ("fcntl");
      return -1;
    }

  return 0;

}
