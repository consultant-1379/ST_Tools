#include "networkLayerTranslator.h"

#include <vector>

extern pthread_t SignalThreadID;
extern SignalReason sigReason;

extern ToolData toolData;
extern std::vector<Listener> v_listeners;
extern std::vector<Connection> v_connections;

using namespace std;

void* _ConnectionThread(void *arg)
{

    Connection *myConnection = (Connection *)arg;
    int errsv;
    stringstream logString;
    logString.clear();
    logString.str("");
    logString << "_ConnectionThread "<< myConnection->threadID <<": Thread Starting" << endl;
    LOG(INFO, logString.str());
    
    if (myConnection->be_ssl){
        struct Credentials cred;
        cred.CertFile = toolData.client_cert_file;
        cred.KeyFile = toolData.client_key_file;
        cred.CA_File = toolData.ca_file;
        cred.password = ("ericsson");

        if (myConnection->be_sctp)      myConnection->be_connection = new DTLS_NetworkConnection(myConnection->be_ipv6);
        else                            myConnection->be_connection = new TLS_NetworkConnection(myConnection->be_ipv6);
        
        if (!myConnection->be_connection->set_method_name(myConnection->be_ssl_protocol)){
            logString.clear();
            logString.str("");
            logString << "_ConnectionThread "<< myConnection->threadID <<": Error in set_method_name: "<< myConnection->be_connection->get_error_str()  << endl;
            LOG(ERROR, logString.str());

            connectionResetAndExit(myConnection,EXECUTION_ERROR);
        }
        if (!myConnection->be_connection->init_client_SSL(cred)){
            logString.clear();
            logString.str("");
            logString << "_ConnectionThread "<< myConnection->threadID<<": " << myConnection->be_connection->get_error_str() << endl;
            LOG(ERROR, logString.str());

            connectionResetAndExit(myConnection,EXECUTION_ERROR);
        }
    }
    else{
        if (myConnection->be_sctp)      myConnection->be_connection = new SCTP_NetworkConnection(myConnection->be_ipv6);
        else                            myConnection->be_connection = new TCP_NetworkConnection(myConnection->be_ipv6);
    }
        
        
    int sock = myConnection->be_connection->get_fd();

    if(sock == -1) { 
        logString.clear();
        logString.str("");
        logString << "_ConnectionThread "<< myConnection->threadID <<": error in myConnection->be_connection->get_fd" << endl; 
        LOG(ERROR, logString.str());

        connectionResetAndExit(myConnection,EXECUTION_ERROR);
    }

    struct timeval sendTimer;
    sendTimer.tv_sec = DEFAULT_SEND_TIME;
    sendTimer.tv_usec = 0;

    long long value;
    value = DEFAULT_RCVBUF;
    if (setsockopt (sock, SOL_SOCKET, SO_SNDTIMEO, &sendTimer, sizeof (sendTimer))) {
        errsv = errno;
        logString.clear();
        logString.str("");
        logString << "_ConnectionThread "<< myConnection->threadID <<": Failed when changing SO_SNDTIMEO -> ";
        logString << strerror(errsv) << endl;
        LOG(ERROR, logString.str());

        connectionResetAndExit(myConnection,EXECUTION_ERROR);
    }

    value = DEFAULT_RCVBUF;
    if (setsockopt (sock, SOL_SOCKET, SO_RCVBUF, &value, sizeof (value))) {
        errsv = errno;
        logString.clear();
        logString.str("");
        logString << "_ConnectionThread "<< myConnection->threadID <<": Failed when changing SO_RCVBUF -> ";
        logString << strerror(errsv) << endl;
        LOG(ERROR, logString.str());

        connectionResetAndExit(myConnection,EXECUTION_ERROR);
    }

    if (setsockopt (sock, SOL_SOCKET, SO_SNDBUF, &value, sizeof (value))) {
        errsv = errno;
        logString.clear();
        logString.str("");
        logString << "_ConnectionThread "<< myConnection->threadID <<": Failed when changing SO_SNDBUF -> ";
        logString << strerror(errsv) << endl;
        LOG(ERROR, logString.str());

        connectionResetAndExit(myConnection,EXECUTION_ERROR);
    }

    string nic_ip = get_nic_ip_to_dest_host(myConnection->be_ip);
    if (nic_ip == ""){
        logString.clear();
        logString.str("");
        logString << "_ConnectionThread "<< myConnection->threadID <<": Failed getting nic_ip" <<endl;
        LOG(ERROR, logString.str());

        connectionResetAndExit(myConnection,EXECUTION_ERROR);
    }

    if (!myConnection->be_connection->set_local_addr(nic_ip.c_str())){        
        logString.clear();
        logString.str("");
        logString << "_ConnectionThread "<< myConnection->threadID <<": "<< myConnection->be_connection->get_error_str() << endl;
        LOG(ERROR, logString.str());

        connectionResetAndExit(myConnection,EXECUTION_ERROR);
    }
 
    if (!myConnection->be_connection->bind_socket()){
        logString.clear();
        logString.str("");
        logString << "_ConnectionThread "<< myConnection->threadID<<": " << myConnection->be_connection->get_error_str() << endl;
        LOG(ERROR, logString.str());

        connectionResetAndExit(myConnection,EXECUTION_ERROR);
    }

    logString.clear();
    logString.str("");
    logString << "_ConnectionThread "<< myConnection->threadID <<": Trying to connect to ";
    logString << myConnection->be_ip.c_str()<<" : "<<  myConnection->be_port << endl;
    LOG(CONNECTIONS, logString.str());

    if (!myConnection->be_connection->client_connect(myConnection->be_ip.c_str(), myConnection->be_port)){
        logString.clear();
        logString.str("");
        logString << "_ConnectionThread "<< myConnection->threadID << ": Error in client_connect to ";
        logString << myConnection->be_ip <<" : "<< myConnection->be_port << endl;
        logString << myConnection->be_connection->get_error_str() << endl;
        LOG(ERROR, logString.str());

        connectionResetAndExit(myConnection,EXECUTION_ERROR);
    }

    logString.clear();
    logString.str("");
    logString << "_ConnectionThread "<< myConnection->threadID <<": Network connection (socked id " <<sock << ")";
    logString << " from " << myConnection->be_connection->get_local_peer_str();
    logString << "   to   " << myConnection->be_connection->get_remote_peer_str() << endl;
    LOG(CONNECTIONS, logString.str());

    struct pollfd fds[2];
    int timeout_msecs = 200;
    fds[0].fd = myConnection->be_connection->get_fd();
    fds[1].fd = myConnection->fe_connection->get_fd();

    char buf[4096];
    int bytes, rc;

    while (true){
        if (toolData.status == HAVE_TO_EXIT){
            logString.clear();
            logString.str("");
            logString << "_ConnectionThread "<< myConnection->threadID <<": Have to exit." << endl;
            LOG(INFO, logString.str());

            connectionResetAndExit(myConnection,NO_REASON);
        }

        fds[0].events = POLLIN ;
        fds[1].events = POLLIN ;
        if (!myConnection->toBeSendToBackEnd.empty())   fds[0].events = POLLIN | POLLOUT ;
        if (!myConnection->toBeSendToFrontEnd.empty())  fds[1].events = POLLIN | POLLOUT ;
        
        rc = poll(fds, 2, timeout_msecs);
        if (rc <=0)     continue;

        if((fds[0].revents & POLLOUT) && !myConnection->toBeSendToBackEnd.empty()) { 
            if (!send_message(&myConnection->toBeSendToBackEnd, myConnection->be_connection, myConnection->be_ssl, myConnection->ssl, myConnection->threadID)){
                logString.clear();
                logString.str("");
                logString << "_ConnectionThread "<< myConnection->threadID <<": sending to BackEnd error" << endl;
                LOG(ERROR, logString.str());

                connectionResetAndExit(myConnection,NO_REASON);
            }
        }                        
    
        if((fds[1].revents & POLLOUT)  && !myConnection->toBeSendToFrontEnd.empty()) { 
            if (!send_message(&myConnection->toBeSendToFrontEnd, myConnection->fe_connection, myConnection->fe_ssl, myConnection->ssl, myConnection->threadID)){
                logString.clear();
                logString.str("");
                logString << "_ConnectionThread "<< myConnection->threadID <<": sending to FrontEnd error" << endl;
                LOG(ERROR, logString.str());

                connectionResetAndExit(myConnection,NO_REASON);
            }
        }                        
    
        if(fds[0].revents & POLLIN || myConnection->be_connection->ssl_pending_bytes() > 0) { 
            bytes = myConnection->be_connection->client_read(buf, sizeof(buf));
            if (bytes == 0){
                logString.clear();
                logString.str("");
                logString << "_ConnectionThread "<< myConnection->threadID <<": connection closed by BackEnd " << endl;
                LOG(CONNECTIONS, logString.str());

                connectionResetAndExit(myConnection,NO_REASON);
            }
            if (bytes == -1){
                logString.clear();
                logString.str("");
                logString << "_ConnectionThread "<< myConnection->threadID <<": connection to BackEnd broken" << endl;
                LOG(CONNECTIONS, logString.str());

                connectionResetAndExit(myConnection,NO_REASON);
            }

#ifdef _NLT_DEBUG
            logString.clear();
            logString.str("");
            logString  << "_ConnectionThread "<< myConnection->threadID <<": received " << bytes << " from BackEnd" << endl;
            LOG(DEBUG, logString.str());
#endif
            struct Message message;
            message.bytes_sent = 0;
            message.message_len =  bytes;
            message.buffer = new unsigned char [message.message_len];
            memcpy(message.buffer, buf, message.message_len);
            myConnection->toBeSendToFrontEnd.push_back(message);
        }  

        if(fds[1].revents & POLLIN || myConnection->fe_connection->ssl_pending_bytes() > 0) { 
            bytes = myConnection->fe_connection->client_read(buf, sizeof(buf)); /* get reply & decrypt */
            if (bytes == 0){
                logString.clear();
                logString.str("");
                logString << "_ConnectionThread "<< myConnection->threadID <<": connection closed by FrontEnd " << endl;
                LOG(CONNECTIONS, logString.str());

                connectionResetAndExit(myConnection,NO_REASON);
            }
            if (bytes == -1){
                logString.clear();
                logString.str("");
                logString << "_ConnectionThread "<< myConnection->threadID <<": connection to FrontEnd broken" << endl;
                LOG(CONNECTIONS, logString.str());

                connectionResetAndExit(myConnection,NO_REASON);
            }
            
#ifdef _NLT_DEBUG
            logString.clear();
            logString.str("");
            logString  << "_ConnectionThread "<< myConnection->threadID <<": received " << bytes << " from FrontEnd" << endl;
            LOG(DEBUG, logString.str());
#endif

            struct Message message;
            message.bytes_sent = 0;
            message.message_len =  bytes;
            message.buffer = new unsigned char [message.message_len];
            memcpy(message.buffer, buf, message.message_len);
            myConnection->toBeSendToBackEnd.push_back(message);           
        }
        fds[0].revents=0;
        fds[1].revents=0;       
    }
    

}

bool send_message(MessageToSendDeque * messages, NetworkConnection *net_con, bool use_ssl, SSL *ssl, pthread_t threadID)
{
#ifdef _NLT_DEBUG
    logString.clear();
    logString.str("");
    logString  << "_ConnectionThread "<< threadID <<": executing send_message"<<endl;
    LOG(DEBUG, logString.str());
#endif

    int res_sending = 0;
    int errsv;
    bool keep_sending = true;
    struct Message message;

    while (! (messages->empty()) && keep_sending){
        message = messages->front();
        if (message.message_len > 0){
#ifdef _NLT_DEBUG
            logString.clear();
            logString.str("");
            logString  << "_ConnectionThread "<< threadID <<": message.message_len: "<<message.message_len << endl ;
            LOG(DEBUG, logString.str());
#endif

            res_sending = net_con->client_write((const char*)(message.buffer + message.bytes_sent),
                                                message.message_len - message.bytes_sent);
#ifdef _NLT_DEBUG
            logString.clear();
            logString.str("");
            logString  << "_ConnectionThread "<< threadID << ":  res_sending: "<<res_sending << endl;
            LOG(DEBUG, logString.str());
#endif
            errsv = net_con->get_errsv();
            
            if ( res_sending == message.message_len-message.bytes_sent ||
                    res_sending == -1 ||
                    (res_sending == 0 && errsv==0)) {
                
                if (res_sending == -1 ) {
                    if (errsv == EAGAIN) {
                        return true;
                    }
                }
                if (res_sending == 0) {
                }

                messages->pop_front();
                delete [] message.buffer;
            }

            else  {
                    messages->front().bytes_sent += res_sending;
#ifdef _NLT_DEBUG
                    logString.clear();
                    logString.str("");
                    logString  << "_ConnectionThread "<< threadID <<  ": message.bytes_sent: "<<message.bytes_sent << endl;
                    LOG(DEBUG, logString.str());
#endif
                    keep_sending = false;
            }
        }
    }

    return   res_sending>0?true:false;
}


void cleanPendingMessages(MessageToSendDeque * messages, pthread_t threadID)
{
    stringstream logString;
#ifdef _NLT_DEBUG
    logString.clear();
    logString.str("");
    logString  << "_ConnectionThread "<< threadID <<": executing cleanPendingMessages"<<endl;
    LOG(DEBUG, logString.str());
#endif

    struct Message message;
    while (! (messages->empty())){
        message = messages->front();
        messages->pop_front();
        delete [] message.buffer;
    }
}

void connectionResetAndExit (Connection *myConnection, int fail)
{
    stringstream logString;
#ifdef _NLT_DEBUG
    logString.clear();
    logString.str("");
    logString  << "_ConnectionThread "<< myConnection->threadID <<": executing connectionResetAndExit"<<endl;
    LOG(DEBUG, logString.str());
#endif

    cleanPendingMessages(&(myConnection->toBeSendToFrontEnd), myConnection->threadID);
    cleanPendingMessages(&(myConnection->toBeSendToBackEnd), myConnection->threadID);

    if (myConnection->be_connection != NULL)            delete  myConnection->be_connection;
    if (myConnection->fe_connection != NULL)            delete  myConnection->fe_connection;

    if (fail) {
        sigReason = CONF_ERROR;
        pthread_kill(SignalThreadID ,SIGUSR1);
    }
    
    logString.clear();
    logString.str("");
    logString  << "_ConnectionThread "<< myConnection->threadID <<": Thread terminated " << endl;
    LOG(INFO, logString.str());
    initializeConnection(myConnection);
    pthread_exit(0);
}

void initializeConnection(Connection *myConnection)
{
    myConnection->threadID=NULL;
    myConnection->used = false;
    myConnection->be_connection = NULL;
    myConnection->fe_connection != NULL;
    myConnection->be_ip = "";
    myConnection->be_port = -1;
    myConnection->be_ssl = false;
    myConnection->fe_ssl = false;
    myConnection->be_sctp = false;

}