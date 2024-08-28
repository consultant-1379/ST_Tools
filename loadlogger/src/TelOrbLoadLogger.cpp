// TelOrbLoadLogger.cpp
//==============================================================================
//
//  COPYRIGHT Ericsson España S.A. 2007
//  All rights reserved.
//
//  The Copyright to the computer program(s) herein
//  is the property of Ericsson España S.A.
//  The program(s) may be used and/or copied only
//  with the written permission from Ericsson España S.A.,
//  or in accordance with the terms and conditions
//  stipulated in the agreement/contract under which the program(s)
//  have been supplied.
//
//  Ericsson is in no way responsible for usage and adaptation of this
//  source by third parties, nor liable for any consequences of this.
//  This is the responsibility of the third party.
//
// ============================================================================
//
//! \file TelOrbLoadLogger.cpp
//! \brief Implements the class CTelOrbLoadLogger
//!
//! AUTHOR \n
//!    2007-03-27 by EEM/TIH/P Olov Marklund
//!                        olov.marklund@ericsson.com \n
// =============================================================================
//
//! CHANGES \n
//!    DATE           NAME      DESCRIPTION \n
//
//==============================================================================

#include "TelOrbLoadLogger.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#ifndef _WIN32
#include <unistd.h>
#include <sys/socket.h> 
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <netdb.h>
#include <sys/stat.h>
#endif
#include "Globals.h"
#include "Logger.h"

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

extern bool running;
extern CLogger g_logger;
extern bool g_error;
extern bool g_operator_shdwn;
//bool CTelOrbLoadLogger::abort_requested = false;
namespace //anonymous
{
	//! \brief Captures ctrl+c from the operator
	//!
	//! When the TelOrbLoadLogger is trying to connect and the operator
	//! presses ctrl+c this function gets called and the connection
	//! attemts gets aborted. If setting up the capturing of the event
	//! the connect attemt will be aborted after 5 retries
/*	void operator_abort(int sig)
	{
		CTelOrbLoadLogger::abort_requested = true;
		printf("\nAborting...\n");
		exit(0);
	}
*/
}
//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////


CTelOrbLoadLogger::CTelOrbLoadLogger()
: m_logInterval(1)
, m_readings(0)
, m_buff(new char[0xffff])
{
	sprintf(m_ekm,"ekm");
	memset(&m_vip_addr,0,sizeof(sockaddr_in));
	m_vip_addr.sin_family = AF_INET;
#ifdef _WIN32
	m_sock = INVALID_SOCKET;
#else
	m_sock = -1;
#endif
	

}

CTelOrbLoadLogger::~CTelOrbLoadLogger()
{
#ifdef _DEBUG
	printf("ENTER ~CTelOrbLoadLogger()\n");
#endif
	StopPeriodicTimer();
#ifdef _WIN32
	if(m_sock != INVALID_SOCKET)
	{
		closesocket(m_sock);
		m_sock = INVALID_SOCKET;
	}
#else
	if(m_sock != -1)
	{
		close(m_sock);
		m_sock = -1;
	}
#endif
#ifdef _DEBUG
	printf("EXIT ~CTelOrbLoadLogger()\n");
#endif
}

bool CTelOrbLoadLogger::Init(pchar host)
{
	return m_fun.get_hostip(&m_vip_addr.sin_addr,host);
}

void CTelOrbLoadLogger::Init(int port)
{
	m_vip_addr.sin_port = htons(port);
}

void CTelOrbLoadLogger::SetLogInterval(int ival)
{
	m_logInterval = ival;
}

int CTelOrbLoadLogger::Connect()
{
	
	m_sock = socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
#ifdef _WIN32
	if(m_sock == INVALID_SOCKET)
	{
		printf("Failed to create socket\n");
		printf("Error %s\n",strerror(WSAGetLastError()));
		return -1;
	}
#else
	if(m_sock == -1)
	{
		printf("Failed to create socket\n");
		printf("Error %s\n",strerror(errno));
		return -1;
	}
#endif
	FD_ZERO(&m_fds);
	m_tv.tv_sec = 1;
	m_tv.tv_usec = 0;
	FD_SET(m_sock,&m_fds);

	printf("Connecting to load proxy %s:%u\n",inet_ntoa(m_vip_addr.sin_addr),ntohs(m_vip_addr.sin_port));
	while(connect(m_sock,(sockaddr*)&m_vip_addr,sizeof(m_vip_addr))!=0)
	{
#ifdef _WIN32
		Sleep(1000);
#else
		sleep(1);
#endif
		printf("Retrying load proxy %s:%u\n",inet_ntoa(m_vip_addr.sin_addr),ntohs(m_vip_addr.sin_port));
	}
	printf("Connected to load proxy %s:%u\n",inet_ntoa(m_vip_addr.sin_addr),ntohs(m_vip_addr.sin_port));
	return 0;
}

bool CTelOrbLoadLogger::startLogging()
{
	if(!g_logger.openLoadLogFiles())
		return false;
	PeriodicTimer((unsigned int)m_logInterval*1000);
	return true;

}

void CTelOrbLoadLogger::HandlePeriodicTimeout()
{
	int res = send(m_sock,m_ekm,4,0);
	if(res != 4)
	{
		printf("Error: Failed to send to load proxy\n");
		
	}
	m_tmpfds = m_fds;
	select(m_sock+1, &m_tmpfds, NULL, NULL, &m_tv);
	if(FD_ISSET(m_sock,&m_tmpfds))
	{
		res = recv(m_sock,m_buff.get(),0xffff,0);
		if(res < 1)
		{
			if(res == -1)
			{
				printf("Error: Broken pipe from load proxy\n");
				exit(1);
			}
			printf("Error: The load proxy closed the connection\n");
			exit(1);
		}
		m_readings++;
		g_logger.logLoad(m_buff.get(),m_readings,m_logInterval);
	}

}

void CTelOrbLoadLogger::HandleTimeout()
{
	fprintf(stderr,"\nError: CTelOrbLoadLogger::HandleTimeout should never be called\n\n");
	exit(1);
}

void CTelOrbLoadLogger::ShutDown()
{
	StopPeriodicTimer();
}
