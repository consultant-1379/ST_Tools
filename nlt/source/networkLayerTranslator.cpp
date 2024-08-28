
#include <unistd.h>
#include <malloc.h>
#include <string.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <resolv.h>
#include "openssl/ssl.h"
#include "openssl/err.h"
#define FAIL    -1

// For parsing cfg file
#include <libconfig.h++>
#include <iomanip>
#include <cstdlib>


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <sstream>
#include <fstream>
#include <vector>
#include <map>

#include "networkLayerTranslator.h"

pthread_mutex_t CONNECTION_VECTOR = PTHREAD_MUTEX_INITIALIZER;

using namespace std;
using namespace libconfig;
pthread_t SignalThreadID;
SignalReason sigReason= NO_REASON;

ToolData toolData;
vector<Listener> v_listeners;
vector<Connection> v_connections;



void readConfigFile(string cfg_file)
{
    char myFile[355];
    strcpy(myFile,cfg_file.c_str());

    Config cfg;
    // Read the file. If there is an error, report it and exit.
    try {
        cfg.readFile(myFile);
        cout << endl << "Configuration file:\t"<<cfg_file<<endl<< endl;
    }
    catch(const FileIOException &fioex) {
        cout << endl << "ERROR: I/O error while reading file " << cfg_file << endl;
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
            toolConfig.lookupValue("logMask",toolData.logMask);
#ifdef _NLT_DEBUG
            cout << "Store logMask: " << toolData.logMask << endl;
#endif
        }
        catch(const SettingNotFoundException &nfex){
#ifdef _NLT_DEBUG
            cout << "No 'logMask' setting in configuration file." << endl;
#endif
        }
    
        // Get the logMode.
        try{
            toolConfig.lookupValue("logMode",toolData.logMode);
#ifdef _NLT_DEBUG
            cout << "Store logMode: " << toolData.logMode << endl;
#endif
        }
        catch(const SettingNotFoundException &nfex){
#ifdef _NLT_DEBUG
            cout << "No 'logMode' setting in configuration file." << endl;
#endif
        }
    
        // Get the server_cert_file.
        try{
            found = toolConfig.lookupValue("server_cert_file",toolData.server_cert_file);
            if (!found){
                cout << "ERROR: Mandatory 'server_cert_file' not found." << endl;
                exit (1);
            }
#ifdef _NLT_DEBUG
            cout << "Store server_cert_file: " << toolData.server_cert_file << endl;
#endif
         }
        catch(const SettingNotFoundException &nfex){
            cout << "ERROR: Mandatory 'server_cert_file' not found" << endl;
            exit (1);
        }
    
        // Get the server_key_file.
        try{
            found  = toolConfig.lookupValue("server_key_file",toolData.server_key_file);
            if (!found){
                cout << "ERROR: Mandatory 'server_key_file' not found." << endl;
                exit (1);
            }
#ifdef _NLT_DEBUG
        cout << "Store server_key_file: " << toolData.server_key_file << endl;
#endif
        }
        catch(const SettingNotFoundException &nfex){
            cout << "ERROR: Mandatory 'server_key_file' not found" << endl;
            exit (1);
        }
        
        // Get the client_cert_file.
        try{
            found = toolConfig.lookupValue("client_cert_file",toolData.client_cert_file);
            if (!found){
                cout << "ERROR: Mandatory 'client_cert_file' not found." << endl;
                exit (1);
            }
#ifdef _NLT_DEBUG
            cout << "Store client_cert_file: " << toolData.client_cert_file << endl;
#endif
         }
        catch(const SettingNotFoundException &nfex){
            cout << "ERROR: Mandatory 'client_cert_file' not found" << endl;
            exit (1);
        }
    
        // Get the client_key_file.
        try{
            found  = toolConfig.lookupValue("client_key_file",toolData.client_key_file);
            if (!found){
                cout << "ERROR: Mandatory 'client_key_file' not found." << endl;
                exit (1);
            }
#ifdef _NLT_DEBUG
        cout << "Store client_key_file: " << toolData.client_key_file << endl;
#endif
        }
        catch(const SettingNotFoundException &nfex){
            cout << "ERROR: Mandatory 'client_key_file' not found" << endl;
            exit (1);
        }

        // Get the CA_File.
        try{
            found  = toolConfig.lookupValue("CA_File",toolData.ca_file);
            if (!found){
                cout << "ERROR: Mandatory 'CA_File' not found." << endl;
                exit (1);
            }
#ifdef _NLT_DEBUG
        cout << "Store CA_File: " << toolData.ca_file << endl;
#endif
        }
        catch(const SettingNotFoundException &nfex){
            cout << "ERROR: Mandatory 'CA_File' not found" << endl;
            exit (1);
        }


        const Setting &Listeners = root["Translators"];
        int count = Listeners.getLength();
        v_listeners.reserve(count);
        bool enable;

        for(int i = 0; i < count; ++i) {
            const Setting &Listener = Listeners[i];

            Listener.lookupValue("enable", enable);
            if (enable){

                struct Listener my_Listener;
                my_Listener.enable = true;
                try {
                    found = Listener.lookupValue("name", my_Listener.name);
                    if (!found){
                        cout << "ERROR: Mandatory 'name' not found." << endl;
                        exit (1);
                    }
#ifdef _NLT_DEBUG
                    cout << "Reading name: " << my_Listener.name << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "ERROR: Mandatory 'name' not found." << endl;
                    exit (1);
                }

                try {
                    found = Listener.lookupValue("be_ip", my_Listener.be_ip);
                    if (!found){
                        cout << "ERROR: Mandatory 'be_ip' not found in " << my_Listener.name  << endl;
                        exit (1);
                    }
                    my_Listener.be_ipv6 = is_ipv6(my_Listener.be_ip.c_str());
#ifdef _NLT_DEBUG
                    cout << "Reading be_ip: " << my_Listener.be_ip << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "ERROR: Mandatory 'be_ip' not found in " << my_Listener.name  << endl;
                    exit (1);
                }
 
                try {
                    found = Listener.lookupValue("fe_ip", my_Listener.fe_ip);
                    if (!found){
                        cout << "ERROR: Mandatory 'fe_ip' not found in " << my_Listener.name  << endl;
                        exit (1);
                    }
                    my_Listener.fe_ipv6 = is_ipv6(my_Listener.fe_ip.c_str());
#ifdef _NLT_DEBUG
                    cout << "Reading fe_ip: " << my_Listener.fe_ip << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "ERROR: Mandatory 'fe_ip' not found in " << my_Listener.name  << endl;
                    exit (1);
                }
 
                try {
                    found = Listener.lookupValue("be_port", my_Listener.be_port);
                    if (!found){
                        cout << "ERROR: Mandatory 'be_port' not found in " << my_Listener.name  << endl;
                        exit (1);
                    }
#ifdef _NLT_DEBUG
                    cout << "Reading be_port: " << my_Listener.be_port << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "ERROR: Mandatory 'be_port' not found in " << my_Listener.name  << endl;
                    exit (1);
                }

                try {
                    found = Listener.lookupValue("fe_port", my_Listener.fe_port);
                    if (!found){
                        cout << "ERROR: Mandatory 'fe_port' not found in " << my_Listener.name  << endl;
                        exit (1);
                    }
#ifdef _NLT_DEBUG
                    cout << "Reading fe_port: " << my_Listener.fe_port << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "ERROR: Mandatory 'fe_port' not found in " << my_Listener.name  << endl;
                    exit (1);
                }

                try {
                    my_Listener.be_ssl_protocol="";
                    my_Listener.be_ssl = false;
                    Listener.lookupValue("be_ssl_protocol", my_Listener.be_ssl_protocol);
                    if (!my_Listener.be_ssl_protocol.empty()){
                        my_Listener.be_ssl = true;
                    }
#ifdef _NLT_DEBUG
                    if (!my_Listener.be_ssl_protocol.empty())   cout << "Backend side will use SSL with "<< my_Listener.be_ssl_protocol << endl;
                    else                                        cout << "Backend side will not use SSL" << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "be_ssl_protocol not found for "<<  my_Listener.name << "Backend side will not use SSL" << endl;
                }

                try {
                    my_Listener.fe_ssl_req_cred=false;
                    Listener.lookupValue("fe_ssl_req_cred", my_Listener.fe_ssl_req_cred);
#ifdef _NLT_DEBUG
                    if (my_Listener.fe_ssl_req_cred)            cout << "Frontend will request client SSL credentials"<< endl;
                    else                                        cout << "Frontend will not request client credentials" << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "fe_ssl_req_cred not found for "<<  my_Listener.name << "Frontend side will not request client SSL credentials" << endl;
                }

                try {
                    my_Listener.fe_ssl_protocol="";
                    my_Listener.fe_ssl = false;
                    Listener.lookupValue("fe_ssl_protocol", my_Listener.fe_ssl_protocol);
                    if (!my_Listener.fe_ssl_protocol.empty()){
                        my_Listener.fe_ssl = true;
                    }

#ifdef _NLT_DEBUG
                    if (!my_Listener.fe_ssl_protocol.empty())   cout << "Frontend side will use SSL with "<< my_Listener.fe_ssl_protocol << endl;
                    else                                        cout << "Frontend side will not use SSL" << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "fe_ssl_protocol not found for "<<  my_Listener.name << "Frontend side will not use SSL" << endl;
                }

                try {
                    found = Listener.lookupValue("be_sctp", my_Listener.be_sctp);
                    if (!found){
                        cout << "ERROR: Mandatory 'be_sctp' not found in " << my_Listener.name  << endl;
                        exit (1);
                    }
#ifdef _NLT_DEBUG
                    if (my_Listener.be_sctp)   cout << "Backtend side will use SCTP" << endl;
                    else        cout << "Backtend side will use TCP" << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "ERROR: Mandatory 'be_sctp' not found in " << my_Listener.name  << endl;
                    exit (1);
                }

                 try {
                    found = Listener.lookupValue("fe_sctp", my_Listener.fe_sctp);
                    if (!found){
                        cout << "ERROR: Mandatory 'fe_sctp' not found in " << my_Listener.name  << endl;
                        exit (1);
                    }
#ifdef _NLT_DEBUG
                    if (my_Listener.fe_sctp)   cout << "Frontend side will use SCTP" << endl;
                    else        cout << "Frontend side will use TCP" << endl;
#endif
                }
                catch(const SettingNotFoundException &nfex){
                    cout << "ERROR: Mandatory 'fe_sctp' not found in " << my_Listener.name  << endl;
                    exit (1);
                }
                
               v_listeners.push_back(my_Listener);
   
            } // if (enable)
        } // end for
    }
    catch(const SettingNotFoundException &nfex) {
        cout << endl << "ERROR: Parse error Configuration file:\t"<<cfg_file<<endl<< endl;
        exit (1);
    }
}
        
void printConfiguration()
{
    string protocol;
    cout << endl<<"NetworkLayerTranslator configuration" << endl;
    cout << "------------------------------------" << endl;

    for (unsigned int i = 0; i < v_listeners.size(); i++) {
        cout << "  " <<v_listeners[i].name << endl<< endl;
        cout << "     FrontEnd" << endl;
        cout << "         IP        : " << v_listeners[i].fe_ip << endl;
        cout << "         Port      : " << v_listeners[i].fe_port << endl;
        if (v_listeners[i].fe_sctp){
            if (v_listeners[i].fe_ssl_protocol.empty())   protocol = "SCTP";
            else                                        protocol = "DTLS ("+ v_listeners[i].fe_ssl_protocol +")";
        }
        else{
            if (v_listeners[i].fe_ssl_protocol.empty())   protocol = "TCP";
            else                                        protocol = "TLS ("+ v_listeners[i].fe_ssl_protocol +")";
        }

        cout << "         Protocol  : " << protocol << endl << endl;
        if (v_listeners[i].fe_ssl){
            if (v_listeners[i].fe_ssl_req_cred)   cout << "         Request client SSL credentials" << endl;
            else                                  cout << "         Do NOT request client SSL credentials" << endl;
        }
       cout << endl;
 
        cout << "     BacktEnd" << endl;
        cout << "         IP        : " << v_listeners[i].be_ip << endl;
        cout << "         Port      : " << v_listeners[i].be_port << endl;
        if (v_listeners[i].be_sctp){
            if (v_listeners[i].be_ssl_protocol.empty())   protocol = "SCTP";
            else                                        protocol = "DTLS ("+ v_listeners[i].be_ssl_protocol +")";
        }
        else{
            if (v_listeners[i].be_ssl_protocol.empty())   protocol = "TCP";
            else                                        protocol = "TLS ("+ v_listeners[i].be_ssl_protocol +")";
        }

        cout << "         Protocol  : " << protocol << endl;
        cout << endl;
        
    }
    
     cout << endl;
}
int main(int argc, char *argv[])
{
    if ( argc != 2 )
    {
        cout << "Usage: "<<argv[0] << "<cfg_file>"<<endl;
        exit(0);
    }

    toolData.status = STARTING;
    toolData.server_cert_file = "";
    toolData.server_key_file = "";
    toolData.client_cert_file = "";
    toolData.client_key_file = "";
    toolData.ca_file = "";
    toolData.logMask = 63;
    toolData.logMode = 2;
    toolData.numberOfConnections = DEFAULT_NUM_OF_CON;

    string cfg_file(argv[1]);
    readConfigFile(cfg_file);
    
    string logFile ("netLayerTranslator");
    string prg("NLT");
    Log::Instance().ini(logFile, prg);
    Log::Instance().set_log_mask(toolData.logMask);
    Log::Instance().set_log_mode(toolData.logMode);

    stringstream logString;	

    printConfiguration();

#ifdef _NLT_DEBUG
    logString.clear();
    logString.str("");
    logString << "(main): Initialize SSL library" <<endl;
    LOG(DEBUG, logString.str());
#endif

    // Initialize the SSL library
    SSL_library_init();
    OpenSSL_add_all_algorithms();  /* Load cryptos, et.al. */
    SSL_load_error_strings();   /* Bring in and register error messages */

#ifdef _NLT_DEBUG
    logString.clear();
    logString.str("");
    logString << "(main): Initialize v_connections" <<endl;
    LOG(DEBUG, logString.str());
#endif

    struct Connection connection;
    initializeConnection(&connection);

    v_connections.reserve(toolData.numberOfConnections);
    v_connections.assign(toolData.numberOfConnections,connection);
    for (unsigned int i = 0; i < v_connections.size(); i++) {
        v_connections[i].pos = i;
    }

    /* block all signals */
    sigset_t signal_set;
    sigfillset( &signal_set );
    pthread_sigmask( SIG_BLOCK, &signal_set,NULL );
    
#ifdef _NLT_DEBUG
    logString.clear();
    logString.str("");
    logString << "(main): Creating Signal Thread" <<endl;
    LOG(DEBUG, logString.str());
#endif
    int ret, errsv;
    ret = pthread_create(&SignalThreadID, NULL,_SignalThread, NULL );
    if (ret){
        errsv = ret;
        logString.clear();
        logString.str("");
        logString << "(main): SignalThread creation returned" << ret << endl;
        logString <<"\tError: " << strerror(errsv) << endl;
        LOG(ERROR, logString.str());
    }
    
#ifdef _NLT_DEBUG
    logString.clear();
    logString.str("");
    logString << "(main): Creating Listener Threads" <<endl;
    LOG(DEBUG, logString.str());
#endif
    for (int index = 0; index < v_listeners.size(); index++) { 
        ret = pthread_create(&v_listeners[index].threadID,NULL,_ListenerThread,(void *) &(v_listeners[index]));
        if (ret){
            errsv = ret;
            logString.clear();
            logString.str("");
            logString << "(main): _ListenerThread creation returned" << ret << endl;
            logString <<"\tError: " << strerror(errsv) << endl;
            LOG(ERROR, logString.str());
            pthread_kill(SignalThreadID ,SIGUSR1);            
        }

#ifdef _NLT_DEBUG
        logString.clear();
        logString.str("");
        logString << "(main): Created _ListenerThread for " << v_listeners[index].name <<endl;
        LOG(DEBUG, logString.str());
#endif
        
    }

    sleep(2); //go to sleep
    //while the thread is still alive, go on..... 
    void *theThreadStatus;
    pthread_join(SignalThreadID,&theThreadStatus);

    return 0;

    
}