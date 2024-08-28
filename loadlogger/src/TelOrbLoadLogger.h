// TelOrbLoadLogger.h: interface for the CTelOrbLoadLogger class.
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
//! \file TelOrbLoadLogger.h
//! \brief declares the class CTelOrbLoadLogger used by loadlogger
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
#ifndef TELORBLOADLOGGER_H
#define TELORBLOADLOGGER_H
#ifdef _WIN32
#include <winsock2.h>
#else
#include <pthread.h>
#include <sys/socket.h> 
#endif

#include "structs.h"
#include "types.h"
#include "Functions.h"
#include "OMTimer.h"

#include <memory>
#include <vector>

using namespace std;

//! \brief Declares the class CTelOrbLoadLogger
//!
//! The class is used to log the processor load in the linux, loader and
//! and dicos processors
//!
class CTelOrbLoadLogger : public COMTimer 
{
public:
	//! \brief The constructor of the class
	CTelOrbLoadLogger();
	//! \brief The destructor of the class
	virtual ~CTelOrbLoadLogger();

	//! \brief Starts the logging and reading of the load.
	//! 
	//! The type of the processors and if it is excluded from the average load 
	//! are taken into account for
	//! loggings and calculations. 
	//! \return Returns true if successful otherwise false
	bool startLogging();

	//! \brief Initiate the TCP connection for the EKM protocol
	//! \return Returns 0 if successful otherwise -1
	int Connect();

	//! \brief Sets the reading sampling interval
	//! \arg IN ival - The interval in seconds
	void SetLogInterval(int ival);


	//! \brief Sets the remote port for the EKM protocol
	//! \arg IN port - The remote port number
	void Init(int port);

	//! \brief Sets and resolves the remote host for the EKM protocol
	//! \arg IN host - The host name or IP address to resolve
	//! \return Returns true if successful otherwise false
	bool Init(pchar host);

	void ShutDown();
	//! \brief Goes true when the operator presses ctrl+c. See TelOrbLoadLogger.cpp
	//static bool abort_requested;
private:
	void HandlePeriodicTimeout();

	void HandleTimeout();

	//! \brief The remote struct sockaddr_in
	sockaddr_in m_vip_addr; 

	//! \brief Member for utility functions See \ref CFunctions
	CFunctions m_fun;

	//! \brief The socket for communication
#ifdef _WIN32
	SOCKET m_sock;
#else
	int m_sock;
#endif

	int  m_logInterval;

	uint m_readings;
	fd_set m_fds, m_tmpfds;
	
	struct timeval m_tv;

	char m_ekm[4];

	auto_ptr<char> m_buff;

};
#endif
