#ifndef LOADPLOTTER_H
#define LOADPLOTTER_H

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
#include "logger.h"
#include "SignalHandling.h"
#include "UtilsSsh.h"
#include "UtilsLoadMeas.h"

#define LOG_PRG       "LoadPlotter.2.0"

#define LOGMASK_ERROR		1
#define LOGMASK_WARNING		3
#define LOGMASK_CONNECTIONS	7
#define LOGMASK_EVENT		15
#define LOGMASK_INFO		31
#define LOGMASK_DEBUG		63
#define LOGMASK_ALL		255

#define NUM_DICOS_1_SUBRACK 6
#define NUM_DICOS_2_SUBRACK 18


#define DEFAULT_STACK_SIZE			2097152
#define DEFAULT_BUFFER_SIZE			4096
#define DEFAULT_SEND_TIME			5
#define MAX_PROCESSOR_NAME_LEN 100
#define REMOTE_PORT				5555

#define MAX_NUMBER_OF_CONNECTIONS	50

#define DEFAULT_SCAN_SIZE	0
#define DEFAULT_MEASURE_TIME	1
#define DEFAULT_REFRESH_TIME	0
#define DEFAULT_CBA_USRID	"root"
#define DEFAULT_CBA_PASSW	"rootroot"
#define DEFAULT_DEST_PORT_CBA	22

using namespace std;

enum ToolStatus {
	LOADPLOTTER_STARTING,
	LOADPLOTTER_TO_BE_CONFIGURED,
	LOADPLOTTER_READY,
	LOADPLOTTER_TO_BE_RESET,
	LOADPLOTTER_HAVE_TO_EXIT	
};
        

struct applicationData {
	ToolStatus status;
	std::string hostname;
        std::string logFile;
        unsigned int logMask;
        unsigned int logMode;
        bool KeepGraphicAfterExecution;
};   
 
enum ConnectionStatus {
        NOT_USED,
	OFFLINE,
	STARTING,
       	TO_BE_CONNECTED,
       	ONLINE,
	TO_BE_CLOSED,
	FAULTY
};
enum LoadType {
	TOTAL,
       	SYSTEM,
       	TRAFFIC,
	OAM
};


struct Connection {
	int position;
       	char message[1024];
        int messageLen;
       	std::string destHostIP;
	std::string dataFileName;
	std::string cmdFileName;
	std::string loopFileName;
	std::string name;
	int destPort;
	unsigned int scanSize;
	unsigned int measureTime;
	int sock;
	struct sockaddr_in remote_addr;
	ConnectionStatus status;
	pthread_t threadID;
	vector <string> procFilter;                
	vector <string> excludeProcFilter;
        LoadType regulatedLoadType; 
        float regulatedloadValue; 
        float trafficloadValue; 
        float oamloadValue; 
        float systemloadValue; 
        float totalloadValue; 
        char *  cba_firstLoadFilter;          
	float cba_acc_Load ;
	float cba_total_Load ;
	unsigned int cba_load_cnt ;
	unsigned int cba_round_cnt ;
	unsigned int acc_systemLoad ;
	unsigned int acc_trafficLoad;
	unsigned int acc_oamLoad ;
	bool LoadTotalPlot;
	std::string CBA_userid;
	std::string CBA_password;
        CUtilsSsh * sshCntPtr;
	unsigned int refreshTime;
};

struct loadMeassure {
       	char procName[MAX_PROCESSOR_NAME_LEN];
	unsigned int systemLoad;
	unsigned int trafficLoad;
	unsigned int oamLoad;
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

void initConnection(struct Connection * newConnection);
int findConnection();

void readConfigFile(string nameFile);
bool parseCommandLine (int argc, char **argv);
void displayHelp();
void purgeLine(char * line);
bool filterLine (const char * line, string filter, bool after, string & element);
string getIpByHostname (string host);
void* _ConnectionThread_CBA(void *arg);
void parseLoadRead_CBA(char * line, Connection *myConnection);
void resetConnectionAndExit_CBA(Connection *myConnection, auto_ptr <CUtilsSsh> ptrShCnct);
bool isIpFormat(string host);
void* _ControlThread(void *arg);
void* _RemoteThread(void *);
void resetRemoteAndExit (int fail);

// Remote command functions
std::string getConfiguration();
std::string getStatus();
std::string exitTool();
std::string addConnection(std::istream& cmd);
std::string getLoad(std::istream& ss);
std::string changeDataTool(std::istream& ss);
std::string displayAppInfo();
std::string displayCmdHelp();

std::string getConnectionInfo(Connection &con);
string getConnection();
string getConnectionId(std::istream& cmd);
string checkConnectionData(struct Connection * con);



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
