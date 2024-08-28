// Telnet.cpp
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
//! \file Telnet.cpp
//! \brief CTelnet class implementation. Implements a telnet functionality
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

#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <signal.h>

#ifndef _WIN32
#include <sys/socket.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <netdb.h>
#include <sys/stat.h>
#endif
#include "Telnet.h"

void debugPrint(string line);
//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

SOCKET CTelnet::sock = INVALID_SOCKET;

CTelnet::CTelnet()
: m_window_width(500)
, m_window_height(20)
, MaxBufSizeC(0x300000)
, MaxRecvRetriesC(5)
, m_buf(new char[MaxBufSizeC])
{
	lineFeedC[0] = 0x0a;
	lineFeedC[1] = 0x00;	
	options.do_echo = false;
	options.do_sgh = true;
	options.host_will_echo = false;
	options.host_will_sgh = true;

	memset(&remote_addr,0,sizeof(remote_addr));
	remote_addr.sin_family = AF_INET;

	m_port = 23;

	m_recv_timeout.tv_sec = 2;
	m_recv_timeout.tv_usec = 0;
	m_recv_retries = 1;
}

CTelnet::~CTelnet()
{
	if(sock == INVALID_SOCKET)
		return;
	closesocket(sock);
	sock = INVALID_SOCKET;
}


int CTelnet::err(int theRes)
{
	closesocket(sock);
	sock = INVALID_SOCKET;
	if(theRes<0)
	{
		OnError(string("The remote host broke the connection"));
	}
	else if(theRes==0)
	{
		OnError(string("The remote host closed the connection"));
	}
	return -1;

}

void CTelnet::get_hostip(struct in_addr *where, string hostname)
{
	in_addr_t addr = inet_addr(hostname.c_str());
	if(addr != (INADDR_NONE))
	{
		memcpy(&(where->s_addr), &addr, sizeof(addr));
	}
	else
	{
        struct hostent *hptr = gethostbyname(hostname.c_str());
		if ( hptr != NULL )
		{
			memcpy(&(where->s_addr), hptr->h_addr_list[0], hptr->h_length);
		}
		else
		{
			string theErr = "Failed to resolve host name " + hostname;
			OnError(theErr);
		}
	}
	
}


int CTelnet::negotiate(int& len, unsigned char** inbuff, unsigned char *outbuff, bool& done)
{
	if(len < 1)
		return 0;
	unsigned char *ibuff = *inbuff;
	unsigned char *obuff = outbuff;
	int toret = 0;
//printf("Starting at %02x\n",ibuff[0]);
	while(len > 0)
	{ //while(len > 0)
		if(ibuff[0]!=t_iac)
		{
//printf("Breaking because of %02x\n",ibuff[0]);
			done = true;
			*inbuff = ibuff;
			return toret;
		}
//printf("Switching1  %02x\n",ibuff[1]);
//printf("Switching2  %02x\n",ibuff[2]);
		switch(ibuff[1])
		{ //switch(ibuff[1])
		case t_sb:
			{ //case t_sb:
				switch(ibuff[2])
				{ //switch(ibuff[2])
				case t_terminal_type:
					{ //case t_terminal_type:
						if(ibuff[3]==0)
						{						
							ibuff += 10;
							len -= 10;
						}
						else
						{
							obuff[0] = t_iac;
							obuff[1] = t_sb;
							obuff[2] = t_terminal_type;
							obuff[3] = 0;
							obuff[4] = 'A';
							obuff[5] = 'N';
							obuff[6] = 'S';
							obuff[7] = 'I';
							obuff[8] = t_iac;
							obuff[9] = t_se;
							obuff += 10;
							toret += 10;
							ibuff += 6;
							len -= 6;
						}
					} //case t_terminal_type:
					break;
				case t_window_size:
					{ //case t_window_size:
						if(ibuff[3]==0)
						{						
							ibuff += 4;
							setWindowSize(ibuff);
							len -= 10;
							ibuff += 6;
						}
						else
						{
							obuff[0] = t_iac;
							obuff[1] = t_sb;
							obuff[2] = t_window_size;
							obuff[3] = 0;
							obuff += 4;
							getWindowSize(obuff);
							obuff += 4;
							obuff[0] = t_iac;
							obuff[1] = t_se;
							obuff += 2;
							toret += 10;
							ibuff += 6;
						}

					} //case t_window_size:
					break;
				default:
					{ //default: switch(ibuff[2])
						if(ibuff[3]==0)
						{
							ibuff += 10;
							len -= 10;
						}
						else
						{
							obuff[0] = t_iac;
							obuff[1] = t_wont;
							obuff[2] = ibuff[2];
							obuff += 3;
							len -= 6;
							ibuff += 6;
							toret += 3;
						}
						
					} //default: switch(ibuff[2])
					break;
				}; //switch(ibuff[2])
			} //case t_sb:
			break;
		case t_will:
			{ //case t_will:
				switch(ibuff[2])
				{ //switch(ibuff[2])
				case t_echo:
					{ //case t_echo:
						options.host_will_echo = true;
						obuff[0] = t_iac;
						obuff[1] = t_do;
						obuff[2] = t_echo;
						obuff += 3;
						len -= 3;
						toret += 3;
						ibuff += 3;
					} //case t_echo:
					break;
				case t_suppress_go_ahead:
					{ //case t_suppress_go_ahead:
						options.host_will_sgh = true;
						obuff[0] = t_iac;
						obuff[1] = t_do;
						obuff[2] = t_suppress_go_ahead;
						obuff += 3;
						len -= 3;
						toret += 3;
						ibuff += 3;
					} //case t_suppress_go_ahead:
					break;
				case t_window_size:
					{ //case t_window_size:
						obuff[0] = t_iac;
						obuff[1] = t_dont;
						obuff[2] = t_window_size;
						obuff += 3;
						len -= 3;
						toret += 3;
						ibuff += 3;
					} //case t_window_size:
					break;
				default:
					{ //default: switch(ibuff[2])
						obuff[0] = t_iac;
						obuff[1] = t_dont;
						obuff[2] = ibuff[2];
						obuff += 3;
						len -= 3;
						toret += 3;
						ibuff += 3;
					} //default: switch(ibuff[2])
					break;
				}; //switch(ibuff[2])
			} //case t_will:
			break;
		case t_wont:
			{ //case t_wont:
				switch(ibuff[2])
				{ //switch(ibuff[2])
				case t_echo:
					{ //case t_echo:
						options.host_will_echo = false;
						ibuff += 3;
						len -= 3;
					} //case t_echo:
					break;
				default:
					{ //default: switch(ibuff[2])
						ibuff += 3;
						len -= 3;
					} //default: switch(ibuff[2])
					break;
				}; //switch(ibuff[2])
			} //case t_wont:
			break;
		case t_do:
			{ //case t_do:
				switch(ibuff[2])
				{ //switch(ibuff[2])
				case t_echo:
					{ //case t_echo:
						options.do_echo = true;
						obuff[0] = t_iac;
						obuff[1] = t_will;
						obuff[2] = t_echo;
						obuff += 3;
						len -= 3;
						toret += 3;
						ibuff += 3;
					} //case t_echo:
					break;
				case t_terminal_type:
					{ //case t_terminal_type:
						obuff[0] = t_iac;
						obuff[1] = t_will;
						obuff[2] = t_terminal_type;
						obuff += 3;
						len -= 3;
						ibuff += 3;
						/*
						obuff[0] = t_iac;
						obuff[1] = t_sb;
						obuff[2] = t_terminal_type;
						obuff[3] = 0;
						obuff[4] = 'A';
						obuff[5] = 'N';
						obuff[6] = 'S';
						obuff[7] = 'I';
						obuff[8] = t_iac;
						obuff[9] = t_se;
						obuff += 10;
						toret += 13;
						*/
						toret += 3;
					} //case t_terminal_type:
					break;
				case t_window_size:
					{ //case t_window_size:
						obuff[0] = t_iac;
						obuff[1] = t_will;
						obuff[2] = t_window_size;
						obuff += 3;
						len -= 3;						
						obuff[0] = t_iac;
						obuff[1] = t_sb;
						obuff[2] = t_window_size;
						obuff += 3;
						getWindowSize(obuff);
						obuff += 4;
						obuff[0] = t_iac;
						obuff[1] = t_se;
						obuff += 2;
						toret += 12;
						ibuff += 3;
					} //case t_window_size:
					break;
				default:
					{ //default: switch(ibuff[2])
						obuff[0] = t_iac;
						obuff[1] = t_wont;
						obuff[2] = ibuff[2];
						obuff += 3;
						len -= 3;
						toret += 3;
						ibuff += 3;
					} //default: switch(ibuff[2])
					break;
				}; //switch(ibuff[2])
			} //case t_do:
			break;
		case t_dont:
			{ //case t_dont:
				switch(ibuff[2])
				{ //switch(ibuff[2])
				case t_echo:
					{ //case t_echo:
						options.do_echo = false;
						obuff[0] = t_iac;
						obuff[1] = t_wont;
						obuff[2] = t_echo;
						obuff += 3;
						len -= 3;
						toret += 3;
						ibuff += 3;
					} //case t_echo:
					break;
				case t_window_size:
					{ //case t_window_size:
						obuff[0] = t_iac;
						obuff[1] = t_wont;
						obuff[2] = t_window_size;
						obuff += 3;
						len -= 3;
						toret += 3;
						ibuff += 3;
					} //case t_window_size:
					break;
				default:
					{ //default: switch(ibuff[2])
						printf("Unknown2 %02x\n",ibuff[2]);
						obuff[0] = t_iac;
						obuff[1] = t_wont;
						obuff[2] = ibuff[2];
						obuff += 3;
						len -= 3;
						toret += 3;
						ibuff += 3;
					} //default: switch(ibuff[2])
					break;
				}; //switch(ibuff[2])
			} //case t_dont:
			break;
		default:
			{
				printf("Unknown1 %02x\n",ibuff[1]);
				done = true;
				*inbuff = ibuff;
				return toret;
			}
			break;			
		}; //switch(ibuff[1])
	} //while(len > 0)
	done = false;
	*inbuff = ibuff;
	return toret;
}

void CTelnet::getWindowSize(unsigned char *buff)
{
	buff[0] = 0xff & (m_window_width >> 8);
	buff[1] = 0xff & m_window_width;
	buff[2] = 0xff & (m_window_height>> 8);
	buff[3] = 0xff & m_window_height;
}

void CTelnet::setWindowSize(unsigned char *size)
{
	m_window_width = size[0] << 8;
	m_window_width += size[1];
	m_window_height = size[2] << 8;
	m_window_height += size[3];

}


void debugPrint(unsigned char* buf,int len)
{
#ifdef _DEBUG
	int i,j;
	printf("Length: %d\n",len);
	for(i=0;i<len;i++)
	{
		printf("%02x ",buf[i]);
		if(((i+1)%16)==0)
		{
			printf("| ");
			for(j=i-15;j<(i+1);j++)
			{
				printf("%c ",buf[j]>31?buf[j]:'.');
			}
			printf("|\n");
		}
	}
	if(((i+1)%16)!=0)
	{
		int to = i;
		while(((i+1)%16)!=0) 
		{
			printf("   ");
			i++;
		}
		printf("   | ");
		for(j=i-15;j<to;j++)
		{
			printf("%c ",buf[j]>31?buf[j]:'.');
		}
		while(((j)%16)!=0) 
		{
			printf("  ");
			j++;
		}
		printf("|\n");
	}
	printf("\n");
#endif
}

int CTelnet::Connect()
{
	if((m_host.length()==0) | (m_port==0))
	{
		OnError(string("Telnet not initiated"));
		return -1;
	}
	return Connect(m_host,m_port);
}

int CTelnet::Connect(string host, int port)
{
	remote_addr.sin_port = htons(port);
	get_hostip(&remote_addr.sin_addr,host);

	sock = socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
	if(sock == INVALID_SOCKET)
	{
		string theErr = strerror(errno);
		OnError(theErr);
		return -1;
	}
	while(connect(sock,(sockaddr*)&remote_addr,sizeof(remote_addr))!=0)
	{
		Sleep(1000);
		char tmp[256];
		sprintf(tmp,"Retrying %s:%u",inet_ntoa(remote_addr.sin_addr),ntohs(remote_addr.sin_port));
		string theMsg = tmp;
		OnConnectFailed(theMsg);

	}
	fd_set fds, tmpfds;
	struct timeval tv;
	FD_ZERO(&fds);
	FD_SET(sock, &fds);
	unsigned char buff[0xffff];
	unsigned char* pbuff = buff;
	unsigned char nbuff[0xffff];
	bool done = false;
	bool havePrompt = false;
	int res, tores, tres;
	int retries = 0;
	vector<string> theLines;
	while(!done && (retries<(int)MaxRecvRetriesC))
	{ //while()
		tv.tv_sec = 2;
		tv.tv_usec = 0;
		tmpfds = fds;
		select(sock+1,&tmpfds,NULL,NULL,&tv);
		if(FD_ISSET(sock,&tmpfds))
		{
			retries = 0;
			pbuff = buff;
			res = recv(sock,(char*)buff,sizeof(buff),0);
			if(res<1)
			{
				return err(res);
			}
			buff[res] = '\0';
debugPrint(buff,res);
			tores = negotiate(res,&pbuff,nbuff,done);
			if(done)
			{ //if(done)
				if(tores>0)
				{ //if(tores>0)
					tres = send(sock,(const char *)nbuff,tores,0);
					if(tres!=tores)
					{
						return err(tres);
					}
				} //if(tores>0)
			} //if(done)
			else
			{
				tres = send(sock,(const char *)nbuff,tores,0);
				if(tres!=tores)
				{
					return err(tres);
				}
			}
			split_into_lines((char*)pbuff,res,theLines);
			for(int i=0;i<(int)theLines.size();i++)
			{
debugPrint(theLines[i]);
				if((int)theLines[i].find(m_prompt)!=-1)
				{
					havePrompt = true;
					break;
				}
			}
		}
		else
			retries++;
		if(done) break;
	} //while(!done)
	if(!done)
	{
		OnError(string("Negotioation failed"));
		return -1;
	}
	if(m_login_prompt.length()==0)
	{
		retries = 0;
		if(havePrompt) 
		{
			char tmp[256];
			sprintf(tmp,"Connected to %s:%u",inet_ntoa(remote_addr.sin_addr),ntohs(remote_addr.sin_port));
			string theMsg = tmp;
			OnEvent(theMsg);
			return 0;
		}
		//wait for the prompt
		while(!havePrompt && (retries<(int)MaxRecvRetriesC))
		{ //while(retries<5)
			tv.tv_sec = 2;
			tv.tv_usec = 0;
			tmpfds = fds;
			select(sock+1,&tmpfds,NULL,NULL,&tv);
			if(FD_ISSET(sock,&tmpfds))
			{
				retries = 0;
				pbuff = buff;
				int res = recv(sock,(char*)buff,sizeof(buff),0);
				if(res<1)
					return err(res);
				buff[res] = '\0';
debugPrint(buff,res);
				tores =  negotiate(res,&pbuff,nbuff,done);
				if(tores>0)
					if(send(sock,(const char*)nbuff,tores,0)!=tores)
						return err(res);
				split_into_lines((char*)pbuff,res,theLines);
				for(int i=0;i<(int)theLines.size();i++)
				{
debugPrint(theLines[i]);
					if((int)theLines[i].find(m_prompt)!=-1)
					{
						char tmp[256];
						sprintf(tmp,"Connected to %s:%u",inet_ntoa(remote_addr.sin_addr),ntohs(remote_addr.sin_port));
						string theMsg = tmp;
						OnEvent(theMsg);
						return 0;
					}
				}
			}
			else
				retries++;
		} //while(true)
		OnError(string("Could not find prompt"));
		return -1;
	}
//Wait for login prompt
	if(strstr((const char*)buff,m_login_prompt.c_str())!=0)
	{ //if(strstr((const char*)buff,m_login_prompt)!=0)
		sprintf((char*)buff,"%s\n",m_login.c_str());
		int len = strlen((char*)buff);
		res = send(sock,(const char*)buff,len,0);
		if(res != len)
			return err(res);
	} //if(strstr((const char*)buff,m_login_prompt)!=0)
	else
	{ //else to if(strstr((const char*)buff,m_login_prompt)!=NULL)
		while(true)
		{ //while(true)
			tv.tv_sec = 2;
			tv.tv_usec = 0;
			tmpfds = fds;
			select(sock+1,&tmpfds,NULL,NULL,&tv);
			if(FD_ISSET(sock,&tmpfds))
			{
				res = recv(sock,(char*)buff,sizeof(buff),0);
				if(res<1)
					return err(res);
				tores = negotiate(res,(unsigned char**)&buff,nbuff,done);
				if(tores>0)
					if(send(sock,(const char*)nbuff,tores,0)!=tores)
						return err(res);
				if(strstr((const char*)buff,m_login_prompt.c_str())!=NULL)
				{ //if(strstr((const char*)buff,m_login_prompt)!=NULL)
					sprintf((char*)buff,"%s\n",m_login.c_str());
					int len = strlen((char*)buff);
					res = send(sock,(const char*)buff,len,0);
					if(res != len)
						return err(res);
					break;
				} //if(strstr((const char*)buff,m_login_prompt)!=NULL)
			}
		} //while(true)

	} //else to if(strstr((const char*)buff,m_login_prompt)!=NULL)

//wait for password prompt
	while(true)
	{ //while(true)
		tv.tv_sec = 2;
		tv.tv_usec = 0;
		tmpfds = fds;
		select(sock+1,&tmpfds,NULL,NULL,&tv);
		if(FD_ISSET(sock,&tmpfds))
		{
			int res = recv(sock,(char*)buff,sizeof(buff),0);
			if(res<1)
				return err(res);
			tores = negotiate(res,(unsigned char**)&buff,nbuff,done);
			if(tores>0)
				if(send(sock,(const char*)nbuff,tores,0)!=tores)
					return err(tores);
			if(strstr((const char*)buff,m_password_prompt.c_str())!=NULL)
			{ //if(strstr((const char*)buff,m_password_prompt)!=NULL)
				sprintf((char*)buff,"%s\n",m_pwd.c_str());
				int len = strlen((char*)buff);
				res = send(sock,(const char*)buff,len,0);
				if(res != len)
					return err(res);
				break;
			} //if(strstr((const char*)buff,m_password_prompt)!=NULL)
			else
			{
				if(strstr((const char*)buff,m_login_prompt.c_str())!=NULL)
				{
					OnError(string("Login failed"));
					closesocket(sock);
					sock = INVALID_SOCKET;
					return -1;
				}
			}
		}
	} //while(true)
//wait for prompt

	while(true)
	{ //while(retries<5)
		retries = 0;
		tv.tv_sec = 2;
		tv.tv_usec = 0;
		tmpfds = fds;
		select(sock+1,&tmpfds,NULL,NULL,&tv);
		if(FD_ISSET(sock,&tmpfds))
		{
			int res = recv(sock,(char*)buff,sizeof(buff),0);
			if(res<1)
				return err(res);
			tores = negotiate(res,(unsigned char**)&buff,nbuff,done);
			if(tores>0)
				if(send(sock,(const char*)nbuff,tores,0)!=tores)
					return err(res);
			if(strstr((const char*)buff,m_prompt.c_str())!=NULL)
			{ //if(strstr((const char*)buff,m_prompt)!=NULL)
				char tmp[256];
				sprintf(tmp,"Connected to %s:%u",inet_ntoa(remote_addr.sin_addr),ntohs(remote_addr.sin_port));
				string theMsg = tmp;
				OnEvent(theMsg);
				return 0;
			} //if(strstr((const char*)buff,m_prompt)!=NULL)
		}
		else
			retries++;
		if(retries==5)
		{
			OnError(string("Could not find prompt"));
			return -1;
		}
	} //while(true)
	return -1;
}

void CTelnet::setHost(string host)
{
	m_host = host;
}

void CTelnet::setPort(int port)
{
	if(port==0)
		return;
	m_port = port;
}

void CTelnet::setLoginPrompt(string prompt)
{
	m_login_prompt = prompt;
}

void CTelnet::setLogin(string login)
{
	m_login = login;
}

void CTelnet::setPasswordPrompt(string prompt)
{
	m_password_prompt = prompt;
}

void CTelnet::setLoginPassword(string pwd)
{
	m_pwd = pwd;
}

void CTelnet::setPrompt(string prompt)
{
	m_prompt = prompt;
}

void CTelnet::setExitCmd(string exitcmd)
{
	m_exit_cmd = exitcmd;
}

int CTelnet::send_lf1()
{
	if(sock==INVALID_SOCKET) return -1;
	fd_set fds, tmpfds;
	struct timeval tv;
	FD_ZERO(&fds);
	FD_SET(sock, &fds);
	int retries = 0;
	int lfres;
	int i;
	char* pLf = lineFeedC;
	char* pbuf = m_buf.get();
	if(options.host_will_echo)
	{
		for(i=0;i<1;i++)
		{
			lfres = send(sock,pLf,1,0);
			retries = 0;
			while(retries<(int)MaxRecvRetriesC)
			{ //while(retries<MaxRecvRetriesC)
				tv = m_recv_timeout;
				tmpfds = fds;
				select(sock+1,&tmpfds,NULL,NULL,&tv);
				if(FD_ISSET(sock,&tmpfds))
				{
					retries = 0;
					lfres = recv(sock,pbuf,1,0);
					if(lfres<1)
						return err(lfres);
debugPrint((unsigned char*)pbuf,lfres);
					if((pbuf[0]!='\n') && (pbuf[0]!='\r'))
					{
						OnError("Host failed to echo");
						return err(1);
					}
					return 0;
				}
				else
					retries++;
			}
		}
	}
	else
	{
		lfres = send(sock,lineFeedC,1,0);
		if(lfres != 1)
			return err(lfres);
	}
	return 0;
}
  
int CTelnet::send_lf()
{
	if(sock==INVALID_SOCKET) return -1;
	int res = send(sock,lineFeedC,sizeof(lineFeedC),0);
	if(res != sizeof(lineFeedC))
		return err(res);
	if(options.host_will_echo)
	{
		string theCmd = (char*)lineFeedC;
		return read_echo(theCmd);
	}
	return 0;

}

int CTelnet::send_cmd(string theCmd)
{
	if(sock==INVALID_SOCKET) return -1;
	int res;
	char* pcmd = (char*)theCmd.c_str();
	
	res = send(sock,pcmd,theCmd.length(),0);
	if(res != (int)theCmd.length())
		return err(res);
	if(options.host_will_echo)
	{
		if(read_echo(theCmd)==-1) return -1;
	}
	if(send_lf1()<0) return -1;

	return theCmd.length();
}

bool CTelnet::get_line(string& theLines, string& theLine)
{
	int rpos = theLines.find_first_of("\r");
	int npos = theLines.find_first_of("\n");
	int dist;
	switch(rpos)
	{
	case -1:
		{
			switch(npos)
			{
			case -1:
				{
					//Neither \r or \n was found
					//return the rest of the line
					theLine = theLines;
					return false;				
				}break;
			default:
				{
					//only \n has been found
					//return string before \n
					theLine = theLines.substr(0,npos);
					theLines = theLines.substr(npos+1,theLines.length());
					return true;
				}break;
			}
		}break;
	default:
		{
			switch(npos)
			{
			case -1:
				{
					//only \r has been found
					//return string before \r
					theLine = theLines.substr(0,rpos);
					theLines = theLines.substr(rpos+1,theLines.length());
					return true;
				}break;
			default:
				{
					dist = npos - rpos; 
					//if \r\n then dist = 1
					//return string before \r
					if(dist==1)
					{
						theLine = theLines.substr(0,rpos);
						theLines = theLines.substr(npos+1,theLines.length());
						return true;
					}
					//if dist is negative then \n is found earlier on the line
					//return string before \n
					if(dist<0)
					{
						theLine = theLines.substr(0,npos);
						theLines = theLines.substr(npos+1,theLines.length());
						return true;
					}
					//when dist is greater then 1 then there \r
					//has been found much before \n and there
					//is info betweem. Return string before \r
					if(dist>1)
					{
						theLine = theLines.substr(0,rpos);
						theLines = theLines.substr(rpos+1,theLines.length());
						return true;
					}
					OnError("Unknown error removing prompt from line " + theLine);
					return false;
				}break;
			}
		}
	}

}

void debugPrint(string line)
{
#ifdef _DEBUG
	int i=0;
	while(i<line.length())
	{
		printf("%c",line[i]);
		i++;
	}
	printf("\n");
#endif
}

void CTelnet::split_into_lines(char* theLine, int theLength, vector<string>& theLines)
{
	int lcount = 0;
	string tmpLine;
	string strBuff;
	int length = 0;
	char* pbuff = theLine;
	
	while(length < theLength)
	{
		strBuff = pbuff;
		if(get_line(strBuff,tmpLine))
		{
			pbuff += tmpLine.length();
			if(tmpLine.length()>1)
			{
				lcount++;
				theLines.resize(lcount);
				theLines[lcount-1] = tmpLine;
			}
			length += tmpLine.length();
			while((pbuff[0]=='\n') 
			||    (pbuff[0]=='\r') 
			||    (pbuff[0]=='\t') 
			||    (pbuff[0]=='\0') 
			||    (pbuff[0]==' ')) 
			{
				pbuff++; 
				length++;
				if(length > theLength)
				{
					return;
				}
			}
		}
		else
		{
			if(tmpLine.length()>1)
			{
				lcount++;
				theLines.resize(lcount);
				theLines[lcount-1] = tmpLine;
			}
			return;
		}
	}
}

bool CTelnet::remove_prompt(char* theLine, int& theLength)
{	

	if(theLength < (int)m_prompt.length()) return false;
	char* pprompt = strstr(theLine,m_prompt.c_str());
	while(pprompt!=0)
	{
//printf("Prompt: %s\n",pprompt);
		if((theLength - (pprompt - theLine)) == (int)m_prompt.length())
		{
			pprompt[0] = '\0';
			theLength = pprompt - theLine;
			return true;
		}
		pprompt++;
		pprompt = strstr(pprompt,m_prompt.c_str());

	}
	return false;
}

int CTelnet::recv_answer(vector<string>& theAnswer)
{
	if(sock==INVALID_SOCKET) return -1;
	fd_set fds, tmpfds;
	struct timeval tv;
	FD_ZERO(&fds);
	FD_SET(sock, &fds);
	int retries = 0;
	int res, tres;
	int toret = 0;
	string line;
	char* pbuf = m_buf.get();
	

	while(retries<(int)MaxRecvRetriesC)
	{ //while(retries<MaxRecvRetriesC)
		tv = m_recv_timeout;
		tmpfds = fds;
		select(sock+1,&tmpfds,NULL,NULL,&tv);
		if(FD_ISSET(sock,&tmpfds))
		{
			retries = 0;
			res = recv(sock,pbuf,MaxBufSizeC,0);
			if(res<1)
				return err(res);
debugPrint((unsigned char*)pbuf,res);
			tres = res;
			toret += res;
			pbuf[res] = '\0';
			line = pbuf;

			if(remove_prompt(pbuf,res))
			{
				split_into_lines(m_buf.get(),toret,theAnswer);
				return toret;
			}
			else
				pbuf += res;
		}
		else
			retries++;
	} //while(retries<MaxRecvRetriesC)
	return -1;
}


void CTelnet::shut_down()
{
	closesocket(sock);
	sock = INVALID_SOCKET;
}

int CTelnet::read_echo(string theCmd)
{
	if(sock==INVALID_SOCKET) return -1;
	fd_set fds, tmpfds;
	struct timeval tv;
	FD_ZERO(&fds);
	FD_SET(sock, &fds);
	int retries = 0;
	int res;
	int i;
	int length = theCmd.length();
	char* pbuf = m_buf.get();
	char* pcmd = (char*)theCmd.c_str();
	int tres = 0;
	while(tres<length)
	{
		while(retries<(int)MaxRecvRetriesC)
		{ //while(retries<MaxRecvRetriesC)
			tv = m_recv_timeout;
			tmpfds = fds;
			select(sock+1,&tmpfds,NULL,NULL,&tv);
			if(FD_ISSET(sock,&tmpfds))
			{
				retries = 0;
				res = recv(sock,pbuf,MaxBufSizeC,0);
debugPrint((unsigned char*)pbuf,res);
				if(res<1)
					return err(res);
				tres += res;

				for(i=0;i<res;i++)
				{
					//printf("pbuf[i]: %c pcmd[i]: %c\n",pbuf[i],pcmd[i]);
					if(pbuf[i]!=pcmd[i])
					{
						//printf("ERROR: pbuf[i]: %c pcmd[i]: %c\n",pbuf[i],pcmd[i]);
						OnError(string("Host failed to echo cmd " + theCmd));
						return -1;
					}
				}
				pcmd += res;
			}
			else
				retries++;
			if(tres>=length) return 0;
		}
		if(retries==(int)MaxRecvRetriesC)
		{
			OnError(string("Max retries exceeded"));
			return -1;
		}
	}
	return 0;
}
