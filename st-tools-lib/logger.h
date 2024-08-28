/////////////////////////////////////////////////////////////////////////////////
//
// Logger.h written by Olov Marklund
// Date: 06/10/05 Time: 11:06:39
// Version: 1.0 Build: 002
//
/////////////////////////////////////////////////////////////////////////////////
// Logger.h: interface for the CLogger class.
//
//////////////////////////////////////////////////////////////////////

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <iostream>
#include <fstream>

#include <syslog.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <time.h>
#include <unistd.h>
#include <errno.h>
#include <pthread.h>
#include <math.h>

#define LOG_SIZE 6
#define LOG_FILE "NetLayerTrans.log"


/////////////////////////////////////////////////////////////////////////////////

#define MAX_SIZE_FILE 10000000
#define LOG(X,Y) (Log::Instance().write(X,Y))
#define DEFAULT_LOG_MASK    15


//logging modes
enum log_modes{
    FILE_MODE       = 0,
    STDOUT_MODE     = 1,
    MIXED_MODE      = 2
};


enum log_types{
    ERROR=          1,
    WARNING=        2,
    CONNECTIONS=    4,
    EVENT=          8,
    INFO=           16,
    DEBUG=          32,
    DISPLAY
};

struct Timestamp
{
    time_t seconds;
    long milliseconds;
    char timestring[32];
};

struct Timestamp getTimestamp();

class Log
{
public:
    static Log& Instance() {
        static Log theLog;
        return theLog;
    };

    bool ini (std::string file, std::string prg_user);
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
    std::string get_log_type_string(int log_type);
};








