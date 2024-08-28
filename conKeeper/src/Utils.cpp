#include "ConnectionKeeper.h"
extern applicationData dataTool;
extern pthread_mutex_t sync_mutex;
extern pthread_t SignalThreadID;
extern pthread_t RemoteThreadID;
extern pthread_t HeartBeatThreadID;

extern RemoteControl remoteControlData;
extern struct HeartBeat  heartBeatData; 

using namespace std;

std::string appStatus[] = {
        "STARTING",
	"TO_BE_CONFIGURED",
       	"READY",
	"TO_BE_RESET",
	"HAVE_TO_EXIT"        
} ;       
       
std::string zoneActive[] = {
        "UNKNOWM",
	"PRIMARY",
       	"SECONDARY"
} ;       
       
std::string ConStatus[] = {
        "OFF_LINE",
	"CONNECTING",
       	"ON_LINE",
	"TO_BE_CLOSED",
	"TO_BE_RESTARTED"        
} ;       
        

std::string ListennerStatus[] = {
        "OFF",
	"STARTING",
	"TO_BE_CONFIGURED",
       	"ON",
       	"FAULTY",
       	"TO_BE_STARTED",
	"TO_BE_CLOSED",        
	"NOT_USED"        
} ;       

        
std::string ConType[] = {
        "NONE",
	"LOAD",
       	"DIAMETER",
	"LDAP"        
} ;
        
        
std::string displayCmdHelp()
{
        std::stringstream info;
	char line [1024]; 
	ifstream inFile; 
    
    char * path = getenv("ST_TOOL_PATH");
        
    if (path == NULL) {
        info << endl << "ERROR: Env variable ST_TOOL_PATH not defined "<< endl << endl;
        return info.str();
    }
        
    string help_file (path);
    
    help_file = help_file + "/share/conKeeper/conkeeper_help.txt";
                  
	inFile.open (help_file.c_str());
				
	if (!inFile) {
		info << endl << "ERROR:Failed to open " << help_file << endl << endl;
 		return info.str();
	}
        
	info << endl;
                
	while(inFile) {
		inFile.getline(line, 1024);
		info << line << endl;
        }
        
 	return info.str();

}






std::string displayAppInfo()
{
        std::stringstream info;
                
        info << "\n";        
        info << "\tHostname:\t\t" <<  dataTool.hostname << "\n";        
        info << "\tConKeeper status:\t" <<  appStatus[dataTool.status] << "\n";    
        
        info << "\tRedundancy:\t\t" ;  
        if (dataTool.redundancy)		info <<  "ENABLED\n"; 
        else					info <<  "DISABLED\n";       
          
        info << "\tActive Zone:\t\t" <<  zoneActive[dataTool.activeZone] << "\n";    
        info << "\tLog file:\t\t" <<  Log::Instance().get_log_file() << "\n";        
        info << "\tLog mask:\t\t" <<  dataTool.logMask << "\n";        
        info << "\tLog mode:\t\t" <<  dataTool.logMode << "\n";        
        info << "\n";        
        
 	return info.str();
}


std::string getConnectionInfo(Connection &con, int index)
{
        std::stringstream info;
                
        info << "\n";        
        info << "\tConnection number:\t" <<  index << "\n";         
        info << "\tConnection type:\t" <<  con.type_str << "\n";        
        info << "\tServer Status:\t\t" <<  ConStatus[con.server.status].c_str() << "\n";        
        info << "\tServer socket:\t\t" <<  con.server.sock << "\n";        
        info << "\tClient Status:\t\t" <<  ConStatus[con.client.status].c_str() << "\n";        
        info << "\tClient socket:\t\t" <<  con.client.sock << "\n";   

	if (dataTool.redundancy) {
 		switch (con.client.connectedTo) {
			case UNKNOWM:{
        			info << "\tConnected to:\t\tNOT CONNECTED" << "\n";  
				break;
			}
			case PRIMARY:{
        			info << "\tConnected to:\t\t" <<  inet_ntoa(con.client.primary_remote_addr.sin_addr) <<":"<<ntohs(con.client.primary_remote_addr.sin_port)<< "\n";  
				break;
			}
        
			case SECONDARY:{
        			info << "\tConnected to:\t\t" <<  inet_ntoa(con.client.secondary_remote_addr.sin_addr) <<":"<<ntohs(con.client.secondary_remote_addr.sin_port)<< "\n";  
				break;
			}
		}
        }       
        else {
		info << "\tConnected to:\t\t" <<  inet_ntoa(con.client.primary_remote_addr.sin_addr) <<":"<<ntohs(con.client.primary_remote_addr.sin_port)<< "\n";  
        }
        
        info << "\n";        
        
 	return info.str();
}

std::string getListennerInfo(Listener &listenner, int index)
{
        std::stringstream info;
                
        info << "\n";        
	info << "\tListener number:\t\t" <<  index << "\n";        
        info << "\tListener type:\t\t\t" <<  ConType[listenner.type].c_str() << "\n";        
        info << "\tListener Status:\t\t" <<  ListennerStatus[listenner.status].c_str() << "\n";        
//        info << "\tListener ip_host:\t\t" <<  listenner.ip_host << "\n";        
        info << "\tListener primary ip_host:\t" <<  listenner.primary_ip_host << "\n";        
        info << "\tListener secondary ip_host:\t" <<  listenner.secondary_ip_host << "\n";        
        info << "\tListener port:\t\t\t" <<  listenner.port << "\n";        
        info << "\tListener socket:\t\t" <<  listenner.sock << "\n";        
        info << "\n";        
        
 	return info.str();
}



string getIpByHostname (string host)
{
    string  filter = ".";;  
    string::size_type idx;

    idx = host.find(filter);
    if (idx != string::npos) {
        return host;
    }

    struct hostent *he;
    he = gethostbyname(host.c_str()); 
    if (he == 0) {
        string ip ="0.0.0.0";
        return ip;
    }   

    if (he->h_addr_list[0] == NULL) {
        string ip ="0.0.0.0";
        return ip;
    }   

    string ip (inet_ntoa( (struct in_addr) *((struct in_addr *) he->h_addr_list[0])));

    return   ip; 
}

bool filterLine (char * line, string filter, bool after, string & element)
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

void resetServerConnectionAndExit(Connection *myConnection)
{
	if (dataTool.logMask >= LOGMASK_INFO){
        	stringstream logString;
		logString.clear();
		logString.str("");
		logString << "resetServerConnectionAndExit: SocketId: "<< myConnection->server.sock <<", ThreadId: "<< myConnection->server.threadID<<endl;
		LOG(INFO, logString.str());
        }
        
	pthread_mutex_lock(&sync_mutex);
		if (myConnection->server.sock != -1)		close(myConnection->server.sock);
		myConnection->server.status = OFFLINE;
                if (myConnection->client.status !=  OFFLINE)			myConnection->client.status = TO_BE_CLOSED;
		myConnection->server.sock = -1;
		myConnection->server.threadID = 0;                
		myConnection->message[0] = '\0';
		myConnection->messageLen = 0;
		myConnection->firstConnectionOk = false;
               
                
	pthread_mutex_unlock(&sync_mutex);

	pthread_exit(0);
}

void resetClientConnectionAndExit(Connection *myConnection, ConnectionStatus status )
{
	if (dataTool.logMask >= LOGMASK_INFO){
        	stringstream logString;
		logString.clear();
		logString.str("");
		logString << "resetClientConnectionAndExit: SocketId: "<< myConnection->client.sock <<", ThreadId: "<< myConnection->client.threadID<<endl;
		LOG(INFO, logString.str());
        }

	pthread_mutex_lock(&sync_mutex);
		if (myConnection->client.sock != -1)		close(myConnection->client.sock);
                                
		myConnection->client.status = status;
		myConnection->client.sock = -1;
		myConnection->client.threadID = 0;
	pthread_mutex_unlock(&sync_mutex);

        if (status == TO_BE_RESTARTED) {
                sleep (10);
        }
	pthread_exit(0);
}

void resetRemoteAndExit (int fail)
{
	
	if (dataTool.logMask >= LOGMASK_INFO){
        	stringstream logString;
		logString.clear();
		logString.str("");
		logString << "resetRemoteAndExit: SocketId: "<<remoteControlData.sock <<", ThreadId: "<< RemoteThreadID<<endl;
		LOG(INFO, logString.str());
        }
        
	pthread_mutex_lock(&sync_mutex);
		remoteControlData.status = REMOTE_OFF;
	pthread_mutex_unlock(&sync_mutex);

	if (remoteControlData.sock != -1)	close (remoteControlData.sock);	

	if (fail) {
		pthread_kill(SignalThreadID ,SIGUSR1);
	}

	pthread_exit(0);

}
void resetHeartBeatAndExit (int fail)
{
	
	if (dataTool.logMask >= LOGMASK_INFO){
        	stringstream logString;
		logString.clear();
		logString.str("");
		logString << "resetHeartbeatAndExit: SocketId: "<<heartBeatData.sock <<", ThreadId: "<< HeartBeatThreadID<<endl;
		LOG(INFO, logString.str());
        }
        
	if (heartBeatData.sock != -1)	close (heartBeatData.sock);	

	if (fail) {
		pthread_kill(SignalThreadID ,SIGUSR1);
	}

	pthread_exit(0);

}

char* getlocalhostname (char *name) 
{
	if (gethostname(name, 100))
	{
		name[0] = '\0';
	}
	return name;
}


//determines the bytes to be added as padding to a piece of data
int topad(int len)
{
	int i = 0;
	while(((len + i)*8) % 32)
		i++;
	return i;
}


int str2int (char* str) {
	return atoi (str);
}


void  int2oct (char i[4], int number) {
	sprintf(i,"%d", number);
}

void int2hex (char *buff, int number, int size) {
	buff[size-1] = number%256;
	for (int i = 0; i<=(size-2); i++) {
		int factor = 1;
		for (int j=0;j!=(size-1-i);factor*=256,j++);
		
		buff [i] = number/factor;
	}
}

//converts an IP address contained in a buffer into one in 4-byte format
void ip2oct(uchar ip[4], const char *ipstr)
{
	char * tstr = (char *)ipstr;
	int tmp = atoi(tstr);
	ip[0] = (uchar)tmp;
	tstr = strchr(tstr,'.') + 1;

	tmp = atoi(tstr);
	ip[1] = (uchar)tmp;
	tstr = strchr(tstr,'.') + 1;

	tmp = atoi(tstr);
	ip[2] = (uchar)tmp;
	tstr = strchr(tstr,'.') + 1;

	tmp = atoi(tstr);
	ip[3] = (uchar)tmp;
}

//converts an integer expressed as text in a buffer to 4-byte format
void int2oct(uchar i[4], char *intstr)
{
	int tmp = atoi(intstr);
	i[0] = (uchar)(0xff & (tmp >> 24));
	i[1] = (uchar)(0xff & (tmp >> 16));
	i[2] = (uchar)(0xff & (tmp >> 8));
	i[3] = (uchar)(0xff & tmp);
}

//converts a 4-byte formatted integer into a integer value
void oct2int(int *i_value, uchar i[4])
{
	*i_value = 0;
	*i_value = *i_value + (int)i[0]*256*256*256;
	*i_value = *i_value + (int)i[1]*256*256;
	*i_value = *i_value + (int)i[2]*256;
	*i_value = *i_value + (int)i[3];
}

