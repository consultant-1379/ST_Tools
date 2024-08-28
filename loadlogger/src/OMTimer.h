// OMTimer.h: interface for the COMTimer class.
//
//////////////////////////////////////////////////////////////////////

#ifndef OMTIMER
#define OMTIMER

#ifdef _WIN32
#include <windows.h>
#define CREATE_THREAD(func,arg,id, h) h = CreateThread(NULL,0,func,(void*)arg,0,&id)
#define KILL_THREAD(id) TerminateThread(id,0)
#define THREAD_ID DWORD
#define THREAD_HANDLE_RESULT HANDLE
#define EXIT_THREAD(ecode) ExitThread(ecode)
#define RETURN_THREAD(ecode) return ecode
#define SLEEP(t) Sleep(t)
#else
#include <pthread.h>
#include <signal.h>
#define CREATE_THREAD(func,arg,id,h) h = pthread_create(&id,NULL,func,(void*)arg)
#define KILL_THREAD(id) pthread_kill(id,SIGINT)
#define THREAD_ID pthread_t
#define THREAD_HANDLE_RESULT int
#define EXIT_THREAD(ecode) pthread_exit(ecode)
#define RETURN_THREAD(ecode) return (void*)(ecode)
#define SLEEP(t) usleep(1000*t)
#endif

#include <memory>
using namespace std;


class COMTimer;

typedef struct _omtimer_thread_arg
{
	unsigned int period;
	unsigned int nrTimeouts;
	THREAD_HANDLE_RESULT thread_handle;
	THREAD_HANDLE_RESULT caller_thread_handle;
	THREAD_ID    thread_id;
	THREAD_ID    caller_thread_id;
	COMTimer*    handler;
}OMTIMER_THREAD_ARG, *POMTIMER_THREAD_ARG;

class COMTimer
{
public:
	COMTimer();
	virtual ~COMTimer();
	void Timer(unsigned int usecs);
	void PeriodicTimer(unsigned int usecs, unsigned int nrTimes=0);
	void StopTimer();
	void StopPeriodicTimer();
	virtual void HandleTimeout(void) = 0;
	virtual void HandlePeriodicTimeout(void) = 0;
private:
	auto_ptr<OMTIMER_THREAD_ARG> m_timer_arg;
	auto_ptr<OMTIMER_THREAD_ARG> m_periodic_timer_arg;
};


#endif
