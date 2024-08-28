#ifndef CNDIAPROXY_H
#define CNDIAPROXY_H
#include "Types.h"
#include <netinet/in.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <netdb.h>

#include "ProxyThread.h"
#include "Utils.h"
#include "Wda.h"
#include <deque>
#include <map>
#include <vector>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <iostream>
#include <fstream>
#include <algorithm>
#include <poll.h>

// st-tools lib headers
#include "logger.h"
#include "netcon.h"

//default values for configuration
#define LOG_PRG                 "cnDiaProxy"
#define CONFIGURATION_PATH      ".cnDiaProxy"
#define CONFIGURATION_FILE      "cnDiaProxy.cfg"

#define DEFAULT_NUMBER_CLIENTS      1000
#define DEFAULT_MAX_RECONNECTION    1
#define TRANSACTIONPERCLIENT        1000
#define WDR_TIME                    1000
#define MAX_WDR_PENDING             5
#define DEFAULT_PROTOCOL            TCP_PROTOCOL
#define DEFAULT_HSS_PORT            "3868"
#define DEFAULT_PROXY_PORT          3868
#define MAX_CLIENTS_THREADS         50
#define MAX_CLIENTS_PER_THREAD      200
#define DEFAULT_CLIENTS_THREADS     5
#define DEFAULT_RCVBUF              108544
#define DEFAULT_SOCKETBUFSIZE       108544
#define DEFAULT_RECONNECT_TIME      5          //time in seconds

#define HSS     "hss"
#define EPC     "sapc"

#define TCP_PROTOCOL			"tcp"
#define SCTP_PROTOCOL			"sctp"

#define DIAMETER_SUCCESS 		2001 
#define DIAMETER_UNABLE_TO_DELIVER 	3002 
#define DIAMETER_TOO_BUSY  		3004 
#define DIAMETER_UNABLE_TO_COMPLY 5012
#define DIAERRCOUNTERS_REPORT_TIMEOUT 	5

//default values for cer data
#define DEFAULT_OH_PREFIX                   "cnDiaProxy"
#define DEFAULT_ORIGIN_REALM                "ericsson.se"
#define DEFAULT_HOST_IP_ADDRESS_IF_FAIL     0x0a011459
#define DEFAULT_FIRMWARE_REVISION           1
#define DEFAULT_VENDOR_ID                   0x00000000
#define DEFAULT_PRODUCT_NAME                "Ericsson Diameter"
#define ERICSSON_VENDOR_ID                  10415


//Miscelanoeus default values 
#define DEFAULT_UDP_BUFFER_SIZE     4096
#define DEFAULT_BUFFER_SIZE			65535
#define DEFAULT_SEND_TIME			10
#define DEFAULT_STACK_SIZE			2097152
#define	MSG_MAX_CLIENTS_REACHED			"Sorry, maximum number of client reached.\nTry later.\n"
#define DIA_PROXY_from_TSP_SO_RCVBUFF_VALUE	110000
#define DIA_PROXY_to_TSP_SO_SNDBUFF_VALUE	16000
#define DIA_PROXY_from_PTC_SO_RCVBUFF_VALUE	8000
#define DIA_PROXY_to_PTC_SO_SNDBUFF_VALUE	17500
#define MAX_ACTIVE_NODE_FIND_RETRIES		10
#define MAX_TRANS_SIZE				67108863
#define MAX_PENDING_MESSAGES			25000
#define MIN_PENDING_MESSAGES			500

enum DiaProxyStatus {
    DIAPROXY_OFF,
    DIAPROXY_FINDING_SERVER,
    DIAPROXY_STARTING,
    DIAPROXY_STANDBY,
    DIAPROXY_PROCESSING,
    DIAPROXY_CLEANNING,
    DIAPROXY_SHUTINGDOWN
};

enum ListennerStatus {
    LISTENNER_OFF,
    LISTENNER_CONNECTING,
    LISTENNER_READY,
    LISTENNER_FAULTY
};


enum SignalReason {
    NO_REASON,
    MAX__INACTIVE__REACHED,
    DIA__CONF__ERROR,
    PTHREAD_ERROR,
    DIA__CONRETRIES__REACHED,
    DIA_EXIT_REQ_BY_USER
};


enum ClientStatus {
    OFFLINE,
    ONGOING,
    ONLINE
};

struct ClientConnection {
    int sock;
    int fd_index;
    NetworkConnection *net_con;
    sockaddr_in remote_addr;
    ClientStatus status;
    bool waitingAnswer;
    int pos;
    int diaServerConnection;
    pthread_t clientThreadID;
    uchar client_buff[DEFAULT_BUFFER_SIZE];
    int toreceive;
    int received;

};

enum MessageType {
    REQUEST_TO_SERVER,
    ANSWER_TO_CLIENT
};

struct Message {
    MessageType     message_type;
    int             diaServerConnection;
    int             transaction;
    int             message_len;
    int             bytes_sent;
    unsigned char *	    buffer;
};


typedef std::deque<struct Message> MessageToSendDeque;
typedef std::map<int, MessageToSendDeque> PendingToSendMap;

struct clientThread {
    struct pollfd fds[MAX_CLIENTS_PER_THREAD];
    int nfds;
    std::vector<int> conectionClients;
    pthread_t 	clientThreadID;
    int pos;
};

enum ConnectionStatus {
    OFF,
    TOBECONNECTED,
    CONNECTING,
    CONNECTED,
    DISCONNECTED,
    BROKEN,
    MAXCONEXIONREACHED,
    CONFIGURATIONERROR
};

struct reportData{
    std::string sessionId;
    unsigned int cmd_code;
    double  time_event;
};

typedef std::deque<struct reportData> ReportDataDeque;

enum TransactionStatus {
    NOTUSED,
    USED
};

struct Transaction {
    TransactionStatus status;
    int end2end;
    int hopByHop;
    int client;
    int answerToDiaServerConnection;
    unsigned int recvReqSend;
    unsigned int recvAnsSend;
    struct timeval reqSent2AnsRecv;
    struct timeval request_sent_time;
    struct timespec request_time;
    unsigned int cmd_code;
};

enum RemoteStatus {
    REMOTE_DISABLED,
    REMOTE_ENABLED,
    REMOTE_OFF,
    REMOTE_CONNECTING,
    REMOTE_ON
};

struct RemoteControl {
    int sock;
    int port;
    RemoteStatus status;
};

typedef struct _DIAMETER_HEADER
{
    uchar	ver;
    uchar	length[3];
    uchar	flags;
    uchar	cmd_code[3];
    uint	vendor_id;
    uint	hop2hop;
    uint	end2end;
} DIAMETER_HEADER;

const int DIAMETER_HEADER_LENGTH = sizeof (DIAMETER_HEADER);

typedef struct _AVP_HEADER
{
    uint	avp_code;
    uchar	flags;
    uchar	avp_len[3];
    uint	value;
}AVP_HEADER;

struct DiaServerConnection {
    ConnectionStatus status;
    NetworkConnection *net_con;
    int pos;
    pthread_t threadID;
    int conexionRetries;
    int pendingWatchDog;
    PendingToSendMap  pendingToSendMap;
    bool    firstConnectionTry;

    bool    use_sctp;
    bool    use_ssl;
    std::string ssl_protocol;
    bool    ipv6;
    char    name[100];
    char    diameter_server[100];
    uint    serv_port;
    char    diaproxy_host[100];
    struct  sockaddr_in6 localaddr_v6;
    uchar   host_ip_address[4];
    char    diameter_host[100];
    uchar   origin_host[200];
    uchar   origin_realm[200];
    std::vector<int> vendor_specific_application;

    unsigned int requestSentToServer;
    unsigned int requestReceivedFromClient;
    unsigned int requestDiscardFromClient;

    unsigned int answerReceivedFromServer;
    unsigned int answerSentToClient;
    unsigned int answerDiscardFromServer;

    unsigned int resultCode_Success;
    unsigned int resultCode_Busy;
    unsigned int resultCode_UnableToComply;
    unsigned int resultCode_Other;
    unsigned int request_Sent;
    ReportDataDeque reportData;
};

struct applicationData
{
    int     local_port;
    char    oh_prefix[100];
    uint    e2e_seed;
    bool    skip_wd;
    uint    log_mask;
    int     numberOfTransactions;
    int     numberOfConnections;
    int     numberOfClients;
    uint    reconnectTime;
    uint    maxReconnections;
    int     maxNumberClientThreads;
    bool    clientsSharingThreads;
    int     max_size_message_queue;
    bool    cve_report;
    bool    capture_enable;
    char    report_file[100];
    int     socketbuffersize;
    std::vector<int> all_appids;
    int     activeTTCNConnections;

    std::string  cert_file;
    std::string  key_file;
    std::string  CA_File;
    std::string  ssl_password;

    bool    latency_report_enabled;
    bool    latency_report_running;
    char    latency_report_file[100];

    bool    DiaErrCounters_report_enabled;        
    bool    DiaErrCounters_report_running;
    char    DiaErrCounters_report_file[100];
    int     DiaErrCounters_report_timeout;

    unsigned int resultcode_request;
    unsigned int resultcode_success;
    unsigned int resultcode_busy;
    unsigned int resultcode_utc;
    unsigned int resultcode_other;
};

enum avps
{
    acct__application__id               = 0x03010000,
    auth__application__id               = 0x02010000,
    host__ip__address                   = 0x01010000,
    origin__host                        = 0x08010000,
    disconnect__cause                   = 0x11010000,
    origin__realm                       = 0x28010000,
    destination__host                   = 0x25010000,
    destination__realm                  = 0x1b010000,
    product__name                       = 0x0d010000,
    result__code                        = 0x0c010000,
    supported__vendor__id               = 0x09010000,
    vendor__id                          = 0x0a010000,
    vendor__specific__application__id   = 0x04010000,
    firmware__revision                  = 0x0b010000
};


enum result_codes
{
    result__diameter__multi__round__auth			= 0xe9030000,
    result__diameter__success				= 0xd1070000,
    result__diameter__authorized__and__already__registered	= 0x98080000,
    result__diameter__authorized__first__registration	= 0x99080000,
    //new 
    result__diameter__invalid__avp__length 			= 0x96130000,
    result__diameter__invalid__avp__value	 		= 0x8c130000,
    result__diameter__no_common__application 		= 0x92130000,
    result__diameter__unable_to_comply	 		= 0x94130000

};

typedef enum  _AvpCode{

    USERNAME_CODE                       = 1,
    HOST_IP_ADDRESS_CODE                = 257,
    AUTH_APPLICATION_ID_CODE            = 258,
    ACCT_APPLICATION_ID_CODE            = 259,
    VENDOR_SPECIFIC_APPLICATION_ID_CODE = 260,
    SESSIONID_CODE                      = 263,
    ORIGINHOST_CODE                     = 264,
    SUPPORTED_VENDOR_ID_CODE            = 265,
    VENDOR_ID_CODE                      = 266,
    RESULTCODE_CODE                     = 268,
    PRODUCTNAME_CODE                    = 269,
    DISCONNECT_CAUSE                    = 273,
    AUTHSESSIONSTATE_CODE               = 277,
    DESTINATIONHOST_CODE                = 293,
    ORIGINREALM_CODE                    = 296,
    EXPERIMENTAL_RESULTCODE_CODE        = 297,
    ACCOUNTING_RECORD_TYPE_CODE         = 480,
    ACCOUNTING_RECORD_NUMBER_CODE       = 485,
    INDICATION_CODE                     = 1002,
    SIP_SERVER_CAPABILITIES_CODE        = 1011,
    SIP_SERVERNAME_CODE                 = 1012,
    USERDATA_CODE                       = 1017,
    AUTH_DATA_ITEM_CODE                 = 1018,
    NUMBERAUTHENTICATIONITEMS_CODE      = 1026

}AVP_CODE;

enum cmd_codes
{
    cmd__code__cer  = 0x101,
    cmd__watchdog   = 0x118,
    cmd__rar        = 0x1f4,
    cmd__mar        = 0x1fa,
    cmd__lur        = 0x1f5,
    cmd__udr        = 0x1f6,
    cmd__lir        = 0x1f7,
    cmd__dpr        = 0x11a,
    cmd__ulr        = 0x28a,
    cmd__air        = 0x28b,
    cmd__idr        = 0x28c,
    cmd__idr_rfe5   = 0x13f,
    cmd__clr        = 0x28d,
    cmd__clr_rfe5   = 0x13d,
    cmd__dsr_rfe5   = 0x140,
    cmd__rsr_rfe5   = 0x142
};


enum app_id
{
        applicationId_cx    =0x01000000,    //16777216
        applicationId_zx    =0x0100000C,    //16777228
        applicationId_sh    =0x01000001,    //16777217
        applicationId_s6a   =0x01000023,    //16777251
        applicationId_s6t   =0x01000081,    //16777345
        applicationId_s6m   =0x0100005E,    //16777310
        applicationId_zh    =0x01000005,    //16777221
        applicationId_swx   =0x01000031,    //16777265
        applicationId_slh   =0x0100004b     //16777291
};


void printusage();
int setNonblocking(int fd);
int setBlocking(int fd);
int findTotalPendingMessages();


void readConfigFile(std::string cfg_file);
bool printConfiguration();
struct DiaServerConnection newDiaCon();
bool filterLine (const char * line, std::string filter, bool after, std::string & element);

inline
char my_tolower( char c )
{  return
   static_cast<char>( tolower( static_cast<unsigned char>( c ) ) );
}

inline
char my_toupper( char c )
{  return
   static_cast<char>( toupper( static_cast<unsigned char>( c ) ) );
}



void* _RemoteThread(void *);

std::string getStatus();

std::string getConfiguration();

std::string changeDataTool(std::istream& cmd);

std::string displayCmdHelp();

void resetRemoteAndExit (int fail);

std::string exitTool();
std::string get_status_info() ;
std::string get_configuration_info(); 
std::string get_result_code_info();
void reset_result_code_info();

std::string stop_report(std::istream& cmd) ;
std::string start_report(std::istream& cmd) ;
std::string enable_report(std::istream& cmd) ;
std::string change_file_report(std::istream& cmd) ;
std::string change_result_codes_period(std::istream& cmd) ;

std::string get_result_code_counter(std::istream& cmd) ;
std::string reset_result_code_counter(std::istream& cmd) ;
std::string get_and_reset_result_code_counter(std::istream& cmd) ;
std::string check_connections_up(std::istream& cmd) ;


void signal_all_and_exit(uint sig);

void signal_client_threads(uint sig);

void check_signals(const char *thread, int fd, int pos);

void * handler(void *);
void * _ReportManagerThread(void *);
void save_latency_data(std::ofstream & outFile) ;
void save_DiaErrCounters_data(std::ofstream & outFile_absolute, std::ofstream & outFile_pecentage, int time) ;
std::string get_connection_info(void *connection);
bool check_connection(void *connection);
std::string get_connection_statistic(void *connection, int index);
void logAndPrint(int what, const std::string & logString);

#endif