#ifndef LOG_HPP_
#define LOG_HPP_

#include <fstream>
#include <string>
#include <sstream>
#include <pthread.h>

#define MAX_SIZE_FILE 10000000
#define LOG(X,Y) (Log::Instance().write(X,Y))

#define  FILE_MODE 0
#define  STDOUT_MODE 1
#define  MIXED_MODE 2



enum LOG_TYPES {
	ERROR,
	WARNING,
	CONNECTIONS,
	EVENT,
	INFO,
	DEBUG
};
        
const std::string LOG_TYPES_MESSAGES[]= {"LOG_ERROR","LOG_WARNING","LOG_CONNECTIONS","LOG_EVENT",
				 	"LOG_INFO","LOG_DEBUG"};            
					
				 
//log types
enum log_types
{
	log_error			= 0x00000001,
	log_warning			= 0x00000002,
	log_connections			= 0x00000004,
	log_event			= 0x00000008,
	log_info 			= 0x00000010,
	log_debug			= 0x00000020,
	log_all				= 0xffffffff
};

      
class Log
{
public:
    static Log& Instance() {
        static Log theLog;
        return theLog;
    };

    bool ini (std::string file, std::string prg_user);
//    void write (char const * line);
    void write (unsigned int what, std::string line);
    void set_log_mask(uint log_mask);
    void set_log_mode( int log_mode);
    std::string get_log_file();
    ~Log();

    
private:
    Log();
    Log(Log const&);
    Log& operator=(Log const&);

    void swapFile();
    std::string myFileName;
    std::string myUser;
    std::ofstream myFile;
    unsigned int logmask;
    int logmode;
    int fileSize;
    pthread_mutex_t lock;           // Mutex
    pid_t myPid;
};

#endif /*LOG_HPP_*/
