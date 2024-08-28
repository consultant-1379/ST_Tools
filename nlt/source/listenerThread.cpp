#include "networkLayerTranslator.h"

extern pthread_mutex_t CONNECTION_VECTOR;
extern pthread_t SignalThreadID;
extern SignalReason sigReason;

extern ToolData toolData;
extern std::vector<Listener> v_listeners;
extern std::vector<Connection> v_connections;

using namespace std;

void* _ListenerThread(void *arg)
{

    Listener *myListener = (Listener *)arg;
    stringstream logString;
    int errsv;
    int sock;
    logString.clear();
    logString.str("");
    logString << "_ListenerThread "<< myListener->name <<": Thread starting... " << endl;
    LOG(INFO, logString.str());

    if (toolData.status == HAVE_TO_EXIT){
        logString.clear();
        logString.str("");
        logString << "_ListenerThread "<< myListener->name <<": Have to exit." << endl;
        LOG(INFO, logString.str());

        listenerResetAndExit(myListener,NO_REASON);
    }

    if (myListener->fe_ssl){
        struct Credentials cred;
        cred.CertFile = toolData.server_cert_file;
        cred.KeyFile = toolData.server_key_file;
        cred.CA_File = toolData.ca_file;
        cred.password = ("ericsson");

        if (myListener->fe_sctp)      myListener->server = new DTLS_NetworkConnection(myListener->fe_ipv6);
        else                          myListener->server = new TLS_NetworkConnection(myListener->fe_ipv6);

        if (!myListener->server->set_method_name(myListener->fe_ssl_protocol)){
            logString.clear();
            logString.str("");
            logString <<  "_ListenerThread "<< myListener->name <<": Error in set_method_name: "<< myListener->server->get_error_str()  << endl;;
            LOG(ERROR, logString.str());

            listenerResetAndExit(myListener,EXECUTION_ERROR);
        }
        if (!myListener->server->init_server_SSL(cred, myListener->fe_ssl_req_cred)){
            logString.clear();
            logString.str("");
            logString <<  "_ListenerThread "<< myListener->name <<": Error in init_server_SSL: "<< myListener->server->get_error_str()  << endl;;
            LOG(ERROR, logString.str());

            listenerResetAndExit(myListener,EXECUTION_ERROR);
        }
    }
    else{
        if (myListener->fe_sctp)      myListener->server = new SCTP_NetworkConnection(myListener->fe_ipv6);
        else                          myListener->server = new TCP_NetworkConnection(myListener->fe_ipv6);
    }
    
    if(myListener->server->get_fd() == -1) { 
        logString.clear();
        logString.str("");
        logString << "_ListenerThread "<< myListener->name <<": Error in myListener->server->get_fd" << endl;        
        LOG(ERROR, logString.str());

        listenerResetAndExit(myListener,EXECUTION_ERROR);
    }

    myListener->server->openListener(myListener->fe_ip.c_str(), myListener->fe_port);

    pthread_attr_t myAttr;
    if (pthread_attr_init(&myAttr)){
        errsv = errno;
        logString.clear();
        logString.str("");
        logString << "_ListenerThread "<< myListener->name <<": Failed to init pthread attr." << endl;
        logString <<"\tError: " << strerror(errsv) << endl;
        LOG(ERROR, logString.str());

        listenerResetAndExit(myListener,EXECUTION_ERROR);
    }
    if (pthread_attr_setstacksize (&myAttr, DEFAULT_STACK_SIZE)){
        errsv = errno;
        logString.clear();
        logString.str("");
        logString << "_ListenerThread "<< myListener->name <<": Failed to change stack size" << endl;
        logString <<"\tError: " << strerror(errsv) << endl;
        LOG(ERROR, logString.str());

        listenerResetAndExit(myListener,EXECUTION_ERROR);
    }

    if (pthread_attr_setdetachstate (&myAttr, PTHREAD_CREATE_DETACHED)){
        errsv = errno;
        logString.clear();
        logString.str("");
        logString << "_ListenerThread "<< myListener->name <<": Failed to change detach state" << endl;
        logString <<"\tError: " << strerror(errsv) << endl;
        LOG(ERROR, logString.str());

        listenerResetAndExit(myListener,EXECUTION_ERROR);
    }

    struct pollfd fds[1];
    int timeout_msecs = 1000;
    fds[0].fd = myListener->server->get_fd();
    fds[0].events = POLLIN ;
    int rc;

    int con_index;
    
    while (true){
        if (toolData.status == HAVE_TO_EXIT){
            logString.clear();
            logString.str("");
            logString  << "_ListenerThread "<< myListener->name <<": Have to exit." << endl;
            LOG(EVENT, logString.str());
            
            listenerResetAndExit(myListener,NO_REASON);
        }

        //passive wait for any activity in the socket
        rc = poll(fds, 1, timeout_msecs);
        if (rc > 0 && (fds[0].revents & POLLIN)) {
            fds[0].revents = 0;
            pthread_mutex_lock(&CONNECTION_VECTOR);
                con_index = get_free_connection();          
            pthread_mutex_unlock(&CONNECTION_VECTOR);
            if(con_index < 0) { 
                logString.clear();
                logString.str("");
                logString  << "_ListenerThread "<< myListener->name <<": There are not free connections records. Max number is " << toolData.numberOfConnections <<endl;
                LOG(ERROR, logString.str());

                listenerResetAndExit(myListener,EXECUTION_ERROR);
            } 

            v_connections[con_index].fe_connection = myListener->server->accept_client();
            if (!v_connections[con_index].fe_connection) {
                logString.clear();
                logString.str("");
                logString  << "_ListenerThread "<< myListener->name <<": Problem creating client connection -> ";
                logString << myListener->server->get_error_str() << endl;
                connectionResetAndExit (&v_connections[con_index], NO_REASON);
                continue;
            }

            sock = v_connections[con_index].fe_connection->get_fd();
#ifdef _NLT_DEBUG
            logString.clear();
            logString.str("");
            logString  << "_ListenerThread "<< myListener->name <<": Accepted connection with socket: " << sock <<endl;
            LOG(DEBUG, logString.str());
#endif

            if(sock > 1023) { 
                logString.clear();
                logString.str("");
                logString  << "_ListenerThread "<< myListener->name <<": Returned fd is higher than 1023. Messages for this connection wont be processed. " <<endl;
                LOG(ERROR, logString.str());

                listenerResetAndExit(myListener,EXECUTION_ERROR);
            } 

            long long value;
            value = DEFAULT_RCVBUF;
            if (setsockopt (sock, SOL_SOCKET, SO_RCVBUF, &value, sizeof (value))) {
                errsv = errno;
                logString.clear();
                logString.str("");
                logString  << "_ListenerThread "<< myListener->name <<": Failed step 1 when changing SO_RCVBUF -> ";
                logString << strerror(errsv) << endl;
                LOG(WARNING, logString.str());

            }

            if (setsockopt (sock, SOL_SOCKET, SO_SNDBUF, &value, sizeof (value))) {
                errsv = errno;
                logString.clear();
                logString.str("");
                logString  << "_ListenerThread "<< myListener->name <<": Failed step 1 when changing SO_SNDBUF -> " ;
                logString << strerror(errsv) << endl;
                LOG(WARNING, logString.str());
            }

            logString.clear();
            logString.str("");
            logString  << "_ListenerThread "<< myListener->name << ": Incoming client (socket Id "<< sock <<") connecting from ";
            logString << myListener->server->get_remote_peer_str()<< endl;
            LOG(CONNECTIONS, logString.str());

            v_connections[con_index].be_ssl = myListener->be_ssl;
            v_connections[con_index].be_ssl_protocol = myListener->be_ssl_protocol;
            v_connections[con_index].be_ipv6 = myListener->be_ipv6;
            v_connections[con_index].fe_ssl = myListener->fe_ssl;
            v_connections[con_index].be_ip = myListener->be_ip;
            v_connections[con_index].be_port = myListener->be_port;
            v_connections[con_index].be_sctp = myListener->be_sctp;

            int result = pthread_create(&v_connections[con_index].threadID,&myAttr,_ConnectionThread,(void*)&v_connections[con_index]);
            if (result) {
                errsv = result;
                logString.clear();
                logString.str("");
                logString  << "_ListenerThread "<< myListener->name <<": pthread_create returned ";
                logString << strerror(errsv) << endl;
                LOG(ERROR, logString.str());

                listenerResetAndExit(myListener,EXECUTION_ERROR);
            }

            pthread_detach(v_connections[con_index].threadID);
        }
    }
}

int get_free_connection()
{
    for(unsigned int index = 0; index < v_connections.size(); index++) {
        if (!v_connections[index].used){
            v_connections[index].used=true;
            return index;
        }
    }
    return -1;
}

void listenerResetAndExit (Listener *myListener, int fail)
{
    stringstream logString;
    if (myListener->server != NULL)    delete myListener->server;

    if (fail) {
        sigReason = CONF_ERROR;
        pthread_kill(SignalThreadID ,SIGUSR1);
    }

    logString.clear();
    logString.str("");
    logString  << "_ListenerThread "<< myListener->name <<": Thread terminated " << endl;
    LOG(INFO, logString.str());
   pthread_exit(0);
}
