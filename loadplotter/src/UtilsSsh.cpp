// UtilsSsh.cc
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
//  This is the responsibility of the third party..
//
// ============================================================================
//
//! \file UtilsSsh.cc
//! \brief implements UtilsSsh class
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
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <pty.h>
#include <unistd.h>
#include <fcntl.h>
#include <iostream>

#include "UtilsSsh.h"

std::string root_credential="";
//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////
std::string get_node_user_credential()
{
    std::string cmd = "get_node_user_credential -v hss_cba root 1>get_node_user_credential.data 2>get_node_user_credential.log ";

    if(system(cmd.c_str())!=0){
        printf("\n\nERROR: There is some problem reading node root credential. Analyze get_node_user_credential.log\n");
        exit (1);
    }

    std::ifstream inFile;
    inFile.open ("get_node_user_credential.data");
    if (!inFile) {
        printf("\n\nERROR: get_node_user_credential.data can not be opened\n");
        exit (1);
    }
    std::string root_credential, line;
    while (getline(inFile, line)){
        root_credential = line;
    }
    inFile.close();
    if (root_credential.empty()){
        printf("\n\nERROR: There is some problem reading node root credential\n");
        exit (1);
    }
    cmd = "rm get_node_user_credential.data get_node_user_credential.log";
    system(cmd.c_str());
    return root_credential;
}
CUtilsSsh::CUtilsSsh()
{
	//Initvars
	memset(m_host,0,SSH_HOST_SIZE);
	memset(m_user,0,SSH_USER_SIZE);
	memset(m_password_prompt,0,SSH_PASSWORD_PROMPT_SIZE);
	memset(m_password,0,SSH_PASSWORD_SIZE);
	memset(m_prompt,0,SSH_PROMPT_SIZE);
	memset(m_exit_cmd,0,SSH_EXIT_COMMAND_SIZE);
	m_connected=false;

	//Setting default values.
	setExitCmd(SSH_DEFAULT_EXIT_COMMAND);
	setPasswordPrompt(SSH_DEFAULT_PASSWORD_PROMPT);
	//Default port
	setPort(SSH_DEFAULT_PORT);
	fd=-1;
}

CUtilsSsh::~CUtilsSsh()
{
	//Destroy
        /*
	if (m_connected==true)
		sendCmd(m_exit_cmd);
   */               
        if (fd !=-1)	close(fd);
      
	return;
}
int CUtilsSsh::isready(int fd)
{
    int rc;
    fd_set fds;
    struct timeval tv;

    FD_ZERO(&fds);
    FD_SET(fd,&fds);
    tv.tv_sec =2;
	tv.tv_usec = 0;

    rc = select(fd+1, &fds, NULL, NULL, &tv);

    if (rc < 0)
      return -1;
    return FD_ISSET(fd,&fds) ? 1 : 0;

}
char * CUtilsSsh::getHost()
{
	return (char *)&m_host;
}

bool CUtilsSsh::Connect()
{

	if ((m_host[0]==0)||(m_user[0]==0)||(m_password[0]==0))
	{
		perror("Connection params not initialized.");
		return false;
	}
	return Connect(m_host,m_port,m_user,m_password);
}

bool CUtilsSsh::resetConnection()
{
	m_connected=false;
	return true;
}

bool CUtilsSsh::disConnect()
{
	if(m_connected)
	{
		sendCmd(m_exit_cmd);
		sendCmd(m_exit_cmd);
		m_connected=false;
	}
	return m_connected;
}
int CUtilsSsh::getSshfd()
{
	return fd;
}
bool CUtilsSsh::Connect(const char *host, int port,const char *user, const char *password)
{
	char parmuser[SSH_USER_SIZE];
	char parport[10];
	char buffer[SSH_STD_BUFFER_SIZE];
	//Starts pseudo-terminal and negotiates session.
	sprintf(parmuser,"-l%s",user);
	sprintf(parport,"%d",port);
	if (m_connected)
	{
		//Already connected.
		return true;
	}

	pid = forkpty(&fd, NULL, NULL, NULL);
  	if (pid == -1)
	{
    		perror("forkpty");
    		return false;
	}
	else
	{
		if (pid == 0)
		{
			if (execlp("/usr/bin/ssh",
				   "ssh",
				   "-o UserKnownHostsFile=/dev/null,StrictHostKeyChecking=no",
				   "-p",parport,parmuser,host,(void*)NULL) == -1)
			{
				perror("execlp");
			}
			return false;
		}
	}

	// Set non-blocking
	int flags;
	if ((flags = fcntl(fd, F_GETFL, 0)) == -1)
	{
		flags = 0;
	}
	if (fcntl(fd, F_SETFL, flags | O_NONBLOCK) == -1)
	{
		perror("fcntl");
		return false;
	}
	receiveAll((char *)&buffer,SSH_STD_TIMEOUT);
	if (!strcasestr(buffer,m_password_prompt))
	{
		if (strcasestr(buffer,SSH_KNOWN_SERVER_QUESTION))
		{

			//Send YES
			sendCmd(SSH_KNOWN_SERVER_ANSWER);
			receiveAll((char *)&buffer,SSH_STD_TIMEOUT);

			if (!strcasestr(buffer,m_password_prompt))
			{
				perror("Password prompt error.");
				return false;
			}
			else
			{
				sendCmd(password);
			}
		}
		else
		{
			perror("Cannot continue connecting.");
			return false;
		}
	}
	else
	{
		sendCmd(password);
	}


	//Wait until the prompt comes.
	receiveAll((char *)&buffer,SSH_STD_TIMEOUT);
	if (strcasestr(buffer,m_password_prompt))
	{
		perror("Wrong password provided.");
		return false;
	}

	if(strcmp(user,"root") != 0){
        //Send YES
        sendCmd("su -");
        receiveAll((char *)&buffer,SSH_STD_TIMEOUT);

        if (!strcasestr(buffer,m_password_prompt))
        {
            perror("Password prompt error.");
            return false;
        }
        else
        {
            if (root_credential.empty())   root_credential = get_node_user_credential();
            sendCmd(root_credential.c_str());
        }
	
    }
    //Wait until the prompt comes.
    receiveAll((char *)&buffer,SSH_STD_TIMEOUT);
    if (strcasestr(buffer,m_password_prompt))
    {
        perror("Wrong password provided for 'su -'");
        return false;
    }
	
	//At this point we are connected.
	m_connected=true;
	//The last line doesn't have an eol.
	//That line is the prompt.
	setPrompt(buffer);
	return m_connected;
}
bool CUtilsSsh::isConnected()
{
	return m_connected;
}




void CUtilsSsh::receiveAll(char *buffer,int timeout)
{
	int cent=1;
	while(cent>0)
	{
		cent=recvLine(buffer,timeout);
	}
	if (cent==-2)
	{
		//IO Error. Printing what's left on buffer for more info.
		fprintf(stderr," %s \n",&buffer[1]);
	}

}

bool CUtilsSsh::setHost(char *host)
{
	if (strlen(host)>=SSH_HOST_SIZE)
	{
		//Error. Oversized host name.
		return false;
	}
	else
	{
		strcpy(m_host,host);
		return true;
	}
}


bool CUtilsSsh::setPassword(char *password)
{
	if (strlen(password)>=SSH_PASSWORD_SIZE)
	{
		//Error. Oversized password.
		return false;
	}
	else
	{
		strcpy(m_password,password);
		return true;
	}
}



void CUtilsSsh::setPort(int port)
{
	m_port=port;
}


bool CUtilsSsh::setUser(char *user)
{
	if (strlen(user)>=SSH_USER_SIZE)
	{
		//Error. Oversized user name.
		return false;
	}
	else
	{
		strcpy(m_user,user);
		return true;
	}
}

bool CUtilsSsh::setPasswordPrompt(char *prompt)
{
	if (strlen(prompt)>=SSH_PASSWORD_PROMPT_SIZE)
	{
		//Error. Oversized password prompt size.
		return false;
	}
	else
	{
		strcpy(m_password_prompt,prompt);
		return true;
	}
}


bool CUtilsSsh::setPrompt(char *prompt)
{
	if (strlen(prompt)>=SSH_PROMPT_SIZE)
	{
		//Oversized prompt.
		return false;
	}
	else
	{
		strcpy(m_prompt,prompt);
		return true;
	}
}

bool CUtilsSsh::setExitCmd(char *exitcmd)
{
	if (strlen(exitcmd)>=SSH_EXIT_COMMAND_SIZE)
	{
		//Error. Oversized exit command.
		return false;
	}
	else
	{
		strcpy(m_exit_cmd,exitcmd);
		return true;
	}
}

bool CUtilsSsh::err()
{
	return true;
}

int CUtilsSsh::send_err()
{
	return 0;
}


int CUtilsSsh::sendCmd(char *buff)
{
	char intbuf[SSH_STD_BUFFER_SIZE];

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

int CUtilsSsh::sendCmd(const char *buff)
{
	char intbuf[SSH_STD_BUFFER_SIZE];
        
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

int CUtilsSsh::recvLine(char *buff, int timeout)
{
        int nread=0;
        int count=0;
        int acumnread=0;
	char recv;

	buff[0]=0;

	if(fd==-1)
        {
                //Not connected
                return -1;
        }
        else
        {
		if (isready(fd))
		{
			recv=0;

               	while ((count<timeout) && (acumnread<SSH_STD_BUFFER_SIZE-1) && (recv!='\n'))
                {
                        nread = read(fd, &recv, 1);
                        if (nread == -1)
                        {
                                if (errno == EAGAIN)
                                {
                                        usleep(1000);
                                        count++;
                                }
				else
				{
					return -2;
				}
                        }
                        else
                        {
                                count=0;
				buff[acumnread]=recv;
                                acumnread+=nread;

                        }
                }
		}
        }
        //
	buff[acumnread-1]=0;
	if (count>=timeout)
	{
		return -1;
	}
	else
	{
		return acumnread;
	}
}

