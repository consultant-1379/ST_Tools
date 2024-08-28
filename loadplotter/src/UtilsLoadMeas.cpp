// UtilsLoadMeas.cc
//==============================================================================
//
//  COPYRIGHT Ericsson España S.A. 2013
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
//! \file UtilsLoadMeas.cc
//! \brief implements UtilsLoadMeas class
//!
//! AUTHOR \n
//!    2012-12-18 by Beatriz Prieto
//!                        beatriz.prieto@blue-tc.com \n
// =============================================================================
//
//! CHANGES \n
//!    DATE           NAME      DESCRIPTION \n
//      ...
//
//==============================================================================
#include "UtilsLoadMeas.h"


#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <unistd.h>
#include <syscall.h>




unsigned short m_idle_pos = 0;
unsigned short m_memused_pos = 0;
unsigned short m_memcmd_pos = 0;
unsigned short m_cpucmd_pos = 0;

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////



UtilsLoadMeas::UtilsLoadMeas()
{
}

UtilsLoadMeas::~UtilsLoadMeas()
{
}

unsigned short UtilsLoadMeas::labelOrder(char *fullstring, char *label, char* sep)
{
	unsigned short 	count;
	char		*aux;
	bool		found;
	char		int_buffer[CP_MAX_BUFFER_SIZE];
	//Returns the position of label in string.
	if (!strcasestr(fullstring,label))
	{
		//String doesn't contain label.
		return 0;
	}
	strcpy(int_buffer,fullstring);
	aux=strtok(int_buffer,sep);
	count=1;
	found=false;
	while ((aux)&&(!found))
	{
		if (strcasestr(aux,label))
		{
			found=true;
		}
		else
		{
			aux=strtok(NULL,sep);
			count++;
		}
	}
	return count;
}

bool UtilsLoadMeas::confGetHeaderParams(char *fullstring)
{
	bool isHeader = false;
	//Configures the order in wich the output params of sar will be displayed
	if (strstr(fullstring, IDLE_PARAM_LABEL))
	{
		m_idle_pos=labelOrder(fullstring, IDLE_PARAM_LABEL, " ");
		//printf("header % s \n",fullstring);// 8
		//printf("idle_pos, pos %d \n", m_idle_pos); //8
		isHeader = true;
	}
	if(strstr(fullstring, MEMUSED_PARAM_LABEL))
	{
		m_memused_pos=labelOrder(fullstring, MEMUSED_PARAM_LABEL, " ");
		//printf("memused_pos, pos %d \n", m_memused_pos); //4
		isHeader = true;
	}
	if (strstr(fullstring, CPU_PARAM_LABEL))
	{
		m_cpucmd_pos=labelOrder(fullstring, CPU_PARAM_LABEL, " ");
		//printf("cpucmd_pos, pos %d \n", m_cpucmd_pos); //6
		isHeader= true;
	}
	if (strstr(fullstring, MEM_PARAM_LABEL))
	{
		m_memcmd_pos=labelOrder(fullstring, MEM_PARAM_LABEL, " ");
		//printf("memcmd_pos, pos %d \n", m_memcmd_pos); //7
		isHeader= true;
	}


	//return true if fullstring is a header string.
	return isHeader;
}


int UtilsLoadMeas::parCount(char *instr, char *sep)
{
	int count=0;
	char *aux;

	aux=instr;
	do
	{
		aux=strstr(aux,sep);
		if (aux)
		{
			aux+=strlen(sep);
			count++;

		}
	}while (aux);
	return count+1;
}

float UtilsLoadMeas::getParamNumber(char *in, int index)
{
	char 	int_buffer[CP_MAX_BUFFER_SIZE];
	char	*aux;
	int	count=1;

	strcpy(int_buffer,in);

	aux=strtok(int_buffer, " ");
	while ((aux)&&(count<index))
	{
		count++;
		aux=strtok(NULL," ");
	}
	//printf("return %s \n", aux);

	return atof(aux);
}

float UtilsLoadMeas::getFloatLoad(char *in)
{
//	printf("load string %s pos %d \n", in, m_idle_pos);
	return getParamNumber(in, m_idle_pos);
}

float UtilsLoadMeas::getFloatMem(char *in)
{
	//printf("mem string %s posi %d \n", in, m_memused_pos);
	return getParamNumber(in, m_memused_pos);
}

float UtilsLoadMeas::getFloatLoadCmd(char *in)

{
	//printf("load cmd string %s pos %d \n", in, m_cpucmd_pos);
	return getParamNumber(in, m_cpucmd_pos);
}

float UtilsLoadMeas::getFloatMemCmd(char *in)
{
	//printf("mem cmd string %s pos %d \n", in, m_memcmd_pos);
	return getParamNumber(in, m_memcmd_pos);
}

int UtilsLoadMeas::sendCmd(char *buff, int fd)
{
	char intbuf[5000];

	sprintf(intbuf,"%s\n",buff);

	if (write(fd, intbuf, strlen(intbuf)) == -1)
	{
		perror("write");
		return 1;
	}
	else
	{
		return 0;
	}
}


int UtilsLoadMeas::recvLine(int fd, char *buff, int timeout)
{
    int nread=0;
    int count=0;
    int acumnread=0;
	char recv;

	buff[0]=0;

	if(fd==-1){
		//Not connected
		return -1;
    }
	else{
		recv=0;
        while ((count<timeout) && (acumnread<BUFFLEN-1) && (recv!='\n')){
        	nread = read(fd, &recv, 1);
            if (nread == -1){
            	if (errno == EAGAIN){
                	usleep(1000);
                    count++;
                }
				else{
					return -2;
				}
            }
            else{
            	count=0;
				buff[acumnread]=recv;
              	acumnread+=nread;
            }
        }
    }

	buff[acumnread-1]=0;
	if (count>=timeout){
		return -1;
	}
	else{
		return acumnread;
	}
}

string UtilsLoadMeas::replaceAll(const string from, string m_const, const char *m_var){
string bufferString = "";

string cmdTmp1 = from;
size_t idx1 = 0;
for (;;) {
        idx1 = cmdTmp1.find(m_const, idx1);
        if (idx1 == string::npos)  break;
        cmdTmp1.replace(idx1, m_const.size(), m_var);
        idx1 += strlen(m_var);
}
bufferString=bufferString+cmdTmp1;
return bufferString;
}



