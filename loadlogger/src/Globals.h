// Globals.h
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
//! \file Globals.h
//! \brief defines constants used by loadlogger
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
#ifndef GLOBALS_H
#define GLOBALS_H

#include <time.h>
#include "types.h"
/**
* \defgroup GlobalsMacroDefs Global definitions
*/
//! \addtogroup GlobalsMacroDefs
//! @{
//! Defines the debug version
#define			DEBUG_VERSION		"2.30 debug"
//! Defines the program version
#define			PROGRAM_VERSION		"2.30"
//! Defines the debug program name
#define			DEBUG_APP_NAME		"loadloggerdbg"
//! Defines the program name
#define			APP_NAME			"loadlogger"
//! Defines the default configuration path
#define			CONFIGURATION_PATH		".loadlogger"
//! Defines the path to the configuration template
#define			CONFIG_TEMPLATE			"/share/loadlogger/loadlogger30.cfg"
//! Defines the default name of the configuration file
#define			CONFIGURATION_FILE		"loadlogger30.cfg"

//! Defines the comment char used in the configuration file
#define			COMMENT_CHAR			'#'
//! Defines the length of the communication buffer
#define BUFFLEN 0xffff
//! Defines the maximum name length for processors
#define MAX_PROCESSOR_NAME_LEN 100
//! @}

/**
* \defgroup GlobalsConstDefs Global constant definitions
*/
#ifdef GLOBALS_H
//! \addtogroup GlobalsConstDefs
//! @{
//! \brief Defines some constant for ORB communication
/*
const uchar GIOP[4] = {0x47, 0x49, 0x4f, 0x50};  
const uchar GVER[2] = {0x01, 0x01};
const uchar BIG_EDIAN = 0x00;
const uchar LITTLE_EDIAN = 0x01;
const uchar GREQ = 0x00;
const uchar GREP = 0x01;
const uchar GNO_EXCEPTION[4] = {0x00, 0x00, 0x00, 0x00};
*/
//! @}
#endif
//! \brief Used for version checking to notify
//! users about news
struct _userdata
{
	time_t last_time;
	time_t first_time;
	uint times_used;
};

#endif


