// Telnet.h: interface for the CTelnet class.
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
//! \file Telnet.h
//! \brief Declares the class CTelnet used by loadlogger
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
#ifndef TELNET_H
#define TELNET_H


#ifdef _WIN32
#include <winsock2.h>
#else
#include <sys/socket.h>
#include <netinet/in.h>
#endif

#include <string>
#include <vector>
#include <memory>

using namespace std;

#ifndef _WIN32
#define INVALID_SOCKET -1
#define SOCKET int
#define closesocket close
#ifndef INADDR_NONE
#define INADDR_NONE in_addr_t - 1
#endif
#define Sleep sleep
#else
#define in_addr_t unsigned long
#endif

/**
 * \defgroup TelnetConstMacroDefs Telnet constants
 */

//! \addtogroup TelnetConstMacroDefs
//! @{
#define T_ECHO					0x01
#define T_SUPPRESS_GO_AHEAD     0x03
#define T_TIMING_MARK			0x06
#define T_TERMINAL_TYPE			0x18
#define T_TERMINAL_SPEED		0x20
#define T_X_DISPLAY_LOCATION	0x23
#define T_NEW_ENVIROMENT_OPTION	0x27
#define T_WINDOW_SIZE			0x1f
#define T_EXOPL					0xff

#define T_SE                  240    //End of subnegotiation parameters.
#define T_NOP                 241    //No operation.
#define T_DATA_MARK           242    //The data stream portion of a Synch.
                                   //This should always be accompanied
                                   //by a TCP Urgent notification.
#define T_BREAK               243    //NVT character BRK.
#define T_INTERRUPT_PROCESS   244    //The function IP.
#define T_ABORT_OUTPUT        245    //The function AO.
#define T_ARE_YOU_THERE       246    //The function AYT.
#define T_ERASE_CHARACTER     247    //The function EC.
#define T_ERASE_LINE          248    //The function EL.
#define T_GO_AHEAD            249    //The GA signal.
#define T_SB                  250    //Indicates that what follows is
                                   //subnegotiation of the indicated
                                   //option.


#define T_WILL 251 //(option code) Indicates the desire to begin
                   //              performing, or confirmation that
                   //              you are now performing, the
                   //              indicated option.

#define T_WONT 252 //(option code) Indicates the refusal to perform,
                   //              or continue performing, the
                   //              indicated option.

#define T_DO 253 //(option code)   Indicates the request that the
             //                    other party perform, or
             //                    confirmation that you are expecting
             //                    the other party to perform, the
             //                    indicated option.

#define T_DONT 254 //(option code) Indicates the demand that the
               //                  other party stop performing,
               //                  or confirmation that you are no
               //                  longer expecting the other party
               //                  to perform, the indicated option.

#define T_IAC  255 //              Data Byte 255.
//! @}

//! See also http://www.scit.wlv.ac.uk/~jphb/comms/telnet.html
typedef enum
{
	//! End of subnegotiation parameters.
	t_se					= T_SE,
	//! No operation.
	t_nop					= T_NOP,
	//! The data stream portion of a Synch.
	t_data_mark				= T_DATA_MARK,
    //! NVT character BRK.
	t_break					= T_BREAK,  
	//! The function IP.
	t_interrupt_process		= T_INTERRUPT_PROCESS, 
	//! The function AO.
	t_abort_output			= T_ABORT_OUTPUT, 
	//! The function AYT
	t_are_you_there			= T_ARE_YOU_THERE,  
	//! The function EC..
	t_erase_character		= T_ERASE_CHARACTER, 
	//! The function EL.
	t_erase_line			= T_ERASE_LINE,   
	//! The GA signal.
	t_go_ahead				= T_GO_AHEAD,    
	//! Indicates that subnegotiation of the indicated option follows.
	t_sb					= T_SB,    
	t_will					= T_WILL,
	t_wont					= T_WONT,
	t_do					= T_DO,
	t_dont					= T_DONT,
	//! Interpret as command
	t_iac					= T_IAC
}TelnetCmdEnum;

//! See also http://www.scit.wlv.ac.uk/~jphb/comms/telnet.html
typedef enum
{
	//! http://community.roxen.com/developers/idocs/rfc/rfc857.html
	t_echo					= T_ECHO,
	//! http://community.roxen.com/developers/idocs/rfc/rfc858.html
	t_suppress_go_ahead		= T_SUPPRESS_GO_AHEAD,
	//! http://community.roxen.com/developers/idocs/rfc/rfc860.html
	t_timing_mark			= T_TIMING_MARK,
	//! http://community.roxen.com/developers/idocs/rfc/rfc1091.html
	t_terminal_type			= T_TERMINAL_TYPE,
	//! http://community.roxen.com/developers/idocs/rfc/rfc1079.html
	t_terminal_speed		= T_TERMINAL_SPEED,
	//! http://community.roxen.com/developers/idocs/rfc/rfc1096.html
	t_x_display_location	= T_X_DISPLAY_LOCATION,
	//! http://community.roxen.com/developers/idocs/rfc/rfc1572.html
	t_new_enviroment_option	= T_NEW_ENVIROMENT_OPTION,
	//! http://community.roxen.com/developers/idocs/rfc/rfc1073.html
	t_window_size			= T_WINDOW_SIZE,
	//! http://community.roxen.com/developers/idocs/rfc/rfc861.html
	t_exopl					= T_EXOPL
}TelnetNegoCmdEnum;

//! \brief Structure for telnet session options
typedef struct
{
	//! The host will echo
	bool host_will_echo;
	//! Client must echo
	bool do_echo;
	//! The host will suppress go ahead
	bool host_will_sgh;
	//! Client will suppress go ahead
	bool do_sgh;
}TELNET_OPTIONS;

//! \brief Declares the class CTelnet
//!
//! The class interfaces a telnet functionality
class CTelnet  
{
public:
	static void shut_down();
	//! \brief Constructor
	CTelnet();
	//! \brief Destructor
	virtual ~CTelnet();

	bool get_line(string& theLines, string& theLine);

	void split_into_lines(char* theLine, int theLength, vector<string>& theLines);

	void split_into_lines(string& theLine, vector<string>& theLines);

	//! \brief Removes the received prompt from the end of the line
	//! \arg INOUT theLine - the line to remove the prompt from
	//!      INOUT theLength - Search to max length
	//! \return Returns true if the prompt has been found and removed
	//!         otherwise false
	bool remove_prompt(char* theLine, int& theLength);

	//! \brief Receive the answer from the host
	//! \arg OUT theAnswer - the answer from the host
	//! \return Returns 0 on success otherwise -1
	int recv_answer(vector<string>& theAnswer);

	//! \brief Send a command to the host
	//! \arg IN theCmd - the command in plain test to send
	//! \return Returns the number of bytes sent if successful otherwise -1
	int send_cmd(string theCmd);

	//! \brief Sends linefeed to the host
	//! \return Returns -1 on error otherwize 0
	int send_lf();

	int send_lf1();
	//! \brief Set the telnet host name or IP address
	//! \arg IN host - the host name or IP address
	void setHost(string host);

	//! \brief Set the telnet port of the host
	//! \arg IN port - the port number
	void setPort(int port);

	//! \brief Set the password prompt to expect for login
	//! \arg IN prompt - the password prompt
	void setPasswordPrompt(string prompt);

	//! \brief Set the name of the user to login
	//! \arg IN login - the name of the user to login 
	void setLogin(string login);
	//! \brief Set the login password for the user \see setLogin
	//! \arg IN pwd - the password for the user

	void setLoginPassword(string pwd);
	//! \brief Set the login prompt to expect
	//! \arg IN prompt - the login prompt
	void setLoginPrompt(string prompt);
	//! \brief Set the idle prompt to expect
	//! \arg IN prompt - the idle prompt
	void setPrompt(string prompt);

	//! \brief Set the exit command for logout
	//! \arg IN exitcmd - the exit command
	void setExitCmd(string exitcmd);

	//! \brief Connect using the current configuration
	//! \return returns 0 on success otherwise -1
	int Connect();

	//! \brief Connect to telnet host
	//! \arg IN host - the host name or IP address
	//!      IN port - the telnet port of the host
	//! \return returns 0 on success otherwise -1
	int Connect(string host, int port);

	//! \brief Called on Connect failed
	virtual void OnConnectFailed(string theMsg) = 0;

	//! \brief Called on unrecoverable error
	virtual void OnError(string theError) = 0;

	//! \brief Called on events
	virtual void OnEvent(string theEvent) = 0;

	//! \brief Called with verbose information
	virtual void OnInfo(string theInfo) = 0;

	//! \brief Used to capture CTRL+C
//	static bool abort_requested;
private:
	int read_echo(string theCmd);
	//! \brief Negotiate telnet session settings
	//! \arg IN len - length of negotiation options
	//!      IN inbuff - the negotiation options
	//!      INOUT outbuff - sending buffer
	//!      OUT done - indicate if negotiation options have been constructed
	//! \return Returns the length of the negotiation constructed options
	int negotiate(int& len, unsigned char** inbuff, unsigned char *outbuff, bool& done);
	//! \brief Resolves host names
	//! \arg OUT where - will contain the host IP address on successful resolve
	//!      IN hostname - the name or IP address to resolve
	void get_hostip(struct in_addr *where, string hostname);
	//! \brief Set the window size of the telnet session
	//! \arg IN size - the window size
	void setWindowSize(unsigned char *size);
	//! \brief Get the window size of the telnet session
	//! \arg OUT buff - the window size
	void getWindowSize(unsigned char *buff);
	//! \brief Closes the socket and reports a sending or receiving error
	//! \arg IN theRes - the result for sending or receiving operation
	//| \return Returns always -1
	int err(int theRes);
	//! Holds the options for the telnet session \see TELNET_OPTIONS
	TELNET_OPTIONS options;
	//! Holds the window width of the telnet session
	short m_window_width;
	//! Holds the window height of the telnet session
	short m_window_height;
	//! Used for communication
	sockaddr_in remote_addr;
	//! Holds the telnet host name or IP address
	string m_host;
	//! Holds the telnet host port number
	int m_port;
	//! Holds the login prompt to expect
	string m_login_prompt;
	//! Holds the login user name
	string m_login;
	//! Holds the password prompt to expect
	string m_password_prompt;
	//! Holds the password for the login user
	string m_pwd;
	//! Holds the idle prompt to expect
	string m_prompt;
	//! Holds the exit command for logout
	string m_exit_cmd;

	//! Used for receive timeouts
	struct timeval m_recv_timeout;

	//! Counter for receive retries
	int m_recv_retries;


	//! The socket for communication
	static SOCKET sock;

	//! Defines the size of the buffer (0x300000 = 3MB)
	const unsigned int MaxBufSizeC;

	//! Defined the number of receive retries (5)
	const unsigned int MaxRecvRetriesC;

	char lineFeedC[2];


	//! Buffer for receiving from host
	auto_ptr<char> m_buf;

};

#endif
