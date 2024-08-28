// Functions.h: interface for the CFunctions class.
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
//! \file Functions.h
//! \brief declares the class CFunctions used by loadlogger
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
#ifndef FUNCTIONS_H
#define FUNCTIONS_H

#include <time.h>
#include <stdio.h>
#include <vector>

#ifdef _WIN32
#include <winsock2.h>
#else
#include <sys/socket.h> 
#endif



#include "types.h"
#include "structs.h"

using namespace std;

//! \brief Declares the class CFunctions
//!
//! The class implements utility functions
//!
class CFunctions  
{
public:
	//! \brief The constructor of the class
	CFunctions();
	//! \brief The destructor of the class
	virtual ~CFunctions();

	//! \brief Creates a directory
	//!
	//! \arg IN - Path of the director to create
	//! \return Returns true if successful otherwise false
	bool CreateDir(pcchar path);

	//! \brief Converts a string to time format
	//! \arg IN str - The time in string format
	//!      OUT hh - The hours in the string
	//!      OUT mm - The minutes in the string
	//!      OUT ss - The seconds in the string
	//! \return Returns the time in time_t format
	time_t StrToTime(pchar str, int& hh, int& mm, int& ss);

	//! \brief Remove quotes from the argument
	//! \arg IN line - The line to remove the quotes from
	//! \return Returns the arguments without quotes
	pchar removeQuots(pchar line);

	//! \brief DNS lookup for host name
	//! Resolves host name to IP address
	//! \arg IN where - The host name or IP address to resolve \n
	//!      OUT hostname - The IP address. The buffer has to be at least 20 bytes
	//! \return Returns true if successful otherwise false
	bool get_hostip(struct in_addr *where, const char *hostname);

	//! \brief Removes comments from a line
	//! Removes the comment from al line. The comment token is #
	//! \arg INOUT line - The line to search for comments
	//! \return Returns the line with the comment removed
	pchar removeComment(pchar line);

	//! \brief Checks if the whole line is commented
	//! \arg IN line - The line to check if it is a commneted line
	//! \return Returns true if the line is commneted otherwise false
	bool isCommented(pchar line);

	//! \brief Right trims a line
	//!
	//! The function removes line feeds, spaces and tabulators from the end of the line
	//! \arg INOUT line - The line to right trim
	//! \return Returns the right trimmed line
	pchar rtrim(pchar line);

	//! \brief Left trims a line
	//!
	//! The function removes line feeds, spaces and tabulators from the begining of the line
	//! \arg INOUT line - The line to left trim
	//! \return Returns the left trimmed line
	pchar ltrim(pchar line);

	//! \brief Right and left trims a line
	//!
	//! The function removes line feeds, spaces and tabulators from the begining and end of the line
	//! \arg INOUT line - The line to trim
	//! \return Returns the trimmed line
	pchar trim(pchar line);

	//! \brief Checks if a file exists
	//!
	//! The function checks if a file exist and if you have reights to read it
	//! \arg IN fName - The name of the file
	//! \return Returns true if the file exist and you have reading rights 
	//!         otherwise false
	bool fExists(pchar fName);

};

#endif
