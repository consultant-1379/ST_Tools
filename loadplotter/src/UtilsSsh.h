// UtilsSsh.h
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
//! \file UtilsSsh.h
//! \brief defines UtilsSsh class
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
#include <string.h>
#include <iostream>
#include <fstream>

#ifndef UTILSSSH_H
#define UTILSSSH_H

#define SSH_HOST_SIZE			100
#define SSH_USER_SIZE			100
#define SSH_PASSWORD_PROMPT_SIZE	100
#define SSH_PASSWORD_SIZE		100
#define SSH_PROMPT_SIZE			100
#define SSH_EXIT_COMMAND_SIZE		100
#define SSH_STD_BUFFER_SIZE		1000

#define SSH_DEFAULT_PORT		22
#define SSH_DEFAULT_EXIT_COMMAND	"exit"
//Password prompt. Case is ignored.
#define SSH_DEFAULT_PASSWORD_PROMPT	"Password:"
#define SSH_KNOWN_SERVER_QUESTION	"(yes/no)"
#define SSH_KNOWN_SERVER_ANSWER		"yes"

#define SSH_STD_TIMEOUT			1000
std::string get_node_user_credential();

class CUtilsSsh
{
public:
	int recvLine(char *buff, int len);
	int sendCmd(char *buff);
	int sendCmd(const char *buff);
	bool setHost(char *host);
	void setPort(int port);
	bool setUser(char *user);
	bool setPassword(char *password);
	bool setPasswordPrompt(char *prompt);
	bool setPrompt(char *prompt);
	bool setExitCmd(char *exitcmd);
	bool Connect();
	bool disConnect();
	bool resetConnection();
	bool Connect(const char *host, int port,const char *user, const char *password);
	int negotiate(int len, unsigned char *inbuff, unsigned char *outbuff, bool *done);
	int getSshfd();
	bool isConnected();
	char *getHost();
	void receiveAll(char *buffer,int timeout);
	int isready(int fd);
	CUtilsSsh();
	virtual ~CUtilsSsh();
private:
	bool err();
	int send_err();
	char m_host[100];
	int m_port;
	char m_user[SSH_USER_SIZE];
	char m_password_prompt[SSH_PASSWORD_PROMPT_SIZE];
	char m_password[SSH_PASSWORD_SIZE];

	char m_prompt[SSH_PROMPT_SIZE];
	char m_exit_cmd[SSH_EXIT_COMMAND_SIZE];
	struct timeval m_recv_timeout;
	int m_recv_retries;
	int fd;
	pid_t pid;
	bool m_connected;


};

#endif
