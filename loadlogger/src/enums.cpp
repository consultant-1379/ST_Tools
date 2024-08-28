// enums.cpp
//==============================================================================
//
//  COPYRIGHT Ericsson España S.A. 2007
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
//! \file enums.cpp
//!
//! AUTHOR \n
//!    2007-03-27 by EEM/TIH/P Olov Marklund
//!                        olov.marklund@ericsson.com \n
// =============================================================================
//
//! CHANGES \n
//!    DATE           NAME      DESCRIPTION \n
//
//==============================================================================

#include "types.h"
#include "enums.h"

pchar enum_processorType2String(ProcessorTypeE type)
{
	switch(type)
	{
	case linuxProcessorE: return LINUXPROCESSOR;
	case loaderProcessorE: return LOADERPROCESSOR;
	case dicosProcessorE: return DICOSPROCESSOR;
	case excludedDicosProcessorE: return EXCLUDEDDICOSPROCESSOR;
	case unknownProcessorTypeE: return UNDEFINEDPROCESSOR;
	};
	return UNDEFINEDPROCESSOR;
}
