// OMTimer.cpp: implementation of the COMTimer class.
//
//////////////////////////////////////////////////////////////////////

#include "OMTimer.h"
#ifndef _WIN32
#include <unistd.h>
#include <stdio.h>
#endif
//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

#ifdef _WIN32
DWORD WINAPI
#else
void*
#endif
_TimerThread(void* arg);

#ifdef _WIN32
DWORD WINAPI
#else
void*
#endif
_PeriodicTimerThread(void* arg);

#ifdef _WIN32
DWORD WINAPI
#else
void*
#endif
_CallerThread(void* arg);


COMTimer::COMTimer()
: m_timer_arg(new OMTIMER_THREAD_ARG)
, m_periodic_timer_arg(new OMTIMER_THREAD_ARG)
{
	m_timer_arg.get()->thread_id = 0;
	m_timer_arg.get()->caller_thread_id = 0;
	m_timer_arg.get()->thread_handle = 0;
	m_timer_arg.get()->caller_thread_handle = 0;

	m_periodic_timer_arg.get()->thread_id = 0;
	m_periodic_timer_arg.get()->caller_thread_id = 0;
	m_periodic_timer_arg.get()->thread_handle = 0;
	m_periodic_timer_arg.get()->caller_thread_handle = 0;
}

COMTimer::~COMTimer()
{
	StopPeriodicTimer();
	StopTimer();
}

void COMTimer::Timer(unsigned int usecs)
{
	m_timer_arg.get()->period = usecs;
	m_timer_arg.get()->nrTimeouts = 0;
	m_timer_arg.get()->handler = this;
#ifdef _DEBUG
printf("Timer %p %u %u\n",m_timer_arg.get()->handler
			,m_timer_arg.get()->period
			,m_timer_arg.get()->nrTimeouts);
#endif
	CREATE_THREAD(_TimerThread,m_timer_arg.get()
				,m_timer_arg.get()->thread_id
				,m_timer_arg.get()->thread_handle);
}

void COMTimer::PeriodicTimer(unsigned int usecs, unsigned int nrTimes)
{
	m_periodic_timer_arg.get()->period = usecs;
	m_periodic_timer_arg.get()->nrTimeouts = nrTimes;
	m_periodic_timer_arg.get()->handler = this;

#ifdef _DEBUG
	printf("PeriodicTimer %p %u %u\n",m_periodic_timer_arg.get()->handler
				,m_periodic_timer_arg.get()->period
				,m_periodic_timer_arg.get()->nrTimeouts);
#endif
	CREATE_THREAD(_PeriodicTimerThread,m_periodic_timer_arg.get()
					,m_periodic_timer_arg.get()->thread_id
					,m_periodic_timer_arg.get()->thread_handle);
}

void COMTimer::StopTimer()
{
#ifdef _WIN32
#ifdef _DEBUG
	 printf("Killing timer %u\n",m_timer_arg.get()->thread_handle);
#endif
	 KILL_THREAD(m_timer_arg.get()->thread_handle);
	 DWORD ecode = STILL_ACTIVE;
	 while((ecode==STILL_ACTIVE) && (GetExitCodeThread(m_timer_arg.get()->thread_handle,&ecode)!=0))
	 {
		SLEEP(100);
	 }
#ifdef _DEBUG
	 printf("Killed timer %u\n",m_timer_arg.get()->thread_handle);
#endif
#else
#ifdef _DEBUG
	 printf("Killing timer %u\n",m_timer_arg.get()->thread_id);
#endif
	 if(m_timer_arg.get()->thread_id==0) return;
	 KILL_THREAD(m_timer_arg.get()->thread_id);
	 while(pthread_kill(m_timer_arg.get()->thread_id,0)==0)
	 {
		 SLEEP(100);
	 }
#ifdef _DEBUG
	 printf("Killed timer %u\n",m_timer_arg.get()->thread_id);
#endif
#endif
}

void COMTimer::StopPeriodicTimer()
{
#ifdef _WIN32
	 KILL_THREAD(m_periodic_timer_arg.get()->thread_handle);
	 DWORD ecode = STILL_ACTIVE;
	 while((ecode==STILL_ACTIVE) && (GetExitCodeThread(m_timer_arg.get()->thread_handle,&ecode)!=0))
	 {
		SLEEP(100);
	 }
#ifdef _DEBUG
	 printf("Killed periodic %u\n",m_periodic_timer_arg.get()->thread_handle);
#endif
	 KILL_THREAD(m_periodic_timer_arg.get()->caller_thread_handle);
	 ecode = STILL_ACTIVE;
	 while((ecode==STILL_ACTIVE) && (GetExitCodeThread(m_timer_arg.get()->caller_thread_handle,&ecode)!=0))
	 {
		SLEEP(100);
	 }
#ifdef _DEBUG
	printf("Killed caller %u\n",m_periodic_timer_arg.get()->caller_thread_handle);
#endif
#else //_WIN32
#ifdef _DEBUG
	 printf("Killing periodic %u\n",m_periodic_timer_arg.get()->thread_id);
#endif
	 if(m_periodic_timer_arg.get()->thread_id==0) return;
	 KILL_THREAD(m_periodic_timer_arg.get()->thread_id);
	 while(pthread_kill(m_periodic_timer_arg.get()->thread_id,0)==0)
	 {
		 SLEEP(100);
	 }
#ifdef _DEBUG
	 printf("Killed periodic %u\n",m_periodic_timer_arg.get()->thread_id);
	 m_periodic_timer_arg.get()->thread_id = 0;
	 printf("Killing caller %u\n",m_periodic_timer_arg.get()->caller_thread_id);
#endif
	 if(m_periodic_timer_arg.get()->caller_thread_id==0) return;

	 KILL_THREAD(m_periodic_timer_arg.get()->caller_thread_id);
	 while(pthread_kill(m_periodic_timer_arg.get()->caller_thread_id,0)==0)
	 {
		 SLEEP(100);
	 }
#ifdef _DEBUG
	 printf("Killed caller %u\n",m_periodic_timer_arg.get()->caller_thread_id);
	m_periodic_timer_arg.get()->caller_thread_id = 0;
#endif
#endif
}


#ifdef _WIN32
DWORD WINAPI
#else
void*
#endif
_TimerThread(void* arg)
{
	POMTIMER_THREAD_ARG theArgs = (POMTIMER_THREAD_ARG)arg;
#ifdef _DEBUG
printf("_TimerThread %p %u %u\n",theArgs->handler
				,theArgs->period
				,theArgs->nrTimeouts);
#endif
#ifndef _WIN32
	sigset_t set,pset;
	sigemptyset(&set);
	sigemptyset(&pset);
	sigaddset(&set, SIGINT);
	pthread_sigmask(SIG_BLOCK, &set, NULL);
#endif
	SLEEP(theArgs->period);
#ifndef _WIN32
		sigpending(&pset);
		if(__sigismember(&pset,SIGINT))	RETURN_THREAD(0);
#endif
	theArgs->handler->HandleTimeout();
	RETURN_THREAD(0);
}

#ifdef _WIN32
DWORD WINAPI
#else
void*
#endif
_PeriodicTimerThread(void* arg)
{
#ifndef _WIN32
	sigset_t set,pset;
	sigemptyset(&set);
	sigemptyset(&pset);
	sigaddset(&set, SIGINT);
	pthread_sigmask(SIG_BLOCK, &set, NULL);
#endif
	POMTIMER_THREAD_ARG theArgs = (POMTIMER_THREAD_ARG)arg;
	while(true)
	{
#ifndef _WIN32
		sigpending(&pset);
		if(__sigismember(&pset,SIGINT))	RETURN_THREAD(0);
#endif
#ifdef _DEBUG
printf("_PeriodicTimerThread %p %u %u\n",theArgs->handler
					,theArgs->period
					,theArgs->nrTimeouts);
#endif
		CREATE_THREAD(_CallerThread,theArgs
					,theArgs->caller_thread_id
					,theArgs->caller_thread_handle);
#ifdef _DEBUG
#ifdef _WIN32
		printf("%u Started %u for %p\n",theArgs->thread_handle,theArgs->caller_thread_handle,theArgs->handler);
		printf("%u going to sleep %u\n",theArgs->thread_handle,theArgs->period);
#else
		printf("%u Started %u for %p\n",theArgs->thread_id,theArgs->caller_thread_id,theArgs->handler);
		printf("%u going to sleep %u\n",theArgs->thread_id,theArgs->period);
#endif
#endif
		SLEEP(theArgs->period);
#ifdef _WIN32
		 DWORD ecode = STILL_ACTIVE;
		 while((ecode==STILL_ACTIVE) && (GetExitCodeThread(theArgs->caller_thread_handle,&ecode)!=0))
		 {
			SLEEP(100);
		 }
#else
		 while(pthread_kill(theArgs->caller_thread_id,0)==0)
		 {
			 SLEEP(100);
		 }
#endif
		if(theArgs->nrTimeouts>0)
		{
			theArgs->nrTimeouts--;
			if(theArgs->nrTimeouts==0) RETURN_THREAD(0);
		}
	}
	RETURN_THREAD(0);
}

#ifdef _WIN32
DWORD WINAPI
#else
void*
#endif
_CallerThread(void* arg)
{
	POMTIMER_THREAD_ARG theArgs = (POMTIMER_THREAD_ARG)arg;
#ifdef _DEBUG
printf("_CallerThread %p %u %u\n",theArgs->handler
					,theArgs->period
					,theArgs->nrTimeouts);
#endif
#ifdef _DEBUG
#ifdef _WIN32
	printf("Calling %p from %u\n",theArgs->handler,theArgs->caller_thread_handle);
#else
	printf("Calling %p from %u\n",theArgs->handler,theArgs->caller_thread_id);
#endif
#endif
	theArgs->handler->HandlePeriodicTimeout();
#ifdef _DEBUG
#ifdef _WIN32
	printf("Call to %p from %u done\n",theArgs->handler,theArgs->caller_thread_handle);
#else
	printf("Call to %p from %u done\n",theArgs->handler,theArgs->caller_thread_id);
#endif
#endif
	RETURN_THREAD(0);
}


