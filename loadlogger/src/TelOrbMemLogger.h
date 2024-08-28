// TelnetClient.h: interface for the CTelnetClient class.
//
//////////////////////////////////////////////////////////////////////

#ifndef TELORBMEMLOGGER_H
#define TELORBMEMLOGGER_H

#include "Telnet.h"
#include "structs.h"
#include "OMTimer.h"
#include <string>

using namespace std;

class CTelOrbMemLogger : public CTelnet, COMTimer  
{
public:
	bool startLogging();
	void SetTelnetHost(char* host, unsigned short port);

	//! \brief Sets the reading sampling interval
	//! \arg IN ival - The interval in seconds
	void SetLogInterval(int ival);

	CTelOrbMemLogger();
	virtual ~CTelOrbMemLogger();

	void ShutDown();


private:
	void HandlePeriodicTimeout();
	void HandleTimeout();
	void OnEvent(string theEvent);
	bool m_logReadings;
	int m_logInterval;
	unsigned int m_readings;
	vector<ProcInstance> m_procList;
	vector<string> m_processorGetInfoCmd;
	void OnConnectFailed(string theMsg);
	void OnInfo(string theInfo);
	void OnError(string theError);
};

#endif
