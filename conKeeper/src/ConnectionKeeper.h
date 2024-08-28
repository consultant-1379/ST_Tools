/////////////////////////////////////////////////////////////////////////////////
//
// HSSproxy.h written by Olov Marklund
// Date: 06/10/05 Time: 11:06:39
// Version: 1.0 Build: 002
//
/////////////////////////////////////////////////////////////////////////////////
#ifndef HSSPROXY_H
#define HSSPROXY_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <algorithm>
#include <cctype>
#include <syslog.h>
#include <stdarg.h>
#include <errno.h>
#include <time.h>
#include <signal.h>
#include <pthread.h>
#include <signal.h>
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
#include <fcntl.h>
#include <termios.h>
#include <sys/time.h>
#include <iostream>
#include <fstream>
#include <sstream>

#include "SignalHandling.h"
#include "AVP.h"
#include "logger.h"

#define LOG_PRG       "conKeeper"

typedef unsigned char			uchar;
typedef unsigned char *			puchar;
typedef unsigned int			uint;
typedef char *				LPTSTR;
typedef const char *			LPCTSTR;


//default values for configuration

#define DEFAULT_NUMBER_CONNECTIONS	500
#define LDAP_PORT	7323
#define LOAD_PORT	10000
#define DIA_PORT	3868
#define REMOTE_PORT	4444

#define LOGMASK_ERROR		1
#define LOGMASK_WARNING		3
#define LOGMASK_CONNECTIONS	7
#define LOGMASK_EVENT		15
#define LOGMASK_INFO		31
#define LOGMASK_DEBUG		63
#define LOGMASK_ALL		255

#define LOG_ONLY_FILE	255



//Miscelanoeus default values 

#define DEFAULT_BUFFER_SIZE			65535
#define DEFAULT_SEND_TIME			10
#define DEFAULT_STACK_SIZE			2097152
#define DIA_PROXY_from_TSP_SO_RCVBUFF_VALUE	110000
#define DIA_PROXY_to_TSP_SO_SNDBUFF_VALUE	16000
#define DIA_PROXY_from_PTC_SO_RCVBUFF_VALUE	8000
#define DIA_PROXY_to_PTC_SO_SNDBUFF_VALUE	17500



void* _ControlThread(void *arg);
void* _DiameterServerThread(void *arg);
void* _DiameterClientThread(void *arg);
void* _LdapServerThread(void *arg);
void* _LdapClientThread(void *arg);
void* _LoadServerThread(void *arg);
void* _LoadClientThread(void *arg);
void* _ListenerThread(void *arg);
void* _RemoteThread(void *arg);
void* _HeartBeatThread(void *arg);

enum ConKeeperStatus {
	CONKEEPER_STARTING,
	CONKEEPER_TO_BE_CONFIGURED,
	CONKEEPER_READY,
	CONKEEPER_TO_BE_RESET,
	CONKEEPER_HAVE_TO_EXIT	
};
        
enum ActiveZone {
	UNKNOWM,
	PRIMARY,
	SECONDARY
};

struct applicationData {
	ConKeeperStatus status;
	std::string hostname;
        char ip_host[20];
        std::string logFile;
        unsigned int logMask;
        unsigned int logMode;
        ActiveZone activeZone;
        bool redundancy;
        bool statistic;
};   
      
enum RemoteStatus {
	REMOTE_OFF,
	REMOTE_CONNECTING,
	REMOTE_ON
};
        
struct RemoteControl {
	int sock;
	int port;
	RemoteStatus status;
};
        
struct HeartBeat {
	int sock;
	int port;
        char primary_ip_host[20];
        char secondary_ip_host[20];
};
        
enum ListenerStatus {
	LISTENER_OFF,
	LISTENER_STARTING,
	LISTENER_TO_BE_CONFIGURED,                        
	LISTENER_ON,
	LISTENER_FAULTY,
	LISTENER_TO_BE_STARTED,
	LISTENER_TO_BE_CLOSED,                       
	LISTENER_NOT_USED                        
};
        
        
enum ConnectionType {
        NONE,
	LOAD,
	DIAMETER,
	LDAP
  
};
               
struct Listener {
	int sock;
	int port;
        char primary_ip_host[20];
        char secondary_ip_host[20];
        ConnectionType type;
	ListenerStatus status;
	pthread_t threadID;
};

enum ConnectionStatus {
	OFFLINE,
	CONNECTING,
       	ONLINE,
	TO_BE_CLOSED,
	TO_BE_RESTARTED       
};
     
struct OutConnection {
	int sock;
	struct sockaddr_in primary_remote_addr;
	struct sockaddr_in secondary_remote_addr;
        ActiveZone connectedTo;
	ConnectionStatus status;
	pthread_t threadID;
};
       
struct InConnection {
	int sock;
	ConnectionStatus status;
	pthread_t threadID;
};
        
struct Connection {
        ConnectionType type;
        char type_str[10];
	int position;
       	char message[1024];
        int messageLen;
        bool firstConnectionOk;
	InConnection server;
	OutConnection client;
};

struct myOutConnection {
	int sock;
	ConnectionStatus status;
};
       
struct myInConnection {
	int sock;
	ConnectionStatus status;
};
        
struct myConnection {
        char type_str[10];
	InConnection server;
	OutConnection client;
}; 


typedef struct _LDAP_MESSAGE
{
	uchar	protId[2];
        uchar	messageId[6];
	uchar	cmd_code[1];
	uchar	length[1];
	uchar	result_code[3];
} LDAP_MESSAGE;

enum ldap_result_codes{
	success_bind			= 0x0a0100
};

                              
bool sendFirstLdapMessage(Connection *myConnection);
bool sendFirstDiameterMessage(Connection *myConnection);
bool receive_CEA (Connection *myConnection);

void resetServerConnectionAndExit(Connection *myConnection);
void resetClientConnectionAndExit(Connection *myConnection, ConnectionStatus status );
void resetRemoteAndExit (int fail);
void resetHeartBeatAndExit (int fail);
                
char* getlocalhostname (char *name);
bool receive_heartbeat_CEA ();
int create_heartbeat_CER(unsigned char *cermsg);

void displayHelp();
bool parseCommandLine (int argc, char **argv);

bool checkConnection(char * connection_host);


bool read_message_body (Connection *myConnection, int bytes_to_read, puchar *p_head,fd_set fds, int *dp_size); 
void storeFirstMessage(Connection *myConnection, int len, char * buff);
bool configure();

std::string addListenner(std::istream& cmd);
std::string setdesthost(std::istream& ss);
std::string getListenner(std::istream& ss);
std::string getConnection(std::istream& ss);
std::string changeDataTool(std::istream& ss);
std::string resetTool();
std::string exitTool();


void oct2int(int *i_value, uchar i[4]);
void int2oct(uchar i[4], char *intstr);
void ip2oct(uchar ip[4], const char *ipstr);
void int2hex (char *buff, int number, int size); 
void  int2oct (char i[4], int number); 
int str2int (char* str); 
int topad(int len);


               
void addNewListenner(ConnectionType type, int port);                
std::string getIpByHostname (std::string host);
bool filterLine (char * line, std::string filter, bool after, std::string & element);
void displayConnection(Connection &con, int index);
void displayListenner(Listener &listenner, int index);
std::string displayAppInfo();
std::string displayCmdHelp();

std::string getConnectionInfo(Connection &con, int index);
std::string getListennerInfo(Listener &listenner, int index);
std::string getConfiguration();
std::string getStatus();

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


#endif
