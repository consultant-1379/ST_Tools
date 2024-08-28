// ConfigReader.cpp
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
//! \file ConfigReader.cpp
//! \brief CConfigReader class implementation. This code implements the
//! \brief configuration file parser
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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <vector>
#include <memory>
#include "ConfigReader.h"
#include "Functions.h"
#include "TelOrbMemLogger.h"
#include "TelOrbLoadLogger.h"
#include "Logger.h"

using namespace std;

#ifdef _IOMEM_LOGGING
extern CIoMemLogger m_IoMl;
#endif
extern CTelOrbMemLogger m_TOMl;
extern CTelOrbLoadLogger m_TOLl;
extern CFunctions m_fun;
extern CLogger g_logger;
extern int g_hh, g_mm, g_ss;

extern time_t g_s2log;
extern bool g_tlimited;
extern bool no_load_log;
extern bool no_mem_log;
extern int load_ival;
extern int mem_ival;
extern char cfgTemplate[];
//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

CConfigReader::CConfigReader()
{

}

CConfigReader::~CConfigReader()
{

}

bool CConfigReader::ReadCfg(pchar fName)
{
	if((f=fopen(fName,"r"))==NULL)
	{
		printf("Failed to open configuration file %s\n",fName);
		printf("Error: %s\n",strerror(errno));
		return false;
	}

	char line[1024];
	if(fgets(line,1023,f)==0)
	{
		printf("Failed to read %s\n",fName);
		return err(f);
	}
	pchar pline = strstr(line,CFG_VERSION_STRING);
	if(pline==NULL)
	{
		printf("\n*******************************************************\n");
		printf("You are using a wrong version of the configuration file\n");
		printf("The correct version is %s\n",CFG_FILE_VERSION);
		printf("Replace the file %s with the template %s\n",fName,cfgTemplate);
		printf("or check the file %s for changes\n",cfgTemplate);
		printf("*******************************************************\n\n");

		printf("Do you want to copy a new template?\n");
		printf("NOTE: YOUR OLD CURRENT CONFIGURATION FILE WILL BE OVERWRITTEN\n\n");
		printf("Copy? (y/n): ");
		char ch = getchar();
		if((ch == 'y') | (ch == 'Y'))
		{
			err(f);
			char cmd[1024];
			sprintf(cmd,"cp %s %s",cfgTemplate,fName);
			if(system(cmd)==-1)
			{
				printf("\n\nError: %s\n",strerror(errno));
				printf("Failed to copy the template to %s\n",fName);
				printf("Copy manually %s to %s\n",cfgTemplate,fName);
				printf("Make the configurations using the -cfg switch and try again\n\n");
				return false;
			}
			printf("A new template has been copied to %s\n",fName);
			printf("Make the configurations using the -cfg switch and try again\n\n");
			return false;
		}
		return err(f);
	}
	lcount = 1;
	while((fgets(line,1023,f)!=NULL) & !feof(f))
	{ //while((fgets(line,1023,f)!=NULL) & !eof(f))
		lcount++;

		pline = m_fun.trim(line);
		if(m_fun.isCommented(pline))
			goto next_line;
		pline = m_fun.removeComment(pline);
//EXCLUDEDICOS
		if(strstr(line,EXCLUDEDICOS)!=NULL)
		{ //if(strstr(line,EXCLUDEDICOS)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",EXCLUDEDICOS);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			g_logger.excludeDicos(pline);
		} //if(strstr(line,EXCLUDEDICOS)!=NULL)

//VIP
		if(strstr(line,VIP)!=NULL)
		{ //if(strstr(line,VIP)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",VIP);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			m_TOMl.setHost(pline);
			if(!m_TOLl.Init(pline))
				return err(f);
		} //if(strstr(line,VIP)!=NULL)

//TELORB_SHELL_PORT

		if(strstr(line,TELORB_SHELL_PORT)!=NULL)
		{ //if(strstr(line,TELORB_SHELL_PORT)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",TELORB_SHELL_PORT);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			int port = atoi(pline);
			if(port==0)
			{
				printf("Invalid value %s\n",pline);
				printf("Line %u\n",lcount);
				return err(f);
			}
			m_TOMl.setPort(port);
		} //if(strstr(line,TELORB_SHELL_PORT)!=NULL)

//LOADLOGGERPORT
		if(strstr(line,LOADLOGGERPORT)!=NULL)
		{ //if(strstr(line,LOADLOGGERPORT)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",LOADLOGGERPORT);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			int port = atoi(pline);
			if(port==0)
			{
				printf("Invalid value %s\n",pline);
				printf("Line %u\n",lcount);
				return err(f);
			}
			m_TOLl.Init(port);
		} //if(strstr(line,LOADLOGGERPORT)!=NULL)


//LOADLOGINTERVAL
		if(strstr(line,LOADLOGINTERVAL)!=NULL)
		{ //if(strstr(line,LOADLOGINTERVAL)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",LOADLOGINTERVAL);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			int ival = atoi(pline);
			if(ival==0)
			{
				printf("Invalid value %s\n",pline);
				printf("Line %u\n",lcount);
				return err(f);
			}
			m_TOLl.SetLogInterval(ival);
			load_ival = ival;
		} //if(strstr(line,LOADLOGINTERVAL)!=NULL)
//BUILDOTAL
		if(strstr(line,BUILDOTAL)!=NULL)
		{ //if(strstr(line,BUILDOTAL)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",BUILDOTAL);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			int ival = atoi(pline);
			if(ival==0)
			{
				printf("Invalid value %s\n",pline);
				printf("Line %u\n",lcount);
				return err(f);
			}
			g_logger.setBuildAverOver((uint)ival);
		} //if(strstr(line,BUILDOTAL)!=NULL)

//MEMLOGINTERVAL
		if(strstr(line,MEMLOGINTERVAL)!=NULL)
		{ //if(strstr(line,MEMLOGINTERVAL)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",MEMLOGINTERVAL);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			int ival = atoi(pline);
			if(ival==0)
			{
				printf("Invalid value %s\n",pline);
				printf("Line %u\n",lcount);
				return err(f);
			}
			m_TOMl.SetLogInterval(ival);
			mem_ival = ival;
		} //if(strstr(line,MEMLOGINTERVAL)!=NULL)


//LOGLOADREADINGS
		if(strstr(line,LOGLOADREADINGS)!=NULL)
		{ //if(strstr(line,LOGLOADREADINGS)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",LOGLOADREADINGS);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			if(strcmp(pline,"true")!=0)
			{
				//m_TOLl.SetLogReadings(false);
				g_logger.setLogLoadReadings(false);
				no_load_log = true;
			}
		} //if(strstr(line,LOGLOADREADINGS)!=NULL)

		//GRAPHSCANSIZE
				if(strstr(line,GRAPHSCANSIZE)!=NULL)
				{ //if(strstr(line,GRAPHSCANSIZE)!=NULL)
					if((pline = strchr(pline,'='))==NULL)
					{ //if((pline = strchr(pline,'='))==NULL)
						printf("Missing =  after %s\n",GRAPHSCANSIZE);
						printf("Line %u\n",lcount);
						return err(f);
					} //if((pline = strchr(pline,'='))==NULL)
					pline++;
					pline = m_fun.ltrim(pline);
					pline = m_fun.removeQuots(pline);
					if(strlen(pline)==0)
					{
						printf("Missing parameter after =\n");
						printf("Line %u\n",lcount);
						return err(f);
					}
					int ival = atoi(pline);
					if(ival<0)
					{
						printf("Invalid value %s\n",pline);
						printf("Line %u\n",lcount);
						return err(f);
					}
					g_logger.setGraphScanSize(ival);
				} //if(strstr(line,LOGLOADREADINGS)!=NULL)

//LOGLOADBINARY
		if(strstr(line,LOGLOADBINARY)!=NULL)
		{ //if(strstr(line,LOGLOADBINARY)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",LOGLOADBINARY);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			if(strcmp(pline,"true")==0)
			{
				g_logger.setLogBinary(true);
			}
		} //if(strstr(line,LOGLOADBINARY)!=NULL)


//LOGMEMREADINGS
		if(strstr(line,LOGMEMREADINGS)!=NULL)
		{ //if(strstr(line,LOGMEMREADINGS)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",LOGMEMREADINGS);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			if(strcmp(pline,"true")!=0)
			{
				g_logger.setLogMemReadings(false);
				no_mem_log = true;
			}
		} //if(strstr(line,LOGMEMREADINGS)!=NULL)

//LOGTIME
		if(strstr(line,LOGTIME)!=NULL)
		{ //if(strstr(line,LOGTIME)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",LOGTIME);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			g_hh = g_mm = g_ss = 0;
			time_t t = m_fun.StrToTime(pline,g_hh,g_mm,g_ss);
			if(t>0)
			{
				g_s2log = t;
				g_tlimited = true;
			}
			else
				g_tlimited = false;
		} //if(strstr(line,LOGTIME)!=NULL)

//SUMMARYDIRECTORY
		if(strstr(line,SUMMARYDIRECTORY)!=NULL)
		{ //if(strstr(line,SUMMARYDIRECTORY)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",SUMMARYDIRECTORY);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			if(!g_logger.setSummaryDir(pline))
				return err(f);
		} //if(strstr(line,SUMMARYDIRECTORY)!=NULL)
//MEMORYDIRECTORY
		if(strstr(line,MEMORYDIRECTORY)!=NULL)
		{ //if(strstr(line,MEMORYDIRECTORY)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",MEMORYDIRECTORY);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			if(!g_logger.setMemDir(pline))
				return err(f);
		} //if(strstr(line,MEMORYDIRECTORY)!=NULL)
//LOADDIRECTORY
		if(strstr(line,LOADDIRECTORY)!=NULL)
		{ //if(strstr(line,LOADDIRECTORY)!=NULL)
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",LOADDIRECTORY);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			if(!g_logger.setLoadDir(pline))
				return err(f);
		} //if(strstr(line,LOADDIRECTORY)!=NULL)

next_line:;
	} //while((fgets(line,1023,f)!=NULL) & !eof(f))
	fclose(f);
	return true;
}

bool CConfigReader::err(FILE *f)
{
	fclose(f);
	f = NULL;
	return false;
}


bool CConfigReader::getEditor(pchar fName, pchar edt)
{
	FILE *f;
	if((f=fopen(fName,"r"))==NULL)
	{
		printf("Error: Failed to open file %s\n",fName);
		printf("Error: %s\n",strerror(errno));
		return false;
	}
	char line[1024];
	if(fgets(line,1023,f)==0)
	{
		printf("Failed to read %s\n",fName);
		return err(f);
	}
	pchar pline = strstr(line,CFG_VERSION_STRING);
	if(pline==NULL)
	{
		printf("You are using a wrong version of the configuration file\n");
		printf("The correct version is %s\n",CFG_FILE_VERSION);
		printf("Replace the file %s with the template %s\n",fName,cfgTemplate);
		return err(f);
	}
	uint lcount = 1;
	while((fgets(line,1023,f)!=0) & (!feof(f)))
	{
		lcount++;
		pline = m_fun.trim(line);
		if(m_fun.isCommented(pline))
			goto next_line;
		pline = m_fun.removeComment(pline);
		if((pline=strstr(pline,CFG_EDITOR))!=NULL)
		{
			if((pline = strchr(pline,'='))==NULL)
			{ //if((pline = strchr(pline,'='))==NULL)
				printf("Missing =  after %s\n",CFG_EDITOR);
				printf("Line %u\n",lcount);
				return err(f);
			} //if((pline = strchr(pline,'='))==NULL)
			pline++;
			pline = m_fun.ltrim(pline);
			pline = m_fun.removeQuots(pline);
			if(strlen(pline)==0)
			{
				printf("Missing parameter after =\n");
				printf("Line %u\n",lcount);
				return err(f);
			}
			strcpy(edt,pline);
			fclose(f);
			return true;
		}
next_line:;
	}
	return false;
}
