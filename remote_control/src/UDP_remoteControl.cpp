#include "UDP_remoteControl.h"

#include <sstream>
#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <string.h>

#include <syslog.h>
#include <stdarg.h>
#include <errno.h>
#include <time.h>
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

using namespace std;

string sendCommand(string dest_host, int port, string command, int timer)
{ 

	stringstream answer;
	int errsv = 0;
	char buff[DEFAULT_BUFFER_SIZE];
        
        struct sockaddr_in local_addr;
	memset(&local_addr,0,sizeof(local_addr));
	local_addr.sin_family = AF_INET;
       
        int sockId = socket(AF_INET, SOCK_DGRAM, 0);

	//binding the socket to a local port
	if(bind(sockId,(sockaddr*)&local_addr, sizeof(local_addr)) == -1){

		errsv = errno;
		answer <<"ERROR " << strerror(errsv) << endl;

		return answer.str();
	}
		
	struct sockaddr_in remote_addr;
	memset(&remote_addr,0,sizeof(sockaddr_in));
	remote_addr.sin_family = AF_INET;
        remote_addr.sin_port = htons(port);
        
                
 	struct hostent *he;
	he = gethostbyname(dest_host.c_str()); 
	if (he == 0) {
		answer << "ERROR: Destination host not valid: "<< dest_host << endl;      
       		return answer.str();
	}

	bcopy(he->h_addr_list[0], &remote_addr.sin_addr.s_addr, he->h_length);
        
 	socklen_t len = sizeof(remote_addr);
       
        int sent = sendto (sockId,command.c_str(),command.size(),0, (struct sockaddr *) &remote_addr, len);

        if (sent != command.size()){                
			answer << "ERROR: "<<sent <<" of " << command.size() << " bytes have been sent."<< endl;      
       			return answer.str();
	}
                        
	fd_set fds;
	fd_set tmpset;
	struct timeval tv;
	tv.tv_sec = timer;
	tv.tv_usec = 0;
	
	//subscribing the server socket to the mask to be used in the 'select'
	FD_ZERO(&fds);
	FD_SET(sockId, &fds);
	int received = 0;
	string recvCommand = "";
                
	tmpset = fds;

	//passive wait for any activity in the socket
	select(sockId+1,&tmpset, NULL, NULL, &tv);

	if(FD_ISSET(sockId, &tmpset)){ 
		
		if ( (received = recvfrom(sockId, buff, DEFAULT_BUFFER_SIZE, 0, (struct sockaddr *) &remote_addr, &len)) <= 0) {
			answer <<"ERROR Received <= 0" << endl;
			return answer.str();
		}
			
		buff[received] = '\0';
		recvCommand = buff;
		answer << recvCommand;
                return answer.str();
	} 
	else {
		answer << "ERROR No Answer received";                        
                return answer.str();
	}

}


