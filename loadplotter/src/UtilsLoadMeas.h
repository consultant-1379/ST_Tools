// UtilsLoadMeas.h
//==============================================================================
//
//  COPYRIGHT Ericsson España S.A. 2013
//  All rights reserved.
//
//  The Copyright to the computer program(s) herein
//  is the property of Ericsson España S.A.
//  The program(s) may be used and/or copied only
//  with the written permission from Ericsson España S.A.,
//  or in accordance with the terms and conditions
//  stipulated in the agreement/contract under which the program(s)
//  have been supplied.
//
//  Ericsson is in no way responsible for usage and adaptation of this
//  source by third parties, nor liable for any consequences of this.
//  This is the responsibility of the third party.
//
// ============================================================================
//
//! \file UtilsLoadMeas.h
//! \brief defines UtilsLoadMeas class
//!
//! AUTHOR \n
//!    2012-12-18 by Beatriz Prieto
//!                        beatriz.prieto@blue-tc.com \n
// =============================================================================
//
//! CHANGES \n
//!    DATE           NAME      DESCRIPTION \n
//      ...
//
//==============================================================================
#ifndef UTILSLOADMEAS_H
#define UTILSLOADMEAS_H

#include <memory>
#include <string>

#define BUFFLEN 65535
#define CP_MAX_BUFFER_SIZE 200
#define IDLE_PARAM_LABEL	"%idle"
#define MEMUSED_PARAM_LABEL	"%memused"
#define CPU_PARAM_LABEL		"%CPU"
#define MEM_PARAM_LABEL		"%MEM"


using namespace std;

class UtilsLoadMeas
{
public:


	bool confGetHeaderParams(char *fullstring);
	int parCount(char *instr, char *sep);
	float getFloatLoad(char *line);
	float getFloatMem(char *line);
	float getFloatLoadCmd(char *line);
	float getFloatMemCmd(char *line);
	int sendCmd(char *buff, int fd);
	int recvLine(int fd, char *buff, int timeout);
	string replaceAll(const string from, string m_const, const char *m_var);

	UtilsLoadMeas();
	virtual ~UtilsLoadMeas();

private:
	unsigned short labelOrder(char *fullstring, char *label, char* sep);
	float getParamNumber(char *in, int index);

};

#endif
