#ifndef SCENARIO_GEN_H
#define SCENARIO_GEN_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <algorithm>

#include <vector>
#include <map>
#include <deque>
#include <list>

#include <errno.h>


using namespace std;

#define ISMSDA_TEMPLATE		"/traffic_IMS/IMS_Traffic.data"
#define ESM_TEMPLATE		"/traffic_EPC/EPC_Traffic.data"
#define OAM_TEMPLATE		"/traffic_OAM/OAM_Traffic.data"
#define WSM_TEMPLATE		"/traffic_WLAN/WLAN_Traffic.data"


enum TrafficType {
	ISMSDA,
	ESM,
	WSM,
	OAM,
        NOT_VALID               
};
  
struct ScriptData {
        string name;
	string trafficWeight;		
	string subcriberTypeName;
	deque  <string> params;
        bool toBeIncluded;
	bool addPre;
	bool addLoad;
	bool addPost;
        string base;
        string range;
	vector <string> groupName;                
};
  
struct TestCaseData {
	string name;
};
 
struct SubCounter {
	int counter;
};

struct Host {
        string name;
        int port;
        int nc;
        string local_ip;
};

struct DefineData {
        string name;
	string value;		
};
                                       
bool parseCommandLine (int argc, char **argv);
void displayHelp();
void purgeLine(char * line);
void readTemplateFile(string nameFile);
void readTrafficDescUserFile(string nameFile);
void readConfigurationFile(string nameFile);
bool filterLine (const char * line, string filter, bool after, string & element);
void excludeTraffiCase();
void addTrafficGroup();

void writeScenarioFile(string nameFile);
void writeDeploymentFile(string nameFile);
bool isPreNeeded();
bool isPostNeeded();
bool isAnyTcToBeIncluded();

string booleanToString(bool value);
string intToString(int value);
string addQuottes(string value);

bool prepareRangeInfo();
bool modTrafficCase(string Tc);
bool remTrafficCase(string Tc);
bool updateDefineParam(string name, string value);
bool updateDefine();
bool customizeDefine();
bool userModifyDefineParam(string userEntry);
bool changeRange(string value);
bool storeloadSched(string value);

inline
char my_toupper( char c )
{  return
   static_cast<char>( toupper( static_cast<unsigned char>( c ) ) );
}

#define RANGEEXECUTIONTYPE "{nrOfRangeLoop:={count:=1,actions:={}}}"


#define PHASELISTDECLARATORS_PREFIX "\ntsp_EPTF_ExecCtrl_PhaseList_Declarators :=\n{\n\t{\n\t  name := \"ExecPhases\",\n\t  phases :=\n\t    {"
#define PHASELISTDECLARATORS_SUFFIX "\n\t    }\n\t  }\n}\n\n"


#define SCENARIOGROUP_0   "tsp_EPTF_ExecCtrl_ScenarioGroup_Declarators :=\n{\n  {\n\tname := \"ScGroup_"
#define SCENARIOGROUP_1   "\",\n\texecMode := AUTOMATIC,\n\tscenarioNames := { \"eg_Tc_"
#define SCENARIOGROUP_2   "\" },\n\tphaseListName := \"ExecPhases\"\n  }\n}"


#define ENTITYGRPDECLARATORS_0 "tsp_LGenBase_EntityGrpDeclarators :=\n{\n\t{name := \"eg_Tc_"
#define ENTITYGRPDECLARATORS_1 "\", eType := \"CS_Entity_Tc_"
#define ENTITYGRPDECLARATORS_2 "\", eCount := "
#define ENTITYGRPDECLARATORS_3 "},\n\t{name := \"eg_LGen_"
#define ENTITYGRPDECLARATORS_4 "\", eType := \"CS_Entity_LGen_"
#define ENTITYGRPDECLARATORS_5 "}\n}"


#define SCENARIO2ENTITY_1 "tsp_EPTF_ExecCtrl_Scenario2EntityGroupList :=\n{\n\t{scenarioName := \""
#define SCENARIO2ENTITY_2 "\", eGrpName := \"eg_Tc_"
#define SCENARIO2ENTITY_3 "\", name := omit}\n}"






#define SCENARIO2ENTITYGROUPLIST_1 "tsp_EPTF_ExecCtrl_Scenario2EntityGroupList := {\n\t{scenarioName := \""
#define SCENARIO2ENTITYGROUPLIST_2 "\", eGrpName := \"eg_Tc_"
#define SCENARIO2ENTITYGROUPLIST_3 "\", name := omit}\n}"	

#define TCTYPEDECLARATORS2_PREFIX "tsp_LGenBase_TcMgmt_tcTypeDeclarators2 := {"
#define TCTYPEDECLARATORS2_SUFFIX "\n}\n"
#define TCTYPEDECLARATORS2_ELEM_PREFIX "\n\t{\n\t\tname := \""
#define TCTYPEDECLARATORS2_ELEM_MED "\",\n\t\tfsmName := \"EPTF_CS_FSM_Tc\",\n\t\tentityType := \"CS_Entity_Tc_"
#define TCTYPEDECLARATORS2_ELEM_SUFFIX "\",\n\t\tcustomEntitySucc := \"\"\n\t}"

#define LOADREGULATORS_PREFIX    "tsp_LoadRegulators := \n{"
#define LOADREGULATORS_SUFFIX    "\n}"

#define LOADREGULATORS_1  "\n\t{\n\t  host := $LOAD_REG_HOSTNAME,\n\t  name := \"LoadReg"
//#define LOADREGULATORS_1  "\n\t{\n\t  host := \"\",\n\t  name := \"LoadReg"
#define LOADREGULATORS_2  "\", \n\t  loadToReach :=" 
#define LOADREGULATORS_3  "\n\t}"

#define EXECCTRL_REGULATORNAMES_PREFIX   "tsp_EPTF_ExecCtrl_RegulatorNames :=\n{"
#define EXECCTRL_REGULATORNAMES_SUFFIX   "\n}"

#define EXECCTRL_REGULATEDITEMS_PREFIX   "tsp_EPTF_ExecCtrl_RegulatedItems :=\n{"
#define EXECCTRL_REGULATEDITEMS_SUFFIX   "\n}"

#define REGULATEDITEMS_1   "\n\t{\n\t  idName := {\n\t\tcps_SCInPhase := {\n\t\t  eGrpName := \"eg_Tc_"
#define REGULATEDITEMS_2   "\",\n\t\t  scName := \""
#define REGULATEDITEMS_3   "\",\n\t\t  phase := \""
#define REGULATEDITEMS_4   "\"\n\t\t}\n\t  },\n\t  weight := 1.0,\n\t  enabled := ${ENABLE_REG, boolean},\n\t  regulatorName := \"LoadReg"
#define REGULATEDITEMS_5   "\"\n\t}"


#define SCENARIODECLARATORS3_PREFIX "tsp_LGenBase_TcMgmt_ScenarioDeclarators3 := {\n\t{\n\t\tname := \""
#define SCENARIODECLARATORS3_SUFFIX "\n\t}\n}"
#define TC_LIST_PREFIX "\t\ttcList := {"
#define TC_LIST_SUFFIX "\n\t\t},\n"

#define TC_ELEMENT_SUB_1 "\n\t\t\t{\n\t\t\t\ttcName := \""
#define TC_ELEMENT_SUB_2 "\",\n\t\t\t\ttcParamsList := {\n\t\t\t\t\t{target := { "
#define TC_ELEMENT_SUB_3 "}},\n\t\t\t\t\t{enableEntitiesAtStart := true},\n\t\t\t\t\t{ranges := {{name := \"subscriber id\", enableSplit := true, baseOffset := " 
#define TC_ELEMENT_SUB_4 "}},\n\t\t\t\t\t{params := {\n"
#define TC_ELEMENT_SUB_5 "\n\t\t\t\t\t\t}\n\t\t\t\t\t},\n\t\t\t\t\t{trafficStartFinish := {\n"
#define TC_ELEMENT_SUB_6 "\n\t\t\t\t\t\t}\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}"

#define SC_PARAM_LIST_PREFIX "\t\tscParamsList := {\n\t\t\t{weightedScData := {cpsToReach := ${NUMOFCPS, float}, lockCPS := ${LOCKCPS, boolean}, deterministicMix := true, scheduler := omit}},\n\t\t\t{phaseListName := \"ExecPhases\"},\n"
#define SC_PARAM_LIST_SUFFIX "\n\t\t}\n"

#define FINISH_COND_SUB_0       "\t\t\t{phaseFinishConditions := {"
#define FINISH_COND_SUB_1_1     "\n\t\t\t\t{\n\t\t\t\t\tphase := \"preexec\",\n\t\t\t\t\tconditions := {"
#define FINISH_COND_SUB_1_2     "\n\t\t\t\t\t}\n\t\t\t\t}"
#define FINISH_COND_SUB_2_1     "\n\t\t\t\t{\n\t\t\t\t\tphase := \"loadgen\",\n\t\t\t\t\tconditions := {"
#define FINISH_COND_SUB_2_2     "\n\t\t\t\t\t}\n\t\t\t\t}"
#define FINISH_COND_SUB_3_1     "\n\t\t\t\t{\n\t\t\t\t\tphase := \"postexec\",\n\t\t\t\t\tconditions := {"
#define FINISH_COND_SUB_3_2     "\n\t\t\t\t\t}\n\t\t\t\t}"
#define FINISH_COND_SUB_4       "\n\t\t\t}},"

#define CHANGE_ACTIONS_SUB_0    "\n\t\t\t{phaseStateChangeActions := {"

#define CHANGE_ACTIONS_SUB_1_1  "\n\t\t\t\t{\n\t\t\t\t\tphase := \"preexec\",\n\t\t\t\t\tstate := RUNNING,\n\t\t\t\t\tactions := {"
#define CHANGE_ACTIONS_SUB_1_2  "\n\t\t\t\t\t}\n\t\t\t\t}"


#define CHANGE_ACTIONS_SUB_2_1  "\n\t\t\t\t{\n\t\t\t\t\tphase := \"preexec\",\n\t\t\t\t\tstate := STOPPING,\n\t\t\t\t\tactions := {"
#define CHANGE_ACTIONS_SUB_2_2  "\n\t\t\t\t\t}\n\t\t\t\t}"

#define CHANGE_ACTIONS_SUB_3_1  "\n\t\t\t\t{\n\t\t\t\t\tphase := \"loadgen\",\n\t\t\t\t\tstate := RUNNING,\n\t\t\t\t\tactions := {"
#define CHANGE_ACTIONS_SUB_3_2  "\n\t\t\t\t\t}\n\t\t\t\t}"

#define CHANGE_ACTIONS_SUB_4_1  "\n\t\t\t\t{\n\t\t\t\t\tphase := \"loadgen\",\n\t\t\t\t\tstate := STOPPING,\n\t\t\t\t\tactions := {"
#define CHANGE_ACTIONS_SUB_4_2  "\n\t\t\t\t\t}\n\t\t\t\t}"

#define CHANGE_ACTIONS_SUB_5_1  "\n\t\t\t\t{\n\t\t\t\t\tphase := \"postexec\",\n\t\t\t\t\tstate := RUNNING,\n\t\t\t\t\tactions := {"
#define CHANGE_ACTIONS_SUB_5_2  "\n\t\t\t\t\t}\n\t\t\t\t}"

#define CHANGE_ACTIONS_SUB_6_1  "\n\t\t\t\t{\n\t\t\t\t\tphase := \"postexec\",\n\t\t\t\t\tstate := STOPPING,\n\t\t\t\t\tactions := {"
#define CHANGE_ACTIONS_SUB_6_2  "\n\t\t\t\t\t}\n\t\t\t\t}"


#define CHANGE_ACTIONS_SUB_7 "\n\t\t\t}}"

 
#endif
