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


#include "DiaProxy.h"
#include "ClientThread.h"
#include "DiaThread.h"
#include "Logger.h"
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
extern CER_DATA cer_data;
extern int local_port;

extern std::vector<DiaServerConnection> v_connections;
extern std::vector<ClientConnection> v_client;
extern std::vector<clientThread> v_clientThread;
extern PendingToSendMap  m_pendingToSend;

struct DiaServerConnection *servCon = NULL;
extern unsigned int nextConnection;
int srv_sock;
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

    if (srv_sock != -1)	close (srv_sock);	
    
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
    LOG(DEBUG, logString.str());
    
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
	int errsv;

        logString.clear();
        logString.str("");
        logString << "(ListenerThread): Thread starting up" << endl;
        LOG(EVENT, logString.str());
        
	//creating the server socket
	srv_sock = socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);

	if (srv_sock == -1)	//if error in socket creation
	{
	    errsv = errno;

	    logString.clear();
	    logString.str("");
	    logString << "(ListenerThread):  Failed to create TCP server socket" <<endl;
	    logString <<"\tError: " << strerror(errsv) << endl;
	    LOG(ERROR, logString.str());
            
	    resetAndExit (1);
	}

        errsv = setNonblocking(srv_sock);
        
 	if (errsv == -1)	
	{
	    logString.clear();
	    logString.str("");
	    logString << "(ListenerThread):  Failed to set NONBLOCKING on socket" <<endl;
	    logString <<"\tError: " << strerror(errsv) << endl;
	    LOG(ERROR, logString.str());
		
	    resetAndExit (1);
	}

	struct sockaddr_in local_addr;
	memset(&local_addr,0,sizeof(local_addr));
	local_addr.sin_family = AF_INET;
	local_addr.sin_addr.s_addr = INADDR_ANY;
	local_addr.sin_port = htons(local_port);

	struct sockaddr_in remote_addr;
	memset(&remote_addr,0,sizeof(sockaddr_in));

	//binding the socket to a local port
	if(bind(srv_sock,(sockaddr*)&local_addr, sizeof(local_addr)) == -1)
	{
	    errsv = errno;

	    logString.clear();
	    logString.str("");
	    logString << "(ListenerThread):  Failed to bind socket on port "<< local_port<<endl;
	    logString <<"\tError: " << strerror(errsv) << endl;
	    LOG(ERROR, logString.str());
            
	    resetAndExit (1);
	}
	
	//the socket stars listening in the local port
	listen(srv_sock, 5);	//backlog of 5 (number of maximum pending connections for accepting)
	
	logString.clear();
	logString.str("");
        logString << "(ListenerThread): Server side is listening on port "<< htons(local_addr.sin_port)<<endl;
        LOG(INFO, logString.str());

	pthread_mutex_lock(&TOOL_STATUS);
	    listennerState = LISTENNER_READY;
	pthread_mutex_unlock(&TOOL_STATUS);
	
	int sock;	//this socket will be initialized when a connection request arrives
	socklen_t len = sizeof(remote_addr);

	fd_set fds;
	fd_set tmpset;
	struct timeval tv;
	tv.tv_sec = 2;
	tv.tv_usec = 0;
	
	//subscribing the server socket to the mask to be used in the 'select'
	FD_ZERO(&fds);
	FD_SET(srv_sock, &fds);

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

		tmpset = fds;
		tv.tv_sec = 2;
		tv.tv_usec = 0;

		//passive wait for any activity in the socket
		select(srv_sock+1,&tmpset, NULL, NULL, &tv);

		//let's check if the server socket was the one that finished the
		//invokation of 'select'
		if(FD_ISSET(srv_sock, &tmpset))
		{ //if(FD_ISSET(fd, &tmpset))
		
#ifdef _DIA_PROXY_DEBUG
       			logString.clear();
			logString.str("");
			logString << "(ListenerThread): TTTCN-client trying to connect. " <<endl;
			LOG(DEBUG, logString.str());
#endif

			time(&lastaction);
			sock = accept(srv_sock,(sockaddr*)&remote_addr,&len);
                        
 			if(sock > 1023) { 
       			    logString.clear();
			    logString.str("");
			    logString << "(ListenerThread): Returned fd is higher than 1023. Messages for this connection wont be processed. " <<endl;
			    LOG(ERROR, logString.str());
			} 
			
                    int status = fcntl(sock, F_SETFL, fcntl(sock, F_GETFL, 0) | O_NONBLOCK);

                    if (status == -1){
	                errsv = errno;
	                logString.clear();
	                logString.str("");
	                logString << "(ListenerThread): Failed setting O_NONBLOCK for sockid " << sock <<endl;
	                logString <<"\tError: " << strerror(errsv) << endl;
	                LOG(ERROR, logString.str());
                    }
            
            
			pthread_mutex_lock(&TOOL_STATUS);
				myDiaProxyState = diaProxyState;
			pthread_mutex_unlock(&TOOL_STATUS);
				
				if((myDiaProxyState < DIAPROXY_STANDBY) || (myDiaProxyState > DIAPROXY_PROCESSING) ){ 
					//closing connetions towards the clients
					sendto(sock,MSG_MAX_CLIENTS_REACHED,strlen(MSG_MAX_CLIENTS_REACHED)+1,0,(sockaddr*)&remote_addr,sizeof(remote_addr));
					close(sock);
					continue;
				} 

        		long long value;
			socklen_t value_len = sizeof (value);
        
        		value = DEFAULT_RCVBUF;
        		if (setsockopt (sock, SOL_SOCKET, SO_RCVBUF, &value, sizeof (value))) {
	                    errsv = errno;
	                    logString.clear();
	                    logString.str("");
	                    logString << "(ListenerThread): Failed step 1 when changing SO_RCVBUF " << endl;
	                    logString <<"\tError: " << strerror(errsv) << endl;
	                    LOG(WARNING, logString.str());
			}

        		if (setsockopt (sock, SOL_SOCKET, SO_SNDBUF, &value, sizeof (value))) {
	                    errsv = errno;
	                    logString.clear();
	                    logString.str("");
	                    logString << "(ListenerThread): Failed step 1 when changing SO_SNDBUF " << endl;
	                    logString <<"\tError: " << strerror(errsv) << endl;
	                    LOG(WARNING, logString.str());
			}

	                logString.clear();
	                logString.str("");
	                logString << "(ListenerThread): incoming client (socket Id "<< sock <<") connecting from ";
                        logString << inet_ntoa(remote_addr.sin_addr)<< ":" << ntohs(remote_addr.sin_port)<< endl;
	                LOG(CONNECTIONS, logString.str());
                        
			int nr = 0;
			//while forever (a break exists for getting out of the loop)
			while(true){ 

				//if maximum number of clients is reached
				if(nr == cer_data.numberOfClients){ 
	                            logString.clear();
	                            logString.str("");
	                            logString << "(ListenerThread): Maximum connection reachead" << endl;
	                            LOG(WARNING, logString.str());
                                    
				    //closing connetions towards the clients
				    sendto(sock,MSG_MAX_CLIENTS_REACHED,strlen(MSG_MAX_CLIENTS_REACHED)+1,0,(sockaddr*)&remote_addr,sizeof(remote_addr));
				    close(sock);
				    break;
				} 
				//searching for an empty slot for inserting the client
				if(v_client[nr].status == OFFLINE){
					//once the slot has been identified (nr), the information is copied
					int conFound = findConnection();
					if (conFound == -1) {
	                                    logString.clear();
	                                    logString.str("");
	                                    logString << "(ListenerThread): Not connection to Diameter server" << endl;
	                                    LOG(ERROR, logString.str());
                                            
					    resetAndExit (1);
					}
					
					memcpy(&v_client[nr].remote_addr,&remote_addr,sizeof(remote_addr));
					v_client[nr].sock = sock;
					v_client[nr].pos = nr;
					v_client[nr].diaServerConnection = conFound;
                                        if (cer_data.ism_port) {
						v_client[nr].esmServerConnection = conFound;
						v_client[nr].ismServerConnection = 0;		//The first connection will be used for ISM messages on a EPC scenario
                                        }
                                        else {
						v_client[nr].esmServerConnection = conFound;
						v_client[nr].ismServerConnection = conFound;
                                        }

                    int clientThreadPos;

                    if (cer_data.clientsSharingThreads && (numberClientThreads >= cer_data.maxNumberClientThreads)) {
                    	clientThreadPos = addConnectionToClientThread(nr);
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
                            
                    	    resetAndExit (1);
                    	}
                    	if (pthread_attr_setstacksize (&myAttr, DEFAULT_STACK_SIZE)){
	                    errsv = errno;
	                    logString.clear();
	                    logString.str("");
	                    logString << "(ListenerThread): Failed to change stack size" << endl;
	                    logString <<"\tError: " << strerror(errsv) << endl;
	                    LOG(ERROR, logString.str());

                    	    resetAndExit (1);
                    	}
                    	if (pthread_attr_setdetachstate (&myAttr, PTHREAD_CREATE_DETACHED)){
	                    errsv = errno;
	                    logString.clear();
	                    logString.str("");
	                    logString << "(ListenerThread): Failed to change detach state" << endl;
	                    logString <<"\tError: " << strerror(errsv) << endl;
	                    LOG(ERROR, logString.str());

                    	    resetAndExit (1);

                    	}
                    	clientThreadPos = addConnectionToClientThread(nr);

                    	if (clientThreadPos == -1) {
	                    logString.clear();
	                    logString.str("");
	                    logString << "(ListenerThread): Error : Too many connections. The max is " << MAX_CLIENTS_THREADS<< endl;
	                    LOG(ERROR, logString.str());

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

					v_connections[conFound].numberOfClients++;
					v_connections[conFound].totalNumberOfClients++;

					couldBeCleaned = true;
					usleep(500);
					break; //get out of the while

				}
				//incrementing the variable for going on searching an empty slot
				nr++;
			} //while(true)
		} //if(FD_ISSET(fd, &tmpset))
	} //while(true)
        
        logString.clear();
        logString.str("");
        logString << "(ListenerThread): Exiting..." << endl;
        LOG(EVENT, logString.str());

	return 0;
} //void* _ListenerThread(void *arg)


void close_server_socket () 
{
	if (srv_sock != -1)	close (srv_sock);
}


int findConnection()
{
	int index = nextConnection;
	unsigned int searches = 1;
	char logline[1024];	

	do {
            pthread_mutex_lock(&CONNECTION_VECTOR);
                ConnectionStatus status = v_connections[index].status;
                ConnectionType type = v_connections[index].type;
            pthread_mutex_unlock(&CONNECTION_VECTOR);
            
		if (status == CONNECTED && type == GENERIC) {
			if (nextConnection < v_connections.size() -1)	nextConnection++;
			else nextConnection = 0;
			
			return index;
			
		}
		else {
			searches++;
			if (searches > v_connections.size())	return -1;
			else					index++;
		}
	} while (true);
}


int addConnectionToClientThread(int clientConnection)
{

	if (cer_data.clientsSharingThreads)	{
		if (nextClientThread < (cer_data.maxNumberClientThreads - 1)) {
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
 	pthread_mutex_unlock(&CLIENT_VECTOR);
           
	pthread_mutex_lock(&CLIENT_THREAD_VECTOR);
	    FD_SET(sock, &v_clientThread[nextClientThread].fds);
	    if (sock >= v_clientThread[nextClientThread].maxFd)
		    v_clientThread[nextClientThread].maxFd = sock + 1;
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
