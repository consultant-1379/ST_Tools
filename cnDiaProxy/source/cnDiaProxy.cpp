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

#include "cnDiaProxy.h"
#include "AVP.h"
#include "ProxyThread.h"

#include <libconfig.h++>
#include <iomanip>
#include <cstdlib>

using namespace std;
using namespace libconfig;

/******************************************************************************************
	Global variables for sharing common values between the different modules
*******************************************************************************************/
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

//thread handler for the ReportThreadID
pthread_t ReportThreadID;

//time variables used for controlling inactivity periods
time_t start, stop, lastaction;

//structure where all the configuration data is stored
applicationData dataTool;

//socket handler of the connection towards the DIAMETER server
int diameter_sock;

ListennerStatus listennerState;
DiaProxyStatus diaProxyState;
SignalReason sigReason= NO_REASON;
bool haveToExit = false;
bool couldBeCleaned = false;
vector<DiaServerConnection> v_connections;
vector<ClientConnection> v_client;
vector<Transaction> v_transaction;
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
    openlog ("cnDiaProxy", LOG_PID, LOG_USER);
    setlogmask (LOG_UPTO(LOG_NOTICE));
}


void process_parameters (struct applicationData *dataTool, char **argv, int argc)
{
    //processing the parameters
    for(int i = 1;i<argc;i++){ 
        if(strcmp(argv[i],"-oh_prefix") == 0){
            i++;
            if(argc == i){
                printf("\nWrong usage -oh_prefix <origin_host_prefix>\n");
                exit(1);
            }
            strcpy((char*)dataTool->oh_prefix,argv[i]);
        }
        else if(strcmp(argv[i],"-e") == 0){ 
            i++;
            if(argc == i){ 
                printf("\nWrong usage -e <nr>\n");
                exit(1);
            } 
            dataTool->e2e_seed = atoi(argv[i]);  //conversion
            if((dataTool->e2e_seed < 0) || (dataTool->e2e_seed >96)){
                printf("\nWrong usage -e <nr>\n");
                exit(1);
            }
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
            dataTool->socketbuffersize = size; 	
        } 
        else if(strcmp(argv[i],"-li") == 0){ 
            i++;
            if(argc == i)
            { 
                printf("\nWrong usage -li <port>\n");
                exit(1);
            } 
            dataTool->local_port = atoi (argv[i]);
            if(dataTool->local_port < 1){
                printf("\nWrong usage -li <port>\n");
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
            remoteControlData.port = temp;
            remoteControlData.status = REMOTE_ENABLED;
        } 
        else if(strcmp(argv[i],"-lm") == 0){ 
            i++;
            if(argc == i){ 
                printf("\nWrong usage -lm <mask>\n");
                exit(1);
            } 
            int lmask = atoi(argv[i]); 
            if(lmask > 0) {
                dataTool->log_mask = lmask;
                Log::Instance().set_log_mask(dataTool->log_mask);
            }
        } 
        else if(strcmp(argv[i],"-f") == 0){ 
            i++;
        } 
        else if(strcmp(argv[i],"-size") == 0){ 
            i++;
            if(argc == i){ 
                printf("\nWrong usage -size <messages>\n");
                exit(1);
            } 
            dataTool->max_size_message_queue = atoi (argv[i]);
            if(dataTool->max_size_message_queue < MIN_PENDING_MESSAGES){
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
            dataTool->reconnectTime = atoi (argv[i]);
        } 
        else if(strcmp(argv[i],"-c") == 0){
            i++;
            if(argc == i){
                printf("\nWrong usage -c <numOfClientsThreads>\n");
                exit(1);
            }
            dataTool->maxNumberClientThreads = atoi (argv[i]);
            dataTool->clientsSharingThreads = true;
            if(dataTool->maxNumberClientThreads < 1 || dataTool->maxNumberClientThreads > MAX_CLIENTS_THREADS){
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
            int tmp = atoi (argv[i]);
            if ((tmp < 1) || (tmp > MAX_TRANS_SIZE)) {
                printf("\nValue for -r out of range (1 - %d)\n", MAX_TRANS_SIZE);
                exit(1);
            }
            dataTool->numberOfTransactions = tmp;
        } 
        else if(strcmp(argv[i],"-skip_wd") == 0){ 
            //filling in the data
            dataTool->skip_wd = true;
        } 
        else {
            printf ("Unknown option. Exiting.\n\n");
            exit (1);
        }
    }
}

void printusage()
{ 
    printf("cnDiaProxy [options]\n\n");
    printf("-h                    Print command line usage.\n\n");
    printf("-view [file_name]     View settings.\n\n");
    printf("-f <file_name>        Full path of Server connection configuration file\n");
    printf("                      The default file is $HOME/%s/%s\n\n",CONFIGURATION_PATH,CONFIGURATION_FILE);

    printf("-oh_prefix <prefix>   Specify a prefix to be used for building individual origin host per connection\n");
    printf("                      The default oh_prefix is %s\n\n",DEFAULT_OH_PREFIX);

    printf("-li <port>            Specify the TCP port that cnDiaProxy will listen on for PTC to connect.\n");
    printf("                      The default port is %d\n\n",DEFAULT_PROXY_PORT);

    printf("-udp <port>           Specify the UDP port to use for remote control\n\n");
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

    printf("-e <nr>               Specify seed used for e2e creation.\n");
    printf("                      This option is also used for building individual origin host with oh_prefix.\n\n");

    printf("-r <nr>               Specify the max value number of transactions records.\n\n");
    printf("-c <nr>               Specify the max number of threads managing TTCN connections. Default value is 5. Max value 200\n\n");
    printf("-size <nr>            Specify the max number of messages that can be queued. Value shall be > %d\n\n",MIN_PENDING_MESSAGES);
    printf("-reconnect <tim(sec)> Waiting time before trying to reconnect with Diameter server. Default values is %d sec.\n\n",DEFAULT_RECONNECT_TIME);
    printf("-buffersize <size>    Specify the recv/send socket buffer size. Default %d\n\n",DEFAULT_SOCKETBUFSIZE);
    printf("-skip_wd              DO not send WDR to HSS.\n\n");
} 


//main program
int main(int argc, char* argv[])
{

    diaProxyState = DIAPROXY_OFF;
    listennerState = LISTENNER_OFF;
    init_syslog();
    sigset_t signal_set;

    memset(&dataTool,0,sizeof(applicationData));	//initialization of the configuration data to '\0's

    dataTool.numberOfConnections = 0;
    dataTool.skip_wd = false;
    dataTool.local_port = DEFAULT_PROXY_PORT;
    dataTool.log_mask = DEFAULT_LOG_MASK;
    dataTool.numberOfClients = DEFAULT_NUMBER_CLIENTS;
    dataTool.numberOfTransactions = dataTool.numberOfClients * TRANSACTIONPERCLIENT;
    dataTool.maxReconnections = DEFAULT_MAX_RECONNECTION;
    dataTool.e2e_seed = 0;
    dataTool.maxNumberClientThreads = DEFAULT_CLIENTS_THREADS;
    dataTool.max_size_message_queue = MAX_PENDING_MESSAGES;
    dataTool.clientsSharingThreads = true;
    dataTool.reconnectTime = DEFAULT_RECONNECT_TIME;

    dataTool.socketbuffersize = DEFAULT_SOCKETBUFSIZE;
    strcpy ((char*)dataTool.oh_prefix, DEFAULT_OH_PREFIX);
    dataTool.activeTTCNConnections = 0;
    
    dataTool.latency_report_enabled = false;
    dataTool.latency_report_running = false;
    dataTool.latency_report_file[100];
    strcpy((char*)dataTool.latency_report_file,"Not configured"); 

    dataTool.DiaErrCounters_report_enabled = false;
    dataTool.DiaErrCounters_report_running = false;
    dataTool.DiaErrCounters_report_file[100];
    dataTool.DiaErrCounters_report_timeout = DIAERRCOUNTERS_REPORT_TIMEOUT;
    strcpy((char*)dataTool.DiaErrCounters_report_file,"Not configured"); 

    dataTool.resultcode_request = 0;
    dataTool.resultcode_success = 0;
    dataTool.resultcode_busy = 0;
    dataTool.resultcode_utc = 0;
    dataTool.resultcode_other = 0;

    start = clock();			//moment of starting the execution (= now)

    remoteControlData.sock = -1;
    remoteControlData.port = -1;
    remoteControlData.status = REMOTE_DISABLED;

    if(argc == 2) {
        //if the 'help' option was specified, print usage
        if(strcmp(argv[1],"-h") == 0) {
            printusage();
            return 0;
        }
    }

    char * home = getenv("HOME");

    if (home == NULL) {
        printf("\n\nERROR: Environment is not properly set: HOME variable not defined\n");
        exit (1);
    }
    string cfg_file(home);
    cfg_file += "/" + string(CONFIGURATION_PATH )+ "/" + string(CONFIGURATION_FILE);
    if (argc >= 2) {
        if(strcmp(argv[1],"-view") == 0){
            if(argc == 3){
                cfg_file = string(argv[2]);
            }
            readConfigFile(cfg_file);
            clear();
            printConfiguration();
            return 0;
        } 
    }
    for(int i = 1;i<argc;i++) {
        if(strcmp(argv[i],"-f") == 0){ 
            i++;
            if(argc == i){ 
                printf("\n\nERROR: Wrong usage -f <file>\n");
                exit(1);
            } 
            cfg_file = string(argv[i]);
        } 
    }

    readConfigFile   (cfg_file);
    clear (); //clean screen

    //parameters processing
    process_parameters (&dataTool,argv, argc);


    string logFile ("cnDiaProxy");
    string prg(LOG_PRG);
    Log::Instance().ini(logFile, prg);
    Log::Instance().set_log_mask(dataTool.log_mask);
    Log::Instance().set_log_mode(MIXED_MODE);

    stringstream logString;	

    /*** Threads Spawning ***/
    //configuration is printed out for allowing the user to see what data are being used
    printConfiguration();

#ifdef _DIA_PROXY_DEBUG
    logString.clear();
    logString.str("");
    logString << "(main): Initialize v_connections" <<endl;
    LOG(DEBUG, logString.str());
#endif



#ifdef _DIA_PROXY_DEBUG
    logString.clear();
    logString.str("");
    logString << "(main): Initialize v_client" <<endl;
    LOG(DEBUG, logString.str());
#endif

    struct ClientConnection initialClient;

    initialClient.net_con = NULL;
    initialClient.sock = -1;
    initialClient.fd_index = -1;
    initialClient.status = OFFLINE;
    initialClient.waitingAnswer = false;
    initialClient.pos = -1;
    initialClient.diaServerConnection = -1;
    initialClient.clientThreadID = 0;
    initialClient.toreceive = 0;
    initialClient.received = 0;

    v_client.reserve(dataTool.numberOfClients);
    v_client.assign(dataTool.numberOfClients,initialClient);

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

    v_transaction.reserve(dataTool.numberOfTransactions );
    v_transaction.assign(dataTool.numberOfTransactions ,initialTransaction);

#ifdef _DIA_PROXY_DEBUG
    logString.clear();
    logString.str("");
    logString << "(main): v_transaction size is " << v_transaction.size() <<endl;
    LOG(DEBUG, logString.str());
#endif


    struct clientThread InitialClientThread;

    InitialClientThread.nfds = 0;
    InitialClientThread.clientThreadID = 0;

    v_clientThread.reserve(MAX_CLIENTS_THREADS);
    v_clientThread.assign(MAX_CLIENTS_THREADS ,InitialClientThread);

    for (unsigned int i = 0; i < v_clientThread.size(); i++) {
        v_clientThread[i].pos = i;
        v_clientThread[i].conectionClients.reserve(DEFAULT_NUMBER_CLIENTS);
    }

  /* Initialize openssl */
    SSL_library_init();
    OpenSSL_add_all_algorithms();  /* load & register all cryptos, etc. */
    SSL_load_error_strings();   /* load all error messages */

    if (!rand_initialize()) {
        cout << "Error in rand_initialize" << endl;
        exit(0);
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

    pthread_create(&ProxyThreadID,NULL,_ProxyThread,NULL);

    if (remoteControlData.status == REMOTE_ENABLED) {
 #ifdef _DIA_PROXY_DEBUG
        logString.clear();
        logString.str("");
        logString << "(main): Creating Remote Thread" <<endl;
        LOG(DEBUG, logString.str());
#endif
        //creation of the ProxyThread (= main thread)
        pthread_create(&RemoteThreadID,NULL,_RemoteThread,NULL);

#ifdef _DIA_PROXY_DEBUG
        logString.clear();
        logString.str("");
        logString << "(main): Creating ReportManager Thread" <<endl;
        LOG(DEBUG, logString.str());
#endif
        //creation of the ProxyThread (= main thread)
        pthread_create(&ReportThreadID,NULL,_ReportManagerThread,NULL);
    }

    sleep(2); //go to sleep
    //while the thread is still alive, go on..... 
    void *theThreadStatus;
    pthread_join(SignalThreadID,&theThreadStatus);
    return 0;
} //int main(int argc, char* argv[])

struct DiaServerConnection newDiaCon()
{

    struct DiaServerConnection initialConnection;
    initialConnection.status = OFF;
    initialConnection.pos = -1;
    initialConnection.threadID = 0;
    initialConnection.conexionRetries = 0;  
    initialConnection.pendingWatchDog = 0;  

    initialConnection.firstConnectionTry = true;

    initialConnection.requestSentToServer = 0;
    initialConnection.requestReceivedFromClient = 0;
    initialConnection.requestDiscardFromClient = 0;

    initialConnection.answerReceivedFromServer = 0;
    initialConnection.answerSentToClient = 0;
    initialConnection.answerDiscardFromServer = 0;

    initialConnection.resultCode_Success = 0;
    initialConnection.resultCode_Busy = 0;
    initialConnection.resultCode_UnableToComply = 0;
    initialConnection.resultCode_Other = 0;
    initialConnection.request_Sent = 0;

    initialConnection.use_sctp = false;
    initialConnection.ssl_protocol = "";
    initialConnection.use_ssl = false;
    initialConnection.ipv6 = false;
    strcpy((char*)initialConnection.origin_realm,DEFAULT_ORIGIN_REALM);

    initialConnection.pos = v_connections.size();

    return initialConnection;
}
inline bool file_exists (const std::string& name) {
    ifstream f(name.c_str());
    return f.good();
}
void readConfigFile(string cfg_file)
{
    char myFile[355];

    if (file_exists(cfg_file)){
        strcpy(myFile,cfg_file.c_str());
    }
    else {
        cout << endl << "ERROR:Failed to open " << cfg_file << endl << endl;
        exit (1);
    }
    
    Config cfg;
    // Read the file. If there is an error, report it and exit.
    cout << endl << "Configuration file:\t"<<myFile<<endl<< endl;
    try {
        cfg.readFile(myFile);
    }
    catch(const FileIOException &fioex) {
        cout << endl << "ERROR: I/O error while reading file " << myFile << endl;
        exit (1);
    }
    catch(const ParseException &pex){
        cout << endl << "ERROR: Parse error at " << pex.getFile() << ":" << pex.getLine()
                << " - " << pex.getError() << endl;
        exit (1);
    }


    bool found = false;
    try {
        const Setting& root = cfg.getRoot();
        const Setting &toolConfig = root["ToolConfig"];

        // Get the logMask.
        try{
            toolConfig.lookupValue("logMask",dataTool.log_mask);
#ifdef _DIA_PROXY_DEBUG
            cout << "Store logMask: " << dataTool.log_mask << endl;
#endif
        }
        catch(const SettingNotFoundException &nfex){
#ifdef _DIA_PROXY_DEBUG
            cout << "No 'logMask' setting in configuration file." << endl;
#endif
        }
    
   
        // Get the client_cert_file.
        try{
            found = toolConfig.lookupValue("cert_file",dataTool.cert_file);
            if (!found){
                cout << "ERROR: Mandatory 'cert_file' not found." << endl;
                exit (1);
            }
#ifdef _DIA_PROXY_DEBUG
            cout << "Store client_cert_file: " << dataTool.cert_file << endl;
#endif
         }
        catch(const SettingNotFoundException &nfex){
            cout << "ERROR: Mandatory 'cert_file' not found" << endl;
            exit (1);
        }
    
 
        // Get the client_key_file.
        try{
            found  = toolConfig.lookupValue("key_file",dataTool.key_file);
            if (!found){
                cout << "ERROR: Mandatory 'key_file' not found." << endl;
                exit (1);
            }
#ifdef _DIA_PROXY_DEBUG
        cout << "Store client_key_file: " << dataTool.key_file << endl;
#endif
        }
        catch(const SettingNotFoundException &nfex){
            cout << "ERROR: Mandatory 'key_file' not found" << endl;
            exit (1);
        }

        // Get the CA_File.
        try{
            found  = toolConfig.lookupValue("CA_File",dataTool.CA_File);
            if (!found){
                cout << "ERROR: Mandatory 'CA_File' not found." << endl;
                exit (1);
            }
#ifdef _DIA_PROXY_DEBUG
        cout << "Store CA_File: " << dataTool.CA_File << endl;
#endif
        }
        catch(const SettingNotFoundException &nfex){
            cout << "ERROR: Mandatory 'CA_File' not found" << endl;
            exit (1);
        }
 
        // Get the ssl_password.
        try{
            found  = toolConfig.lookupValue("ssl_password",dataTool.ssl_password);
            if (!found){
                cout << "ERROR: Mandatory 'ssl_password' not found." << endl;
                exit (1);
            }
#ifdef _DIA_PROXY_DEBUG
        cout << "Store ssl_password: " << dataTool.ssl_password << endl;
#endif
        }
        catch(const SettingNotFoundException &nfex){
            cout << "ERROR: Mandatory 'ssl_password' not found." << endl;
            exit (1);
        }
 
 
        const Setting &serverConections = root["ServerConections"];
        int count = serverConections.getLength();
        string name, origin_realm, ip, nic_ip, ssl_protocol;
        bool enable, sctp = false;
        int port, numOfCon, appid;
        found = false;

        for(int i = 0; i < count; ++i) {
            const Setting &serverConection = serverConections[i];

            // Only output the record if all of the expected fields are present.
            serverConection.lookupValue("enable", enable);
            if (enable){

                struct DiaServerConnection diacon = newDiaCon();
                try {
                    found = serverConection.lookupValue("name", name);
#ifdef _DIA_PROXY_DEBUG
                    cout << "Reading name: " << name << endl;
#endif
                    if (!found){
                        cout << "ERROR: Mandatory 'name' not found in ServerConnection." << endl;
                        exit (1);
                    }
                }
                catch(const SettingNotFoundException &nfex){
                        cout << "ERROR: Mandatory 'name' not found in ServerConnection." << endl;
                        exit (1);
                }

                try {
                    origin_realm = "";
                    found = serverConection.lookupValue("origin_realm", origin_realm);
#ifdef _DIA_PROXY_DEBUG
                    if (!found)     cout << "origin_realm: not found. Using default ericsson.se" << endl;
                    else            cout << "origin_realm: " << origin_realm << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
#ifdef _DIA_PROXY_DEBUG
                    cout << "'origin_realm' not found. Using default ericsson.se" << endl;
#endif
                }

                try {
                    sctp=false;
                    serverConection.lookupValue("sctp", sctp);
#ifdef _DIA_PROXY_DEBUG
                    if (sctp)   cout << "Using sctp" << endl;
                    else        cout << "Using tcp" << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
#ifdef _DIA_PROXY_DEBUG
                    cout << "'sctp' not found. Using default tcp" << endl;
#endif
                }

                try {
                    ssl_protocol = "";
                    found = serverConection.lookupValue("ssl_protocol", ssl_protocol);
#ifdef _DIA_PROXY_DEBUG
                    if (!ssl_protocol.empty())   cout << "ssl_protocol: "<< ssl_protocol << endl;
                    else                         cout << "ssl_protocol: not found. Using default 'not ssl'" << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
#ifdef _DIA_PROXY_DEBUG
                    cout << "'ssl_protocol' not found. Using default 'not ssl'" << endl;
#endif
                }

                try {
                    ip="";
                    found = serverConection.lookupValue("ip", ip);
#ifdef _DIA_PROXY_DEBUG
                    cout << "Reading ip: " << ip << endl;
#endif
                    if (!found){
                        cout << "ERROR: Mandatory 'ip' not found in ServerConnection " << diacon.name  << endl;
                        exit (1);
                    }
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "ERROR: Mandatory 'ip' not found in ServerConnection " << diacon.name  << endl;
                    exit (1);
                }
                nic_ip = get_nic_ip_to_dest_host(ip);

                try {
                    found = serverConection.lookupValue("port", port);
#ifdef _DIA_PROXY_DEBUG
                    cout << "Reading port: " << port << endl;
#endif
                    if (!found){
                        cout << "ERROR: Mandatory 'port' not found in ServerConnection " << diacon.name  << endl;
                        exit (1);
                    }
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "ERROR: Mandatory 'port' not found in ServerConnection " << diacon.name  << endl;
                    exit (1);
                }

                try {
                    found = serverConection.lookupValue("numOfCon", numOfCon);
#ifdef _DIA_PROXY_DEBUG
                    cout << "Reading numOfCon:  " << numOfCon << endl;
#endif
                    if (!found){
                        cout << "ERROR: Mandatory 'numOfCon' not found in ServerConnection " << diacon.name << endl;
                        exit (1);
                    }
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "ERROR: Mandatory 'numOfCon' not found in ServerConnection " << diacon.name  << endl;
                    exit (1);
                }
                for (int index=0;index<numOfCon;index++) {
                    cout << endl << "Connection "<<v_connections.size() << endl ;
                    struct DiaServerConnection diacon = newDiaCon();
                    strcpy((char*)diacon.name,name.c_str());

                    sprintf ((char*)diacon.origin_host,"%s.%s.%d.%d.ericsson.se",(char*)dataTool.oh_prefix,diacon.name,dataTool.e2e_seed,index);
                    cout <<"\tOrigin host             : "<<diacon.origin_host<< endl ;

                    strcpy ((char*)diacon.origin_realm,origin_realm.c_str());
                    cout <<"\tOrigin realm            : "<<diacon.origin_realm << endl;

                    diacon.ipv6 = is_ipv6(ip.c_str());
                    
                    if (diacon.ipv6)   cout << "\tIP version              : 6" << endl;
                    else               cout << "\tIP version              : 4" << endl;

                    diacon.ssl_protocol = ssl_protocol;
                    if (!ssl_protocol.empty())   diacon.use_ssl = true;

                    diacon.use_sctp = sctp;
                    if (sctp){
                        if (diacon.use_ssl)    cout << "\tProtocol                : DTLS " << endl;
                        else                   cout << "\tProtocol                : SCTP " << endl;
                    }
                    else {
                        if (diacon.use_ssl)    cout << "\tProtocol                : TLS " << endl;
                        else                   cout << "\tProtocol                : TCP " << endl;
                    }

                    strcpy((char*)diacon.diameter_host,ip.c_str());
                    cout <<"\tDiameter Server IP      : "<<diacon.diameter_host << endl ;

                    diacon.serv_port = port;
                    cout <<"\tDiameter Server Port    : "<<diacon.serv_port << endl ;

                    strcpy((char*)diacon.diaproxy_host,(const char*)nic_ip.c_str());
                    cout <<"\tcnDiaProxy IP           : "<<diacon.diaproxy_host << endl ;

                    if (diacon.ipv6){
                        inet_pton(AF_INET6, diacon.diaproxy_host, &diacon.localaddr_v6.sin6_addr);
                    }
                    else {
                        ip2oct(diacon.host_ip_address,diacon.diaproxy_host);
                    }

                    try {
                        const Setting &appids = serverConection.lookup("appid");
                        cout << "\tDiameter appid          : " ;
                        for (int n = 0; n < appids.getLength(); ++n) {
                            int value = appids[n];
                            diacon.vendor_specific_application.push_back(value);
                            cout << value << " " ;

                            if(find(dataTool.all_appids.begin(), dataTool.all_appids.end(), value) == dataTool.all_appids.end()) {
                                dataTool.all_appids.push_back(value);
                            }
                        }
                        cout << endl;
                    }
                    catch(const SettingNotFoundException &nfex){
                        cout << "ERROR: Mandatory 'appid' not found in ServerConnection " << diacon.name<<endl;
                        exit (1);
                    }
                    v_connections.push_back(diacon);
                    dataTool.numberOfConnections++;
                    cout << endl << endl;
                }
            }
        }
        if (dataTool.numberOfConnections == 0){
            cout << "ERROR: Enabled server connections not found in configuratioon file." << endl;
            exit (1);
        }
    }
    catch(const SettingNotFoundException &nfex) {
        // Ignore.
    }
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



bool printConfiguration()
{
    cout << "Settings" <<endl;
    cout << "-------------" <<endl;
    cout << "Number Diameter Server Con.     : " << dataTool.numberOfConnections <<endl;
    cout << "Supportted appid          .     : ";
    for (int i=0; i< dataTool.all_appids.size();i++){
        cout << dataTool.all_appids[i] << " ";
    }
    cout << endl;
    cout << "cnDiaProxy port                 : " << dataTool.local_port <<endl;
    cout << "Log mask                        : " << dataTool.log_mask <<endl;
    cout << "Max number of connection retries: " << dataTool.maxReconnections <<endl <<endl<<endl;

    return true;
}

