#ifndef NETLAYERTRANSLATOR_H
#define NETLAYERTRANSLATOR_H
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <iostream>
#include <fstream>
#include <algorithm>

#include <netinet/in.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <netdb.h>
#include <errno.h>
#include <time.h>
#include <signal.h>
#include <pthread.h>
#include <signal.h>
#include <sys/ioctl.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <net/if.h>
#include <stropts.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <netdb.h>
#include <sys/timeb.h>
#include <fcntl.h>
#include <termios.h>
#include <sys/time.h>
#include <deque>

#include <malloc.h>
#include <resolv.h>
#include "openssl/ssl.h"
#include "openssl/err.h"
#include <openssl/rand.h>
#include <vector>
#include <poll.h>
#include "netcon.h"
#include "logger.h"

#define FAIL    -1
#define DEFAULT_RCVBUF          108544
#define DEFAULT_SOCKETBUFSIZE   108544
#define DEFAULT_SEND_TIME       10
#define DEFAULT_STACK_SIZE      2097152
#define DEFAULT_NUM_OF_CON      100

enum ToolStatus {
    STARTING,
    READY,
    HAVE_TO_EXIT
};

struct ToolData {
    ToolStatus status;
    std::string server_cert_file;
    std::string server_key_file;
    std::string client_cert_file;
    std::string client_key_file;
    std::string ca_file;
    unsigned int logMask;
    unsigned int logMode;
    unsigned int numberOfConnections;
};
      
struct Listener {
    bool enable;
    pthread_t threadID;
    std::string name;
    std::string be_ip;
    std::string fe_ip;
    unsigned int be_port;
    unsigned int fe_port;
    bool be_sctp;
    bool fe_sctp;
    bool fe_ipv6;
    std::string be_ssl_protocol;
    std::string fe_ssl_protocol;
    bool fe_ssl_req_cred;
    bool be_ssl;
    bool fe_ssl;
    bool be_ipv6;
    unsigned int port;
    bool ipv6;
    bool sctp;
    NetworkConnection *server;
};    
   
struct Message {
    int             message_len;
    int             bytes_sent;
    unsigned char * buffer;
};
typedef std::deque<struct Message> MessageToSendDeque;

struct Connection{
    pthread_t threadID;
    int pos;
    bool used;
    NetworkConnection *be_connection;
    NetworkConnection *fe_connection;
    MessageToSendDeque toBeSendToFrontEnd;
    MessageToSendDeque toBeSendToBackEnd;    
    std::string be_ip;
    unsigned int be_port;
    bool be_ssl;
    bool fe_ssl;
    std::string be_ssl_protocol;
    SSL *ssl;
    bool be_sctp;
    bool be_ipv6;
    SSL_CTX *ctx_client;
};

enum SignalReason {
    NO_REASON,
    CONF_ERROR,
    EXECUTION_ERROR
};

void readConfigFile(std::string cfg_file);

int setNonblocking(int fd);
int setBlocking(int fd);

SSL_CTX* InitClientCTX(void);
SSL_CTX* InitServerCTX(void);
void ShowCerts(SSL* ssl);
void Servlet(SSL* ssl);

void* _ListenerThread(void *arg);
void* _ConnectionThread(void *arg);
void* _SignalThread(void *);

int get_free_connection();
void listenerResetAndExit (Listener *myListener, int fail);
void connectionResetAndExit (Connection *myConnection, int fail);
void cleanPendingMessages(MessageToSendDeque & messages, pthread_t threadID);
bool send_message(MessageToSendDeque * messages, NetworkConnection *net_con, bool use_ssl, SSL *ssl, pthread_t threadID);
void initializeConnection(Connection *myConnection);


#endif
