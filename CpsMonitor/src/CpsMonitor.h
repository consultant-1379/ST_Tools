#ifndef CPSMONITOR_H
#define CPSMONITOR_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <algorithm>
#include <deque>
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
#include <time.h>
#include <signal.h>

#define LOG_PRG       "CpsMonitor.1.0"

#define LOGMASK_ERROR		1
#define LOGMASK_WARNING		3
#define LOGMASK_CONNECTIONS	7
#define LOGMASK_EVENT		15
#define LOGMASK_INFO		31
#define LOGMASK_DEBUG		63
#define LOGMASK_ALL		255

#define DEFAULT_BUFFER_SIZE	4096
#define DEFAULT_PORT	        8888
#define DEFAULT_MEASURETIME	2
#define DEFAULT_REFRESH		10
#define DEFAULT_SCAN		5

#define MAX_NO_ANSWER           3

using namespace std;

enum MonitorStatus {
	MONITOR_OFF,
	MONITOR_STARTING,
	MONITOR_ON,
	MONITOR_HAVE_TO_EXIT
};
struct MonitorData {
        MonitorStatus status;
	int sock;
        string server;
        string serverIP;
	int port;
	struct sockaddr_in remote_addr;
	std::string hostname;
        std::string logFile;
        unsigned int logMask;
        unsigned int logMode;
        string dataFileName;
        string cmdFileName;
        string loopFileName;
        int refreshTime;
        int measureTime;
        int scan;
        int acc_currentCPS;
        int acc_targetCPS;
        int noAnswerCounter;
        bool display_active;
        bool schedulingEnabled;

};


struct Step {
    int time;
    int cps;
};

typedef deque<struct Step> StepDeque;

void exitMonitor ();
bool parseCommandLine (int argc, char **argv, bool onlyCfg);
void displayHelp();
string getIpByHostname (string host);
string sendCommand(string command);
bool filterLine (char * line, string filter, bool after, string & element);

void readConfigFile(string nameFile);
void purgeLine(char * line);

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

vector<string> &split(const string &s, char delim, vector<string> &elems) ;

vector<string> split(const string &s, char delim);

// SignalThread

void signal_all_and_exit(unsigned int sig);
void signal_client_threads(unsigned int sig);
void check_signals(const char *thread, int fd, int pos);
void * handler(void *);

// _MonitorThread

void* _MonitorThread(void *);

#endif
