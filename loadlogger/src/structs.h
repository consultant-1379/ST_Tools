// structs.h
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
//! \file structs.h
//! \brief defines structures used by loadlogger
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
#ifndef STRUCTS_H
#define STRUCTS_H
#include "types.h"
#include "enums.h"
#include "Globals.h"
#include "Telnet.h"
#ifdef _WIN32
#include <winsock2.h>
#else
#include <sys/socket.h> 
#endif
/**
* \defgroup LoadLoggerStructures Definition of structures used by loadlogger
*/
//! \addtogroup LoadLoggerStructures
//! @{


typedef struct _aver_values
{
   double vals[9];
}AVER_VALUES;

typedef struct _proc_instance
{
	string			name; 
	ProcessorTypeE	ptype;
	FILE*			lfptr;
	FILE*			mfptr;
	AVER_VALUES		laver;
	AVER_VALUES		maver;	
}ProcInstance;

//! @}


#endif
