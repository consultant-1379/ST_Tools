// Functions.cpp
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
//! \file Functions.cpp
//! \brief Implements the class CFunctions which contains utilites
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
#ifdef _WIN32
#include <winsock2.h>
#include <direct.h>
#else
#include <sys/socket.h> 
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <netdb.h>
#include <sys/stat.h>
#include <stdlib.h>
#include <dirent.h>
#include <errno.h>
#endif

#include <stdio.h>
#include <string.h>
#include <memory>
#include <string>
#include "Functions.h"
#include "Globals.h"

using namespace std;
//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////


CFunctions::CFunctions()
{

}

CFunctions::~CFunctions()
{

}

bool CFunctions::fExists(pchar fName)
{
	FILE *f;
	if((f=fopen(fName,"r"))!=NULL)
	{
		fclose(f);
		return true;
	}
	return false;
}

pchar CFunctions::trim(pchar line)
{
	pchar pline = ltrim(line);
	return rtrim(pline);
}

pchar CFunctions::ltrim(pchar line)
{
	uint len = strlen(line)-1;
	if (len <= 0)	return line;

	while((line[0]==' ') | (line[0]=='\t') | (line[0]=='\n'))
		line++;
	return line;
}

pchar CFunctions::rtrim(pchar line)
{
	uint len = strlen(line)-1;
	if (len <= 0)	return line;

	while((line[len]==' ') | (line[len]=='\t') | (line[len]=='\n'))
	{
		line[len] = '\0';
		len--;
	}
	return line;

}

bool CFunctions::isCommented(pchar line)
{
	if(strlen(line)==0)
		return true;
	if(strchr(line,COMMENT_CHAR)==line)
		return true;
	return false;
}

pchar CFunctions::removeComment(pchar line)
{
	pchar cchar;
	if((cchar=strchr(line,COMMENT_CHAR))!=NULL)
		line[cchar-line] = '\0';
	return rtrim(line);
}

bool CFunctions::get_hostip(struct in_addr *where, const char *hostname)
{
#ifdef _WIN32
	unsigned long addr = inet_addr(hostname);
	if(addr != INADDR_NONE)
#else
	in_addr_t addr = inet_addr(hostname);
	if(addr != (in_addr_t)-1)
	
#endif
	{
		memcpy(&(where->s_addr), &addr, sizeof(addr));
	}
	else
	{
        struct hostent *hptr = gethostbyname(hostname);
		if ( hptr != NULL )
		{
			memcpy(&(where->s_addr), hptr->h_addr_list[0], hptr->h_length);
		}
		else
		{
			printf("Failed to resolve hostname %s\n",hostname);
			return false;
		}
	}
	return true;
}

pchar CFunctions::removeQuots(pchar line)
{
	pchar q1, q2;
	if((q1=strchr(line,'\"'))==NULL)
		return line;
	q1++;
	if((q2=strchr(q1,'\"'))==NULL)
		return q1;
	q1[q2-q1] = '\0';
	return q1;
}

time_t CFunctions::StrToTime(pchar str, int& hh, int& mm, int& ss)
{
	if(str == NULL)
		return 0L;
	char *pstr = strchr(str,':');
	if(pstr == NULL)
	{
		ss = atoi(str);
		return (time_t)ss;
	}
	int lhh = atoi(str);
	pstr++;
	int lmm = atoi(pstr);
	if((pstr = strchr(pstr,':')) == NULL)
	{
		mm = lhh;
		ss = lmm;
		return (time_t)(lhh*60 + lmm);
	}
	pstr++;
	int lss = atoi(pstr);
	hh = lhh;
	mm = lmm;
	ss = lss;
	return (time_t)(3600*lhh + 60*lmm + lss);

}


bool CFunctions::CreateDir(pcchar path)
{
	std::string tmp;
	tmp = path;
	int len = tmp.length();
	while((tmp.c_str()[len-1] == '\\') || (tmp.c_str()[len-1] == '/'))
	{
		tmp[len-1] = 0;
		len--;
	}

#ifdef _WIN32
	int result = mkdir(tmp.c_str());
#else
	int result = mkdir(tmp.c_str(),0777);
#endif
	switch(result)
	{ //switch(result)
	case -1:
		{ //case -1:
			switch(errno)
			{ //switch(errno)
			case 17:
				return true;
			default:
				fprintf(stderr,"Error: Failed to create directory %s\n",tmp.c_str());
				fprintf(stderr,"Error: %s\n",strerror(errno));
				return false;
			}; //switch(errno)
		} //case -1:
		break;
	case 0:
		return true;
	default:
		return false;
	}; //switch(result)
	return true;

}

