#include <iostream>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <stdio.h>

#include "logger.h"

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

/*
 * Write a line to the log file
 * 
 * Since this write method will be called from multi-threaded applications, we must make sure
 * there are no concurrent writes (or write attempts) to the log file. Notice that the way
 * we have chosen to prevent write conflicts is the most simple one: a lock to the critical
 * section. This method does not guarantee fairness but, since all threads calling this
 * method are presumed to be clones of each other, it does not really matter if a given
 * thread starves to death as long as the wheels keep turning, so to say

void Log::write (char const * line) {

    pthread_mutex_lock(&lock); // Start critical section

    myFile << myUser << " (" << myPid << ") " << line << std::endl;

    // Check file size
	fileSize += strlen(line);
    if (fileSize > MAX_SIZE_FILE)
        swapFile();

    pthread_mutex_unlock(&lock); // End critical section
}
*/
void Log::write (unsigned int what, std::string line) {

	int log_level = 0x00000001 << what;
	if((logmask & log_level) != 0){

            time_t clk= time(NULL);
            std::string timestamp (ctime(&clk));
            timestamp.at(timestamp.size()-1)='\0';


                 
                 switch (logmode) {
                       case  FILE_MODE:
				pthread_mutex_lock(&lock); // Start critical section
					myFile << timestamp << " " << myUser << " (" << myPid << ") " << LOG_TYPES_MESSAGES[what] <<": " << line << std::endl;
					fileSize += line.size();
    					if (fileSize > MAX_SIZE_FILE)
        					swapFile();
    				pthread_mutex_unlock(&lock); // End critical section
                                break;
                        
                       case  STDOUT_MODE:
                                std::cout << timestamp << " " << myUser << " (" << myPid << ") " << LOG_TYPES_MESSAGES[what] <<": " << line << std::endl;
                                break;
                                
                       case  MIXED_MODE:
				pthread_mutex_lock(&lock); // Start critical section
					myFile << timestamp << " " << myUser << " (" << myPid << ") " << LOG_TYPES_MESSAGES[what] <<": " << line << std::endl;
					fileSize += line.size();
    					if (fileSize > MAX_SIZE_FILE)
        					swapFile();
    				pthread_mutex_unlock(&lock); // End critical section
                                std::cout << timestamp << " " << myUser << " (" << myPid << ") " << LOG_TYPES_MESSAGES[what] <<": " << line << std::endl;
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
