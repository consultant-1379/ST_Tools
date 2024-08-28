#ifndef UDP_REMOTE_H
#define UDP_REMOTE_H

#include <string>
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
#define DEFAULT_BUFFER_SIZE	65535

std::string sendCommand(std::string dest_host, int port, std::string command, int timer);

#endif

