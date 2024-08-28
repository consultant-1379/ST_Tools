// TelOrbMemLogger.cpp: implementation of the CTelOrbMemLogger class.
//
//////////////////////////////////////////////////////////////////////

#include "TelOrbMemLogger.h"
#include "enums.h"
#include "Logger.h"

#include <stdio.h>
#include <string.h>
#include <signal.h>

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////
extern CLogger g_logger;
extern bool g_error;
extern bool g_operator_shdwn;


CTelOrbMemLogger::CTelOrbMemLogger()
: m_logReadings(true)
, m_logInterval(1)
, m_readings(0)
{
}

CTelOrbMemLogger::~CTelOrbMemLogger()
{
#ifdef _DEBUG
printf("ENTER ~CTelOrbMemLogger()\n");
#endif
	StopPeriodicTimer();
#ifdef _DEBUG
printf("EXIT ~CTelOrbMemLogger()\n");	
#endif
}

void CTelOrbMemLogger::ShutDown()
{
	StopPeriodicTimer();
}

void CTelOrbMemLogger::OnError(string theError)
{
	g_error = true;
	StopPeriodicTimer();
	fprintf(stderr,"\nError: %s\n",theError.c_str());
	fprintf(stderr,"Exiting...\n");
}

void CTelOrbMemLogger::OnInfo(string theInfo)
{
	printf("%s\n",theInfo.c_str());
}

void CTelOrbMemLogger::OnConnectFailed(string theMsg)
{
	printf("%s\n",theMsg.c_str());
}

void CTelOrbMemLogger::OnEvent(string theEvent)
{
	printf("%s\n",theEvent.c_str());
}

void CTelOrbMemLogger::SetTelnetHost(char *host, unsigned short port)
{
	setHost(host);
	setPort(port);
}


bool CTelOrbMemLogger::startLogging()
{
	this->setPrompt("> ");
	this->setLogin("");
	this->setLoginPrompt("");
	this->setExitCmd("exit");
	this->setPasswordPrompt("");
	this->setLoginPassword("");
	int i,j;
	ProcessorTypeE theProcType = unknownProcessorTypeE;
	if(Connect()<0) return false;
	if(send_cmd("cd CLI/Processors")<0) return false;
	vector<string> myAnswer;
	vector<string> myProcessors;
	string tcmd;
	this->recv_answer(myAnswer);
	
	if(send_cmd("listprocessors")<0) return false;
	this->recv_answer(myProcessors);
	myProcessors.pop_back();
	m_procList.resize(myProcessors.size());
	m_processorGetInfoCmd.resize(myProcessors.size());
#ifdef _DEBUG
	for(i=0;i<myProcessors.size();i++)
	{
		printf("%s\n",myProcessors[i].c_str());
	}
#endif
	for(i=0;i<(int)myProcessors.size();i++)
	{
/*
IsLoader: Yes
Loading Group: ProcessorLoadingGroup
Processor Status: In service
Processor Type: LinuxIntelPc
Memory Usage: 59
Memory Alarm level: 70
Load Regulation level: 75
DBN Memory share level: 80
DBN Memory Usage: 0
DBN Memory Alarm level: 85

*/
//Processor Type: LinuxIntelPc
//Processor Type: IntelPc
//IsLoader: No
		if(g_operator_shdwn) return false;
		m_procList[i].name = myProcessors[i].c_str();
		myAnswer.clear();
		theProcType = unknownProcessorTypeE;
		m_processorGetInfoCmd[i] = string("getprocessorinfo ") + myProcessors[i].c_str();
		printf("Getting info for %s... ",myProcessors[i].c_str());
		if(send_cmd(m_processorGetInfoCmd[i].c_str())<0) return false;
		this->recv_answer(myAnswer);
		myAnswer.pop_back();
		for(j=0;j<(int)myAnswer.size();j++)
		{
#ifdef _DEBUG
			 printf("%s\n",myAnswer[j].c_str());
#endif
			 if(myAnswer[j]=="Processor Type: LinuxIntelPc")
			 {
				 theProcType = linuxProcessorE;
				 break;
			 }
			 if(myAnswer[j]=="Processor Type: IntelPc")
			 {
				 if(theProcType == loaderProcessorE) break;
				 theProcType = dicosProcessorE;
				 break;
			 }
			 else
			 {
				 if(myAnswer[j]=="IsLoader: Yes")
				 {
					 theProcType = loaderProcessorE;
				 }
			 }
		}
		m_procList[i].ptype = theProcType;
		printf(" is %s\n", enum_processorType2String(theProcType));
		printf("Listing pools for %s... ",myProcessors[i].c_str());
		myAnswer.clear();
		tcmd = string("listpools ") + myProcessors[i];
		if(g_operator_shdwn) return false;
		if(send_cmd(tcmd.c_str())<0) return false;
		this->recv_answer(myAnswer);
		myAnswer.pop_back();
		for(j=0;j<(int)myAnswer.size();j++)
		{
#ifdef _DEBUG
			printf("%s\n",myAnswer[j].c_str());
#endif
		}
		g_logger.logPools(myAnswer,theProcType,(char*)myProcessors[i].c_str());
		printf("has %d pools\n",myAnswer.size());
		printf("Done %0.0f%%\n",(double)((double)i/(double)myProcessors.size())*100.0);
	}
	printf("Done 100%%\n");
	g_logger.openMemLogFiles();
	
	this->PeriodicTimer((unsigned int)(m_logInterval*1000));
	printf("\n");
	return true;
}

void CTelOrbMemLogger::SetLogInterval(int ival)
{
	m_logInterval = ival;
}

void CTelOrbMemLogger::HandlePeriodicTimeout()
{
	vector<string> myAnswer;
	int vlen = m_processorGetInfoCmd.size(); 
	int i,j, p;
	int dbn, mem;
	char* pval;
	for(i=0;i<vlen;i++)
	{
		if(g_operator_shdwn) return;
		if(send_cmd(m_processorGetInfoCmd[i].c_str())<0) return;
		recv_answer(myAnswer);
		myAnswer.pop_back();
		dbn = mem = -1;
		for(j=0;j<(int)myAnswer.size();j++)
		{
/*
Memory Usage: 59
Memory Alarm level: 70
Load Regulation level: 75
DBN Memory share level: 80
DBN Memory Usage: 0
DBN Memory Alarm level: 85
*/
			p = myAnswer[j].find("DBN Memory Usage:");
			if(p!=-1)
			{

				pval = (char*)myAnswer[j].c_str() + 17;
			   dbn = atoi(pval);
			   break;
			}
			else
			{
				p = myAnswer[j].find("Memory Usage:");
				if(p!=-1)
				{
					pval = (char*)myAnswer[j].c_str() + 13;
				   mem = atoi(pval);
				}
			}
		}
		m_readings++;
		g_logger.logMemory(&m_procList[i],m_readings,mem,dbn);

	}
}

void CTelOrbMemLogger::HandleTimeout()
{
	fprintf(stderr,"\nError: CTelOrbMemLogger::HandleTimeout should never be called\n\n");
	exit(1);
}


