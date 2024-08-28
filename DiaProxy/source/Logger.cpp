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

#include "Logger.h"

#include "Utils.h"
#include "DiaProxy.h"

extern CER_DATA cer_data;


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


            time_t clk= time(NULL);
            std::string timestamp (ctime(&clk));
            
                 switch (logmode) {
                       case  FILE_MODE:
				pthread_mutex_lock(&lock); // Start critical section
					if (what == DISPLAY) {
                                            myFile << timestamp << " " << myUser << " (" << myPid << ") " << get_log_type_string(what) <<": " << std::endl << line << std::endl;
					    fileSize += line.size();
                                        }
                                        else {
                                            myFile << timestamp << " " << myUser << " (" << myPid << ") " << get_log_type_string(what) <<": " << line << std::endl;
					    fileSize += line.size();
                                        }
    					if (fileSize > MAX_SIZE_FILE)
        					swapFile();
    				pthread_mutex_unlock(&lock); // End critical section
                                break;
                        
                       case  STDOUT_MODE:
				if (what == DISPLAY) {
                                    std::cout << line << std::endl;
                                }
                                else {
                                    std::cout << timestamp << " " << myUser << " (" << myPid << ") " << get_log_type_string(what) <<": " << std::endl  << line << std::endl;
                                }
                                break;
                                
                       case  MIXED_MODE:
				pthread_mutex_lock(&lock); // Start critical section
					if (what == DISPLAY) {
                                            myFile << timestamp << " " << myUser << " (" << myPid << ") " << get_log_type_string(what) <<": " << std::endl << line << std::endl;
					    fileSize += line.size();
                                        }
                                        else {
                                            myFile << timestamp << " " << myUser << " (" << myPid << ") " << get_log_type_string(what) <<": " << line << std::endl;
					    fileSize += line.size();
                                        }
    					if (fileSize > MAX_SIZE_FILE)
        					swapFile();
    				pthread_mutex_unlock(&lock); // End critical section
                                std::cout <<  line << std::endl;
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














