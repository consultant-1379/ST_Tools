// Logger.h: interface for the CLogger class.
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
//! \file Logger.h
//! \brief declares the class CLogger used by loadlogger
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
#ifndef LOGGER_H
#define LOGGER_H
#include <stdio.h>
#include "Globals.h"
#include "types.h"
#include "enums.h"
#include "Functions.h"
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <sys/types.h>
#include <sys/time.h>

//! \brief Declares the class CLogger
//!
//! The class manage the logging of readings, summary and pool configuration
class CLogger  
{
public:
	//! \brief The constructor of the class
	CLogger();
	//! \brief The destructor of the class
	virtual ~CLogger();

	//! \brief Sets if to log additional files in binary format
	//! \arg IN log_bin - If true log binary files. If false don't log binary files
	void setLogBinary(bool log_bin);

	//! \brief Exclude a dicos processor from the average processor load
	//! \arg IN name - The name of the dicos processor to exclude
	void excludeDicos(pchar name);

	//! \brief Set the name of the pool configuration file name
	//! \arg IN name - The name of the pool configuration file name
	void setPoolFileName(pchar name);

	void setLogLoadReadings(bool doLog);

	void setLogMemReadings(bool doLog);

	//! \brief The function logs the pool configuration
	//! \arg IN pools - The vector with the pool configuration \n
	//!      IN type - The processor type \n
	//!      IN name - The name of the processor
	void logPools(vector<string> pools, ProcessorTypeE type, pchar name);

	//! \brief prints a separation line in the totala summary file
	void printSummarySeparator();

	//! \brief Get the current processor loads
	//! \arg OUT sysload - The average system processor load \n
	//!      OUT traffic - The average traffic processor load \n
	//!      OUT oam - The average OAM processor load
	void getCurrentTrafficLoad(double& sysload, double& traffic, double& traffic_aver, double& oam);

	//! \brief Opens files for logging processor load readings.
	//! 
	//! The function opens files to log processor load readings
	//! if loadlogger is configured to log readings. It also writes a file header
	//! \arg IN dolog - If readings are to be logged or not
	//! \return Returns true if successful otherwise false	
	bool openLoadLogFiles();

	bool openMemLogFiles();


	//! \brief Searches for a processor in the list
	//! \arg IN name - The name of the processor to search for
	//! \return Retruns -1 if the processor cannot be found otherwise the position is returned
	int findProcessor(string name);

	//! \brief Logs the load reading of a linux, loader or dicos processor
	//! The function calculates the overall average processor load for the
	//! processor and keeps track of the maximum load
	//! \arg IN ldata - Contains the string with the information of the processor loads \n
	//!      IN reading - The number of the reading \n
	//!      IN ival - The value of the sampling interval \n
	//!      IN dolog - If to log the reading to file or not
	void logLoad(pchar ldata, uint reading, uint ival);

	
	//! \brief Writes the load summary to file for linux, loader or dicos processor
	bool writeLoadSummary();
	
	//! \brief Writes the memory usage summary to file for linux, loader or dicos processor
	bool writeMemSummary();

	//! \brief Logs a memory reading for a processor
	//! \arg IN theProc - The processor instance to log the reading for
	//!      IN reading - The sequence number of the reading
	//!      IN mem - The memory usage for the processor
	//!      IN dbn - The DBN memory usage for the processor
	void logMemory(ProcInstance* theProc, uint reading, uint mem, uint dbn);

	//! \brief Sets the name of the overall processor load summary file
	bool setLoadSummaryName(pchar fName);

	//! \brief Sets the name of the overall memory usage summary file
	bool setMemSummaryName(pchar fName);

	//! \brief Sets the number for which to build the over time load average
	void setBuildAverOver(uint theNumber);

	//! \brief Sets the name of the overall summary file
	bool setAllSummaryName(pchar fName);

	//! \brief Sets the name of the directory where to write the memory usage log files
	bool setMemDir(pchar path);

	//! \brief Sets the name of the directory where to write the processor load log files
	bool setLoadDir(pchar path);

	//! \brief Sets the name of the directory where to write the summary log files
	bool setSummaryDir(pchar path);

	void setGraphScanSize(int ival);
	
	bool getSaveGraphData();

private:

	//! \brief Searched for a processor in list of excluded processors
	//! \arg IN name - The name of the processor to search for
	//! \return Returns tru if the processor is found in the list of 
	//! excluded processors otherwise false
	bool isExcludedDicos(string name);

	//! \brief Gets all the processors of a type from the member list of processors
	//! \arg INOUT theProcs - The list of processor names is returned in the parameter
	//!      IN theType - The type of processor to return in the list
	//! \return Returns the number of processors found
	int getProcessors(vector<ProcInstance>& theProcs, ProcessorTypeE theType);

	//! \brief Inititiates the average, max and min values for
	//! memory and load for the member list of processors
	void initAverValues();

	//! \brief Member for utility functions. See CFunctionsfor more information
	CFunctions fun;

	//! \brief Holds the path of the directory where to write the
	//! summary files.
	string m_summaryDir;

	//! \brief Holds the path of the directory where to write the
	//! memory logging files.
	string m_memDir;

	//! \brief Holds the path of the directory where to write the
	//! load logging files.
	string m_loadDir;

	//! \brief Holds the name of the all summary file.
	string m_allSummaryName;

	//! \brief Holds the name of the memory usage summary file 
	//! for linux, loader and dicos processors.
	string m_memSummaryName;


	//! \brief Holds the name of the processor load summary file
	//! for linux, loader and dicos processors.
	string m_loadSummaryName;

	//! \brief Holds the name of the pool distribution file.
	string m_poolFileName;

	//! \brief The file handle for the all summary file.
	FILE* m_allSummary;

	//! \brief The file handle for the memory usage summary file 
	//! for linux, loader and dicos processors.
	FILE* m_memSummary;

	//! \brief The file handle for processor load summary file
	//! for linux, loader and dicos processors.
	FILE* m_loadSummary;

	//! \brief The file handle for the pool distribution file.
	FILE* m_poolFile;

	//! \brief The file handle for binary format average traffic processor load
	//! for all not excluded dicos processors.
	FILE* m_dicosBinLoadTraffic;

	//! \brief The file handle for binary format average system processor load
	//! for all not excluded dicos processors.
	FILE* m_dicosBinLoadSystem;

	//! \brief The file handle for binary format average OAM processor load
	//! for all not excluded dicos processors.
	FILE* m_dicosBinLoadOAM;

	//! \brief Array of file handels for logging readings of linux memory usage
	vector<FILE*> m_linuxMemFiles;

	//! \brief Array of file handels for logging readings of loader memory usage
	vector<FILE*> m_loadersMemFiles;

	//! \brief Array of file handles for logging readings of dicos memory usage
	vector<FILE*> m_dicosMemFiles;

	//! \brief Array with names of excluded dicos processors.
	vector<string> m_excludedDicos;

	//! \brief Holds the number of linux memory usage readings.
	uint m_linuxMemReadings;

	//! \brief Holds the number of loader memory usage readings.
	uint m_loadersMemReadings;
	
	//! \brief Holds the number of dicos memory usage readings.
	uint m_dicosMemReadings;

	//! \brief Holds the number of linux processor load readings.
	uint m_linuxLoadReadings;

	//! \brief Holds the number of loader processor load readings.
	uint m_loadersLoadReadings;
	
	//! \brief Holds the number of dicos processor load readings.
	uint m_dicosLoadReadings;

	//! \brief Holds the number of intervals for which to build the over time average traffic load.
	uint m_buildOTALNr;

	//! \brief Holds the total number of dicos processors
	uint m_nrOfDicos;

	//! \brief Holds the number of excluded dicos processors
	uint m_nrOfExcludedDicos;

	//! \brief Holds the current average system processor load for not excluded dicos processors.
	double m_cur_dicos_sys_load;

	//! \brief Holds the current average traffic processor load for not excluded dicos processors.
	double m_cur_dicos_traffic_load;

	//! \brief Holds the current average traffic processor load over an interval for not excluded dicos processors.
	double m_cur_dicos_ota_load;
	
	//! \brief Holds the current average OAM processor load for not excluded dicos processors.
	double m_cur_dicos_oam_load;

	vector<ProcInstance> m_proc_list;

	vector<double> m_otl_vals;

	//! \brief Flag that indicates if to also log readings in binary format.
	bool m_log_binary;

	//! \brief Flag that indicates if to log load readings to file
	bool m_logLoadReadings;

	//! \brief Falg that indicates if to log memory readings to file
	bool m_logMemReadings;

	bool            m_saveGraphData;
    std::string	    m_graphDataFile;
    std::ofstream	m_outFile;
    unsigned int    m_graphScanSize;
    unsigned int    m_accload_system;
    unsigned int    m_accload_traffic;
    unsigned int    m_accload_oam;
    unsigned int    m_accTimes;
    struct timeval  m_timeOffset;




};

#endif
