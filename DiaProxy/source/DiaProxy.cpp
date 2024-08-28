//==============================================================================
//#****h* src/DiaProxy.capp
//# MODULE
//#   DiaProxy.capp
//#
//# AUTHOR    
//#   TV 
//#
//# VERSION
//#   2.0
//#   	Ckecked by: -
//#	Aproved by: -
//#
//# DATE
//#   September, 2005
//#
//# DESCRIPTION
//# 	Defines the entry point for the console application.
//#   
//# IMPORTS
//#   
//# REFERENCES
//#	[1]	NONE
//#
//# -----------------------------------------------------------------------------
//# HISTORY
//#   Olov Marklund		   	2005/06/10    Creation
//#   Jose Manuel Santos	   	2005/09/26    Comments added
//#   Jose Manuel Santos		2006/01/10    Adding the support for PNR messages
//#******
//==============================================================================

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <sstream>
#include <fstream>
#include <vector>
#include <map>
#include <errno.h>
#include <time.h>
#include <signal.h>
#include <pthread.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <net/if.h>
#include <stropts.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <unistd.h>
#include <netdb.h>
#include <sys/timeb.h>
#include <fcntl.h>
#include <termios.h>
#include <sys/time.h>

#ifdef __DEBUG_PROXY
#include <mcheck.h>
#include "memwatch.h"

#endif

#include "DiaProxy.h"
#include "AVP.h"
#include "Logger.h"
#include "ProxyThread.h"

using namespace std;

/******************************************************************************************
	Global variables for sharing common values between the different modules
*******************************************************************************************/

//TCP port number where the DiameterProxy will be listening for clients (=PTCs)
int local_port;	

//TCP port number used by the DIAMETER server
int server_port;

//number of retries for establishing the CER-CEA connection
int cercea_retries;

//number of retries for establishing the connection towards the server
int server_conn_retries;

//thread handler for Signalling
pthread_t SignalThreadID;

//thread handler for the ProxyThread
pthread_t ProxyThreadID;

//thread handler for the ListenerThread
pthread_t ListenerThreadID;

//thread handler for the DiaThread
pthread_t DiaThreadID;

//thread handler for the RemoteThreadID
pthread_t RemoteThreadID;

//thread handler for the HearbeatThreadID
pthread_t HearbeatThreadID;

//thread handler for the ReportThreadID
pthread_t ReportThreadID;

//time variables used for controlling inactivity periods
time_t start, stop, lastaction;

//structure where all the configuration data is stored
struct CER_DATA cer_data;

//number used for composing the origin host 
int origin_host_number;

//number used for composing the additional origin host 
int add_origin_host_number;

//configuration file path
char cfg_path[255];

//configuration file name
char cfg_file[100];

//socket handler of the connection towards the DIAMETER server
int diameter_sock;

ListennerStatus listennerState;
DiaProxyStatus diaProxyState;
DiaServerMode diaServerMode;
SignalReason sigReason= NO_REASON;
bool haveToExit = false;
bool couldBeCleaned = false;
vector<DiaServerConnection> v_connections;
vector<ClientConnection> v_client;
vector<Transaction> v_transaction;
map<string, Session> m_session;

vector<clientThread> v_clientThread;

PendingToSendMap  m_pendingToSend;

//variable for defining/handling a mutual exclusion zone
pthread_mutex_t TRANSACTION_VECTOR = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t CONNECTION_VECTOR = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t CLIENT_VECTOR = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t CLIENT_THREAD_VECTOR = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t SESSION_MAP = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t PENDING_MESSAGE_MAP = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t TOOL_STATUS = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t STATISTIC = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t REPORT = PTHREAD_MUTEX_INITIALIZER;


RemoteControl remoteControlData;

unsigned int nextTransaction = 0;
unsigned int nextClient = 0;
unsigned int nextConnection = 0;

int nextClientThread = -1;
unsigned int numberClientThreads = 0;

/******************************************************************************************
	END OF Global variables for sharing common values between the different modules
*******************************************************************************************/

void init_syslog ()
{
	//syslog initialization
	openlog ("DiaProxy", LOG_PID, LOG_USER);
	setlogmask (LOG_UPTO(LOG_NOTICE));
}


void process_parameters (struct CER_DATA *cer_data, char **argv, int argc)
{
	uint lmask = 0;			//logging mask
	int i = 1;
	//processing the parameters
	for(;i<argc;i++){ 

		/*** Option: port of the Diameter Server ***/
		if(strcmp(argv[i],"-p") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -p <port>\n");
				exit(1);
			} 
			server_port = atoi(argv[i]);		 //conversion
			strcpy(cer_data->diameter_port,argv[i]); 
			if(server_port < 1){
				printf("\nWrong usage -p <port>\n");
				exit(1);
			}
		} 

		/*** Option: origin host ***/
		else if(strcmp(argv[i],"-oh") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -oh <origin_host>\n");
				exit(1);
			} 

			int origin_host_length = strlen ((const char*)argv[i]);
			strcpy((char*)cer_data->raw_origin_host,argv[i]);
		} 
		else if(strcmp(argv[i],"-oh_prefix") == 0){
			i++;
			if(argc == i){
				printf("\nWrong usage -oh_prefix <origin_host_prefix>\n");
				exit(1);
			}
			strcpy((char*)cer_data->oh_prefix,argv[i]);
		}

		else if(strcmp(argv[i],"-ism_oh") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -ism_oh <origin_host>\n");
				exit(1);
			} 

			int origin_host_length = strlen ((const char*)argv[i]);
			strcpy((char*)cer_data->ism_raw_origin_host,argv[i]);
		} 

		/*** Option: number of the origin host ***/
		else if(strcmp(argv[i],"-o") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -o <nr>\n");
				exit(1);
			} 

			cer_data->origin_host_number = atoi(argv[i]);  //conversion
			
			//if origin host is a non-valid value
			if(cer_data->origin_host_number < 0){
				printf("\nWrong usage -o <nr>\n");
				exit(1);
			}
			
		} 

		/*** Option: seed for e2e ***/
		else if(strcmp(argv[i],"-e") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -e <nr>\n");
				exit(1);
			} 
	
			cer_data->e2e_seed = atoi(argv[i]);  //conversion
			
			//if origin host is a non-valid value
			if((cer_data->e2e_seed < 0) || (cer_data->e2e_seed >96)){
				printf("\nWrong usage -e <nr>\n");
				exit(1);
			}
			
		} 
                
                
          	/*** Option: add host ***/
		else if(strcmp(argv[i],"-add") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -add <nr>\n");
				exit(1);
			} 

			add_origin_host_number = atoi(argv[i]);  //conversion
			
			//if additional origin host is a non-valid value
			if(add_origin_host_number < 0)	{
				printf("\nWrong usage -add <nr>\n");
				exit(1);
			}

                        cer_data->add_origin_host_flag = true; 	
		} 
		
		else if(strcmp(argv[i],"-buffersize") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -buffersize <size>\n");
				exit(1);
			} 

			int size = atoi(argv[i]);  //conversion
			
			if(size < 0)	{
				printf("\nWrong usage -buffersize <size>\n");
				exit(1);
			}

                        cer_data->socketbuffersize = size; 	
		} 
		/*** Option: localport for listening for clients ***/
		else if(strcmp(argv[i],"-li") == 0){ 
			i++;
			if(argc == i)
			{ 
				printf("\nWrong usage -li <port>\n");
				exit(1);
			} 
			//filling in the data
			cer_data->serv_port = atoi (argv[i]);
			local_port = atoi(argv[i]);
			if(local_port < 1){
				printf("\nWrong usage -li <port>\n");
				exit(1);
			}
		} 
		
		/*** Option: ism port for ism messages ***/
		else if(strcmp(argv[i],"-ism") == 0){ 
			i++;
			if(argc == i)
			{ 
				printf("\nWrong usage -ism <port>\n");
				exit(1);
			} 
			//filling in the data
			cer_data->ism_port = atoi (argv[i]);
			if(cer_data->ism_port < 1){
				printf("\nWrong usage -ism <port>\n");
				exit(1);
			}
		} 
		
		else if(strcmp(argv[i],"-udp") == 0){ 
			i++;
			if(argc == i)
			{ 
				printf("\nWrong usage -udp <port>\n");
				exit(1);
			}
                        int temp =  atoi (argv[i]);
			if(temp < 1){
				printf("\nWrong value for -ism <port>\n");
				exit(1);
			}
                        
			//filling in the data
			remoteControlData.port = temp;
			remoteControlData.status = REMOTE_ENABLED;
		} 
		
		/*** Option: log mask ****/
		else if(strcmp(argv[i],"-lm") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -lm <mask>\n");
				exit(1);
			} 
			lmask = atoi(argv[i]); //conversion to an integer number
			if(lmask > 0){						//if mask is != 0, the logger must be set up
				cer_data->log_mask = lmask;			
				Log::Instance().set_log_mask(cer_data->log_mask);
			}
		} 
		
		/*** Option: address of the Diameter Node ****/
		else if(strcmp(argv[i],"-server") == 0)
		{ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -server <ip>\n");
				exit(1);
			} 
			strcpy(cer_data->diameter_primary_host,argv[i]);
		} 
		
		else if(strcmp(argv[i],"-ism_server") == 0)
		{ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -ism_server <ip>\n");
				exit(1);
			} 
			strcpy(cer_data->ism_diameter_host,argv[i]);
		} 
		
		else if(strcmp(argv[i],"-secondary") == 0)
		{ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -secondary <ip>\n");
				exit(1);
			} 
			strcpy(cer_data->diameter_secondary_host,argv[i]);
			diaServerMode = REDUNDANCY;
		} 
		
		/*** Option: address of the DiaProxy Node ****/
		else if(strcmp(argv[i],"-proxy") == 0) { 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -proxy <ip>\n");
				exit(1);
			} 
			struct hostent *h =gethostbyname(argv[i]);
			sprintf (cer_data->diaproxy_host, "%d.%d.%d.%d",(uchar)h->h_addr[0],(uchar)h->h_addr[1],(uchar)h->h_addr[2],(uchar)h->h_addr[3]);
			ip2oct(cer_data->host_ip_address,cer_data->diaproxy_host);
		} 
		
		else if(strcmp(argv[i],"-f") == 0){ 
			i++;    //already read
				
		} 
	
		else if(strcmp(argv[i],"-nc") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -nc <connections>\n");
				exit(1);
			} 
			//filling in the data
			cer_data->numberOfConnections = atoi (argv[i]);
			if(cer_data->numberOfConnections < 1){
				printf("\nWrong usage -nc <connections>\n");
				exit(1);
			}
		} 
			
		else if(strcmp(argv[i],"-size") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -size <messages>\n");
				exit(1);
			} 
			//filling in the data
			cer_data->max_size_message_queue = atoi (argv[i]);
			if(cer_data->max_size_message_queue < MIN_PENDING_MESSAGES){
				printf("\nWrong usage -size <messages>....Value shall be > %d\n",MIN_PENDING_MESSAGES );
				exit(1);
			}
		} 
			
		else if(strcmp(argv[i],"-reconnect") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -reconnect <time>\n");
				exit(1);
			} 
			//filling in the data
			cer_data->reconnectTime = atoi (argv[i]);
		} 
			
		else if(strcmp(argv[i],"-c") == 0){
			i++;
			if(argc == i){
				printf("\nWrong usage -c <numOfClientsThreads>\n");
				exit(1);
			}
			//filling in the data
			cer_data->maxNumberClientThreads = atoi (argv[i]);
			cer_data->clientsSharingThreads = true;
			if(cer_data->maxNumberClientThreads < 1 || cer_data->maxNumberClientThreads > MAX_CLIENTS_THREADS){
				printf("\nWrong usage -c <connections>\n");
				exit(1);
			}
		}

		else if(strcmp(argv[i],"-r") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -r <max_value>\n");
				exit(1);
			} 
			//filling in the data
                        int tmp = atoi (argv[i]);
                        if ((tmp < 1) || (tmp > MAX_TRANS_SIZE)) {
				printf("\nValue for -r out of range (1 - %d)\n", MAX_TRANS_SIZE);
				exit(1);
			}
                                
			cer_data->numberOfTransactions = tmp;
		} 
			
		else if(strcmp(argv[i],"-hb") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -hb <time(sec)>\n");
				exit(1);
			} 
			//filling in the data
			cer_data->hearbeatTime = atoi (argv[i]);
			if(cer_data->hearbeatTime < 1){
				printf("\nWrong usage -hb <time(sec)>\n");
				exit(1);
			}
		} 
		else if(strcmp(argv[i],"-6") == 0){ 
			//filling in the data
			cer_data->ipv6 = true;
        } 
			
        else if(strcmp(argv[i],"-skip_wd") == 0){ 
            //filling in the data
            cer_data->skip_wd = true;
        } 
            
		else if(strcmp(argv[i],"-t") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -t <tcp/sctp>\n");
				exit(1);
			} 

			if (!strcmp(argv[i], TCP_PROTOCOL) || !strcmp(argv[i], SCTP_PROTOCOL) ){
				strcpy ((char*)cer_data->protocol, argv[i]);
			} else {
				printf("\nWrong usage -t <tcp/sctp>\n");
				exit(1);
			}
		} 
			
		else if(strcmp(argv[i],"-tism") == 0){ 
			i++;
			if(argc == i){ 
				printf("\nWrong usage -tism <tcp/sctp>\n");
				exit(1);
			} 

			if (!strcmp(argv[i], TCP_PROTOCOL) || !strcmp(argv[i], SCTP_PROTOCOL) ){
				strcpy ((char*)cer_data->protocol_ism, argv[i]);
			} else {
				printf("\nWrong usage -tism <tcp/sctp>\n");
				exit(1);
			}
		} 
			
		else {
			printf ("Unknown option. Exiting.\n\n");
			exit (1);
		}

	} //for(i=1;i<argc;i++)
}


void printusage()
{ 
	printf("\nDiaProxy version %s\n\n",PROGRAM_VERSION);
	printf("DiaProxy [options]\n\n");
	printf("-h		      Print command line usage.\n\n");
	printf("-view [file_name]     View settings.\n\n");
	printf("-f <file_name>        Configuration file used during execution\n\n");
    printf("-skip_wd              DO not send WDR to HSS.\n\n");

	printf("-6                    Force the usage of IPv6 from DiaProxy to SUT.\n\n");
    printf("-server <ip>          Specify the IP address of the Diameter server vip.\n\n");
	printf("-secondary <ip>       Specify the IP address of the secondary server vip. Redundancy conf.\n\n");
	printf("-hb <time(sec)>       Specify hearbeat time in seconds for redundancy configuration.\n\n");

	printf("-proxy <ip>	      Specify the IP address of the DiaProxy.\n\n");
	
	printf("-nc <connections>     Number of connections towards Diameter server\n\n");
	printf("-t <tcp/sctp>         Transport protocol for connecting with Diameter server.\n\n");

	printf("-p <port>             Specify the TCP port that the Diameter server is listening on.\n");
	printf("                      The default port is %s\n\n",DEFAULT_HSS_PORT);
	
	printf("-li <port>            Specify the TCP port that DiaProxy will listen on for PTC to connect.\n");
	printf("                      The default port is %d\n\n",DEFAULT_PROXY_PORT);

	printf("-lm <mask>            Set log mask.\n");
	printf("    <mask>            Is retined by summing what to log.\n");
	printf("                      Possible loggings are:\n\n");
	printf("    Log type          Binary Value\n");
	printf("    Errors            0000 0001 (1)\n");
	printf("    Events            0000 0010 (2)\n");
	printf("    Warnings          0000 0100 (4)\n");
	printf("    Info              0000 1000 (8)\n");
	printf("    Connections       0001 0000 (16)\n");
	printf("    Debug             0010 0000 (32)\n");
	printf("    Log all           0011 1111 (63)\n\n");

	printf("-oh <host_name>       Specify the origin host to use for CER.\n");
	printf("-o <nr>               Specify the origin host number to use for CER.\n");
	printf("		      altogether with the origin host specified in the config file .\n");
	printf("                      The default origin host values is:\n");
	printf("                      	'%s' for HSS\n", DEFAULT_ORIGIN_HOST_HSS);
	printf("                      	'%s' for EPC\n\n", DEFAULT_ORIGIN_HOST_EPC);
	printf("-add <nr>             Specify the origin host number to use for CER for additional connection.\n");
	printf("-e <nr>               Specify seed used for e2e creation.\n");
	printf("                      This option is also used for building individual origin host with oh_prefix.\n");
	printf("-r <nr>               Specify the max value number of transactions records.\n");
	printf("-ism_oh <host_name>   Specify the origin host to use for CER for an ISM additional connection on EPC scenario.\n");
	printf("-ism_server <ip>      Specify the IP address of the Diameter server vip for an ISM additional connection on EPC scenario.\n\n");
	printf("-ism <port>           Specify the port to use for an ISM additional connection on EPC scenario.\n");
	printf("-tism <tcp/sctp>      Transport protocol for connecting an ISM additional connection on EPC scenario with Diameter server.\n\n");
	printf("-c <nr>               Specify the max number of threads managing TTCN connections. Default value is 5. Max value 200\n");
	printf("-size <nr>            Specify the max number of messages that can be queued. Value shall be > %d\n",MIN_PENDING_MESSAGES);
	printf("-reconnect <tim(sec)> Waiting time before trying to reconnect with Diameter server. Default values is %d sec.\n",DEFAULT_RECONNECT_TIME);
	printf("-buffersize <size>    Specify the recv/send socket buffer size. Default %d\n",DEFAULT_SOCKETBUFSIZE);
	printf("-udp <port>           Specify the UDP port to use for remote control\n");
	printf("-oh_prefix <prefix>   Specify a prefix to be used for building individual origin host per connection\n");
	printf("                      This option make useless -oh, -o and -ism_oh options\n");
} 


void PrintInfo()
{ 

/****************************************************************************/
/* void PrintInfo()															*/
/* Prints program version and a few things more								*/
/****************************************************************************/

#ifdef _WIN32
#ifdef _DIA_PROXY_DEBUG
	printf("Application name:         %s.exe\n",DEBUG_APP_NAME);
#else
	printf("Application name:         %s.exe\n",APP_NAME);
#endif
#else
#ifdef _DIA_PROXY_DEBUG
	printf("Application name:         %s\n",DEBUG_APP_NAME);
#else
	printf("Application name:         %s\n",APP_NAME);
#endif
#endif
#ifdef _DIA_PROXY_DEBUG
	printf("Application version:      %s\n",DEBUG_VERSION);
#else
	printf("Application version:      %s\n",PROGRAM_VERSION);
#endif
} 


//main program
int main(int argc, char* argv[])
{
	diaProxyState = DIAPROXY_OFF;
	diaServerMode = STAND_ALONE;
	listennerState = LISTENNER_OFF;
	init_syslog();

        sigset_t signal_set;
	
	cercea_retries = 0;		//performed CER-CEA retries <- 0
	server_port = 1812;		//server port <- 1812
	local_port = 1812;		//local port for listening to clients <- 1812
	origin_host_number = -1;
	add_origin_host_number = -1;
	
	memset(&cer_data,0,sizeof(CER_DATA));	//initialization of the configuration data to '\0's

	strcpy ((char*)cer_data.supported_node, DEFAULT_NODE);

	strcpy ((char*)cer_data.raw_origin_host,(const char*)DEFAULT_ORIGIN_HOST_HSS);
	strcpy ((char*)cer_data.ism_raw_origin_host,(const char*)DEFAULT_ORIGIN_HOST_HSS);
	cer_data.origin_host_number = 0;
	
	if (strchr (DEFAULT_ORIGIN_HOST_HSS,'%') != NULL) 
	{
		int origin_host_length = strlen ((const char*)DEFAULT_ORIGIN_HOST_HSS);

 		if(strchr(DEFAULT_ORIGIN_HOST_HSS,'%')!=0){
			sprintf ((char*)cer_data.origin_host,(const char*)DEFAULT_ORIGIN_HOST_HSS,cer_data.origin_host_number);
			sprintf ((char*)cer_data.ism_origin_host,(const char*)DEFAULT_ORIGIN_HOST_HSS,cer_data.origin_host_number);
                }
                else {
			strcpy((char*)cer_data.origin_host,DEFAULT_ORIGIN_HOST_HSS);
			strcpy((char*)cer_data.ism_origin_host,DEFAULT_ORIGIN_HOST_HSS);
                }

		cer_data.origin_host[origin_host_length+1] = 0x00;
		cer_data.ism_origin_host[origin_host_length+1] = 0x00;
	} else 
	{
		strcpy ((char*)cer_data.origin_host,DEFAULT_ORIGIN_HOST_HSS);
		strcpy ((char*)cer_data.ism_origin_host,DEFAULT_ORIGIN_HOST_HSS);
	}

	strcpy((char*)cer_data.add_origin_host,DEFAULT_ORIGIN_HOST_HSS);
	cer_data.add_origin_host_number = 0;
	cer_data.add_origin_host_flag = false;
	cer_data.ipv6 = false;
    cer_data.skip_wd = false;

	strcpy((char*)cer_data.origin_realm,DEFAULT_ORIGIN_REALM);
	int2oct(cer_data.vendor_id,"0");
	strcpy((char*)cer_data.product_name,DEFAULT_PRODUCT_NAME);
	cer_data.log_mask = DEFAULT_LOG_MASK;
	cer_data.inactivity_time = DEFAULT_INACTIVITY_TIME;
	strcpy((char*)cer_data.diameter_port ,DEFAULT_HSS_PORT);
	cer_data.serv_port = DEFAULT_PROXY_PORT;
	strcpy ((char*)cer_data.diameter_host, "");
	strcpy ((char*)cer_data.ism_diameter_host, "");
	strcpy ((char*)cer_data.diameter_primary_host, "");
	strcpy ((char*)cer_data.diameter_secondary_host, "");
	strcpy ((char*)cer_data.diaproxy_host, "");
	cer_data.number_of_supported_vendor_ids = 0;
	cer_data.number_of_auth_application_ids = 0;
	cer_data.number_of_vendor_specific_application_ids = 0;
	cer_data.numberOfConnections = DEFAULT_NUMBER_CONNECTIONS;
	cer_data.numberOfClients = DEFAULT_NUMBER_CLIENTS;
	cer_data.numberOfTransactions = cer_data.numberOfClients * TRANSACTIONPERCLIENT;
	cer_data.monitorTime = DEFAULT_MONITOR_TIME;
	cer_data.use_sctp = 0;
	cer_data.use_sctp_ism = 0;
	strcpy ((char*)cer_data.protocol, DEFAULT_PROTOCOL);
	strcpy ((char*)cer_data.protocol_ism, TCP_PROTOCOL);
	cer_data.maxReconnections = DEFAULT_MAX_RECONNECTION;
	cer_data.ism_port = 0;
        cer_data.e2e_seed = 0;
	cer_data.hearbeatTime = DEFAULT_HEARBEAT_TIME;
	cer_data.maxNumberClientThreads = DEFAULT_CLIENTS_THREADS;
	cer_data.max_size_message_queue = MAX_PENDING_MESSAGES;
	cer_data.clientsSharingThreads = true;
	cer_data.reconnectTime = DEFAULT_RECONNECT_TIME;
        
	cer_data.socketbuffersize = DEFAULT_SOCKETBUFSIZE;
	strcpy ((char*)cer_data.oh_prefix, "");

	cer_data.latency_report_enabled = false;;
	cer_data.latency_report_running = false;;
	cer_data.latency_report_file[100];
        strcpy((char*)cer_data.latency_report_file,"Not configured"); 
              
	cer_data.DiaErrCounters_report_enabled = false;;        
	cer_data.DiaErrCounters_report_running = false;;
	cer_data.DiaErrCounters_report_file[100];
	cer_data.DiaErrCounters_report_timeout = DIAERRCOUNTERS_REPORT_TIMEOUT;
        strcpy((char*)cer_data.DiaErrCounters_report_file,"Not configured"); 

    cer_data.resultcode_request = 0;
	cer_data.resultcode_success = 0;
	cer_data.resultcode_busy = 0;
	cer_data.resultcode_utc = 0;
	cer_data.resultcode_other = 0;



	start = clock();			//moment of starting the execution (= now)
	cfg_path[0] = 0;			//the name of the configuration file is initialized to '\0'
	strcpy(cfg_file,CONFIGURATION_FILE);

        remoteControlData.sock = -1;
        remoteControlData.port = -1;
        remoteControlData.status = REMOTE_DISABLED;

	if(argc == 2)
	{
		//if the 'help' option was specified, print usage
		if(strcmp(argv[1],"-h") == 0)
		{
			printusage();
			return 0;
		}
	}

 	char * home = getenv("HOME");

	if (home == NULL) {
		printf("\n\nERROR: Environment is not properly set: HOME variable not defined\n");
		exit (1);
	}
 
	if (argc >= 2) {
		if(strcmp(argv[1],"-view") == 0){
			if(argc == 3){
				strcpy(cfg_file,argv[2]);
			}
			readConfigFile   (home);                     
 			clear();
			printConfiguration(cfg_file);
			return 0;
		} 
	}
		
	for(int i = 1;i<argc;i++){
		
		if(strcmp(argv[i],"-f") == 0){ 
			i++;
			if(argc == i){ 
				printf("\n\nERROR: Wrong usage -f <file>\n");
				exit(1);
			} 
			strcpy(cfg_file,argv[i]);
		} 

	}

		
    readConfigFile   (home);
	clear (); //clean screen

	//dumping configuration variable to individual variables
	server_port = atoi(cer_data.diameter_port);
	local_port = cer_data.serv_port;
	
	//parameters processing
	process_parameters (&cer_data,argv, argc);

    if (cer_data.ipv6 && diaServerMode == REDUNDANCY) {
        printf("\n\nERROR: IPv6 not supportted for GeoRed scenario\n");
        exit (1);
    }

    if(strchr((const char*)cer_data.raw_origin_host,'%')!=0){
		sprintf ((char*)cer_data.origin_host,(const char*)cer_data.raw_origin_host,cer_data.origin_host_number);
	}
	else {
		strcpy((char*)cer_data.origin_host,(const char*)cer_data.raw_origin_host);
	}

	if(strchr((const char*)cer_data.ism_raw_origin_host,'%')!=0){
		sprintf ((char*)cer_data.ism_origin_host,(const char*)cer_data.ism_raw_origin_host,cer_data.origin_host_number);
	}
	else {
		strcpy((char*)cer_data.ism_origin_host,(const char*)cer_data.ism_raw_origin_host);
	}

        if (cer_data.add_origin_host_flag){
 		if(strchr((const char*)cer_data.raw_origin_host,'%')!=0){
				sprintf ((char*)cer_data.add_origin_host,(const char*)cer_data.raw_origin_host,add_origin_host_number);
		}
                else {
			printf("\n\nERROR: Wrong usage -add <nr>.\n");
			exit(1);
                }
        } 

	if (!strcmp((char*)cer_data.protocol, TCP_PROTOCOL)) {
		cer_data.use_sctp = 0;	
	}
	else if(!strcmp((char*)cer_data.protocol, SCTP_PROTOCOL)) {
		cer_data.use_sctp = 1;
	}
	else {
		printf("\n\nERROR: Invalid Protocol: (%s)\nAllowed value = tcp | sctp\n",cer_data.protocol);
		exit (1);
	}
	
	if (!strcmp((char*)cer_data.protocol_ism, TCP_PROTOCOL)) {
		cer_data.use_sctp_ism = 0;	
	}
	else if(!strcmp((char*)cer_data.protocol_ism, SCTP_PROTOCOL)) {
		cer_data.use_sctp_ism = 1;
	}
	else {
		printf("\n\nERROR: Invalid Protocol: (%s)\nAllowed value = tcp | sctp\n",cer_data.protocol_ism);
		exit (1);
	}

// 	if (cer_data.use_sctp || cer_data.ipv6){

		if (!strcmp((char*)cer_data.diaproxy_host, "")){
			string result;
			string host(cer_data.diameter_primary_host);
			string nic_ip = get_nic_ip_to_dest_host(host);
			strcpy((char*)cer_data.diaproxy_host,(const char*)nic_ip.c_str());
		}

// 	}
// 	else {
// 		char host_name[100];
// 		struct hostent *h =gethostbyname(getlocalhostname(host_name));
// 		sprintf (cer_data.diaproxy_host, "%d.%d.%d.%d",(uchar)h->h_addr[0],(uchar)h->h_addr[1],(uchar)h->h_addr[2],(uchar)h->h_addr[3]);
// 	}

	if (cer_data.ipv6){
		inet_pton(AF_INET6, cer_data.diaproxy_host, &cer_data.localaddr_v6.sin6_addr);
	}
	else {
		ip2oct(cer_data.host_ip_address,cer_data.diaproxy_host);
	}

	string logFile ("DiaProxy");
	string prg(LOG_PRG);
	Log::Instance().ini(logFile, prg);
	Log::Instance().set_log_mask(cer_data.log_mask);
 	Log::Instance().set_log_mode(MIXED_MODE);
        
	stringstream logString;	

	//if ((diaServerMode == STAND_ALONE) &&(!cer_data.ipv6)){
	if (diaServerMode == STAND_ALONE) {
		strcpy(cer_data.diameter_host,cer_data.diameter_primary_host);
	}

	//registering 'atexit' function
	syslog (LOG_NOTICE, "Starting DiaProxy\n");
	syslog (LOG_NOTICE, "Diameter Server:\n");
	syslog (LOG_NOTICE, "Local port = %d, Server Address = %s, Remote port = %s\n", cer_data.serv_port , cer_data.diameter_host, cer_data.diameter_port);
	
	/*** Threads Spawning ***/
	int ret = 0;
	//configuration is printed out for allowing the user to see what data are being used
	printConfiguration(cfg_file);
		
#ifdef _DIA_PROXY_DEBUG
	logString.clear();
	logString.str("");
	logString << "(main): Initialize v_connections" <<endl;
	LOG(DEBUG, logString.str());
#endif

	struct DiaServerConnection initialConnection;
	initialConnection.status = OFF;
	initialConnection.sockId = -1;
	initialConnection.pos = -1;
	initialConnection.threadID = 0;
	initialConnection.conexionRetries = 0;	
	initialConnection.pendingWatchDog = 0;	
	initialConnection.additionalOriginHost = false;
	initialConnection.ismOriginHost = false;
	initialConnection.numberOfClients = 0;
	initialConnection.totalNumberOfClients = 0;
        
	strcpy ((char*)initialConnection.origin_host,(char*)cer_data.origin_host);
                
	if(cer_data.use_sctp!=0)	initialConnection.use_sctp = true;
        else				initialConnection.use_sctp = false;
        
        strcpy((char*)initialConnection.diameter_server,(char*)cer_data.diameter_host);
       	initialConnection.serv_port = server_port;
       	initialConnection.type = GENERIC;
        
       	initialConnection.firstConnectionTry = true;
                
	initialConnection.requestSentToServer = 0;
	initialConnection.requestReceivedFromServer = 0;
	initialConnection.requestSentToClient = 0;
	initialConnection.requestReceivedFromClient = 0;
	initialConnection.requestDiscardFromClient = 0;
	initialConnection.requestDiscardFromServer = 0;

	initialConnection.answerSentToServer = 0;
	initialConnection.answerReceivedFromServer = 0;
	initialConnection.answerSentToClient = 0;
	initialConnection.answerReceivedFromClient = 0;
	initialConnection.answerDiscardFromClient = 0;
	initialConnection.answerDiscardFromServer = 0;
       
	initialConnection.resultCode_Success = 0;
	initialConnection.resultCode_Busy = 0;
	initialConnection.resultCode_UnableToComply = 0;
	initialConnection.resultCode_Other = 0;
	initialConnection.request_Sent = 0;
        

	if (cer_data.ism_port)			cer_data.numberOfConnections++;
	if (cer_data.add_origin_host_flag)	cer_data.numberOfConnections++;

	v_connections.reserve(cer_data.numberOfConnections);
	v_connections.assign(cer_data.numberOfConnections,initialConnection); 
	
	for (unsigned int i = 0; i < v_connections.size(); i++) {
		v_connections[i].pos = i;
	}
        
        unsigned v_index = 0;
	
	if (cer_data.ism_port){
		v_connections[v_index].serv_port = cer_data.ism_port;  
                
		if(cer_data.use_sctp_ism != 0)	v_connections[v_index].use_sctp = true;
        else							v_connections[v_index].use_sctp = false;
                              
		strcpy ((char*)v_connections[v_index].origin_host, (char*)cer_data.ism_origin_host);
                strcpy((char*)v_connections[v_index].diameter_server,(char*)cer_data.ism_diameter_host);
       		v_connections[v_index].type = SPECIFIC;
        	v_index ++;			
    }
        
        v_index ++;			
	if (cer_data.add_origin_host_flag){
		v_connections[v_index].additionalOriginHost = true;
		strcpy ((char*)v_connections[v_index].origin_host,(char*)cer_data.add_origin_host);
	}

	if (strcmp(cer_data.oh_prefix,"") != 0){
		for (unsigned int index = 0; index < v_connections.size(); index++) {
			sprintf ((char*)v_connections[index].origin_host,"%s.%d.%d.ericsson.se",(char*)cer_data.oh_prefix,cer_data.e2e_seed,index);
		}
		unsigned v_index = 0;
		if (cer_data.ism_port){
			sprintf ((char*)v_connections[v_index].origin_host,"%s.ism.%d.%d.ericsson.se",(char*)cer_data.oh_prefix,cer_data.e2e_seed,v_index);
		}
	}

        
#ifdef _DIA_PROXY_DEBUG
	logString.clear();
	logString.str("");
	logString << "(main): Initialize v_client" <<endl;
	LOG(DEBUG, logString.str());
#endif

	struct ClientConnection initialClient;
	
	initialClient.sock = -1;
	initialClient.status = OFFLINE;
	initialClient.waitingAnswer = false;
	initialClient.pos = -1;
	initialClient.diaServerConnection = -1;
	initialClient.clientThreadID = 0;
	initialClient.ismServerConnection = -1;
	initialClient.esmServerConnection = -1;
	initialClient.toreceive = 0;
	initialClient.received = 0;
	
	v_client.reserve(cer_data.numberOfClients);
	v_client.assign(cer_data.numberOfClients,initialClient);
	
#ifdef _DIA_PROXY_DEBUG
	logString.clear();
	logString.str("");
	logString << "(main): Initialize v_transaction" <<endl;
	LOG(DEBUG, logString.str());
#endif

	struct Transaction initialTransaction;
	
	initialTransaction.status = NOTUSED;
	initialTransaction.end2end = -1;
	initialTransaction.answerToDiaServerConnection = -1;
	initialTransaction.hopByHop = -1;
	initialTransaction.client = -1;	
	initialTransaction.recvReqSend = 0;
	initialTransaction.recvAnsSend = 0;
	initialTransaction.reqSent2AnsRecv.tv_sec = 0;
	initialTransaction.reqSent2AnsRecv.tv_usec = 0;
	initialTransaction.request_time.tv_sec = 0;
        
	v_transaction.reserve(cer_data.numberOfTransactions );
	v_transaction.assign(cer_data.numberOfTransactions ,initialTransaction);

#ifdef _DIA_PROXY_DEBUG
	logString.clear();
	logString.str("");
	logString << "(main): v_transaction size is " << v_transaction.size() <<endl;
	LOG(DEBUG, logString.str());
#endif


	struct clientThread InitialClientThread;

	FD_ZERO(&InitialClientThread.fds);
	InitialClientThread.maxFd = -1;
	InitialClientThread.clientThreadID = 0;

	v_clientThread.reserve(MAX_CLIENTS_THREADS);
	v_clientThread.assign(MAX_CLIENTS_THREADS ,InitialClientThread);

	for (unsigned int i = 0; i < v_clientThread.size(); i++) {
		v_clientThread[i].pos = i;
		v_clientThread[i].conectionClients.reserve(DEFAULT_NUMBER_CLIENTS);
	}

        /* block all signals */
        sigfillset( &signal_set );
        pthread_sigmask( SIG_BLOCK, &signal_set,NULL );

#ifdef _DIA_PROXY_DEBUG
	logString.clear();
	logString.str("");
	logString << "(main): Creating Signal Thread" <<endl;
	LOG(DEBUG, logString.str());
#endif
        pthread_create(&SignalThreadID, NULL,handler, NULL );

#ifdef _DIA_PROXY_DEBUG
	logString.clear();
	logString.str("");
	logString << "(main): Creating Proxy Thread" <<endl;
	LOG(DEBUG, logString.str());
#endif
	
	ret = pthread_create(&ProxyThreadID,NULL,_ProxyThread,NULL);

        if (remoteControlData.status == REMOTE_ENABLED) {
 #ifdef _DIA_PROXY_DEBUG
	    logString.clear();
	    logString.str("");
	    logString << "(main): Creating ReportManager Thread" <<endl;
	    LOG(DEBUG, logString.str());
#endif
	    //creation of the ProxyThread (= main thread)
	    ret = pthread_create(&RemoteThreadID,NULL,_RemoteThread,NULL);

#ifdef _DIA_PROXY_DEBUG
	    logString.clear();
	    logString.str("");
	    logString << "(main): Creating ReportManager Thread" <<endl;
	    LOG(DEBUG, logString.str());
#endif
	    //creation of the ProxyThread (= main thread)
	    ret = pthread_create(&ReportThreadID,NULL,_ReportManagerThread,NULL);
        }

	sleep(2); //go to sleep
	//while the thread is still alive, go on..... 
	void *theThreadStatus;
	pthread_join(SignalThreadID,&theThreadStatus);
	return 0;
} //int main(int argc, char* argv[])



void readConfigFile(char * home)
{
	char line [1024]; 
	char *buffer, *chunk, *bigchunk;
	buffer = (char*)malloc (200);
       
	string element, filter;
	bool after;
	ifstream inFile; 
              
	sprintf(cfg_path,"%s/%s/",home,CONFIGURATION_PATH);//composing the path to the configuration

	char myFile[355];
	strcpy(myFile,cfg_path);
	strcat(myFile,cfg_file);
	inFile.open (myFile);
				
	if (!inFile) {
		cout << endl << "WARNING:Failed to open file: " << myFile << endl;
		cout << endl << "Trying to open the default cfg file"<< endl;
		char * path = getenv("ST_TOOL_PATH");

		if (path == NULL) {
			cout << endl << "ERROR: Env variable ST_TOOL_PATH not defined "<< endl << endl;
			exit (1);
		}

		string default_file (path);

		default_file = default_file + "/share/DiaProxy/DiaProxy.cfg";

		inFile.open (default_file.c_str());

		if (!inFile) {
			cout << endl << "ERROR:Failed to open " << default_file << endl << endl;
			exit (1);
		}

		cout << endl << "INFO: Using default cfg " << default_file << endl << endl;

	}
        
	while(inFile) {
		inFile.getline(line, 1024);
		purgeLine(line);

		after = false;  
		filter = "=";
		if (filterLine(line, filter, after, element)) {			
			if (!strcmp(element.c_str(),"program_version")){
			}
 			else if (!strcmp(element.c_str(),"origin_host")){
				after = true;  
				filter = "origin_host=";
				if (filterLine(line, filter, after, element)) {
                                    if (! element.size()) continue;
                                    strcpy(line, element.c_str());
              	                    strcpy ((char*)cer_data.raw_origin_host,(const char*)element.c_str());
              	                    strcpy ((char*)cer_data.ism_raw_origin_host,(const char*)element.c_str());
                                    filter = "%d";
                                    if (filterLine(line, filter, after, element)){
                                        sprintf ((char*)cer_data.origin_host,(const char*)line,cer_data.origin_host_number);
                                        sprintf ((char*)cer_data.ism_origin_host,(const char*)line,cer_data.origin_host_number);
                                    }
                                    else {
                      		        strcpy ((char*)cer_data.origin_host,line);
                      		        strcpy ((char*)cer_data.ism_origin_host,line);
                                    }
				}
			}
    			else if (!strcmp(element.c_str(),"origin_realm")){
				after = true;  
				filter = "origin_realm=";
				if   (filterLine(line, filter, after, element)) {
                                    if (! element.size()) continue;
	                            strcpy ((char*)cer_data.origin_realm,element.c_str());
				}
			}
                        
    			else if (!strcmp(element.c_str(),"product_name")){
				after = true;  
				filter = "product_name=";
				if   (filterLine(line, filter, after, element)) { 
                                    if (! element.size()) continue;
	                            strcpy ((char*)cer_data.product_name,element.c_str());
				}
			}
                        
  			else if (!strcmp(element.c_str(),"vendor_id")){
				after = true;  
				filter = "vendor_id=";
				if   (filterLine(line, filter, after, element)) { 
                                    if (! element.size()) continue;
	                            strcpy ((char*)cer_data.vendor_id,element.c_str());
	                            int2oct (cer_data.vendor_id,(char*)element.c_str());
    				}
			}
                        
			else if (!strcmp(element.c_str(),"Supported_Vendor_ID")){
				after = true;  
				filter = "Supported_Vendor_ID=";
				if   (filterLine(line, filter, after, element)) {
                                    if (! element.size()) continue;
	                            strcpy ((char*)buffer,element.c_str());
                                    bigchunk = buffer;
	                            cer_data.number_of_supported_vendor_ids = 0;
	                            if (bigchunk != NULL) {
	                                chunk = strtok (bigchunk,",");
	                                if (chunk != NULL) {
	                                    cer_data.number_of_supported_vendor_ids = 0;
	                                    cer_data.list_of_supported_vendor_ids[cer_data.number_of_supported_vendor_ids++]  = str2int(chunk);
	                                    do {
	                                        chunk = strtok (NULL,",");	//subsequent calls
	                                        if (chunk != NULL) {
	                                           cer_data.list_of_supported_vendor_ids[cer_data.number_of_supported_vendor_ids++]  = str2int(chunk);
	                                        }
	                                    }while (chunk!=NULL) ;	
	                                }
	                             }
                               }
			  }
                        
			  else if (!strcmp(element.c_str(),"Auth_application_ID")){
				after = true;  
				filter = "Auth_application_ID=";
				if   (filterLine(line, filter, after, element)) { 
                                    if (! element.size()) continue;
	                            strcpy ((char*)buffer,element.c_str());
                                    bigchunk = buffer;
	                            cer_data.number_of_auth_application_ids = 0;

	                            if (bigchunk != NULL) {
		                        chunk = strtok (bigchunk,",");
		                        if (chunk != NULL) {
			                    cer_data.number_of_auth_application_ids = 0;
	       		                    cer_data.list_of_auth_application_ids[cer_data.number_of_auth_application_ids++]  = str2int(chunk);
			                    do {
				                chunk = strtok (NULL,",");	//subsequent calls
				                if (chunk != NULL) {
					            cer_data.list_of_auth_application_ids[cer_data.number_of_auth_application_ids++]  = str2int(chunk);
				                }
			                    }while (chunk!=NULL) ;	
		                        }   
	                            }
                                }
			}
			else if (!strcmp(element.c_str(),"Vendor_Specific_application_ID")){
				after = true;  
				filter = "Vendor_Specific_application_ID=";
				if   (filterLine(line, filter, after, element)) { 
                                    if (! element.size()) continue;
	                            strcpy ((char*)buffer,element.c_str());
                                    bigchunk = buffer;
                                
 	         		    cer_data.number_of_vendor_specific_application_ids = 0;

	         		    if (bigchunk != NULL) {
		         		int index_list=0;

		         		chunk = strtok (bigchunk,"-");
		         		if (chunk != NULL) {
	       		         		cer_data.list_of_vendor_specific_application_ids[index_list++]  = str2int(chunk);
			         		chunk = strtok (NULL,",");	//subsequent calls
			         		if (chunk != NULL) {
				        		 cer_data.list_of_vendor_specific_application_ids[index_list++]  = str2int(chunk);
			         		}
			         		cer_data.number_of_vendor_specific_application_ids++;


			         		do {		
				         		chunk = strtok (NULL,"-");
				         		if (chunk != NULL) {
	       				         		cer_data.list_of_vendor_specific_application_ids[index_list++]  = str2int(chunk);
					         		chunk = strtok (NULL,",");	//subsequent calls
					         		if (chunk != NULL) {
						         		cer_data.list_of_vendor_specific_application_ids[index_list++]  = str2int(chunk);
					         		}
					         		cer_data.number_of_vendor_specific_application_ids++;
				         		}
			         		}while (chunk!=NULL) ;
		         		}
	         		    } 
				}
			}
			else if (!strcmp(element.c_str(),"Diameter_server_ip_address")){
				after = true;  
				filter = "Diameter_server_ip_address=";
				if   (filterLine(line, filter, after, element)) { 
                                    if (! element.size()) continue;
	                            strcpy ((char*)cer_data.diameter_primary_host,element.c_str());
				}
			}
			else if (!strcmp(element.c_str(),"Diameter_server_port")){
				after = true;  
				filter = "Diameter_server_port=";
				if   (filterLine(line, filter, after, element)) { 
                                    if (! element.size()) continue;
	                            strcpy ((char*)cer_data.diameter_port,element.c_str());
				}
			}
			else if (!strcmp(element.c_str(),"Diameter_server_protocol")){
				after = true;  
				filter = "Diameter_server_protocol=";
				if   (filterLine(line, filter, after, element)) { 
                                    if (! element.size()) continue;
	                            strcpy ((char*)cer_data.protocol,element.c_str());
				}
			}
			else if (!strcmp(element.c_str(),"Diameter_server_number_connections")){
				after = true;  
				filter = "Diameter_server_number_connections=";
				if   (filterLine(line, filter, after, element)) { 
                                    if (! element.size()) continue;
           			    cer_data.numberOfConnections = atoi (element.c_str());
				}
			}
			else if (!strcmp(element.c_str(),"DiaProxy_port")){
				after = true;  
				filter = "DiaProxy_port=";
				if   (filterLine(line, filter, after, element)) { 
                                    if (! element.size()) continue;
           			    cer_data.serv_port = atoi (element.c_str());
				}
			}
			else if (!strcmp(element.c_str(),"log_mask")){
				after = true;  
				filter = "log_mask=";
				if   (filterLine(line, filter, after, element)) { 
                                     if (! element.size()) continue;
          			    cer_data.log_mask = atoi (element.c_str());
				}
			}
			else if (!strcmp(element.c_str(),"Monitor_time")){
				after = true;  
				filter = "Monitor_time=";
				if   (filterLine(line, filter, after, element)) { 
                                     if (! element.size()) continue;
          			    cer_data.monitorTime = atoi (element.c_str());
				}
			}
			else if (!strcmp(element.c_str(),"Inactivity_time")){
				after = true;  
				filter = "Inactivity_time=";
				if   (filterLine(line, filter, after, element)) { 
           			    cer_data.inactivity_time = atoi (element.c_str());
                                    if (! element.size()) continue;
				}
			}
			else if (!strcmp(element.c_str(),"Max_reconnections")){
				after = true;  
				filter = "Max_reconnections=";
				if   (filterLine(line, filter, after, element)) { 
                                    if (! element.size()) continue;
           			    cer_data.maxReconnections = atoi (element.c_str());
				}
			}
		}
				
        }

	free (buffer);
	inFile.close();	
        						 
}


void purgeLine(char * line)
{
	char myline[1024];
	strcpy (myline, line);
	int index = 0;
	for (int i = 0; myline[i] != '\0'; i++) {
		if ( myline[i] == '#'){
			line[index] = '\0';
			break;
		} 
		else if ( myline[i] == '\r'){
                        line[index] = '\0';
			break;
		} 
		else if (( myline[i] == '/') && (myline[i+1] == '/')){
			line[index] = '\0';
			break;
		} 
		else if (( myline[i] == ' ') || ( myline[i] == '\t')) {}
		else {
			line[index] = myline[i];
			index++;
		}
	}
	line[index] = '\0';
}


bool filterLine (const char * line, string filter, bool after, string & element)
{
	string  myLine(line);  
	int len;
	string::size_type idx;

	idx = myLine.find(filter);
	if (idx == string::npos) {
		return false;

	}
	
	if (after) {
		myLine.erase(0,idx + filter.size());      
	}
	else {
		len = myLine.size();
		myLine.erase(idx, len );  
	}
	element = myLine;
	return  true;
}



bool printConfiguration(char * cfg_file)
{
	int tmp = 0;
	
	printf("DiaProxy version %s\n\n",PROGRAM_VERSION);
	printf("Your current configuration file:\t%s\n\n",cfg_file);

	printf("CER settings\n");
	printf("------------\n");
	printf("Supported node                  : %s\n",cer_data.supported_node);
	printf("Origin Host                     : %s\n",cer_data.origin_host);
	printf("Origin realm                    : %s\n",cer_data.origin_realm);
	printf("Product name                    : %s\n",cer_data.product_name);

	oct2int(&tmp,(uchar*)cer_data.vendor_id);
	printf("Vendor ID                       : %u\n",tmp);

	if (cer_data.number_of_supported_vendor_ids) {
		int index_list=0;
		printf ("Supported Vendor ID             : %d",cer_data.list_of_supported_vendor_ids[index_list]);
		while (++index_list < cer_data.number_of_supported_vendor_ids) {
			printf (",%d",cer_data.list_of_supported_vendor_ids[index_list]);		
		}
	} else {
		printf("Supported Vendor ID             :");
	
	}
	printf("\n");


	if (cer_data.number_of_auth_application_ids) {
		int index_list=0;
		printf ("Auth application ID             : %d",cer_data.list_of_auth_application_ids[index_list]);
		while (++index_list < cer_data.number_of_auth_application_ids) {
				printf (",%d",cer_data.list_of_auth_application_ids[index_list]);		
		}		
	} else{
		printf("Auth application ID             :");
	}
	printf("\n");


	if (cer_data.number_of_vendor_specific_application_ids) {
		int index_list=0;
		printf ("Vendor Specific application ID  : %d-",cer_data.list_of_vendor_specific_application_ids[index_list]);
		printf ("%d",cer_data.list_of_vendor_specific_application_ids[++index_list]);
		while (index_list < 2 * cer_data.number_of_vendor_specific_application_ids - 1) {
			printf (",%d-",cer_data.list_of_vendor_specific_application_ids[++index_list]);
			printf ("%d",cer_data.list_of_vendor_specific_application_ids[++index_list]);		
		}
	} else {
		printf("Vendor Specific application ID  : ");

	
	}
	printf("\n\n");

	printf("Node settings\n");
	printf("-------------\n");
	printf("Diameter Server IP address      : %s\n",cer_data.diameter_primary_host);
	printf("Number Diameter Server Con.     : %d\n",cer_data.numberOfConnections);
	printf("DiaProxy port                   : %u\n",cer_data.serv_port);
	printf("Log mask                        : 0x%02X (%d)\n",cer_data.log_mask,cer_data.log_mask);
	printf("Monitor time                    : %d\n",cer_data.monitorTime);
	printf("Inactivity time                 : %d\n",cer_data.inactivity_time);
	printf("Max number of connection retries: %d\n\n",cer_data.maxReconnections);
	
    return true;
}


string get_nic_ip_to_dest_host(string host)
{
	string cmd = "ip route get " + host + " 2>get_nic_ip.log |  sed -nr 's/.*src \([^ ]*\).*/\\1/p' 1> get_nic_ip.data";

	if(system(cmd.c_str())!=0){
		printf("\n\nERROR: There is some problem reading nic ip for sctp. Analyze get_nic_ip.log\n");
		printf("\t You can use -proxy parameter to skip this action\n");
		exit (1);
	}

	ifstream inFile;
	inFile.open ("get_nic_ip.data");
	if (!inFile) {
		printf("\n\nERROR: get_nic_ip.data can not be opened\n");
		printf("\t You can use -proxy parameter to skip this action\n");
		exit (1);
	}
    string nic_ip,line;
    while (getline(inFile, line)){
    	nic_ip = line;
    }
    inFile.close();
    if (nic_ip.empty()){
		printf("\n\nERROR: There is some problem reading nic ip for sctp\n");
		printf("\t You can use -proxy parameter to skip this action\n");
		exit (1);
    }
    cmd = "rm get_nic_ip.data get_nic_ip.log";
    system(cmd.c_str());
	return nic_ip;
}


