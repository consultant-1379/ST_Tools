/////////////////////////////////////////////////////////////////////////////////
//
// HSSproxy.h written by Olov Marklund
// Date: 06/10/05 Time: 11:06:39
// Version: 1.0 Build: 002
//
/////////////////////////////////////////////////////////////////////////////////
#ifndef REMOTE_H
#define REMOTE_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>

#include <syslog.h>
#include <stdarg.h>
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
#include <fcntl.h>
#include <termios.h>
#include <sys/time.h>

#include <string>
#include <deque>
#include <iostream>
#include <fstream>


//Miscelanoeus default values 

#define DEFAULT_BUFFER_SIZE			65535
#define PORT	4444


struct applicationData {
	int port;
	int waitingTimer;
        std::string destination_host;
        std::string destination_ip;
        std::deque <std::string> commands;
        std::string commandFile;
};

        
bool filterLine (char * line, std::string filter, bool after, std::string & element);
bool parseCommandLine (int argc, char **argv, applicationData *dataPtr);
void displayHelp();
bool readCommandFile (applicationData *dataPtr);
void purgeLine(char * line);
#endif
