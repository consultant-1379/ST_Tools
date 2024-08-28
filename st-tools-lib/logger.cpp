/////////////////////////////////////////////////////////////////////////////////
//
// Logger.cpp written by Olov Marklund
// Date: 06/10/05 Time: 11:06:39
// Version: 1.0 Build: 002
//
/////////////////////////////////////////////////////////////////////////////////
// Logger.cpp: implementation of the CLogger class.
//
//////////////////////////////////////////////////////////////////////

#include "logger.h"

struct Timestamp getTimestamp()
{
    char   timebuffer[32]     = {0};
    struct timeval  tv        = {0};
    struct tm      *tmval     = NULL;
    struct tm       gmtval    = {0};
    struct timespec curtime   = {0};

    struct Timestamp timestamp;

    int i = 0;

    // Get current time
    clock_gettime(CLOCK_REALTIME, &curtime);


    // Set the fields
    timestamp.seconds      = curtime.tv_sec;
    timestamp.milliseconds = round(curtime.tv_nsec/1.0e6);

    if((tmval = localtime_r(&timestamp.seconds, &gmtval)) != NULL)
    {
        // Build the first part of the time
        strftime(timebuffer, sizeof timebuffer, "%Y-%m-%d %H:%M:%S", &gmtval);

        // Add the milliseconds part and build the time string
        snprintf(timestamp.timestring, sizeof timestamp.timestring, "%s.%03ld", timebuffer, timestamp.milliseconds); 
    }

    return timestamp;
}

Log::Log() {
    // Empty constructor
}

bool Log::ini (std::string file, std::string prg_user) {
    pthread_mutex_init(&lock, NULL);
    fileSize = 0;
    myPid = getpid();
    std::stringstream myPidStr;
    myPidStr << file << "_" << myPid <<".log";
    myFileName = myPidStr.str();
    myUser = prg_user;
    myFile.open(myFileName.c_str(), std::ios_base::out|std::ios_base::app);
    set_log_mode (FILE_MODE); 
    set_log_mask (ERROR);  
    return myFile.is_open();
}

std::string Log::get_log_type_string(int log_type){

    std::string answer="";
    switch (log_type) {
        case ERROR:
            answer ="ERROR";
            break;
        case WARNING:
            answer ="WARNING";
            break;
        case CONNECTIONS:
            answer ="CONNECTIONS";
            break;
        case EVENT:
            answer ="EVENT";
            break;
        case INFO:
            answer ="INFO";
            break;
        case DEBUG:
            answer ="DEBUG";
            break;
    }
    return answer;
}

void Log::write (unsigned int what, std::string line) {

    if((logmask & what) != 0 || what == DISPLAY){

        struct Timestamp fulltimestamp = getTimestamp();
        std::string timestamp (fulltimestamp.timestring);
        
        switch (logmode) {
            case  FILE_MODE:
                pthread_mutex_lock(&lock); 
                    myFile << timestamp << " " << myUser << " (" << myPid << ") " << get_log_type_string(what) <<": " << line << std::endl;
                    
                    fileSize += line.size();
                    if (fileSize > MAX_SIZE_FILE)
                            swapFile();
                pthread_mutex_unlock(&lock); 
                break;
                    
            case  STDOUT_MODE:
                pthread_mutex_lock(&lock); 
                    if (what == DISPLAY){
                        std::cout << line << std::endl;
                    }
                    else {
                        std::cout << timestamp << " " << line << std::endl;
                    }
                pthread_mutex_unlock(&lock); 
                break;
                        
            case  MIXED_MODE:
                pthread_mutex_lock(&lock); 
                    myFile << timestamp << " " << myUser << " (" << myPid << ") " << get_log_type_string(what) <<": " << line << std::endl;
                    
                    fileSize += line.size();
                    if (fileSize > MAX_SIZE_FILE)
                            swapFile();

                    if (what == DISPLAY){
                        std::cout << line << std::endl;
                    }
                    else {
                        std::cout << timestamp << " " << line << std::endl;
                    }
                pthread_mutex_unlock(&lock); 
                break;
                        
            default:
                break;        
        }
    }
} 

      
/*
 * Poor man's version of logrotate for our log file
 * 
*/
void Log::swapFile () {
    myFile.close();
    std::string newName = myFileName + "_1";
    rename(myFileName.c_str(), newName.c_str());

    myFile.open(myFileName.c_str(), std::ios_base::out|std::ios_base::trunc);
    fileSize = 0;    
}

void Log::set_log_mask(uint log_mask){ 
    logmask = log_mask;
} 

void Log::set_log_mode(int log_mode){ 
    logmode = log_mode;
} 

std::string Log::get_log_file(){
    return myFileName;
}

Log::~Log() {
    myFile.close();
}














