// ConfigReader.h: interface for the CConfigReader class.
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
//! \file ConfigReader.h
//! \brief Declares the class CConfigReader used by loadlogger
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
#ifndef CONFIGREADER_H
#define CONFIGREADER_H
#include <vector>

#include "types.h"
#include "structs.h"
/**
* \defgroup CfgFileConstMacroDefs Configuration file parameter names
*/
//! \addtogroup CfgFileConstMacroDefs
//! @{

//! \anchor CFG_FILE_VERSION 
//! CFG_FILE_VERSION Defines the version of the configuration \n
//!                  file syntax version \n
#define CFG_FILE_VERSION	"1.02"
//! CFG_VERSION_STRING Defines the version identification string \n
//!                    for \ref CFG_FILE_VERSION \n
//!
#define CFG_VERSION_STRING	"#File version 1.02"
//! \brief Defines the key words used in the 
//! configuration file

#define VIP					"VIP"
#define TELORB_SHELL_PORT	"TelorbShellPort"
#define LOADLOGGERPORT		"LoadLoggerport"
#define LOADLOGINTERVAL		"LoadLogInterval"
#define BUILDOTAL			"BuildOTALNr"
#define LOGLOADBINARY       "LogLoadBinary"
#define LOGLOADREADINGS		"LogLoadReadings"
#define MEMLOGINTERVAL		"MemLogInterval"
#define LOGMEMREADINGS		"LogMemReadings"
#define LOGTIME				"LogTime"
#define SUMMARYDIRECTORY	"SummaryDirectory"
#define MEMORYDIRECTORY		"MemoryDirectory"
#define LOADDIRECTORY		"LoadDirectory"
#define CFG_EDITOR			"CfgEditor"
#define EXCLUDEDICOS		"ExcludeDicos"
#define GRAPHSCANSIZE		"GraphScanSize"
//! @} 
using namespace std;

//! \brief Declares the class CConfigReader
//!
//! The class is used to parse the loadlogger configuration file
//!
class CConfigReader  
{
public:
	//! \brief The constructor of the class
	CConfigReader();

	//! \brief The destructor of the class
	virtual ~CConfigReader();

	//! \brief Reads the name of the editor do use to edit the \n
	//! default configuration file
	//! \arg IN  fName - The name of the configuration file \n
	//!      OUT edt   - The name of the editor to use
	//! \return Returns true if successful otherwise false
	bool getEditor(pchar fName, pchar edt);

	//! \brief Read a configuration file
	//! \arg IN fName - The name of the configuration file
	//! \return Returns true if successful otherwise false
	bool ReadCfg(pchar fName);

private:
	//! \brief Closes the configuration file and returns false
	//! \arg IN f - File handle to close
	//! \return Returns false
	bool err(FILE *f);

	//! \brief Holds the current line number read from the configuration file
	uint lcount;

	//! \brief Handle to the configuration file beeing parsed
	FILE *f;

};

#endif
