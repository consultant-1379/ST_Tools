// Logger.cpp
//==============================================================================
//
//  COPYRIGHT Ericsson Espa� S.A. 2007
//  All rights reserved.
//
//  The Copyright to the computer program(s) herein
//  is the property of Ericsson Espa� S.A.
//  The program(s) may be used and/or copied only
//  with the written permission from Ericsson Espa� S.A.,
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
//! \file Logger.cpp
//! \brief Implements the class CLogger
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

#include <string.h>
#include <errno.h>
#include <stdlib.h>
#ifdef _WIN32
#ifdef _DEBUG
#endif
#endif
#include "Logger.h"
#include "enums.h"


//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

CLogger::CLogger()
: m_allSummary(0)
, m_memSummary(0)
, m_loadSummary(0)
, m_poolFile(0)
, m_dicosBinLoadTraffic(0)
, m_dicosBinLoadSystem(0)
, m_dicosBinLoadOAM(0)
, m_linuxMemReadings(0)
, m_loadersMemReadings(0)
, m_dicosMemReadings(0)
, m_linuxLoadReadings(0)
, m_loadersLoadReadings(0)
, m_dicosLoadReadings(0)
, m_buildOTALNr(5)
, m_nrOfDicos(0)
, m_nrOfExcludedDicos(0)
, m_cur_dicos_sys_load(0.0)
, m_cur_dicos_traffic_load(0.0)
, m_cur_dicos_ota_load(0.0)
, m_cur_dicos_oam_load(0.0)
, m_log_binary(false)
, m_logLoadReadings(true)
, m_logMemReadings(true)


		{
	m_otl_vals.resize(m_buildOTALNr);

	m_saveGraphData = false;
	m_graphDataFile = "loadGraphData.log";
	m_graphScanSize = 0;
	m_accload_system = 0;
	m_accload_traffic= 0;
	m_accload_oam= 0;
	m_accTimes= 0;
    gettimeofday(&m_timeOffset, NULL);
	if (!m_graphDataFile.empty()){

		m_outFile.open(m_graphDataFile.c_str());
		if (!m_outFile) {
			cout << "ERROR:Failed to open file:" << m_graphDataFile.c_str() << endl;
		}
		m_saveGraphData= true;
		m_outFile <<"0\t0\t0\t0\t0"<< std::endl;
	}
}

CLogger::~CLogger()
{
	if(m_allSummary!=0)
		fclose(m_allSummary);
	if(m_memSummary!=0)
		fclose(m_memSummary);
	if(m_loadSummary!=0)
		fclose(m_loadSummary);
	if(m_poolFile!=0)
		fclose(m_poolFile);
	if(m_dicosBinLoadTraffic!=0)
		fclose(m_dicosBinLoadTraffic);
	if(m_dicosBinLoadSystem!=0)
		fclose(m_dicosBinLoadSystem);
	if(m_dicosBinLoadOAM!=0)
		fclose(m_dicosBinLoadOAM);

	int i;
	int len = m_proc_list.size();
	for(i=0;i<len;i++)
	{ //for(i=0;i<len;i++)
		if(m_proc_list[i].lfptr!=0)
			fclose(m_proc_list[i].lfptr);
		if(m_proc_list[i].mfptr!=0)
			fclose(m_proc_list[i].mfptr);
	} //for(i=0;i<len;i++)

	m_outFile.close();
}

bool CLogger::setSummaryDir(pchar path)
{
	if(path == NULL)
		return false;
	m_summaryDir = path;

	int len = m_summaryDir.length() - 1;
#ifdef _WIN32
	if(m_summaryDir.c_str()[len]!='\\')
		m_summaryDir += "\\";
#else
	if(m_summaryDir.c_str()[len]!='/')
		m_summaryDir += "/";
#endif

	return fun.CreateDir(m_summaryDir.c_str());
}

bool CLogger::setLoadDir(pchar path)
{
	if(path == NULL)
		return false;
	m_loadDir = path;

	int len = m_loadDir.length() - 1;
#ifdef _WIN32
	if(m_loadDir.c_str()[len]!='\\')
		m_loadDir += "\\";
#else
	if(m_loadDir.c_str()[len]!='/')
		m_loadDir += "/";
#endif

	return fun.CreateDir(m_loadDir.c_str());
}

bool CLogger::setMemDir(pchar path)
{
	if(path == NULL)
		return false;
	m_memDir = path;

	int len = m_memDir.length() - 1;
#ifdef _WIN32
	if(m_memDir.c_str()[len]!='\\')
		m_memDir += "\\";
#else
	if(m_memDir.c_str()[len]!='/')
		m_memDir += "/";
#endif

	return fun.CreateDir(m_memDir.c_str());
}

bool CLogger::setAllSummaryName(pchar fName)
{
	if(fName==NULL)
		return false;
	m_allSummaryName = m_summaryDir + fName;
	if((m_allSummary=fopen(m_allSummaryName.c_str(),"w"))==NULL)
	{
		printf("Error: Failed to oprn %s for writing\n",m_allSummaryName.c_str());
		printf("Error: %s\n",strerror(errno));
		return false;
	}
	return true;
}

bool CLogger::setMemSummaryName(pchar fName)
{
	if(fName==NULL)
		return false;
	m_memSummaryName  = m_summaryDir + fName;
	if((m_memSummary=fopen(m_memSummaryName.c_str(),"w"))==NULL)
	{
		printf("Error: Failed to oprn %s for writing\n",m_memSummaryName.c_str());
		printf("Error: %s\n",strerror(errno));
		return false;
	}
	return true;
}

void CLogger::setBuildAverOver(uint theNumber)
{
	m_buildOTALNr = theNumber;
	m_otl_vals.resize(theNumber);
}

#ifdef _IOMEM_LOGGING
bool CLogger::setIoMemSummaryName(pchar fName)
{
	if(fName==NULL)
		return false;
	sprintf(memIoSummaryName,"%s%s",summaryDir,fName);
	if((memIoSummary=fopen(memIoSummaryName,"w"))==NULL)
	{
		printf("Error: Failed to oprn %s for writing\n",memIoSummaryName);
		printf("Error: %s\n",strerror(errno));
		return false;
	}
	return true;
}

bool CLogger::setIoLoadSummaryName(pchar fName)
{
	if(fName==NULL)
		return false;
	sprintf(loadIoSummaryName,"%s%s",summaryDir,fName);
	if((loadIoSummary=fopen(loadIoSummaryName,"w"))==NULL)
	{
		printf("Error: Failed to oprn %s for writing\n",loadIoSummaryName);
		printf("Error: %s\n",strerror(errno));
		return false;
	}
	return true;
}
#endif
bool CLogger::setLoadSummaryName(pchar fName)
{
	if(fName==NULL)
		return false;
	m_loadSummaryName = m_summaryDir + fName;
	if((m_loadSummary=fopen(m_loadSummaryName.c_str(),"w"))==NULL)
	{
		printf("Error: Failed to oprn %s for writing\n",m_loadSummaryName.c_str());
		printf("Error: %s\n",strerror(errno));
		return false;
	}
	return true;
}


void CLogger::logMemory(ProcInstance* theProc, uint reading, uint mem, uint dbn)
{
	int pos = findProcessor(theProc->name);

	if(m_logMemReadings)
		if(m_proc_list[pos].mfptr!=0)
		{
			time_t t = time(NULL);
			struct tm *nu = localtime(&t);
			char ttime[10];
			strftime(ttime,10,"%H:%M:%S",nu);
			fprintf(m_proc_list[pos].mfptr,"%-11s | %-8u | %-u\n",ttime,mem,dbn);
		}

	if(m_proc_list[pos].maver.vals[0]<(double)mem)
		m_proc_list[pos].maver.vals[0] = (double)mem;
	if(m_proc_list[pos].maver.vals[1]>(double)mem)
		m_proc_list[pos].maver.vals[1] = (double)mem;

	if(m_proc_list[pos].maver.vals[3]<(double)dbn)
		m_proc_list[pos].maver.vals[3] = (double)dbn;
	if(m_proc_list[pos].maver.vals[4]>(double)dbn)
		m_proc_list[pos].maver.vals[4] = (double)dbn;

	m_proc_list[pos].maver.vals[2] += (double)mem;
	m_proc_list[pos].maver.vals[5] += (double)dbn;


   switch(m_proc_list[pos].ptype)
   {
      case linuxProcessorE:
         m_linuxMemReadings++;
         break;
      case loaderProcessorE:
         m_loadersMemReadings++;
         break;
      case dicosProcessorE: //fallthrough
      case excludedDicosProcessorE:
         m_dicosMemReadings++;
         break;
   }




}


bool CLogger::writeMemSummary()
{

	if(m_memSummary==0)
		return false;
	int i;
	bool toret = false;
	char separator = '-';
	char tmp[500];
	int len;
	double mem_average = 0.0;
	double dbn_average = 0.0;
	double excl_mem_average = 0.0;
	double excl_dbn_average = 0.0;
	int vlen;
	vector<ProcInstance> theProcs;
	if(m_loadersMemReadings>0)
	{ //if(m_loadersMemReadings>0)
		vlen = getProcessors(theProcs, loaderProcessorE);
		if(vlen>0)
		{ //if(vlen>0)

			fprintf(m_memSummary,"Memory usage summary for loader processors\n");
			fprintf(m_memSummary,"------------------------------------------\n\n");
			if(m_allSummary!=0)
			{
				fprintf(m_allSummary,"Memory usage summary for loader processors\n");
				fprintf(m_allSummary,"------------------------------------------\n\n");
			}
			for(i=0;i<vlen;i++)
			{ //for(i=0;i<vlen;i++)
				sprintf(tmp,"Loader processor %s:",theProcs[i].name.c_str());
				fprintf(m_memSummary,"%s\n",tmp);
				if(m_allSummary!=0)
					fprintf(m_allSummary,"%s\n",tmp);
				len = strlen(tmp);
				memset(tmp,separator,len);
				tmp[len-1] = '\0';
				printf("m_loadersMemReadings: %u \n", m_loadersMemReadings);
                                printf("theProcs[i].maver.vals[2]: %f \n", theProcs[i].maver.vals[2]);
                                fprintf(m_memSummary,"%s\n",tmp);
				fprintf(m_memSummary,"Max memory usage         : %6.3f %%\n",theProcs[i].maver.vals[0]);
				fprintf(m_memSummary,"Min memory usage         : %6.3f %%\n",theProcs[i].maver.vals[1]);
				fprintf(m_memSummary,"Average memory usage     : %6.3f %%\n",theProcs[i].maver.vals[2] / double(m_loadersMemReadings/vlen));
				fprintf(m_memSummary,"Max DBN memory usage     : %6.3f %%\n",theProcs[i].maver.vals[3]);
				fprintf(m_memSummary,"Min DBN memory usage     : %6.3f %%\n",theProcs[i].maver.vals[4]);
				fprintf(m_memSummary,"Average DBN memory usage : %6.3f %%\n",theProcs[i].maver.vals[5] / double(m_loadersMemReadings/vlen));
				fprintf(m_memSummary,"%s\n\n",tmp);
				if(m_allSummary!=0)
				{

					fprintf(m_allSummary,"%s\n",tmp);
					fprintf(m_allSummary,"Max memory usage         : %6.3f %%\n",theProcs[i].maver.vals[0]);
					fprintf(m_allSummary,"Min memory usage         : %6.3f %%\n",theProcs[i].maver.vals[1]);
					fprintf(m_allSummary,"Average memory usage     : %6.3f %%\n",theProcs[i].maver.vals[2] / double(m_loadersMemReadings/vlen));
					fprintf(m_allSummary,"Max DBN memory usage     : %6.3f %%\n",theProcs[i].maver.vals[3]);
					fprintf(m_allSummary,"Min DBN memory usage     : %6.3f %%\n",theProcs[i].maver.vals[4]);
					fprintf(m_allSummary,"Average DBN memory usage : %6.3f %%\n",theProcs[i].maver.vals[5] / double(m_loadersMemReadings/vlen));
					fprintf(m_allSummary,"%s\n\n",tmp);
				}
				mem_average += theProcs[i].maver.vals[2] / double(m_loadersMemReadings/vlen);
				dbn_average += theProcs[i].maver.vals[5] / double(m_loadersMemReadings/vlen);
			} //for(i=0;i<vlen;i++)
			fprintf(m_memSummary,"Average memory usage for loader processors\n");
			fprintf(m_memSummary,"==========================================\n");
			fprintf(m_memSummary,"Average memory usage     : %6.3f %%\n",(mem_average / (double)vlen));
			fprintf(m_memSummary,"Average DBN memory usage : %6.3f %%\n",(dbn_average / (double)vlen));
			fprintf(m_memSummary,"==========================================\n\n");
			if(m_allSummary!=0)
			{
				toret = true;
				fprintf(m_allSummary,"Average memory usage for loader processors\n");
				fprintf(m_allSummary,"==========================================\n");
				fprintf(m_allSummary,"Average memory usage     : %6.3f %%\n",(mem_average / (double)vlen));
				fprintf(m_allSummary,"Average DBN memory usage : %6.3f %%\n",(dbn_average / (double)vlen));
				fprintf(m_allSummary,"==========================================\n\n");
			}
		} //if(vlen>0)
	} //if(m_loadersMemReadings>0)


	if(m_linuxMemReadings>0)
	{ //if(m_linuxMemReadings>0)
		theProcs.clear();
		vlen = getProcessors(theProcs,linuxProcessorE);
		if(vlen>0)
		{ //if(vlen>0)

			fprintf(m_memSummary,"Memory usage summary for linux processors\n");
			fprintf(m_memSummary,"------------------------------------------\n\n");
			if(m_allSummary!=0)
			{
				fprintf(m_allSummary,"Memory usage summary for linux processors\n");
				fprintf(m_allSummary,"------------------------------------------\n\n");
			}
			mem_average = 0.0;
			dbn_average = 0.0;
			for(i=0;i<vlen;i++)
			{ //for(i=0;i<vlen;i++)
				sprintf(tmp,"Linux processor %s:",theProcs[i].name.c_str());
				fprintf(m_memSummary,"%s\n",tmp);
				if(m_allSummary!=0)
					fprintf(m_allSummary,"%s\n",tmp);
				len = strlen(tmp);
				memset(tmp,separator,len);
				tmp[len-1] = '\0';
				fprintf(m_memSummary,"%s\n",tmp);
				fprintf(m_memSummary,"Max memory usage         : %6.3f %%\n",theProcs[i].maver.vals[0]);
				fprintf(m_memSummary,"Min memory usage         : %6.3f %%\n",theProcs[i].maver.vals[1]);
				fprintf(m_memSummary,"Average memory usage     : %6.3f %%\n",theProcs[i].maver.vals[2] / double(m_linuxMemReadings/vlen));
				fprintf(m_memSummary,"Max DBN memory usage     : %6.3f %%\n",theProcs[i].maver.vals[3]);
				fprintf(m_memSummary,"Min DBN memory usage     : %6.3f %%\n",theProcs[i].maver.vals[4]);
				fprintf(m_memSummary,"Average DBN memory usage : %6.3f %%\n",theProcs[i].maver.vals[5] / double(m_linuxMemReadings/vlen));
				fprintf(m_memSummary,"%s\n\n",tmp);
				if(m_allSummary!=0)
				{

					fprintf(m_allSummary,"%s\n",tmp);
					fprintf(m_allSummary,"Max memory usage         : %6.3f %%\n",theProcs[i].maver.vals[0]);
					fprintf(m_allSummary,"Min memory usage         : %6.3f %%\n",theProcs[i].maver.vals[1]);
					fprintf(m_allSummary,"Average memory usage     : %6.3f %%\n",theProcs[i].maver.vals[2] / double(m_linuxMemReadings/vlen));
					fprintf(m_allSummary,"Max DBN memory usage     : %6.3f %%\n",theProcs[i].maver.vals[3]);
					fprintf(m_allSummary,"Min DBN memory usage     : %6.3f %%\n",theProcs[i].maver.vals[4]);
					fprintf(m_allSummary,"Average DBN memory usage : %6.3f %%\n",theProcs[i].maver.vals[5] / double(m_linuxMemReadings/vlen));
					fprintf(m_allSummary,"%s\n\n",tmp);
				}
				mem_average += theProcs[i].maver.vals[2] / double(m_linuxMemReadings/vlen);
				dbn_average += theProcs[i].maver.vals[5] / double(m_linuxMemReadings/vlen);
			} //for(i=0;i<vlen;i++)
			fprintf(m_memSummary,"Average memory usage for linux processors\n");
			fprintf(m_memSummary,"=========================================\n");
			fprintf(m_memSummary,"Average memory usage     : %6.3f %%\n",(mem_average / (double)vlen));
			fprintf(m_memSummary,"Average DBN memory usage : %6.3f %%\n",(dbn_average / (double)vlen));
			fprintf(m_memSummary,"=========================================\n\n");
			if(m_allSummary!=NULL)
			{
				toret = true;
				fprintf(m_allSummary,"Average memory usage for linux processors\n");
				fprintf(m_allSummary,"=========================================\n");
				fprintf(m_allSummary,"Average memory usage     : %6.3f %%\n",(mem_average / (double)vlen));
				fprintf(m_allSummary,"Average DBN memory usage : %6.3f %%\n",(dbn_average / (double)vlen));
				fprintf(m_allSummary,"=========================================\n\n");
			}
		} //if(vlen>0)
	} //if(m_linuxMemReadings>0)

	if(m_dicosMemReadings>0)
	{ //if(m_dicosMemReadings>0)
		theProcs.clear();
		getProcessors(theProcs,dicosProcessorE);
		vlen = getProcessors(theProcs,excludedDicosProcessorE);
		if(vlen>0)
		{ //if(vlen>0)

			fprintf(m_memSummary,"Memory usage summary for dicos processors\n");
			fprintf(m_memSummary,"------------------------------------------\n\n");
			if(m_allSummary!=0)
			{
				fprintf(m_allSummary,"Memory usage summary for dicos processors\n");
				fprintf(m_allSummary,"------------------------------------------\n\n");
			}
			mem_average = 0.0;
			dbn_average = 0.0;
			for(i=0;i<vlen;i++)
			{ //for(i=0;i<vlen;i++)
				sprintf(tmp,"Dicos processor %s:",theProcs[i].name.c_str());
				if(theProcs[i].ptype == excludedDicosProcessorE)
					strcat(tmp," (Excluded from traffic load average)");
				fprintf(m_memSummary,"%s\n",tmp);
				if(m_allSummary!=0)
					fprintf(m_allSummary,"%s\n",tmp);
				len = strlen(tmp);
				memset(tmp,separator,len);
				tmp[len-1] = '\0';
				fprintf(m_memSummary,"%s\n",tmp);
				fprintf(m_memSummary,"Max memory usage         : %6.3f %%\n",theProcs[i].maver.vals[0]);
				fprintf(m_memSummary,"Min memory usage         : %6.3f %%\n",theProcs[i].maver.vals[1]);
				fprintf(m_memSummary,"Average memory usage     : %6.3f %%\n",theProcs[i].maver.vals[2] / double(m_dicosMemReadings/m_nrOfDicos));
				fprintf(m_memSummary,"Max DBN memory usage     : %6.3f %%\n",theProcs[i].maver.vals[3]);
				fprintf(m_memSummary,"Min DBN memory usage     : %6.3f %%\n",theProcs[i].maver.vals[4]);
				fprintf(m_memSummary,"Average DBN memory usage : %6.3f %%\n",theProcs[i].maver.vals[5] / double(m_dicosMemReadings/m_nrOfDicos));
				fprintf(m_memSummary,"%s\n\n",tmp);
				if(m_allSummary!=0)
				{
					fprintf(m_allSummary,"%s\n",tmp);
					fprintf(m_allSummary,"Max memory usage         : %6.3f %%\n",theProcs[i].maver.vals[0]);
					fprintf(m_allSummary,"Min memory usage         : %6.3f %%\n",theProcs[i].maver.vals[1]);
					fprintf(m_allSummary,"Average memory usage     : %6.3f %%\n",theProcs[i].maver.vals[2] / double(m_dicosMemReadings/m_nrOfDicos));
					fprintf(m_allSummary,"Max DBN memory usage     : %6.3f %%\n",theProcs[i].maver.vals[3]);
					fprintf(m_allSummary,"Min DBN memory usage     : %6.3f %%\n",theProcs[i].maver.vals[4]);
					fprintf(m_allSummary,"Average DBN memory usage : %6.3f %%\n",theProcs[i].maver.vals[5] / double(m_dicosMemReadings/m_nrOfDicos));
					fprintf(m_allSummary,"%s\n\n",tmp);
				}
				mem_average += theProcs[i].maver.vals[2] / double(m_dicosMemReadings/m_nrOfDicos);
				dbn_average += theProcs[i].maver.vals[5] / double(m_dicosMemReadings/m_nrOfDicos);
				if(theProcs[i].ptype != excludedDicosProcessorE)
				{
					excl_mem_average += theProcs[i].maver.vals[2] / double(m_dicosMemReadings/m_nrOfDicos);
					excl_dbn_average += theProcs[i].maver.vals[5] / double(m_dicosMemReadings/m_nrOfDicos);
				}
			} //for(i=0;i<vlen;i++)
			fprintf(m_memSummary,"Average memory usage for dicos processors\n");
			fprintf(m_memSummary,"=========================================\n");
			fprintf(m_memSummary,"Average memory usage               : %6.3f %%\n",(mem_average / (double)m_nrOfDicos));
			fprintf(m_memSummary,"Average memory usage not excl      : %6.3f %%\n",(excl_mem_average / (double)(m_nrOfDicos-m_nrOfExcludedDicos)));
			fprintf(m_memSummary,"Average DBN memory usage           : %6.3f %%\n",(dbn_average / (double)m_nrOfDicos));
			fprintf(m_memSummary,"Average DBN memory usage not excl  : %6.3f %%\n",(excl_dbn_average / (double)(m_nrOfDicos-m_nrOfExcludedDicos)));
			fprintf(m_memSummary,"=========================================\n\n");
			if(m_allSummary!=0)
			{
				toret = true;
				fprintf(m_allSummary,"Average memory usage for dicos processors\n");
				fprintf(m_allSummary,"=========================================\n");
				fprintf(m_allSummary,"Average memory usage               : %6.3f %%\n",(mem_average / (double)m_nrOfDicos));
				fprintf(m_allSummary,"Average memory usage not excl      : %6.3f %%\n",(excl_mem_average / (double)(m_nrOfDicos-m_nrOfExcludedDicos)));
				fprintf(m_allSummary,"Average DBN memory usage           : %6.3f %%\n",(dbn_average / (double)m_nrOfDicos));
				fprintf(m_allSummary,"Average DBN memory usage not excl  : %6.3f %%\n",(excl_dbn_average / (double)(m_nrOfDicos-m_nrOfExcludedDicos)));
				fprintf(m_allSummary,"=========================================\n\n");
			}
		} //if(vlen>0)
	} //if(m_dicosMemReadings>0)
	return toret;
}



bool CLogger::openMemLogFiles()
{
	initAverValues();
	if(!m_logMemReadings) return true;
	int vlen = m_proc_list.size();
	FILE *f;
	string tmp;

	for(int i=0;i<vlen;i++)
	{
		tmp = m_memDir + m_proc_list[i].name + ".mem.txt";
		if((f=fopen(tmp.c_str(),"w"))==0)
		{
			fprintf(stderr,"\nError: Failed to create file %s\n",tmp.c_str());
			fprintf(stderr,"Error: %s\n\n",strerror(errno));
			return false;
		}
		m_proc_list[i].mfptr = f;
		time_t t = time(NULL);
		fprintf(f,"Log started %s\n",ctime(&t));

		switch(m_proc_list[i].ptype)
		{
		case linuxProcessorE:
			{
				fprintf(f,"Memory log for linux processor %s\n\n",m_proc_list[i].name.c_str());
			}break;
		case loaderProcessorE:
			{
				fprintf(f,"Memory log for loader processor %s\n\n",m_proc_list[i].name.c_str());
			}break;
		case dicosProcessorE:
			{
				fprintf(f,"Memory log for dicos processor %s\n\n",m_proc_list[i].name.c_str());
			}break;
		case excludedDicosProcessorE:
			{
				fprintf(f,"Memory log for excluded dicos processor %s\n\n",m_proc_list[i].name.c_str());
			}break;
		case unknownProcessorTypeE: break;
		}
		fprintf(f,"Table header:\n");
		fprintf(f,"-------------\n");
		fprintf(f,"Time: Time for reading\n");
		fprintf(f,"MEM : Memory usage in %%\n");
		fprintf(f,"DBN : Memory usage in %%\n\n");

		fprintf(f,"Time        | MEM (%%)  | DBN (%%)\n");
		fprintf(f,"----------------------------------\n");
	}
	return true;
}

bool CLogger::openLoadLogFiles()
{
	if(!m_logLoadReadings) return true;
	int vlen = m_proc_list.size();
	FILE *f;
	string tmp;
	for(int i=0;i<vlen;i++)
	{
		tmp = m_loadDir + m_proc_list[i].name + ".load.txt";
		if((f=fopen(tmp.c_str(),"w"))==0)
		{
			fprintf(stderr,"\nError: Failed to create file %s\n",tmp.c_str());
			fprintf(stderr,"Error: %s\n\n",strerror(errno));
			return false;
		}
		m_proc_list[i].lfptr = f;
		time_t t = time(NULL);
		fprintf(f,"Log started %s\n",ctime(&t));
		switch(m_proc_list[i].ptype)
		{
		case linuxProcessorE:
			{

				fprintf(f,"Load log for linux processor %s\n\n",m_proc_list[i].name.c_str());
			}break;
		case loaderProcessorE:
			{
				fprintf(f,"Load log for loader processor %s\n\n",m_proc_list[i].name.c_str());
			}break;
		case dicosProcessorE:
			{
				fprintf(f,"Load log for dicos processor %s\n\n",m_proc_list[i].name.c_str());
			}break;
		case excludedDicosProcessorE:
			{
				fprintf(f,"Load log for dicos processor %s (Excluded from traffic load average)\n\n",m_proc_list[i].name.c_str());
			}break;
		case unknownProcessorTypeE: break;
		}
		fprintf(f,"Table header:\n");
		fprintf(f,"-------------\n");
		fprintf(f,"Time   : Time for reading\n");
		fprintf(f,"System : CPU usage in %%\n");
		fprintf(f,"Traffic: CPU usage in %%\n");
		fprintf(f,"O&M    : CPU usage in %%\n\n");

		fprintf(f,"Time        | System (%%)| Traffic (%%)| O&M (%%)\n");
		fprintf(f,"----------------------------------------------\n");
	}
	if(m_log_binary)
	{
		if(m_dicosBinLoadTraffic==0)
		{
			tmp = m_loadDir + "traffic_load.bin";
			if((m_dicosBinLoadTraffic=fopen(tmp.c_str(),"w"))==0)
			{
				printf("Error: Failed to open file %s for writing\n",tmp.c_str());
				printf("Error: %s\n",strerror(errno));
				return false;
			}
		}
		if(m_dicosBinLoadSystem==0)
		{
			tmp = m_loadDir + "system_load.bin";
			if((m_dicosBinLoadSystem=fopen(tmp.c_str(),"w"))==0)
			{
				printf("Error: Failed to open file %s for writing\n",tmp.c_str());
				printf("Error: %s\n",strerror(errno));
				return false;
			}
		}
		if(m_dicosBinLoadOAM==0)
		{
			tmp = m_loadDir + "oam_load.bin";
			if((m_dicosBinLoadOAM=fopen(tmp.c_str(),"w"))==0)
			{
				printf("Error: Failed to open file %s for writing\n",tmp.c_str());
				printf("Error: %s\n",strerror(errno));
				return false;
			}
		}
	}
	return true;
}


void CLogger::logLoad(pchar ldata, uint reading, uint ival)
{
	pchar koll = strstr(ldata,"LoadData:");
	if(koll == NULL)
		return;
	koll += 9;
	int i;
	int nrofp = atoi(koll);
	if(nrofp == 0)
		return;
	koll += 23;
	int pos = 0;
	char tmp[MAX_PROCESSOR_NAME_LEN];
	uint tv, sv, oam;

	uint tmp_dicos_sys_load = 0;
	uint tmp_dicos_traffic_load = 0;
	uint tmp_dicos_oam_load = 0;
 	time_t t = time(NULL);
	struct tm *nu = localtime(&t);
	char ttime[10];
	strftime(ttime,10,"%H:%M:%S",nu);

	for(i=0;i<nrofp;i++)
	{ //for(int i=0;i<nrofp;i++)
		pchar next = strstr(koll,":");
		if(next == NULL)
			return;
		strncpy(tmp,koll,(next-koll));
		tmp[(next-koll)] = '\0';

		koll = next + 1;
		koll = strchr(koll,':');
		if(koll == NULL)
			return;
		koll++;
		sv = atoi(koll);

		koll = strchr(koll,' ');
		if(koll == NULL)
			return;
		koll++;
		tv = atoi(koll);


		koll = strchr(koll,' ');
		if(koll == NULL)
			return;
		koll++;
		oam = atoi(koll);


		if((pos=findProcessor(tmp))!=-1)
		{ //if(findProcessor(tmp,pos,type))
			if(m_logLoadReadings)
				if(m_proc_list[pos].lfptr!=0)
				{
					fprintf(m_proc_list[pos].lfptr,"%-11s | %-10u | %-11u | %-u\n",ttime,sv,tv,oam);
				}

			if(m_proc_list[pos].laver.vals[0]<(double)sv)
				m_proc_list[pos].laver.vals[0] = (double)sv;
			if(m_proc_list[pos].laver.vals[1]>(double)sv)
				m_proc_list[pos].laver.vals[1] = (double)sv;

			if(m_proc_list[pos].laver.vals[3]<(double)tv)
				m_proc_list[pos].laver.vals[3] = (double)tv;
			if(m_proc_list[pos].laver.vals[4]>(double)tv)
				m_proc_list[pos].laver.vals[4] = (double)tv;

			if(m_proc_list[pos].laver.vals[6]<(double)oam)
				m_proc_list[pos].laver.vals[6] = (double)oam;
			if(m_proc_list[pos].laver.vals[7]>(double)oam)
				m_proc_list[pos].laver.vals[7] = (double)oam;

			m_proc_list[pos].laver.vals[2] += (double)sv;
			m_proc_list[pos].laver.vals[5] += (double)tv;
			m_proc_list[pos].laver.vals[8] += (double)oam;
			switch(m_proc_list[pos].ptype)
			{ //switch(type)
			case linuxProcessorE:
				{ //case linuxProcessor:
#ifdef _WIN32
#ifdef _DEBUG
//TRACE(_T("Linux %s:%d: t: %d, s: %d, o: %d\n"),tmp,pos,tv,sv,oam);
#endif
#endif					   //m_proc_list[pos].lfptr
					m_linuxLoadReadings = reading;
				} //case linuxProcessor:
				break;
			case loaderProcessorE:
				{ //case loaderProcessor:
#ifdef _WIN32
#ifdef _DEBUG
//TRACE(_T("Loader %s:%d: t: %d, s: %d, o: %d\n"),tmp,pos,tv,sv,oam);
#endif
#endif
					m_loadersLoadReadings = reading;
				} //case loaderProcessor:
				break;
			case dicosProcessorE:
				{ //case dicosProcessor:
#ifdef _WIN32
#ifdef _DEBUG
//TRACE(_T("Dicos %s:%d: t: %d, s: %d, o: %d\n"),tmp,pos,tv,sv,oam);
#endif
#endif
					if(m_logLoadReadings)
					{
						if(m_log_binary)
						{
							if(m_dicosBinLoadTraffic!=0)
							{
								fwrite(&tv,1,sizeof(uint),m_dicosBinLoadTraffic);
							}
							if(m_dicosBinLoadSystem!=0)
							{
								fwrite(&sv,1,sizeof(uint),m_dicosBinLoadSystem);
							}
							if(m_dicosBinLoadOAM!=0)
							{
								fwrite(&oam,1,sizeof(uint),m_dicosBinLoadOAM);
							}
						}
					}
					m_dicosLoadReadings = reading;
					tmp_dicos_sys_load += sv;
					tmp_dicos_traffic_load += tv;
					tmp_dicos_oam_load += oam;

				} //case dicosProcessor:
				break;
			case excludedDicosProcessorE:
				{ //case ExcludedDicosProcessor:
#ifdef _WIN32
#ifdef _DEBUG
//TRACE(_T("Excluded %s:%d: t: %d, s: %d, o: %d\n"),tmp,pos,tv,sv,oam);
#endif
#endif
					m_dicosLoadReadings = reading;
				} //case ExcludedDicosProcessor:
				break;
			case unknownProcessorTypeE: break;
			}; //switch(type)
			if((koll=strchr(koll,'\n'))==0)
				return;
			koll++;
		} //if(findProcessor(tmp))
		else
		{
			fprintf(stderr,"\nError: Could not find processor %s in the list\n",tmp);

		}
	} //for(int i=0;i<nrofp;i++)
	if(m_nrOfDicos > 0)
	{
		m_cur_dicos_sys_load = (double)((double)tmp_dicos_sys_load/(double)m_nrOfDicos);
		m_cur_dicos_traffic_load = (double)((double)tmp_dicos_traffic_load/(double)(m_nrOfDicos-m_nrOfExcludedDicos));
		m_cur_dicos_oam_load = (double)((double)tmp_dicos_oam_load/(double)m_nrOfDicos);
		double ota = 0.0;
		m_otl_vals.insert(m_otl_vals.begin(),m_cur_dicos_traffic_load);
		m_otl_vals.resize(m_buildOTALNr);
		for(i=0;i<(int)m_buildOTALNr;i++)
		{
			ota += m_otl_vals[i];
		}
		m_cur_dicos_ota_load = ota / (double)m_buildOTALNr;


	    if (!m_saveGraphData)	return;
	    if (m_graphScanSize == 0)	return;

	    m_accload_system +=  (unsigned int) m_cur_dicos_sys_load;
	    m_accload_traffic +=  (unsigned int) m_cur_dicos_traffic_load ;
	    m_accload_oam +=  (unsigned int) m_cur_dicos_oam_load ;
	    m_accTimes++;
		struct timeval  currentTime;
		gettimeofday(&currentTime, NULL);
		unsigned int seconds = currentTime.tv_sec - m_timeOffset.tv_sec;

	    if (m_accTimes == m_graphScanSize && m_accTimes){
	    	m_outFile <<seconds;
	    	m_outFile <<"\t"<< m_accload_system / m_accTimes;
	    	m_outFile <<"\t"<< m_accload_traffic / m_accTimes;
	    	m_outFile <<"\t"<< m_accload_oam/ m_accTimes;
	    	m_outFile <<"\t"<<((m_accload_system + m_accload_traffic + m_accload_oam)/ m_accTimes) << " ";
	    	m_outFile << std::endl;
	       	m_accTimes = 0;
	       	m_accload_system = 0;
	       	m_accload_traffic = 0;
	       	m_accload_oam = 0;
	    }

	}

}

int CLogger::findProcessor(string name)
{
	int i;
	int vlen = m_proc_list.size();
	for(i=0;i<vlen;i++)
		if(m_proc_list[i].name==name)
		{
			return i;
		}
	return -1;
}


int CLogger::getProcessors(vector<ProcInstance>& theProcs, ProcessorTypeE theType)
{
	int vlen = m_proc_list.size();
	int tlen = theProcs.size();
	for(int i=0;i<vlen;i++)
	{
		if(m_proc_list[i].ptype==theType)
		{
			theProcs.resize(tlen+1);
			theProcs[tlen].name = m_proc_list[i].name.c_str();
			theProcs[tlen].ptype = m_proc_list[i].ptype;
         theProcs[tlen].laver = m_proc_list[i].laver;
         theProcs[tlen].maver = m_proc_list[i].maver;
         tlen++;
		}
	}
	return tlen;
}

bool CLogger::writeLoadSummary()
{
	if(m_loadSummary==0)
		return false;
	int i;
	bool toret = false;
	char separator = '-';
	char tmp[500];
	int len;
	int pos;
	int vlen;
	double sv_average = 0.0;
	double tv_average = 0.0;
	double tv_aver_excluded = 0.0;
	double oam_average = 0.0;
	vector<ProcInstance> theProcs;
	if(m_loadersLoadReadings>0)
	{ //if(m_loadersLoadReadings>0)
		theProcs.clear();
		vlen = getProcessors(theProcs,loaderProcessorE);
		if(vlen>0)
		{ //if(vlen>0)

			fprintf(m_loadSummary,"Load summary for loader processors\n");
			fprintf(m_loadSummary,"----------------------------------\n\n");
			if(m_allSummary!=0)
			{
				toret = true;
				fprintf(m_allSummary,"Load summary for loader processors\n");
				fprintf(m_allSummary,"----------------------------------\n\n");
			}
			for(i=0;i<vlen;i++)
			{
				pos = findProcessor(theProcs[i].name);
				sprintf(tmp,"Loader processor %s:",m_proc_list[pos].name.c_str());
				fprintf(m_loadSummary,"%s\n",tmp);
				if(m_allSummary!=0)
					fprintf(m_allSummary,"%s\n",tmp);
				len = strlen(tmp);
				memset(tmp,separator,len);
				tmp[len-1] = '\0';
				fprintf(m_loadSummary,"%s\n",tmp);
				fprintf(m_loadSummary,"Max system load      : %6.3f %%\n",m_proc_list[pos].laver.vals[0]);
				fprintf(m_loadSummary,"Min system load      : %6.3f %%\n",m_proc_list[pos].laver.vals[1]);
				fprintf(m_loadSummary,"Average system load  : %6.3f %%\n",m_proc_list[pos].laver.vals[2] / double(m_loadersLoadReadings));
				fprintf(m_loadSummary,"Max traffic load     : %6.3f %%\n",m_proc_list[pos].laver.vals[3]);
				fprintf(m_loadSummary,"Min traffic load     : %6.3f %%\n",m_proc_list[pos].laver.vals[4]);
				fprintf(m_loadSummary,"Average traffic load : %6.3f %%\n",m_proc_list[pos].laver.vals[5] / double(m_loadersLoadReadings));
				fprintf(m_loadSummary,"Max O&M load         : %6.3f %%\n",m_proc_list[pos].laver.vals[6]);
				fprintf(m_loadSummary,"Min O&M load         : %6.3f %%\n",m_proc_list[pos].laver.vals[7]);
				fprintf(m_loadSummary,"Average O&M load     : %6.3f %%\n",m_proc_list[pos].laver.vals[8] / double(m_loadersLoadReadings));
				fprintf(m_loadSummary,"Total average load   : %6.3f %%\n",(double)((double)m_proc_list[pos].laver.vals[2]
																		+ (double)m_proc_list[pos].laver.vals[5]
																		+ (double)m_proc_list[pos].laver.vals[8]) / double(m_loadersLoadReadings));
				fprintf(m_loadSummary,"%s\n\n",tmp);
				if(m_allSummary!=0)
				{
					toret = true;
					fprintf(m_allSummary,"%s\n",tmp);
					fprintf(m_allSummary,"Max system load      : %6.3f %%\n",m_proc_list[pos].laver.vals[0]);
					fprintf(m_allSummary,"Min system load      : %6.3f %%\n",m_proc_list[pos].laver.vals[1]);
					fprintf(m_allSummary,"Average system load  : %6.3f %%\n",m_proc_list[pos].laver.vals[2] / double(m_loadersLoadReadings));
					fprintf(m_allSummary,"Max traffic load     : %6.3f %%\n",m_proc_list[pos].laver.vals[3]);
					fprintf(m_allSummary,"Min traffic load     : %6.3f %%\n",m_proc_list[pos].laver.vals[4]);
					fprintf(m_allSummary,"Average traffic load : %6.3f %%\n",m_proc_list[pos].laver.vals[5] / double(m_loadersLoadReadings));
					fprintf(m_allSummary,"Max O&M load         : %6.3f %%\n",m_proc_list[pos].laver.vals[6]);
					fprintf(m_allSummary,"Min O&M load         : %6.3f %%\n",m_proc_list[pos].laver.vals[7]);
					fprintf(m_allSummary,"Average O&M load     : %6.3f %%\n",m_proc_list[pos].laver.vals[8] / double(m_loadersLoadReadings));
					fprintf(m_allSummary,"Total average load   : %6.3f %%\n",(double)((double)m_proc_list[pos].laver.vals[2]
																			+ (double)m_proc_list[pos].laver.vals[5]
																			+ (double)m_proc_list[pos].laver.vals[8]) / double(m_loadersLoadReadings));
					fprintf(m_allSummary,"%s\n\n",tmp);
				}
				sv_average += m_proc_list[pos].laver.vals[2] / double(m_loadersLoadReadings);
				tv_average += m_proc_list[pos].laver.vals[5] / double(m_loadersLoadReadings);
				oam_average += m_proc_list[pos].laver.vals[8] / double(m_loadersLoadReadings);
			}
			fprintf(m_loadSummary,"Average load for loader processors\n");
			fprintf(m_loadSummary,"==================================\n");
			fprintf(m_loadSummary,"Average system load  : %6.3f %%\n",(sv_average / (double)vlen));
			fprintf(m_loadSummary,"Average traffic load : %6.3f %%\n",(tv_average / (double)vlen));
			fprintf(m_loadSummary,"Average O&M load     : %6.3f %%\n",(oam_average / (double)vlen));
			fprintf(m_loadSummary,"Total average load   : %6.3f %%\n",((sv_average + tv_average + oam_average) / (double)vlen));
			fprintf(m_loadSummary,"==================================\n\n");
			if(m_allSummary!=0)
			{
				fprintf(m_allSummary,"Average load for loader processors\n");
				fprintf(m_allSummary,"==================================\n");
				fprintf(m_allSummary,"Average system load  : %6.3f %%\n",(sv_average / (double)vlen));
				fprintf(m_allSummary,"Average traffic load : %6.3f %%\n",(tv_average / (double)vlen));
				fprintf(m_allSummary,"Average O&M load     : %6.3f %%\n",(oam_average / (double)vlen));
				fprintf(m_allSummary,"Total average load   : %6.3f %%\n",((sv_average + tv_average + oam_average) / (double)vlen));
				fprintf(m_allSummary,"==================================\n\n");
			}
		} //if(vlen>0)
	} //if(m_loadersLoadReadings>0)

	if(m_linuxLoadReadings>0)
	{ //if(m_linuxLoadReadings>0)		   �
		theProcs.clear();
		vlen = getProcessors(theProcs,linuxProcessorE);
		if(vlen>0)
		{ //if(vlen>0)

			sv_average = 0.0;
			tv_average = 0.0;
			oam_average = 0.0;
			fprintf(m_loadSummary,"Load summary for linux processors\n");
			fprintf(m_loadSummary,"---------------------------------\n\n");
			if(m_allSummary!=0)
			{
				toret = true;
				fprintf(m_allSummary,"Load summary for linux processors\n");
				fprintf(m_allSummary,"---------------------------------\n\n");
			}
			for(i=0;i<vlen;i++)
			{
				pos = findProcessor(theProcs[i].name);
				sprintf(tmp,"Linux processor %s:",m_proc_list[pos].name.c_str());
				fprintf(m_loadSummary,"%s\n",tmp);
				if(m_allSummary!=0)
					fprintf(m_allSummary,"%s\n",tmp);
				len = strlen(tmp);
				memset(tmp,separator,len);
				tmp[len-1] = '\0';
				fprintf(m_loadSummary,"%s\n",tmp);
				fprintf(m_loadSummary,"Max system load      : %6.3f %%\n",m_proc_list[pos].laver.vals[0]);
				fprintf(m_loadSummary,"Min system load      : %6.3f %%\n",m_proc_list[pos].laver.vals[1]);
				fprintf(m_loadSummary,"Average system load  : %6.3f %%\n",m_proc_list[pos].laver.vals[2] / double(m_linuxLoadReadings));
				fprintf(m_loadSummary,"Max traffic load     : %6.3f %%\n",m_proc_list[pos].laver.vals[3]);
				fprintf(m_loadSummary,"Min traffic load     : %6.3f %%\n",m_proc_list[pos].laver.vals[4]);
				fprintf(m_loadSummary,"Average traffic load : %6.3f %%\n",m_proc_list[pos].laver.vals[5] / double(m_linuxLoadReadings));
				fprintf(m_loadSummary,"Max O&M load         : %6.3f %%\n",m_proc_list[pos].laver.vals[6]);
				fprintf(m_loadSummary,"Min O&M load         : %6.3f %%\n",m_proc_list[pos].laver.vals[7]);
				fprintf(m_loadSummary,"Average O&M load     : %6.3f %%\n",m_proc_list[pos].laver.vals[8] / double(m_linuxLoadReadings));
				fprintf(m_loadSummary,"Total average load   : %6.3f %%\n",(double)((double)m_proc_list[pos].laver.vals[2]
																		+ (double)m_proc_list[pos].laver.vals[5]
																		+ (double)m_proc_list[pos].laver.vals[8]) / double(m_linuxLoadReadings));
				fprintf(m_loadSummary,"%s\n\n",tmp);
				if(m_allSummary!=0)
				{
					fprintf(m_allSummary,"%s\n",tmp);
					fprintf(m_allSummary,"Max system load      : %6.3f %%\n",m_proc_list[pos].laver.vals[0]);
					fprintf(m_allSummary,"Min system load      : %6.3f %%\n",m_proc_list[pos].laver.vals[1]);
					fprintf(m_allSummary,"Average system load  : %6.3f %%\n",m_proc_list[pos].laver.vals[2] / double(m_linuxLoadReadings));
					fprintf(m_allSummary,"Max traffic load     : %6.3f %%\n",m_proc_list[pos].laver.vals[3]);
					fprintf(m_allSummary,"Min traffic load     : %6.3f %%\n",m_proc_list[pos].laver.vals[4]);
					fprintf(m_allSummary,"Average traffic load : %6.3f %%\n",m_proc_list[pos].laver.vals[5] / double(m_linuxLoadReadings));
					fprintf(m_allSummary,"Max O&M load         : %6.3f %%\n",m_proc_list[pos].laver.vals[6]);
					fprintf(m_allSummary,"Min O&M load         : %6.3f %%\n",m_proc_list[pos].laver.vals[7]);
					fprintf(m_allSummary,"Average O&M load     : %6.3f %%\n",m_proc_list[pos].laver.vals[8] / double(m_linuxLoadReadings));
					fprintf(m_allSummary,"Total average load   : %6.3f %%\n",(double)((double)m_proc_list[pos].laver.vals[2]
																			+ (double)m_proc_list[pos].laver.vals[5]
																			+ (double)m_proc_list[pos].laver.vals[8]) / double(m_linuxLoadReadings));
					fprintf(m_allSummary,"%s\n\n",tmp);
				}
				sv_average += m_proc_list[pos].laver.vals[2] / double(m_linuxLoadReadings);
				tv_average += m_proc_list[pos].laver.vals[5] / double(m_linuxLoadReadings);
				oam_average += m_proc_list[pos].laver.vals[8] / double(m_linuxLoadReadings);
			}
			fprintf(m_loadSummary,"Average load for linux processors\n");
			fprintf(m_loadSummary,"=================================\n");
			fprintf(m_loadSummary,"Average system load  : %6.3f %%\n",(sv_average / (double)vlen));
			fprintf(m_loadSummary,"Average traffic load : %6.3f %%\n",(tv_average / (double)vlen));
			fprintf(m_loadSummary,"Average O&M load     : %6.3f %%\n",(oam_average / (double)vlen));
			fprintf(m_loadSummary,"Total average load   : %6.3f %%\n",((sv_average + tv_average + oam_average) / (double)vlen));
			fprintf(m_loadSummary,"==================================\n\n");
			if(m_allSummary!=0)
			{
				toret = true;
				fprintf(m_allSummary,"Average load for linux processors\n");
				fprintf(m_allSummary,"=================================\n");
				fprintf(m_allSummary,"Average system load  : %6.3f %%\n",(sv_average / (double)vlen));
				fprintf(m_allSummary,"Average traffic load : %6.3f %%\n",(tv_average / (double)vlen));
				fprintf(m_allSummary,"Average O&M load     : %6.3f %%\n",(oam_average / (double)vlen));
				fprintf(m_allSummary,"Total average load   : %6.3f %%\n",((sv_average + tv_average + oam_average) / (double)vlen));
				fprintf(m_allSummary,"==================================\n\n");
			}
		} //if(vlen>0)
	} //if(m_linuxLoadReadings>0)

	if(m_dicosLoadReadings>0)
	{ //if(m_dicosLoadReadings>0)
		theProcs.clear();
		vlen = getProcessors(theProcs,dicosProcessorE);
		if(vlen>0)
		{ //if(vlen>0)

			sv_average = 0.0;
			tv_average = 0.0;
			tv_aver_excluded = 0.0;
			oam_average = 0.0;
			fprintf(m_loadSummary,"Load summary for dicos processors\n");
			fprintf(m_loadSummary,"---------------------------------\n\n");
			if(m_allSummary!=0)
			{
				fprintf(m_allSummary,"Load summary for dicos processors\n");
				fprintf(m_allSummary,"---------------------------------\n\n");
			}

			for(i=0;i<vlen;i++)
			{
				pos = findProcessor(theProcs[i].name);
				sprintf(tmp,"Dicos processor %s:",m_proc_list[pos].name.c_str());
				if(m_proc_list[pos].ptype==excludedDicosProcessorE)
					strcat(tmp," (Excluded from traffic load average)");
				fprintf(m_loadSummary,"%s\n",tmp);
				if(m_allSummary!=0)
					fprintf(m_allSummary,"%s\n",tmp);
				len = strlen(tmp);
				memset(tmp,separator,len);
				tmp[len-1] = '\0';
				fprintf(m_loadSummary,"%s\n",tmp);
				fprintf(m_loadSummary,"Max system load      : %6.3f\n",m_proc_list[pos].laver.vals[0]);
				fprintf(m_loadSummary,"Min system load      : %6.3f\n",m_proc_list[pos].laver.vals[1]);
				fprintf(m_loadSummary,"Average system load  : %6.3f\n",m_proc_list[pos].laver.vals[2] / double(m_dicosLoadReadings));
				fprintf(m_loadSummary,"Max traffic load     : %6.3f\n",m_proc_list[pos].laver.vals[3]);
				fprintf(m_loadSummary,"Min traffic load     : %6.3f\n",m_proc_list[pos].laver.vals[4]);
				fprintf(m_loadSummary,"Average traffic load : %6.3f\n",m_proc_list[pos].laver.vals[5] / double(m_dicosLoadReadings));
				fprintf(m_loadSummary,"Max O&M load         : %6.3f\n",m_proc_list[pos].laver.vals[6]);
				fprintf(m_loadSummary,"Min O&M load         : %6.3f\n",m_proc_list[pos].laver.vals[7]);
				fprintf(m_loadSummary,"Average O&M load     : %6.3f\n",m_proc_list[pos].laver.vals[8] / double(m_dicosLoadReadings));
				fprintf(m_loadSummary,"Total average load   : %6.3f\n",((double)(double)m_proc_list[pos].laver.vals[2]
																	+ (double)m_proc_list[pos].laver.vals[5]
																	+ (double)m_proc_list[pos].laver.vals[8]) / double(m_dicosLoadReadings));
				fprintf(m_loadSummary,"%s\n\n",tmp);
				if(m_allSummary!=0)
				{
					fprintf(m_allSummary,"%s\n",tmp);
					fprintf(m_allSummary,"Max system load      : %6.3f %%\n",m_proc_list[pos].laver.vals[0]);
					fprintf(m_allSummary,"Min system load      : %6.3f %%\n",m_proc_list[pos].laver.vals[1]);
					fprintf(m_allSummary,"Average system load  : %6.3f %%\n",m_proc_list[pos].laver.vals[2] / double(m_dicosLoadReadings));
					fprintf(m_allSummary,"Max traffic load     : %6.3f %%\n",m_proc_list[pos].laver.vals[3]);
					fprintf(m_allSummary,"Min traffic load     : %6.3f %%\n",m_proc_list[pos].laver.vals[4]);
					fprintf(m_allSummary,"Average traffic load : %6.3f %%\n",m_proc_list[pos].laver.vals[5] / double(m_dicosLoadReadings));
					fprintf(m_allSummary,"Max O&M load         : %6.3f %%\n",m_proc_list[pos].laver.vals[6]);
					fprintf(m_allSummary,"Min O&M load         : %6.3f %%\n",m_proc_list[pos].laver.vals[7]);
					fprintf(m_allSummary,"Average O&M load     : %6.3f %%\n",m_proc_list[pos].laver.vals[8] / double(m_dicosLoadReadings));
					fprintf(m_allSummary,"Total average load   : %6.3f %%\n",((double)(double)m_proc_list[pos].laver.vals[2]
																		+ (double)m_proc_list[pos].laver.vals[5]
																		+ (double)m_proc_list[pos].laver.vals[8]) / double(m_dicosLoadReadings));
					fprintf(m_allSummary,"%s\n\n",tmp);
				}
				sv_average += m_proc_list[pos].laver.vals[2] / double(m_dicosLoadReadings);
				oam_average += m_proc_list[pos].laver.vals[8] / double(m_dicosLoadReadings);
				tv_average += m_proc_list[pos].laver.vals[5] / double(m_dicosLoadReadings);
				if(m_proc_list[pos].ptype!=dicosProcessorE)
				{
					tv_aver_excluded += m_proc_list[pos].laver.vals[5] / double(m_dicosLoadReadings);
				}
			}
			fprintf(m_loadSummary,"Average load for dicos processors\n");
			fprintf(m_loadSummary,"==================================\n");
			fprintf(m_loadSummary,"Average system load       : %6.3f %%\n",(sv_average / (double)(vlen)));
			fprintf(m_loadSummary,"Average traffic load      : %6.3f %%\n",(tv_average / (double)(vlen)));
			fprintf(m_loadSummary,"Average traffic load excl : %6.3f %%\n",(tv_aver_excluded / (double)(vlen-m_excludedDicos.size())));
			fprintf(m_loadSummary,"Average O&M load          : %6.3f %%\n",(oam_average / (double)(vlen)));
			fprintf(m_loadSummary,"Total average load        : %6.3f %%\n",((sv_average + tv_average + oam_average) / (double)(vlen)));
			fprintf(m_loadSummary,"==================================\n\n");
			if(m_allSummary!=0)
			{
				toret = true;
				fprintf(m_allSummary,"Average load for dicos processors\n");
				fprintf(m_allSummary,"==================================\n");
				fprintf(m_allSummary,"Average system load       : %6.3f %%\n",(sv_average / (double)(vlen)));
				fprintf(m_allSummary,"Average traffic load      : %6.3f %%\n",(tv_average / (double)(vlen)));
				fprintf(m_allSummary,"Average traffic load excl : %6.3f %%\n",(tv_aver_excluded / (double)(vlen-m_excludedDicos.size())));
				fprintf(m_allSummary,"Average O&M load          : %6.3f %%\n",(oam_average / (double)(vlen)));
				fprintf(m_allSummary,"Total average load        : %6.3f %%\n",((sv_average + tv_average + oam_average) / (double)(vlen)));
				fprintf(m_allSummary,"==================================\n\n");
			}
		} //if(m_dicosMemFileCount>0)
	} //if(m_dicosLoadReadings>0)
	return toret;
}


void CLogger::getCurrentTrafficLoad(double& sysload, double& traffic, double& traffic_aver, double& oam)
{
	sysload = m_cur_dicos_sys_load;
	traffic = m_cur_dicos_traffic_load;
	traffic_aver = m_cur_dicos_ota_load;
	oam = m_cur_dicos_oam_load;
}

void CLogger::printSummarySeparator()
{
	if(m_allSummary==0)
		return;
	char tmp[81];
	memset(tmp,'*',80);
	tmp[80] = '\0';
	fprintf(m_allSummary,"\n%s\n",tmp);
	fprintf(m_allSummary,"%s\n\n",tmp);
}

void CLogger::logPools(vector<string> pools, ProcessorTypeE type, pchar name)
{
	char line[1024];
	char sep[1024];
	memset(sep,0,1024);
	if(m_poolFile==0)
	{
		sprintf(line,"%s%s",m_summaryDir.c_str(),m_poolFileName.c_str());
		if((m_poolFile=fopen(line,"w"))==0)
		{
			fprintf(stderr,"\nWarning: Failed to create %s\n",line);
			fprintf(stderr,"Warning: %s\n",strerror(errno));
			return;
		}
		time_t t = time(NULL);
		fprintf(m_poolFile,"This file contains the pool distribution\n");
		fprintf(m_poolFile,"Current date and time: %s\n\n",ctime(&t));
	}
	sprintf(line,"Pools on %s %s",enum_processorType2String(type),name);
	memset(sep,'-',strlen(line));
	fprintf(m_poolFile,"%s\n",line);
	fprintf(m_poolFile,"%s\n\n",sep);

	int vlen = pools.size();
	for(int i=0;i<vlen;i++)
	{
		fprintf(m_poolFile,"%s\n",pools[i].c_str());
	}
	fprintf(m_poolFile,"\n");

	vlen = m_proc_list.size();
	m_proc_list.resize(vlen+1);

	m_proc_list[vlen].name = name;
	m_proc_list[vlen].mfptr = 0;
	m_proc_list[vlen].lfptr = 0;
	if(type == dicosProcessorE)
	{
		if(isExcludedDicos(m_proc_list[vlen].name))
		{
			m_proc_list[vlen].ptype = excludedDicosProcessorE;
			return;
		}
	}
	m_proc_list[vlen].ptype = type;

}

void CLogger::setPoolFileName(pchar name)
{
	m_poolFileName = name;
}

void CLogger::excludeDicos(pchar name)
{
	int vlen = m_excludedDicos.size();
	m_excludedDicos.resize(vlen+1);
	m_excludedDicos[vlen] = name;
}

bool CLogger::isExcludedDicos(string name)
{
	int len = m_excludedDicos.size();
	for(int k=0;k<len;k++)
		if(name == m_excludedDicos[k])
			return true;
	return false;
}

void CLogger::setLogBinary(bool log_bin)
{
	m_log_binary = log_bin;
}

void CLogger::setLogMemReadings(bool doLog)
{
	m_logMemReadings = doLog;
}

void CLogger::setLogLoadReadings(bool doLog)
{
	m_logLoadReadings = doLog;
}

void CLogger::setGraphScanSize(int ival)
{
	m_graphScanSize = ival;
}

bool CLogger::getSaveGraphData()
{
	if ( m_graphScanSize) 	return true;
	else					return false;
}

void CLogger::initAverValues()
{
	int i;
	int vlen = m_proc_list.size();
	int dicosCount = 0;
	int excludedDicosCount = 0;
	int	loaderCount = 0;
	int linuxCount = 0;

	for(i=0;i<vlen;i++)
	{
		switch(m_proc_list[i].ptype)
		{
		case linuxProcessorE:
			{
				linuxCount++;
			}break;
		case loaderProcessorE:
			{
				loaderCount++;
			}break;
		case dicosProcessorE:
			{
				dicosCount++;

			}break;
		case excludedDicosProcessorE:
			{
				excludedDicosCount++;
			}break;
		case unknownProcessorTypeE:break;
		}
	}
	m_nrOfDicos = dicosCount + excludedDicosCount;
	m_nrOfExcludedDicos = excludedDicosCount;
	for(i=0;i<vlen;i++)
	{
		memset(&m_proc_list[i].laver.vals,0,sizeof(AVER_VALUES));
		m_proc_list[i].laver.vals[1] = 9999.9999;
		m_proc_list[i].laver.vals[4] = 9999.9999;
		m_proc_list[i].laver.vals[7] = 9999.9999;

		memset(&m_proc_list[i].maver.vals,0,sizeof(AVER_VALUES));
		m_proc_list[i].maver.vals[1] = 9999.9999;
		m_proc_list[i].maver.vals[4] = 9999.9999;
		m_proc_list[i].maver.vals[7] = 9999.9999;
	}

}
