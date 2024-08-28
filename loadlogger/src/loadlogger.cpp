// loadlogger.cpp
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
//! \file loadlogger.cpp
//! \brief The main entry point for loadlogger.
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
#include <signal.h>

#include "Globals.h"
#include "ConfigReader.h"
#include "TelOrbMemLogger.h"
#include "TelOrbLoadLogger.h"
#include "Functions.h"
#include "Logger.h"

#ifdef _WIN32
#include <winsock2.h>
#include <direct.h>
#include <conio.h>
#else
#include <unistd.h>
#endif

/**
* \defgroup GlobalObjects Global objects
*/

//! \addtogroup GlobalObjects
//! @{

//! \brief The configuration file parser
CConfigReader m_cfgReader;

#ifdef _IOMEM_LOGGING
//! \brief The IO processor memory reader 
CIoMemLogger m_IoMl;
#endif

//! \brief The TelOrb memory reader
//!
//! It reads the memory from the Linux, Loader and 
//! Dicos processors. It reads the DBN and execution memory
//! usage
CTelOrbMemLogger m_TOMl;

//! \brief The TelOrb processor load reader
//!
//! It reads the system, oam and traffic load for
//! the processors that are not excluded
CTelOrbLoadLogger m_TOLl;

//! \brief Various utilities see \ref CFunctions
CFunctions m_fun;

//! \brief The common logger for all
CLogger g_logger;
//! @}


//! \brief Prints version information
void PrintInfo();

//! \brief Opens the default configuration file for editing
bool configurate();

//! \brief Opens the specified configuration file for editing
bool configurate(char* fName);

//! \brief Captures the ctrl+c event
//!
//! When ctrl+c is pressed by the operator this function
//! is called by the operating system. \n
//! The function makes sure that a nice shutdown is performed
//! so no data will be lost
void operator_shutdown(int sig);

//! \brief Prints the help
void printusage();

//! \brief Holds then name of the configuration file
char fName[255];

//! \brief Holds the state of the logging
bool running;

//! \brief Tells if to stop logging after the configured time 
//! or not
bool g_tlimited;

//! \brief Tells if the program is shutdown by ctrl+c or by timeout
bool g_operator_shdwn;

//! \brief Tells if the program is shutdown by an unrecoverable error
bool g_error;

//! \brief Tells if to log memory usage readings of processors or not
bool no_mem_log;

//! \brief Tells if to log load readings of processors or not
bool no_load_log;

//! \brief Holds the interval for which load readings are going to be done
int load_ival;

//! \brief Holds the interval for which memory readings are going to be done
int mem_ival;

//! \brief Stores the time the program has been started
time_t m_start;

//! \brief Stores the number of seconds to log
time_t g_s2log;

//
int g_hh, g_mm, g_ss;
#ifdef _WIN32
	WSADATA wsaData;
#endif

        
char cfgTemplate[1024];   
        
int main(int argc, char* argv[])
{ //int main(int argc, char* argv[])
	running = true;
	g_tlimited = false;
	g_error = false;
	g_operator_shdwn = false;
	no_mem_log = false;
	no_load_log = false;
	load_ival = 1;
	mem_ival = 1;
	bool useCfg = false;
	fName[0] = 0;
	int k;
        
        
        char * path = getenv("ST_TOOL_PATH");
        
	if (path == NULL) {
		printf("ERROR: Env variable ST_TOOL_PATH not defined \n");
 		return 1;
	}
        
        else {
                strcpy(cfgTemplate,path);
        }

        strcat(cfgTemplate, CONFIG_TEMPLATE);
                
	for(k=1;k<argc;k++)
	{
		if(strcmp(argv[k],"-cf")==0)
		{
			k++;
			if(k==argc)
			{
				fprintf(stderr,"Wrong usage of switch -cf\n");
				fprintf(stderr,"Usage -cf <cfg file>");
				return 1;
			}
			strcpy(fName,argv[k]);
			if(!m_fun.fExists(fName))
			{
			   fprintf(stderr,"\nCould not find file %s\n",fName);
			   fprintf(stderr,"%s\n\n",strerror(errno));
			   return 1;
			}
			useCfg = true;
			break;
		}
		else if(strcmp(argv[k],"-h") == 0)
		{ //if(strcmp(argv[i],"-h") == 0)
			printusage();
			return 0;
		} //if(strcmp(argv[i],"-h") == 0)

	}
#ifdef LINUX
	if(!useCfg)
	{ //if(!useCfg)
//   		char *username = getlogin();
   		char * username = getenv("HOME");
        if(username != NULL)
   		{ //if(username != NULL)
   			char cfgpath[500];
   			sprintf(cfgpath,"%s/%s/",username,CONFIGURATION_PATH);
   			sprintf(fName,"%s/%s/",username,CONFIGURATION_PATH);
   			if(m_fun.CreateDir(fName))
   			{ //if(m_fun.CreateDir(fName))
   				strcat(fName,CONFIGURATION_FILE);

   				if(!m_fun.fExists(fName))
   				{
   					char cmd[1024];
   					sprintf(cmd,"cp %s %s.",cfgTemplate,cfgpath);
   					if(system(cmd)!=0)
   					{
   						printf("Failed to copy a template configuration file to directory %s\n", cfgpath);
   						printf("Try to copy the file %s manually to %s and try again\n",cfgTemplate,cfgpath);
   						return 0;
   					}
   					sprintf(cmd,"chmod 644 %s",fName);
   					system(cmd);
   					printf("You need to configure loadlogger before running it.\n");
   					printf("Do you want to configure it now? (y/n): ");
   					char ch = getchar();
   					if((ch=='y') | (ch=='Y'))
   					{
   						char edt[500];
   						if(!m_cfgReader.getEditor(fName,edt))
   							return 0;
   						sprintf(cmd,"%s %s",edt,fName);
   						system(cmd);
   					}
   					return 0;
   				}
   			} //if(m_fun.CreateDir(fName))
   			else
   			{
   				printf("Error: Failed to create configuration directory %s\n",cfgpath);
   				printf("Try to create the directory manually and try again\n");
   				return 0;
   			}
   		} //if(username != NULL)
   		else
   		{
   			printf("Error: Failed to get your HOME directory\n");
   			printf("Check that the environment variable HOME exist and try again\n");
   			return 0;
   		}
   } //if(!useCfg)
#else //LINUX
	if(!useCfg)
	{
		char homepath[500];
		DWORD mlen = 255;
		if(::ExpandEnvironmentStrings("%HOMEDRIVE%",homepath,mlen))
		{
			strcpy(fName,homepath);
		}
		else
		{
			printf("Failed to get home drive\n");
			printf("Set the enviroment variable HOMEDRIVE to your home drive\n");
			printf("and try again\n");
			printf("Example: set HOMEDRIVE=C:\n");
			return 0;
		}
		if(::ExpandEnvironmentStrings("%HOMEPATH%",homepath,mlen))
		{
			strcat(fName,homepath);
		}
		else
		{
			printf("Failed to get home directory\n");
			printf("Set the enviroment variable HOMEPATH to your home directory\n");
			printf("and try again\n");
			printf("Example: set HOMEPATH=\"\\My Documents\"");
			return 0;
		}
		if((fName[strlen(fName)-1])!='\\')
			strcat(fName,"\\");
		strcat(fName,CONFIGURATION_FILE);
		if(!m_fun.fExists(fName))
		{
			printf("Coulden't find configuration file %s\n",fName);
			return 0;
		}
	}
	WORD ver = MAKEWORD(2,2);
	if(WSAStartup(ver,&wsaData)!=0)
	{
		printf("Failed to initiate sockets\n");
		printf("Error: %s\n",strerror(WSAGetLastError()));
		return 0;
	}
#endif //LINUX
	for(k=1;k<argc;k++)
	{
		if(strcmp(argv[k],"-cfg")==0)
		{
			bool result = false;
			if(useCfg)
				result = configurate(fName);
			else
				result = configurate();
			if(result)
			{
				printf("Do you want to run loadlogger now? (no/yes): ");
				while(true)
				{
					char ans[10];
					fgets(ans,9,stdin);
					m_fun.rtrim(ans);
					if(strcmp(ans,"no")==0) return 0;
					else if(strcmp(ans,"yes")==0) break;
				}
			}
			break;
		}
	}
	if(!m_cfgReader.ReadCfg(fName))
		return 0;

	if(argc>1)
	{ //if(argc>1)
		for(int i=1;i<argc;i++)
		{ //for(int i=1;i<argc;i++)
			if(strcmp(argv[i],"-b") == 0)
			{ //if(strcmp(argv[i],"-b") == 0)
				g_logger.setLogBinary(true);
			} //if(strcmp(argv[i],"-b") == 0)
			else if(strcmp(argv[i],"-h") == 0)
			{ //if(strcmp(argv[i],"-h") == 0)
				printusage();
				return 0;
			} //if(strcmp(argv[i],"-h") == 0)
			else if(strcmp(argv[i],"-ver") == 0)
			{ //if(strcmp(argv[i],"-ver") == 0)
				PrintInfo();
				return 0;
			} //if(strcmp(argv[i],"-ver") == 0)
			else if(strcmp(argv[i],"-vip") == 0)
			{ //if(strcmp(argv[i],"-vip") == 0)
				i++;
				if(i == argc)
				{ //if(i == argc)
					printf("Wrong usage of option -vip\n");
					return 1;
				} //if(i == argc)
				m_TOMl.setHost(argv[i]);
				if(!m_TOLl.Init(argv[i]))
					return 1;

			} //if(strcmp(argv[i],"-vip") == 0)
			else if(strcmp(argv[i],"-dp") == 0)
			{ //if(strcmp(argv[i],"-dp") == 0)
				i++;
				if(i == argc)
				{ //if(i == argc)
					printf("Wrong usage of option -dp\n");
					return 0;
				} //if(i == argc)
				int pval = atoi(argv[i]);
				if(pval < 1)
				{ //if(pval < 1)
					printf("Wrong usage -dp %s\n",argv[i]);
					return 0;
				} //if(pval < 1)
				m_TOMl.setPort(pval);
			} //if(strcmp(argv[i],"-dp") == 0)
			else if(strcmp(argv[i],"-lp") == 0)
			{ //if(strcmp(argv[i],"-lp") == 0)
				i++;
				if(i == argc)
				{ //if(i == argc)
					printf("Wrong usage of option -lp\n");
					return 0;
				} //if(i == argc)
				int pval = atoi(argv[i]);
				if(pval < 1)
				{ //if(pval < 1)
					printf("Wrong usage -lp %s\n",argv[i]);
					return 0;
				} //if(pval < 1)
				m_TOLl.Init(pval);
			} //if(strcmp(argv[i],"-lp") == 0)
			else if(strcmp(argv[i],"-li") == 0)
			{ //if(strcmp(argv[i],"-li") == 0)
				i++;
				if(i == argc)
				{ //if(i == argc)
					printf("Wrong usage of option -li\n");
					return 0;
				} //if(i == argc)
				int ival = atoi(argv[i]);
				if(ival < 1)
				{ //if(ival < 1)
					printf("Wrong usage -li %s\n",argv[i]);
					return 0;
				} //if(ival < 1)
				m_TOLl.SetLogInterval(ival);
				load_ival = ival;
			} //if(strcmp(argv[i],"-li") == 0)
			else if(strcmp(argv[i],"-mi") == 0)
			{ //if(strcmp(argv[i],"-mi") == 0)
				i++;
				if(i == argc)
				{ //if(i == argc)
					printf("Wrong usage of option -mi\n");
					return 0;
				} //if(i == argc)
				int ival = atoi(argv[i]);
				if(ival < 1)
				{ //if(ival < 1)
					printf("Wrong usage -mi %s\n",argv[i]);
					return 0;
				} //if(ival < 1)
				m_TOMl.SetLogInterval(ival);
				mem_ival = ival;
			} //if(strcmp(argv[i],"-mi") == 0)
			else if(strcmp(argv[i],"-nm") == 0)
			{
				g_logger.setLogMemReadings(false);
				no_mem_log = true;
			}
			else if(strcmp(argv[i],"-nl") == 0)
			{
				g_logger.setLogLoadReadings(false);
				no_load_log = true;
			}
			else if(strcmp(argv[i],"+t") == 0)
			{ //if(strcmp(argv[i],"+t") == 0)
				i++;
				if(i==argc)
				{ //if(i==argc)
					printf("Wrong usage of option +t\n");
					return 0;
				} //if(i==argc)
				g_s2log = m_fun.StrToTime(argv[i],g_hh,g_mm,g_ss);
				g_tlimited = true;
			} //if(strcmp(argv[i],"+t") == 0)
			else if(strcmp(argv[i],"-t") == 0)
			{ //if(strcmp(argv[i],"-t") == 0)
				g_tlimited = false;
			} //if(strcmp(argv[i],"-t") == 0)			
			else if(strcmp(argv[i],"-cf") == 0)
			{ //if(strcmp(argv[i],"-cf") == 0)
				i++;
				if(i == argc)
				{ //if(i == argc)
					printf("Wrong usage of option -cf\n");
					return 0;
				} //if(i == argc)
				
			} //if(strcmp(argv[i],"-cf") == 0)
			else if(strcmp(argv[i],"-cfg") == 0)
			{ 
			} 			
			else
			{
				fprintf(stderr,"\nIllegal option %s\n\n",argv[i]);
				exit(1);
			}
		} //for(int i=1;i<argc;i++)
	} //if(argc>1)

	g_logger.setLoadSummaryName("loadSummary.txt");
	g_logger.setAllSummaryName("Summary.txt");
	g_logger.setMemSummaryName("memSummary.txt");
	g_logger.setPoolFileName("PoolDistribution.txt");

	char cmd[100];

	// Starting graphical part

	if (g_logger.getSaveGraphData())
	{
		strcpy(cmd, "cp $ST_TOOL_PATH/share/loadlogger/gnuplot_commands.txt .");
		if(system(cmd)!=0)
		{
						printf("Failed to copy $ST_TOOL_PATH/share/loadlogger/gnuplot_commands.txt file \n");
						return 0;
		}

		strcpy(cmd, "chmod 755 gnuplot_commands.txt .");
		if(system(cmd)!=0)
		{
						printf("Failed to change persission to gnuplot_commands.txt file \n");
						return 0;
		}

		strcpy(cmd, "cp $ST_TOOL_PATH/share/loadlogger/loop_forever.gnu .");
		if(system(cmd)!=0)
		{
						printf("Failed to copy a $ST_TOOL_PATH/share/loadlogger/loop_forever.gnu\n");
						return 0;
		}

		strcpy(cmd, "chmod 755 loop_forever.gnu .");
		if(system(cmd)!=0)
		{
						printf("Failed to change persission to loop_forever.gnu file \n");
						return 0;
		}

		strcpy(cmd, "gnuplot gnuplot_commands.txt >& /dev/null &");
		if(system(cmd)!=0)
		{
						printf("Failed to start gnuplot \n");
						return 0;
		}

	}


	if(m_TOMl.Connect() == -1)
		return 0;

	if(m_TOLl.Connect()==-1)
		return 0;
	if(signal(SIGINT,operator_shutdown)==SIG_ERR)
	{
		printf("Warning: Failed to listen for ctrl+c\n");
		printf("Warning: You may loose data if interupting the execution\n\n");
	}


	if(!m_TOMl.startLogging()) return 0;
	printf("\n");
	if(no_load_log)
		printf("Won't log load intervals\n");
	if(no_mem_log)
		printf("Won't log memory intervals\n");
	if(g_tlimited)
		printf("Will exit after %02u:%02u:%02u\n",g_hh,g_mm,g_ss);
	printf("\n");
	if(!m_TOLl.startLogging())
	{
		m_TOMl.ShutDown();
		return 0;
	}

	time_t start,nu;
	time(&start);

	double sv, tv, tvaver, oam;
	char proc[500];
	int infolen = 0;
	if(g_tlimited)
	{ //if(g_tlimited)
		while(running && !g_error)
		{ //while(running)
#ifdef _WIN32
			Sleep(1000);
#else
			sleep(1);
#endif

			g_logger.getCurrentTrafficLoad(sv,tv,tvaver,oam);
			memset(proc,8,infolen);
			proc[infolen] = '\0';
			fprintf(stdout,proc);
			fflush(stdout);
			sprintf(proc,"System: %6.3f, Traffic: %6.3f, O&M: %6.3f, Total: %6.3f, OTAL: %6.3f",sv,tv,oam,(sv+tv+oam),tvaver);
			printf(proc);
			infolen = strlen(proc);

			time(&nu);
			if((nu-start)>=(g_s2log))
			{
				running = false;
			}
		} //while(running)
	} //if(g_tlimited)
	else
	{ //else to if(g_tlimited)
		while(running && !g_error)
		{ //while(running)
#ifdef _WIN32
			Sleep(1000);
#else
			sleep(1);
#endif
			g_logger.getCurrentTrafficLoad(sv,tv,tvaver,oam);
			memset(proc,8,infolen);
			proc[infolen] = '\0';
			fprintf(stdout,proc);
			fflush(stdout);
			sprintf(proc,"System: %6.3f, Traffic: %6.3f, O&M: %6.3f, Total: %6.3f, OTAL: %6.3f",sv,tv,oam,(sv+tv+oam),tvaver);
			printf(proc);
			infolen = strlen(proc);
		} //while(running)
	} //else to if(g_tlimited)
	printf("\n");
	if(g_operator_shdwn)
	{
		printf("Shutting down...\n\n");
	}
	else
	{
		if(g_error) running = false;
		else printf("Time elapsed.\n\n");
	}
	m_TOLl.ShutDown();
	m_TOMl.ShutDown();
#ifdef _WIN32
	Sleep(2000);
#else
	sleep(2);
#endif
	if(g_logger.writeMemSummary())
		g_logger.printSummarySeparator();
	if(g_logger.writeLoadSummary())
		g_logger.printSummarySeparator();


	// reset gnuplot

	if (g_logger.getSaveGraphData()){
		strcpy(cmd, "ps -eaf | grep \"gnuplot gnuplot_commands.txt\" | grep -v \"grep\" | awk '{print $2}' | xargs kill");
		if(system(cmd)!=0){
				printf("Failed to kill gnuplot \n");
				return 0;
		}
	}


	return 0;
}

void printusage()
{ //void printusage()
	printf("\nloadlogger version %s\n\n",PROGRAM_VERSION);
	printf("loadlogger [options]\n\n");

	printf("-b                    Log load in binary format as well\n\n");

	printf("-cf <cfg file>        Specify the configuration file to use\n\n");

	printf("-cfg                  Configure loadlogger\n\n");

	printf("-dp <port>            Specify the DORB IO port\n\n");

	printf("-h                    Prints this help\n\n");

	printf("-li <interval>        Specify the load log interval in seconds.\n");
	printf("                      The default interval is 1 second\n\n");

	printf("-lp <port>            Specify the loadlogger port\n\n");

	printf("-mi <interval>        Specify the memory log interval in seconds.\n");
	printf("                      The default interval is 1 second\n\n");

	printf("-nl                   Don't log load intervals, just print summary\n\n");

	printf("-nm                   Don't log memory intervals, just print summary\n\n");

	printf("+t <hh:mm:ss>         Stop logging after hh hours, mm minutes and ss seconds\n");
	printf("+t <mm:ss>            Stop logging after mm minutes and ss seconds\n");
	printf("+t <ss>               Stop logging after ss seconds\n\n");

	printf("-t                    Log until ctrl+c is pressed\n\n");

	printf("-ver                  Print version information\n\n");

	printf("-vip <vip>            Specify the vip address/hostname\n\n");

} //void printusage()


void PrintInfo()
{ //void PrintInfo()

/****************************************************************************/
/* void PrintInfo()															*/
/* Prints program version and a few more things     						*/
/****************************************************************************/

#ifdef _WIN32
#ifdef _DEBUG
	printf("\nApplication name:         %s.exe\n",DEBUG_APP_NAME);
#else
	printf("\nApplication name:         %s.exe\n",APP_NAME);
#endif
#else
#ifdef _DEBUG
	printf("\nApplication name:         %s\n",DEBUG_APP_NAME);
#else
	printf("\nApplication name:         %s\n",APP_NAME);
#endif
#endif
#ifdef _DEBUG
	printf("Application version:      %s\n",DEBUG_VERSION);
#else
	printf("Application version:      %s\n",PROGRAM_VERSION);
#endif
	printf("\nSend bug reports or comments to olov.marklund@ericsson.com\n\n");
} //void PrintInfo()

bool configurate(char* fName)
{
#ifdef LINUX
	if(!m_fun.fExists(fName))
	{
		fprintf(stderr,"Error: Could not find configuration file %s\n",fName);
		return false;
	}
	char cmd[1024];
	char edt[500];
	if(!m_cfgReader.getEditor(fName,edt))
		return false;
	sprintf(cmd,"%s %s",edt,fName);
	if(system(cmd)!=0)
	{
		fprintf(stderr,"Error: Failed to execute %s\n",cmd);
		fprintf(stderr,"Error: %s\n",strerror(errno));
		return false;
	}
#endif
	return true;

}

bool configurate()
{
	char fName[500];
	fName[0] = 0;
#ifdef LINUX
	char *username = getlogin();
	if(username != NULL)
	{ //if(username != NULL)
		sprintf(fName,"/home/%s/%s/%s",username,CONFIGURATION_PATH,CONFIGURATION_FILE);
		char cmd[1024];
		char edt[500];
		if(!m_cfgReader.getEditor(fName,edt))
			return false;
		sprintf(cmd,"%s %s",edt,fName);
		if(system(cmd)!=0)
		{
			fprintf(stderr,"Error: Failed to execute %s\n",cmd);
			fprintf(stderr,"Error: %s\n",strerror(errno));
			return false;
		}
		return true;
	}
	fprintf(stderr,"Error: Failed to get your login name\n");
	fprintf(stderr,"Check that the environment variable USER exist and try again\n");
	return false;
#else
	return true;
#endif
}

void operator_shutdown(int sig)
{
	if(sig==SIGINT)
	{
		running = false;
		g_operator_shdwn = true;
	}
	if(signal(SIGINT,operator_shutdown)==SIG_ERR)
	{
		fprintf(stderr,"Warning: Failed to listen for ctrl+c\n");
		fprintf(stderr,"Warning: You may loose data if interupting the execution\n");
	}
}


