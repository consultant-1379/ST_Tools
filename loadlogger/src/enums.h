// enums.h
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
//! \file enums.h
//! \brief defines enumerated types used by loadlogger
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
#ifndef ENUMS_H
#define ENUMS_H

//! Enumerated for processor type
typedef enum _processor_typee
{
	linuxProcessorE,
	loaderProcessorE,
	dicosProcessorE,
	excludedDicosProcessorE,
	unknownProcessorTypeE
}ProcessorTypeE;
//! \addtogroup GlobalsMacroDefs
#ifdef ENUMS_H
//! @{
//! Defines the name for Linux processor used in the log files
#define LINUXPROCESSOR "Linux Processor"
//! Defines the name for loader processor used in the log files
#define LOADERPROCESSOR "Loader Processor"
//! Defines the name for dicos processor used in the log files
#define DICOSPROCESSOR "Dicos Processor"
//! Defines the name for excluded dicos processor used in the log files
#define EXCLUDEDDICOSPROCESSOR "Excluded Dicos Processor"
//! Defines the name for unknown processor type used in the log files
#define UNDEFINEDPROCESSOR "Unknown processor type"
//! @}
#endif
//! \brief Enumerated processor type to string function
//! \arg IN type           - Enumerated processoor type \n
//! \return Returns the processor type name string
extern char* enum_processorType2String(ProcessorTypeE type);
#endif
