#include "scenarioDeployGenerator.h"
using namespace std;

string templateFile = "";


// output files
string scenarioFile = "scenario.cfg";
string deploymentFile = "deployment.cfg";
string defineFile = "define.cfg";

// input files
string configFile = "";
string trafficDescFile = "";



string scenarioName = "";
string regulatorName="";

map<string, ScriptData> tcDesc;
map<string, ScriptData>::iterator tcDescIter;

map <string, SubCounter> subType;
map <string, SubCounter>::iterator subTypeIter;

map <string, DefineData> defineParam;
map <string, DefineData> defineParamLayer;
map <string, DefineData> defineParamMO;
map <string, DefineData>::iterator defineParamIter;
map <string, DefineData>::iterator defineParamAuxIter;

deque <string> definedParam;
deque <string>::iterator definedParamIter;

vector <string> loadFilter;
vector <string>::iterator loadFilterIter;

vector <string> groupToExclude;
vector <string>::iterator groupToExcludeIter;

vector <string> groupToAdd;
vector <string>::iterator groupToAddIter;

vector <string> tcToExclude;
vector <string>::iterator tcToExcludeIter;

vector <Host> lgen;
vector <Host>::iterator  lgenIter;

deque <string> scheduleLoad;
deque <string>::iterator  scheduleLoadIter;

vector <Host> DiaProxy;
vector <Host>::iterator  diaProxyIter;

vector <Host> ldapProxy;
vector <Host>::iterator  ldapProxyIter;

Host guiHost;
Host conkeeperHost;
Host loadplotterHost;
string loadplotterPort;

TrafficType trafficType = NOT_VALID;

string vipo, vipt, ExtDB_ip;
string secvipo, secvipt;

string vip_oam, vip_dia_tcp, vip_dia_sctp, vip_radius,vip_controller,vip_soap, vip_udm, vip_soap_ldap;
string secvip_oam, secvip_dia_tcp,secvip_radius,secvip_controller;


string cpsDelta ,cpsDeltaPre ,cpsDeltaLoad ,cpsDeltaPost, numOfCps;
string ExecutionType, loadLevelPre, loadLevel, loadLevelPost;
string FileMask, ConsoleMask, LogFile;

bool use_conkeeper = false;
bool use_loadplotter = false;
bool use_gui = false;
bool slf_proxy_mode = true;
bool servermode = false;
bool headlessmode = false;
bool manualControl = true;
bool stats= true;
bool layer = false;
bool ExecutionTypeSet = false;
bool specificTrafficMix = false;

bool postNeeded = false;
bool preNeeded = false;

bool ttcn3start_used = false;

int  numOfPTCs;
int mcPort;


int main(int argc, char* argv[])
{

       	if (!parseCommandLine(argc, argv)){
		displayHelp();
		exit (1);                
	}        
        
	switch (trafficType){
		
		case  ISMSDA:
			templateFile = templateFile + ISMSDA_TEMPLATE;
			scenarioName = "ISMSDA";
                        regulatorName = "IsmSda";
			break;
		case  ESM:
			templateFile = templateFile + ESM_TEMPLATE;
			scenarioName = "ESM";
                        regulatorName = "Esm";
			break;    
		case  OAM:
			templateFile = templateFile + OAM_TEMPLATE;
			scenarioName = "OAM";
                        regulatorName = "Oam";
			break;
		case  WSM:
			templateFile = templateFile + WSM_TEMPLATE;
			scenarioName = "WSM";
                        regulatorName = "Wsm";
			break;
		default:    
			cout << endl << "ERROR: Unknown traffic type: "<< trafficType << endl << endl;
			exit (1);

	}
	
	readTemplateFile(templateFile);
	if (!trafficDescFile.empty())	readTrafficDescUserFile(trafficDescFile);
    
    readConfigurationFile(configFile);
    addTrafficGroup();


    if (layer){
    	for(defineParamIter = defineParamLayer.begin(); defineParamIter != defineParamLayer.end(); ++defineParamIter) {
    		DefineData myDefine = defineParamIter->second;
			defineParamAuxIter = defineParam.find(defineParamIter->first);
    		if (defineParamAuxIter == defineParam.end()){
    			pair<map<string, DefineData>::iterator,bool> myIter = defineParam.insert(make_pair(defineParamIter->first,myDefine));
    		}
    		else{
    			defineParamAuxIter->second = myDefine;
    		}
    	}
    }
    else {
    	for(defineParamIter = defineParamMO.begin(); defineParamIter != defineParamMO.end(); ++defineParamIter) {
    		DefineData myDefine = defineParamIter->second;
    		defineParamAuxIter = defineParam.find(defineParamIter->first);
    		if (defineParamAuxIter == defineParam.end()){
    			pair<map<string, DefineData>::iterator,bool> myIter = defineParam.insert(make_pair(defineParamIter->first,myDefine));
    		}
    		else{
    			defineParamAuxIter->second = myDefine;
    		}
    	}
    }
        
	excludeTraffiCase();
        
	if (!isAnyTcToBeIncluded()) {
		cout << endl << "ERROR:There is not a valid traffic case to be executed."<< endl << endl;
		exit (1);
	}
        
	if (lgen.empty()) {
		cout << endl << "ERROR:There must be at least one traffic generator."<< endl << endl;
		exit (1);
	}

	if (lgen.size() != 1 && ttcn3start_used) {
		cout << endl << "ERROR:There must be only one traffic generator when using ttcn3_start."<< endl << endl;
		exit (1);
	}
                
	preNeeded = isPreNeeded();
	postNeeded = isPostNeeded();
                              
	writeDeploymentFile(deploymentFile);
   	prepareRangeInfo();
 	writeScenarioFile(scenarioFile);                        
       
        
        
	cout << endl << scenarioFile <<" and "<<deploymentFile <<" for " << scenarioName <<" traffic created SUCCESSFULLY." << endl<< endl;	
                                                	
	return 0;
				
}  

void displayHelp()
{
	cout << endl << "Command line error."<< endl << endl;
				
	cout << "Usage:\t\tscenarioDeployGenerator -t <trafficType> -i <file> [-c <file>] [-s]"<< endl<< endl<< endl;
	cout << "\t\t-t <trafficType>\tAllowed values: ISMSDA | ESM | OAM | WSM "<< endl ;        
	cout << "\t\t-i <file>\t\tUser file with the list of Traffic cases to be configured"<< endl ;
	cout << "\t\t-c <file>\t\tConfiguration file "<< endl ;
	cout << "\t\t-s \t\t\tIndividual traffic cases will be included in Configuration file "<< endl ;
	cout << "\t\t-cfg_path \t\t\tSet specific BAT CONFIGURATION path"<< endl ;
	cout << " "<< endl<< endl;								
}

bool parseCommandLine (int argc, char **argv)
{
	for(int i=1;i<argc;i++){ 
															 
		if(strcmp(argv[i],"-i") == 0){
			i++;
			if(argc == i){ 
				return false;
			}
			trafficDescFile = argv [i];  
		} 
		else if(strcmp(argv[i],"-s") == 0){
			specificTrafficMix = true;  
		} 

		else if(strcmp(argv[i],"-cfg_path") == 0){
                    i++;
                    if(argc == i){ 
			return false;
		    }
                    templateFile = argv[i];
		} 

		else if (strcmp(argv[i],"-t") == 0){
			i++;
			if(argc == i){ 
				return false;
			}
			if      (!strcmp(argv [i],"ISMSDA"))   trafficType = ISMSDA;
			else if (!strcmp(argv [i],"ESM"))      trafficType = ESM;
			else if (!strcmp(argv [i],"WSM"))      trafficType = WSM;
			else if (!strcmp(argv [i],"OAM"))      trafficType = OAM;
			else {
				cout << endl << "ERROR: Wrong traffic type."<< endl << endl;
				return false;
			}					
		}
		else if(strcmp(argv[i],"-c") == 0){
			i++;
			if(argc == i){ 
				return false;
			}
			configFile = argv [i];      
		} else {
			return false;                
		}         		
	}
	
	if (configFile.empty()) {
		cout << endl << "ERROR: Configuration file missing."<< endl << endl;
		return false;
	} 
        				
        if (trafficType == NOT_VALID) {
		cout << endl << "ERROR: Traffic type missing."<< endl << endl;
		return false;
	}					
	return true;     
}

void readTemplateFile(string nameFile)
{
	char line [1024]; 
	string element, filter;
	bool after;
	ifstream inFile;       
	inFile.open (nameFile.c_str());
				
	if (!inFile) {
		cout << endl << "ERROR:Failed to open file: " << nameFile << endl << endl;
		exit (1);                
	}
	ScriptData    scriptData;
	scriptData.trafficWeight = "trafficWeight := 1.000000";
	scriptData.addPre = true;	 
	scriptData.addPost = true;	 
                                        
	if (trafficType == WSM){
		scriptData.toBeIncluded = true;
		scriptData.addLoad = false;
	}
	else {
		scriptData.toBeIncluded = false;
		scriptData.addLoad = true;
	}
        
	while(inFile) {
		inFile.getline(line, 1024);
		purgeLine(line);

		after = false;  
		filter = ":=";
		if (filterLine(line, filter, after, element)) {			
			if (!strcmp(element.c_str(),"tcName")){
				
				if (!scriptData.name.empty()) {
					tcDesc.insert(make_pair(scriptData.name,scriptData)); 
					scriptData.name.erase();
					scriptData.trafficWeight.erase();
					scriptData.subcriberTypeName.erase();
					scriptData.params.clear();
					scriptData.groupName.clear();
					scriptData.addPre = true;	 
					scriptData.addPost = true;
                                        
                                        if (trafficType == WSM){
                                        	scriptData.toBeIncluded = true;
                                                scriptData.addLoad = false;
                                        }
                                        else {
                                        	scriptData.toBeIncluded = false;
                                                scriptData.addLoad = true;
                                        }
                                                                                                	
				}
				
				after = true;  
				filter = "tcName:=";
                                
				if   (filterLine(line, filter, after, element)) {
					scriptData.name = element;
				}
			}
			else if (!strcmp(element.c_str(),"subcriberType")){
				after = true;  
				filter = "subcriberType:=";
				if   (filterLine(line, filter, after, element)) { 

					subTypeIter = subType.find(element);
					if (subTypeIter == subType.end()) {
                                                SubCounter temp;
                                                temp.counter = (int)0;
						subType.insert(make_pair(element,temp)); 
					}					 
					scriptData.subcriberTypeName = element;
				}
			}
			
			else if (!strcmp(element.c_str(),"preRequired")){
				after = true;  
				filter = "preRequired:=";
				if   (filterLine(line, filter, after, element)) { 
					if (!strcmp(element.c_str(),"true"))	scriptData.addPre = true;
					else                                scriptData.addPre = false;
				}
			}
			
			else if (!strcmp(element.c_str(),"postRequired")){
				after = true;  
				filter = "postRequired:=";
				if   (filterLine(line, filter, after, element)) { 
					if (!strcmp(element.c_str(),"true"))	scriptData.addPost = true;
					else                                scriptData.addPost = false;
				}
			}
						
			else if (!strcmp(element.c_str(),"trafficWeight")){
				scriptData.trafficWeight = line;;         
			}
			else if (!strcmp(element.c_str(),"pName")){
				string param = line;
				scriptData.params.push_back(param);         
			}
                        
			else if (!strcmp(element.c_str(),"groupName")){
				after = true;  
				filter = "groupName:=";
				if   (filterLine(line, filter, after, element)) { 
                                        transform( element.begin(), element.end(), element.begin(), my_toupper );
					scriptData.groupName.push_back(element);         
				}
			}
                        
			else if (!strcmp(element.c_str(),"FileMask")){
				after = true;  
				filter = "FileMask:=";
				if   (filterLine(line, filter, after, FileMask)) {
                                         
				}
			}
			
			else if (!strcmp(element.c_str(),"ConsoleMask")){
				after = true;  
				filter = "ConsoleMask:=";
				if   (filterLine(line, filter, after, ConsoleMask)) {
                                         
				}
			}
			else if (!strcmp(element.c_str(),"LogFile")){
				after = true;  
				filter = "LogFile:=";
				if   (filterLine(line, filter, after, LogFile)) {
                                         
				}
			}
			else if (!strcmp(element.c_str(),"numOfPTCs")){
				after = true;  
				filter = "numOfPTCs:=";
				if   (filterLine(line, filter, after, element)) {
                                         numOfPTCs = atoi(element.c_str());
				}
			}
			else if (!strcmp(element.c_str(),"Range")){
				after = true;  
				filter = "Range:=";
				if   (filterLine(line, filter, after, element)) {
					ExecutionType = "{nrOfRangeLoop := {count := " + element + ",actions := {}}}";
                                        ExecutionTypeSet = true;
                                        if (element == "1")	updateDefineParam("CYCLIC", "false");
                                        else			updateDefineParam("CYCLIC", "true");
				}
			}
                        else if (!strcmp(element.c_str(),"Time")){
				after = true;  
				filter = "Time:=";
				if   (filterLine(line, filter, after, element)) {
					ExecutionType = "{execTime := {time := " + element + ",actions := {}}}";
                                        ExecutionTypeSet = true;
                                        updateDefineParam("CYCLIC", "true");
				}
			}
		}
				
		after = true;  
		filter = "DEFINE";
		if (filterLine(line, filter, after, element)) {			
                        DefineData myDefine;
                        
                        after = false;
                        filter = ":=";
                        strcpy(line, element.c_str());
                        if (filterLine(line, filter, after, myDefine.name)) {
                            	pair<map<string, DefineData>::iterator,bool> myIter = defineParam.insert(make_pair(myDefine.name,myDefine));
                                after = true;
                                filter = ":=";
                                if (filterLine(line, filter, after, myIter.first->second.value)) {}
                        }
		}

		filter = "DEF_LAYER";
		if (filterLine(line, filter, after, element)) {
                        DefineData myDefine;

                        after = false;
                        filter = ":=";
                        strcpy(line, element.c_str());
                        if (filterLine(line, filter, after, myDefine.name)) {
                            	pair<map<string, DefineData>::iterator,bool> myIter = defineParamLayer.insert(make_pair(myDefine.name,myDefine));
                                after = true;
                                filter = ":=";
                                if (filterLine(line, filter, after, myIter.first->second.value)) {}

                        }
		}

		filter = "DEF_MO";
		if (filterLine(line, filter, after, element)) {
                        DefineData myDefine;
                        
                        after = false;
                        filter = ":=";
                        strcpy(line, element.c_str());
                        if (filterLine(line, filter, after, myDefine.name)) {
                            	pair<map<string, DefineData>::iterator,bool> myIter = defineParamMO.insert(make_pair(myDefine.name,myDefine));
                                after = true;
                                filter = ":=";
                                if (filterLine(line, filter, after, myIter.first->second.value)) {}
                        }
		}

	}

	// Add last elemente        
  	if (!scriptData.name.empty()) {
		tcDesc.insert(make_pair(scriptData.name,scriptData)); 
	}

        
	inFile.close();	
        						 
}
bool prepareRangeInfo()
{
	stringstream valueString;
        string base, range;
        int counter;
	char line [1024]; 
	string element, filter, type;
	bool after;

	for(subTypeIter = subType.begin();subTypeIter != subType.end();subTypeIter++){
		subTypeIter->second.counter = 0;  
	}
        
	for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                        
		if (tcDescIter->second.toBeIncluded == false)	continue;
              
                subTypeIter = subType.find(tcDescIter->second.subcriberTypeName);
                type = subTypeIter->first.c_str();
                
                strcpy(line, type.c_str());
                after = true;
                filter = "$";
                if (filterLine(line, filter, after, element)){
                    defineParamIter = defineParam.find(element);
                    if (defineParamIter != defineParam.end()) {
                        type = defineParamIter->second.value;
		    }
                    
                    subTypeIter = subType.find(type);
                }
		
                base = "BASE_" + type;
                range = "SUBS_PER_SCRIPT_" + type;
                counter = subTypeIter->second.counter ++;			

		if (subTypeIter == subType.end()) {
			cout << endl << "ERROR:Unknowm subType " << tcDescIter->second.subcriberTypeName << endl << endl;
			exit (1);                
		}
                
                if (tcDescIter->second.range.empty()){
                	valueString << "${" << range <<",integer}";
                        tcDescIter->second.range = valueString.str();
                        valueString.clear();
                        valueString.str("");
                }
                        
                 if (tcDescIter->second.base.empty()){
                	valueString << counter << " * ${" << range << ",integer} + ${" << base << ",integer}";
                        tcDescIter->second.base = valueString.str();
                        valueString.clear();
                        valueString.str("");
                }
	}
                
        
        
}
void readTrafficDescUserFile(string nameFile)
{
	char line [1024]; 
	string element, filter, name,value;
	bool after;
	ifstream inFile;       
	inFile.open (nameFile.c_str());
				
	if (!inFile) {
		cout << endl << "ERROR:Failed to open file: " << nameFile << endl<< endl;
		exit (1);                
	}
	
	TestCaseData testCaseData;
				
	while(inFile) {
		inFile.getline(line, 1024);
		purgeLine(line);
		after = false;  
		filter = ":=";
		if (filterLine(line, filter, after, element)) {
			if (!strcmp(element.c_str(),"tcName")){
				after = true;  
				filter = "tcName:=";
				if   (filterLine(line, filter, after, element)) {
                                        tcDescIter = tcDesc.find(element);
                                        if (tcDescIter != tcDesc.end() && !specificTrafficMix) {
                                                tcDescIter->second.toBeIncluded = true;
                                                tcDescIter->second.addLoad = true;
                                        }
				}
			}                        
                        
		}
                
		after = true;  
		filter = "addToGroup";
		if (filterLine(line, filter, after, element)) {			
                        
                        after = false;
                        filter = ":=";
                        strcpy(line, element.c_str());
                        if (filterLine(line, filter, after, value)) {
                                after = true;
                                filter = ":=";
                                if (filterLine(line, filter, after, name)) { 
                                
                                        tcDescIter = tcDesc.find(name);
                                        if (tcDescIter != tcDesc.end()) {
                                                tcDescIter->second.groupName.push_back(value);  
                                        }
 				}
                        }
                }
                
 		after = true;  
		filter = "remFromGroup";
		if (filterLine(line, filter, after, element)) {			
                        
                        after = false;
                        filter = ":=";
                        strcpy(line, element.c_str());
                        if (filterLine(line, filter, after, value)) {
                                after = true;
                                filter = ":=";
                                if (filterLine(line, filter, after, name)) { 
                                
                                        tcDescIter = tcDesc.find(name);
                                        if (tcDescIter != tcDesc.end()) {
                                            vector <string>::iterator groupIter = find(tcDescIter->second.groupName.begin(),
                                                                                       tcDescIter->second.groupName.end(),
                                                                                       value);
                                            if (groupIter != tcDescIter->second.groupName.end())  {
                                                tcDescIter->second.groupName.erase(groupIter);                           
                                            }
                                        }
 				}
                        }
                }
                
		after = true;  
		filter = "DEFINE";
		if (filterLine(line, filter, after, element)) {			
                        
			after = false;
            filter = ":=";
            strcpy(line, element.c_str());
            if (filterLine(line, filter, after, name)) {
            	after = true;
             	filter = ":=";
             	if (filterLine(line, filter, after, value)) {
					bool paramNotFound=true;
					for(defineParamIter = defineParam.begin(); defineParamIter != defineParam.end(); ++defineParamIter) {
						if (defineParamIter->first.find(name) != string::npos && !value.empty()){
							defineParamIter->second.value = value;
                        	paramNotFound=false;
                        	break;
                		}
        			}
                  	if (paramNotFound)
                  		cout << endl << "WARNING:Wrong define parameter to be modified: " << name << endl<< endl;
					}
            }
		}

		filter = "DEF_LAYER";
		if (filterLine(line, filter, after, element)) {

			after = false;
            filter = ":=";
            strcpy(line, element.c_str());
            if (filterLine(line, filter, after, name)) {
            	after = true;
             	filter = ":=";
             	if (filterLine(line, filter, after, value)) {
					bool paramNotFound=true;
					for(defineParamIter = defineParamLayer.begin(); defineParamIter != defineParamLayer.end(); ++defineParamIter) {
						if (defineParamIter->first.find(name) != string::npos && !value.empty()){
							defineParamIter->second.value = value;
                        	paramNotFound=false;
                        	break;
                		}
        			}
                  	if (paramNotFound)
                  		cout << endl << "WARNING:Wrong define parameter to be modified: " << name << endl<< endl;
					}
            }
		}

		filter = "DEF_MO";
		if (filterLine(line, filter, after, element)) {

			after = false;
            filter = ":=";
            strcpy(line, element.c_str());
            if (filterLine(line, filter, after, name)) {
            	after = true;
             	filter = ":=";
             	if (filterLine(line, filter, after, value)) {
					bool paramNotFound=true;
					for(defineParamIter = defineParamMO.begin(); defineParamIter != defineParamMO.end(); ++defineParamIter) {
						if (defineParamIter->first.find(name) != string::npos && !value.empty()){
							defineParamIter->second.value = value;
                        	paramNotFound=false;
                        	break;
                		}
        			}
                  	if (paramNotFound)
                  		cout << endl << "WARNING:Wrong define parameter to be modified: " << name << endl<< endl;
					}
            }
		}



	}




	inFile.close();
	              
}

void readConfigurationFile(string nameFile)
{
	char line [1024]; 
	string element, filter;
	bool after;
	ifstream inFile;       
	inFile.open (nameFile.c_str());
				
	if (!inFile) {
		cout << endl << "ERROR:Failed to open file: " << nameFile << endl<< endl;
		exit (1);                
	}
	
	TestCaseData testCaseData;
        Host host;
				
	while(inFile) {
		inFile.getline(line, 1024);
		purgeLine(line);
		after = false;  
		filter = ":=";
		if (filterLine(line, filter, after, element)) {
                        
                        if (!strcmp(element.c_str(),"Time")){
				after = true;  
				filter = "Time:=";
				if   (filterLine(line, filter, after, element)) {
					ExecutionType = "{execTime := {time := " + element + ",actions := {}}}";
                                        ExecutionTypeSet = true;
                                        updateDefineParam("CYCLIC", "true");
				}
			}
			else if (!strcmp(element.c_str(),"Range")){
				after = true;  
				filter = "Range:=";
				if   (filterLine(line, filter, after, element)) {
					ExecutionType = "{nrOfRangeLoop := {count := " + element + ",actions := {}}}";
                                        ExecutionTypeSet = true;
                                        if (element == "1")	updateDefineParam("CYCLIC", "false");
                                        else			updateDefineParam("CYCLIC", "true");
				}
			}
			else if (!strcmp(element.c_str(),"Exec")){
				after = true;  
				filter = "Exec:=";
				if   (filterLine(line, filter, after, element)) {
					ExecutionType = "{nrOfExecStart := {count := " + element + ",actions := {}}}";
                                        ExecutionTypeSet = true;
                                        updateDefineParam("CYCLIC", "true");
				}
			}
                        
			else if (!strcmp(element.c_str(),"lgen")){
				after = true;  
				filter = "lgen:=";
				if   (filterLine(line, filter, after, element)) {                                        
					host.name = element;
					lgen.push_back(host);
				}
			}
                                               
			else if (!strcmp(element.c_str(),"guiHost")){
				after = true;  
				filter = "guiHost:=";
				if   (filterLine(line, filter, after, element)) {                                        
					guiHost.name = element;
                                        use_gui = true;
				}
			}
                         
			else if (!strcmp(element.c_str(),"remGroupName")){
				after = true;  
				filter = "remGroupName:=";
				if   (filterLine(line, filter, after, element)) { 
                                        transform( element.begin(), element.end(), element.begin(), my_toupper );
					groupToExclude.push_back(element);
				}
			}
                         
            else if (!strcmp(element.c_str(),"trafficGroupName")){
                after = true;  
                filter = "trafficGroupName:=";
                if   (filterLine(line, filter, after, element)) { 
                                        transform( element.begin(), element.end(), element.begin(), my_toupper );
                    groupToAdd.push_back(element);
                }
            }
                         
			else if (!strcmp(element.c_str(),"guiPort")){
				after = true;  
				filter = "guiPort:=";
				if   (filterLine(line, filter, after, element)) {                                        
					guiHost.port = atoi (element.c_str());
				}
			}
                       
			else if (!strcmp(element.c_str(),"conkeeperHost")){
				after = true;  
				filter = "conkeeperHost:=";
				if   (filterLine(line, filter, after, element)) {                                        
					conkeeperHost.name = element;
                                        use_conkeeper = true;
				}
			}
                         
			else if (!strcmp(element.c_str(),"conkeeperPort")){
				after = true;  
				filter = "conkeeperPort:=";
				if   (filterLine(line, filter, after, element)) {                                        
					conkeeperHost.port = atoi (element.c_str());
				}
			}
                                                
			else if (!strcmp(element.c_str(),"loadplotterHost")){
				after = true;  
				filter = "loadplotterHost:=";
				if   (filterLine(line, filter, after, element)) {                                        
					loadplotterHost.name = element;
                                        use_loadplotter = true;
				}
			}
                         
			else if (!strcmp(element.c_str(),"loadplotterPort")){
				after = true;  
				filter = "loadplotterPort:=";
				if   (filterLine(line, filter, after, element)) { 
                                        loadplotterPort =  element;                                      
					loadplotterHost.port = atoi (element.c_str());
				}
			}
                                                
			else if (!strcmp(element.c_str(),"diaProxy")){

                string base(line);
                string delimiter = "diaProxy:=";
                size_t pos = 0;
                base.erase(0,delimiter.length());
                delimiter = ":";

                if ((pos = base.find(delimiter)) != string::npos){
                    host.name = base.substr(0, pos);
                    base.erase(0, pos + delimiter.length());

                    if ((pos = base.find(delimiter)) != string::npos){
                        host.port = atoi (base.substr(0, pos).c_str());
                        base.erase(0, pos + delimiter.length());

                        if ((pos = base.find(delimiter)) != string::npos){
                        	host.nc = atoi (base.c_str());
                        	base.erase(0, pos + delimiter.length());
							host.local_ip = base;
                        }
                        else{
                        	host.nc = 0;
                        	host.local_ip = "";
                        }
                    }
                    else {
                        host.port = atoi (base.c_str());
                        host.nc = 0;
                        host.local_ip = "";
                    }
                    DiaProxy.push_back(host);
                }
            }
			else if (!strcmp(element.c_str(),"mcPort")){
				after = true;  
				filter = "mcPort:=";
				if   (filterLine(line, filter, after, element)) {                                        
					mcPort = atoi (element.c_str());
				}
			}

			else if (!strcmp(element.c_str(),"vip_oam")){
				after = true;  
				filter = "vip_oam:=";
				if   (filterLine(line, filter, after, element)) {                                        
					 vip_oam = element;
				}
			}

            else if (!strcmp(element.c_str(),"vip_soap")){
                after = true;  
                filter = "vip_soap:=";
                if   (filterLine(line, filter, after, element)) {                                        
                     vip_soap = element;
                }
            }

			else if (!strcmp(element.c_str(),"vip_dia_tcp")){
				after = true;  
				filter = "vip_dia_tcp:=";
				if   (filterLine(line, filter, after, element)) {
					 vip_dia_tcp = element;
				}
			}

			else if (!strcmp(element.c_str(),"vip_dia_sctp")){
				after = true;  
				filter = "vip_dia_sctp:=";
				if   (filterLine(line, filter, after, element)) {                                        
					 vip_dia_sctp = element;
				}
			}
			else if (!strcmp(element.c_str(),"vip_radius")){
				after = true;  
				filter = "vip_radius:=";
				if   (filterLine(line, filter, after, element)) {                                        
					 vip_radius = element;
				}
			}
                        
            else if (!strcmp(element.c_str(),"vip_udm")){
                after = true;  
                filter = "vip_udm:=";
                if   (filterLine(line, filter, after, element)) {                                        
                     vip_udm = element;
                }
            }
                        
            else if (!strcmp(element.c_str(),"vip_soap_ldap")){
                after = true;  
                filter = "vip_soap_ldap:=";
                if   (filterLine(line, filter, after, element)) {                                        
                     vip_soap_ldap = element;
                }
            }
                        
			else if (!strcmp(element.c_str(),"vip_controller")){
				after = true;  
				filter = "vip_controller:=";
				if   (filterLine(line, filter, after, element)) {                                        
					 vip_controller = element;
				}
			}
                        
			else if (!strcmp(element.c_str(),"secvip_oam")){
				after = true;  
				filter = "secvip_oam:=";
				if   (filterLine(line, filter, after, element)) {                                        
					 secvip_oam = element;
				}
			}
                        
			else if (!strcmp(element.c_str(),"secvip_dia_tcp")){
				after = true;  
				filter = "secvip_dia_tcp:=";
				if   (filterLine(line, filter, after, element)) {                                        
					 secvip_dia_tcp = element;
				}
			}
                        
			else if (!strcmp(element.c_str(),"secvip_radius")){
				after = true;  
				filter = "secvip_radius:=";
				if   (filterLine(line, filter, after, element)) {                                        
					 secvip_radius = element;
				}
			}
                        
			else if (!strcmp(element.c_str(),"secvip_controller")){
				after = true;  
				filter = "secvip_controller:=";
				if   (filterLine(line, filter, after, element)) {                                        
					 secvip_controller = element;
				}
			}
                        
			else if (!strcmp(element.c_str(),"ExtDB_ip")){
				after = true;  
				filter = "ExtDB_ip:=";
				if   (filterLine(line, filter, after, element)) {                                        
					 ExtDB_ip = element;
				}
			}
                        
			else if (!strcmp(element.c_str(),"layer")){
				after = true;  
				filter = "layer:=";
				if   (filterLine(line, filter, after, element)) { 
                	if (element == "true" || element == "TRUE"){
                    	layer = true;
                    }
					else {
                    	layer = false;
                    }
				}
			}

            else if (!strcmp(element.c_str(),"ttcn3_start")){
				after = true;  
				filter = "ttcn3_start:=";
				if   (filterLine(line, filter, after, element)) { 
                    if (element == "true" || element == "TRUE")	ttcn3start_used = true;
					else						ttcn3start_used = false;
				}
			}
                                                
			else if (!strcmp(element.c_str(),"stats")){
				after = true;  
				filter = "stats:=";
				if   (filterLine(line, filter, after, element)) { 
                                        if (element == "true" || element == "TRUE")	stats = true;                                         
					else						stats = false;
				}
			}
                        
			else if (!strcmp(element.c_str(),"manualControl")){
				after = true;  
				filter = "manualControl:=";
				if   (filterLine(line, filter, after, element)) {                                        
                                        if (element == "true" || element == "TRUE")	manualControl = true;                                         
					else						manualControl = false;
				}
			}

			else if (!strcmp(element.c_str(),"headlessmode")){
				after = true;  
				filter = "headlessmode:=";
				if   (filterLine(line, filter, after, element)) {                                        
                                        if (element == "true" || element == "TRUE")	headlessmode = true;                                         
					else						headlessmode = false;
				}
			}

			else if (!strcmp(element.c_str(),"servermode")){
				after = true;  
				filter = "servermode:=";
				if   (filterLine(line, filter, after, element)) {                                        
                                        if (element == "true" || element == "TRUE")	servermode = true;                                         
					else						servermode = false;
				}
			}

                        else if (!strcmp(element.c_str(),"slf_proxy_mode")){
				after = true;  
				filter = "slf_proxy_mode:=";
				if   (filterLine(line, filter, after, element)) {                                        
                                        if (element == "true" || element == "TRUE")	slf_proxy_mode = true;                                         
					else						slf_proxy_mode = false;
				}
			}
                                                
			else if (!strcmp(element.c_str(),"loadFilter")){
				after = true;  
				filter = "loadFilter:=";
				if   (filterLine(line, filter, after, element)) {                                        
					loadFilter.push_back(element);
				}
			}                                               
                         
                        else if (!strcmp(element.c_str(),"PreLoadTarget")){
				after = true;  
				filter = "PreLoadTarget:=";
				if   (filterLine(line, filter, after, element)) {
					loadLevelPre = element;
				}
			}
                        
			else if (!strcmp(element.c_str(),"LoadTarget")){
				after = true;  
				filter = "LoadTarget:=";
				if   (filterLine(line, filter, after, element)) {
					loadLevel = element;
				}
			}
                        
			else if (!strcmp(element.c_str(),"PostLoadTarget")){
				after = true;  
				filter = "PostLoadTarget:=";
				if   (filterLine(line, filter, after, element)) {
					loadLevelPost = element;
				}
			}
			else if (!strcmp(element.c_str(),"GraphLoadFile")){
				after = true;  
				filter = "GraphLoadFile:=";
				if   (filterLine(line, filter, after, element)) {
                                        updateDefineParam("GRAPH_DATA_FILE_NAME", element);
				}
			}
                                                
			else if (!strcmp(element.c_str(),"GraphScanSize")){
				after = true;  
				filter = "GraphScanSize:=";
				if   (filterLine(line, filter, after, element)) {
                                        updateDefineParam("GRAPH_SCAN_SIZE", element);
				}
			}
                                                
			else if (!strcmp(element.c_str(),"LoadRegHostName")){
				after = true;  
				filter = "LoadRegHostName:=";
				if   (filterLine(line, filter, after, element)) {
                                        updateDefineParam("LOAD_REG_HOSTNAME", element);
				}
			}
                                                
			else if (!strcmp(element.c_str(),"ExtraTime")){
				after = true;  
				filter = "ExtraTime:=";
				if   (filterLine(line, filter, after, element)) {
                                        updateDefineParam("EXTRA_TIME", element);
				}
			}
                                                
			else if (!strcmp(element.c_str(),"numOfCps")){
				after = true;  
				filter = "numOfCps:=";
				if   (filterLine(line, filter, after, element)) {
					 numOfCps = element;
				}
			}
                         
			else if (!strcmp(element.c_str(),"cpsDelta")){
				after = true;  
				filter = "cpsDelta:=";
				if   (filterLine(line, filter, after, element)) {
					 cpsDelta = element;
				}
			}
                         
			else if (!strcmp(element.c_str(),"cpsDeltaPre")){
				after = true;  
				filter = "cpsDeltaPre:=";
				if   (filterLine(line, filter, after, element)) {
					cpsDeltaPre = element;
				}
			}
                        
			else if (!strcmp(element.c_str(),"cpsDeltaLoad")){
				after = true;  
				filter = "cpsDeltaLoad:=";
				if   (filterLine(line, filter, after, element)) {
					 cpsDeltaLoad = element;
				}
			}
                        
			else if (!strcmp(element.c_str(),"cpsDeltaPost")){
				after = true;  
				filter = "cpsDeltaPost:=";
				if   (filterLine(line, filter, after, element)) {
					cpsDeltaPost = element;
				}
			}
                        
			else if (!strcmp(element.c_str(),"loadSched")){
				after = true;  
				filter = "loadSched:=";
				if   (filterLine(line, filter, after, element)) { 
                                        storeloadSched(element);
				}
			}
                        
			else if (!strcmp(element.c_str(),"numOfPTCs")){
				after = true;  
				filter = "numOfPTCs:=";
				if   (filterLine(line, filter, after, element)) {
                                        numOfPTCs = atoi (element.c_str());
				}
			}
                        
			else if (!strcmp(element.c_str(),"modTc")){
				after = true;  
				filter = "modTc:=";
				if   (filterLine(line, filter, after, element)) {
					modTrafficCase(element);
				}
			}
                        
			else if (!strcmp(element.c_str(),"remTc")){
				after = true;  
				filter = "remTc:=";
				if   (filterLine(line, filter, after, element)) {
					//remTrafficCase(element);
                    tcToExclude.push_back(element);
				}
			}

			else if (!strcmp(element.c_str(),"defParam")){
				after = true;  
				filter = "defParam:=";
				if   (filterLine(line, filter, after, element)) {
                                    int count = std::count(element.begin(), element.end(), ':');
                                    if (count < 2){
                                        cout << endl << "ERROR:Wrong syntax for parameter DEFINE "<< element;
                                        cout << " .Format is TYPE:PARAM_NAME:PARAM_VALUE" << endl<< endl;
                                        exit (1);
                                    }
                                    definedParam.push_back(element);
				}
			}
                        
			else if (!strcmp(element.c_str(),"sub_range")){
				after = true;  
				filter = "sub_range:=";
				if   (filterLine(line, filter, after, element)) {
					changeRange(element);
				}
			}
                        
			else if (!strcmp(element.c_str(),"FileMask")){
				after = true;  
				filter = "FileMask:=";
				filterLine(line, filter, after, FileMask);
			}
			
			else if (!strcmp(element.c_str(),"ConsoleMask")){
				after = true;  
				filter = "ConsoleMask:=";
				filterLine(line, filter, after, ConsoleMask);
			}
			else if (!strcmp(element.c_str(),"LogFile")){
				after = true;  
				filter = "LogFile:=";
				filterLine(line, filter, after, LogFile);
			}
                                                
			else if (!strcmp(element.c_str(),"LoadRegType")){
				after = true;  
				filter = "LoadRegType:=";
				if   (filterLine(line, filter, after, element)) {
                                        if ((element == "traffic") || (element == "oam")|| (element == "system") || (element == "all")) 
                                        	updateDefineParam("LOAD_REG_TYPE", addQuottes(element));
				}
			}
                                                
                        else {
                                
				cout << endl << "ERROR:Wrong key "<< element <<"  on configuration data file: "<< nameFile<<" line: " << line << endl<< endl;
				exit (1);                
			}

		}
	}
	inFile.close();
	
              
}

bool modTrafficCase(string Tc)
{
	bool after;
	char line [1024]; 
        string element, filter, name,range, base, weight;                
	after = false;  
	filter = ":";
	strcpy(line, Tc.c_str());       
	if (filterLine(line, filter, after, name)) {
		after = true;
                if (filterLine(line, filter, after, element)) {
                        strcpy(line, element.c_str());
                        after = false;
                        if (filterLine(line, filter, after, weight)) {
				after = true;
                		if (filterLine(line, filter, after, element)) {
                        		strcpy(line, element.c_str());
                        		after = false;
                        		if (filterLine(line, filter, after, base)) {
						after = true;
                				filterLine(line, filter, after, range);
                                        }
                                }
                        }
                }
        } 
	else
                name = Tc;
                
        bool tc_found = false;                                                                       
	for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                
                if (tcDescIter->first.find(name) != string::npos){
			tcDescIter->second.toBeIncluded = true;
                        tcDescIter->second.addLoad = true;
                        if(!weight.empty()) {
				string::size_type idx;
				idx = weight.find(".");
				if (idx == string::npos)	tcDescIter->second.trafficWeight = "trafficWeight := " + weight + ".0";
				else				tcDescIter->second.trafficWeight = "trafficWeight := " + weight;
                	}

                        if(!base.empty()) {
                                if (tc_found)  {
 					cout << endl << "ERROR:Not allowed to set the same base for more than one script: " << Tc << endl<< endl;
					exit (1);  
                        	}               
                                        
                                tcDescIter->second.base = base;
                        }               
                        if(!range.empty()) {
                                if (tc_found)  {
 					cout << endl << "ERROR:Not allowed to set the same range for more than one script: " << Tc << endl<< endl;
					exit (1);  
                                        
                        	}               
                                tcDescIter->second.range = range;
                                                
                        }               
                        tc_found = true;
                }
        }

        if (!tc_found) {
		cout << endl << "ERROR:Wrong traffic case to be added/modified: " << Tc << endl<< endl;
		exit (1);  
        }
                      
                
}
bool remTrafficCase(string Tc)
{
        
        bool tc_found = false;                                                                       
	for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                
                if (tcDescIter->first.find(Tc) != string::npos){
                     if (trafficType == WSM){
                             tcDescIter->second.addPre = false;
                             tcDescIter->second.addLoad = false;
                             tcDescIter->second.addPost = false;
                     }   
                     else {
                          tcDescIter->second.toBeIncluded = false;   
                     }
                       
                     tc_found = true;
                }
        }
                
        if (!tc_found) {
		cout << endl << "ERROR:Wrong traffic case to be removed: " << Tc << endl<< endl;
		exit (1);                
        }
        
                
}

void addTrafficGroup()
{
    if (groupToAdd.empty()) return;

    cout << endl << "INFO:" << " Allowed only traffic cases for group(s): " ;
    for(int index = 0; index < groupToAdd.size(); index++) {
        cout << groupToAdd[index]<< "  ";
    }
    cout << endl;

    map<string, ScriptData>::iterator localTcDescIter; 
    for(localTcDescIter = tcDesc.begin(); localTcDescIter != tcDesc.end(); ++localTcDescIter) {
        for(int index2 = 0; index2 < localTcDescIter->second.groupName.size(); index2++) {
            for(int index = 0; index < groupToAdd.size(); index++) {
                if (localTcDescIter->second.groupName[index2] == groupToAdd[index]){
                    cout << endl << "INFO: " << localTcDescIter->second.name <<" traffic case is added for being included in group " << groupToAdd[index];
                    localTcDescIter->second.toBeIncluded = true;
                }
            }
        }
    }

}

void excludeTraffiCase()
{
    map<string, ScriptData>::iterator localTcDescIter;

    for(localTcDescIter = tcDesc.begin(); localTcDescIter != tcDesc.end(); ++localTcDescIter) {
        for(int index2 = 0; index2 < localTcDescIter->second.groupName.size(); index2++) {
                for(int index = 0; index < groupToExclude.size(); index++) {
                        if (localTcDescIter->second.groupName[index2] == groupToExclude[index] && localTcDescIter->second.toBeIncluded){
                            cout << endl << "INFO: " << localTcDescIter->second.name <<" traffic case will not be executed when " << groupToExclude[index];
                            remTrafficCase(localTcDescIter->second.name);

                        }
                }
        }
    }
    cout << endl ;
    for(int index = 0; index < tcToExclude.size(); index++) {
        cout << endl << "INFO: " << tcToExclude[index] <<" traffic case removed by user ";
        remTrafficCase(tcToExclude[index]);
    }
    cout << endl ;

}

bool userModifyDefineParam(string userEntry)
{
    bool after;
    bool toBeQuotted = false;
    char line [1024]; 
    string element, filter, name,value;
    after = false;
    filter = ":";
    strcpy(line, userEntry.c_str());
    if (filterLine(line, filter, after, element)) {
        if (element == "q") toBeQuotted= true;
        after = true;
        if (filterLine(line, filter, after, element)) {
            strcpy(line, element.c_str());
            after = false;
            if (filterLine(line, filter, after, name)) {
                after = true;
                filterLine(line, filter, after, value);
            }
        }
     }

     for(defineParamIter = defineParam.begin(); defineParamIter != defineParam.end(); ++defineParamIter) {
                if (defineParamIter->first.find(name) != string::npos && !value.empty()){
                    if (toBeQuotted)    defineParamIter->second.value = addQuottes(value);
                    else                defineParamIter->second.value = value;
                    return true;
                }
    }

    DefineData myDefine;
    myDefine.name = name;
    if (toBeQuotted)    myDefine.value = addQuottes(value);
    else                myDefine.value = value;

    pair<map<string, DefineData>::iterator,bool> myIter = defineParam.insert(make_pair(myDefine.name,myDefine));
    cout << endl << "WARNING:define parameter not found: " << userEntry << "   added to cfg." <<endl<< endl;
}
bool changeRange(string userEntry)
{
	bool after;
        bool base_found = false;
        bool subs_per_script_found = false;
	char line [1024]; 
        string element, filter, name, base, range;                
	after = false;  
	filter = ":";
	strcpy(line, userEntry.c_str());       
	if (filterLine(line, filter, after, name)) {
		after = true;
                if (filterLine(line, filter, after, element)) {
                        strcpy(line, element.c_str());
                        after = false;
                        if (filterLine(line, filter, after, base)) {
				after = true;
                		filterLine(line, filter, after, range);
                        }
                }
        } 

        
        if (base.empty())	base_found = true;
        if (range.empty())	subs_per_script_found = true;
                                                                                
	for(defineParamIter = defineParam.begin(); defineParamIter != defineParam.end(); ++defineParamIter) {
                
                if (defineParamIter->first.find(name) != string::npos){
                        
                        if (defineParamIter->first.find("BASE_") != string::npos && !base.empty()) {
                                base_found = true;
                                defineParamIter->second.value = base;
                        }
                                
                        
                        if (defineParamIter->first.find("SUBS_PER_SCRIPT_") != string::npos && !range.empty()){
				subs_per_script_found   = true;                             
				defineParamIter->second.value = range;
                        }
                        
		}
        }
        
        if (!(subs_per_script_found & base_found)){
		cout << endl << "ERROR:Wrong subcriber range to be modified: " << userEntry << endl<< endl;
		exit (1);                
	}
                
}


bool storeloadSched(string value)
{
	bool after;
	char line [1024]; 
        string element, filter, target, time;                
	after = false;  
	filter = ":";
	strcpy(line, value.c_str());       
	if (filterLine(line, filter, after, target)) {
		after = true;
                filterLine(line, filter, after, time); 
        }

       	stringstream valueString;

	valueString<< "{loadTarget:="<<target<<".0,loadTime:="<<time<<".0}";
	scheduleLoad.push_back(valueString.str());

}




bool updateDefineParam(string name, string value)
{
        
	for(defineParamIter = defineParam.begin(); defineParamIter != defineParam.end(); ++defineParamIter) {
                
                if (defineParamIter->first.find(name) != string::npos){

                	defineParamIter->second.value = value;
                        return true;
                }
   }

	// DEFINE not found, just add it
	DefineData myDefine;
	myDefine.name = name;
	myDefine.value = value;
	
   	defineParam.insert(make_pair(name,myDefine));


}

void writeDeploymentFile(string nameFile)
{
	bool firstParam;
       	ofstream outFile;  
        outFile.open(nameFile.c_str());
	if (!outFile) {
		cout << endl << "ERROR:Failed to open file: " << nameFile << endl<< endl;
		exit (1);                
	}

	outFile <<"[MODULE_PARAMETERS]" << endl << endl;

	if (!guiHost.name.empty()) {
		outFile <<"tsp_xtdp_listen_addr := " <<guiHost.name << endl << endl; 
  		outFile <<"tsp_xtdp_listen_port := " <<guiHost.port << endl << endl;
	}
    
    	outFile <<"tsp_use_"<<scenarioName<<"_Stack := true" << endl << endl;
    
	outFile <<"tsp_nof_CS_Admins_"<<scenarioName<<" := " << lgen.size() << endl << endl; 
  
  	outFile <<"tsp_CS_Admin_"<<scenarioName<<"_HostList := {";
                
        firstParam = true;
        for (int index = 0; index < lgen.size(); index++) {
		if (firstParam){
			firstParam = false;
		} else {
			outFile << ",";			
		}
                
                outFile <<lgen[index].name;
                
        }
        outFile <<"}" << endl << endl;

	if (trafficType == ISMSDA || trafficType == ESM){
                
    		outFile <<"use_DIAMETER_proxy := true " << endl << endl;    
      		outFile <<"tsp_"<<scenarioName<<"_nrOfDiameterProxies := " << DiaProxy.size() << endl << endl;
        }

	if (trafficType != WSM ){
                
                int numberOfLdapProxies = 1 + ((numOfPTCs / lgen.size())/ 50);
//                if (trafficType == ISMSDA )numberOfLdapProxies = 1;	
                 
                DefineData myDefine;
                
                myDefine.name = "NUMBERLDAPPROXIES";
                myDefine.value = intToString(numberOfLdapProxies);
		defineParam.insert(make_pair(myDefine.name,myDefine));
                
                
      		outFile <<"tsp_"<<scenarioName<<"_nrOfLDAPProxies := ${NUMBERLDAPPROXIES,integer}"<< endl << endl;
                
    		outFile <<"tsp_CS_Admin_"<<scenarioName<<"_LDAPProxyHostList := {";
        
        	firstParam = true;
        	for (int index = 0; index < lgen.size(); index++) {
			if (firstParam){
				firstParam = false;
			} else {
				outFile << ",";			
			}
                
                	outFile <<lgen[index].name;
        	}
        	outFile <<"}" << endl << endl;
        }
    
        outFile <<"tsp_EPTF_CS_LGenHostnameList := {";
        
        firstParam = true;
        for (int index = 0; index < lgen.size(); index++) {
		if (firstParam){
			firstParam = false;
		} else {
			outFile << ",";			
		}
                
                outFile <<lgen[index].name;
                
        }
        outFile <<"}" << endl << endl;
  
        outFile <<"full_admin_deploy := true" << endl << endl;
        
        if (use_conkeeper && (trafficType == ISMSDA || trafficType == ESM || trafficType == OAM))
        	outFile <<"conkeeperHost := {enable:=true,hostName:="<<conkeeperHost.name<<",hostPort:="<< conkeeperHost.port <<"}" << endl << endl;

        if (use_loadplotter)
        	outFile <<"loadplotterHost := {enable:=true,hostName:="<<loadplotterHost.name<<",hostPort:="<< loadplotterHost.port <<"}" << endl << endl;

        if (loadFilter.size()) {
                outFile << endl << "tsp_Load_Filter:= {";
        	for (int index = 0; index < loadFilter.size(); index++) {                
                	outFile <<loadFilter[index] ;
                        if (index < loadFilter.size() -1)
                              outFile << "," ;
        	}
                outFile << "}" << endl;
        }
                        
	outFile << endl;        
                
       	if (scheduleLoad.size()){
        	outFile <<"loadSchedulingEnabled := false" << endl << endl;        
        	outFile <<"loadSchedulingEnabled := true" << endl << endl;        
        	outFile <<"loadschedList := {";
                
        	firstParam = true;
 		while (!scheduleLoad.empty()) {
			if (firstParam){
				firstParam = false;
			} else {
				outFile << ",";			
			}
                
                	outFile <<scheduleLoad.front();
			scheduleLoad.pop_front();
        	}
         	outFile <<"}" << endl << endl;
       }
       else {
        	outFile <<"loadSchedulingEnabled := false" << endl << endl;        
       }

                      
        outFile << endl;
                
      	outFile <<"[TESTPORT_PARAMETERS]" << endl << endl;
        
	if (trafficType == ISMSDA || trafficType == ESM){
        	for (int index = 0; index < DiaProxy.size(); index++) { 
                        if (trafficType == ISMSDA) {
                		outFile << "DIAMETER_POOL_"<< index <<".Diameter.remote_address_ipv4 := "<<DiaProxy[index].name << endl;
                		outFile << "DIAMETER_POOL_"<< index <<".Diameter.remote_port_ipv4 := \""<<DiaProxy[index].port <<"\""<< endl << endl;               
                        } 
                        else {
                		outFile << "DIAMETER_POOL_"<< index <<"_ESM.Diameter.remote_address_ipv4 := "<<DiaProxy[index].name << endl;
                		outFile << "DIAMETER_POOL_"<< index <<"_ESM.Diameter.remote_port_ipv4 := \""<<DiaProxy[index].port <<"\""<< endl << endl;               
                        }              
        	}
        }
        
        
        for (int index = 0; index < loadFilter.size(); index++) {                
                outFile << "*.EPTF_CPUloadOnSUT_PCO.filter := "<<loadFilter[index] << endl;
        }
        
	outFile << endl << endl ;
	outFile <<"[LOGGING]" << endl << endl;
        
        outFile << "FileMask := " << FileMask << endl << endl;
        outFile << "ExecCtrl.FileMask := ERROR|USER|ACTION|PARALLEL|WARNING" << endl << endl;
        outFile << "ConsoleMask := " << ConsoleMask << endl << endl;
        outFile << "LogFile := " << LogFile << endl << endl;
        
	outFile << endl << endl ;                        
        outFile <<"[DEFINE]" << endl << endl;
               
	updateDefine();

	while (!definedParam.empty()) {
		
		userModifyDefineParam(definedParam.front());
		definedParam.pop_front();
        }
    string value;
	for(defineParamIter = defineParam.begin(); defineParamIter != defineParam.end(); ++defineParamIter) {
        if (defineParamIter->second.value.length())     value = defineParamIter->second.value;
        else                                            value = "\"\"";
		outFile << defineParamIter->second.name <<" := " << value << endl;	
	}
                        
        
       	outFile << endl << endl;
        
        
        outFile <<"[MAIN_CONTROLLER]" << endl << endl;
        
        outFile <<"TCPPort := ${TCPPORT, integer}" << endl;
        
        if (!ttcn3start_used)	outFile <<"NumHCs  := ${NUMHCS,integer}" << endl;
        
       	outFile << endl << endl;
        outFile.close();	
        
}
void writeScenarioFile(string nameFile)
{
	
	ofstream outFile;  
        outFile.open(nameFile.c_str());
	if (!outFile) {
		cout << endl << "ERROR:Failed to open file: " << nameFile << endl<< endl;
		exit (1);                
	}
	string TcName, param, range, base;
	bool firstElem = true;
	bool firstParam = true;
	string phases_suffix[]= {"_Pre","","_Post"};
	
	outFile <<"[MODULE_PARAMETERS]" << endl;

        if (trafficType == ISMSDA || trafficType == ESM)  { 
        	outFile << "Diaproxy_info_list:={ \n" ;
        	for (int index = 0; index < DiaProxy.size(); index++) { 
            	    outFile << "\t{hostname:=" << DiaProxy[index].name<<", listeningPort:=\""<<DiaProxy[index].port;
            	    outFile <<"\", connections_number:="<<DiaProxy[index].nc<<", local_ip:=\""<<DiaProxy[index].local_ip<<"\"}";
            	    if (index < DiaProxy.size() -1){
                        	outFile << ",";
            	    }
            
                    outFile << "\n";
        	}
        	outFile << "}\n\n";
        }
        
        firstElem = true;
	outFile << endl << LOADREGULATORS_PREFIX;
        if (preNeeded) {
              firstElem = false; 
              outFile <<LOADREGULATORS_1 << regulatorName << "Pre"<< LOADREGULATORS_2 << "${LOAD_LEVEL_PRE, float}" <<LOADREGULATORS_3; 
        }
        
	if (firstElem){
		firstElem = false;
	} else {
		outFile << ",";			
	}
        outFile <<LOADREGULATORS_1 << regulatorName << LOADREGULATORS_2 << "${LOAD_LEVEL, float}" <<LOADREGULATORS_3; 
                
                
        if (postNeeded) {
        	outFile << "," << LOADREGULATORS_1 << regulatorName << "Post"<< LOADREGULATORS_2 << "${LOAD_LEVEL_POST, float}" <<LOADREGULATORS_3; 
        }
                        
 	outFile << LOADREGULATORS_SUFFIX << endl ;
                
 	outFile << endl << EXECCTRL_REGULATORNAMES_PREFIX;
        
        firstElem = true;
        if (preNeeded) {
              firstElem = false; 
              outFile <<"\n\t\"LoadReg" << regulatorName << "Pre\""; 
        }
        
	if (firstElem){
		firstElem = false;
	} else {
		outFile << ",";			
	}
        outFile <<"\n\t\"LoadReg" << regulatorName << "\""; 
                                
        if (postNeeded) {
        	outFile << "," <<"\n\t\"LoadReg" << regulatorName << "Post\""; 
        }

      	outFile << EXECCTRL_REGULATORNAMES_SUFFIX << endl ;
                
        
 	outFile << endl << EXECCTRL_REGULATEDITEMS_PREFIX;
        
        firstElem = true;
        if (preNeeded) {
              firstElem = false; 
              outFile <<REGULATEDITEMS_1 << scenarioName << REGULATEDITEMS_2 << scenarioName << REGULATEDITEMS_3 << "preexec";
              outFile <<REGULATEDITEMS_4 << regulatorName << "Pre" <<REGULATEDITEMS_5;
        }
        
	if (firstElem){
		firstElem = false;
	} else {
		outFile << ",";			
	}
        
        outFile <<REGULATEDITEMS_1 << scenarioName << REGULATEDITEMS_2 << scenarioName << REGULATEDITEMS_3 << "loadgen";
        outFile <<REGULATEDITEMS_4 << regulatorName << REGULATEDITEMS_5;
                     
        if (postNeeded) {
              outFile << "," << REGULATEDITEMS_1 << scenarioName << REGULATEDITEMS_2 << scenarioName << REGULATEDITEMS_3 << "postexec";
              outFile <<REGULATEDITEMS_4 << regulatorName << "Post" <<REGULATEDITEMS_5;
        }
        
 	outFile << EXECCTRL_REGULATEDITEMS_SUFFIX << endl ;
        
                        
        firstElem = true;
        outFile << endl << PHASELISTDECLARATORS_PREFIX;
        if (preNeeded) {
              firstElem = false; 
              outFile <<"\n\t\t { name := \"preexec\", enabled := true }"; 
        }
                        
	if (firstElem){
		firstElem = false;
	} else {
		outFile << ",";			
	}
                
	outFile <<"\n\t\t { name := \"loadgen\", enabled := true }";
                
        if (postNeeded) {
              outFile <<",\n\t\t { name := \"postexec\", enabled := true }";
        }
                        
        outFile << PHASELISTDECLARATORS_SUFFIX;
                
       	outFile << endl << SCENARIOGROUP_0 << scenarioName << SCENARIOGROUP_1 << scenarioName << "." << scenarioName << SCENARIOGROUP_2 << endl; 
       	outFile << ENTITYGRPDECLARATORS_0 << scenarioName << ENTITYGRPDECLARATORS_1 << scenarioName; 
       	outFile << ENTITYGRPDECLARATORS_2 << "${NUMBEROFENTITIES,integer}";
        outFile << ENTITYGRPDECLARATORS_3 << scenarioName << ENTITYGRPDECLARATORS_4 << scenarioName<< ENTITYGRPDECLARATORS_2 << numOfPTCs <<ENTITYGRPDECLARATORS_5;     

       	outFile << endl << SCENARIO2ENTITY_1<< scenarioName << SCENARIO2ENTITY_2<< scenarioName <<SCENARIO2ENTITY_3; 
          
                
       	outFile << endl << TCTYPEDECLARATORS2_PREFIX;
	firstElem = true;
	for (int index = 0; index < 3; index++) {	// One iteration per phase PRE LOAD POST

		for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                        if (tcDescIter->second.toBeIncluded == false ) continue;
                        
			if (firstElem){
				firstElem = false;
			} else {
				outFile << ",";			
			}
			TcName = tcDescIter->first;
			outFile << TCTYPEDECLARATORS2_ELEM_PREFIX << TcName << phases_suffix[index] << TCTYPEDECLARATORS2_ELEM_MED << scenarioName << TCTYPEDECLARATORS2_ELEM_SUFFIX;	
		}
	}

	outFile << TCTYPEDECLARATORS2_SUFFIX;
	outFile << endl << endl;

	outFile << SCENARIODECLARATORS3_PREFIX << scenarioName << "\",\n";
	outFile << TC_LIST_PREFIX;
	
	firstElem = true;	

	for (int index = 0; index < 3; index++) {	// One iteration per phase PRE LOAD POST
                
		for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                        
                        if (tcDescIter->second.toBeIncluded == false) 	continue;
                        
			if (firstElem){
				firstElem = false;
			} else {
				outFile << ",";			
			}
                        
			outFile << TC_ELEMENT_SUB_1 << tcDescIter->first << phases_suffix[index] << TC_ELEMENT_SUB_2 << tcDescIter->second.trafficWeight;
			outFile << TC_ELEMENT_SUB_3 ;
			outFile << tcDescIter->second.base <<", count := " << tcDescIter->second.range <<"}";
			outFile << TC_ELEMENT_SUB_4;	

                        deque  <string> my_params= tcDescIter->second.params;
                        			
			if (phases_suffix[index].empty() || trafficType == WSM){	  //Load phase -> add params
				firstParam = true;
				while (!my_params.empty()) {
					if (firstParam){
						firstParam = false;
					} else {
						outFile << ",";			
					}
		
			  		param = "\n\t\t\t\t\t\t\t{aName:=\"" + scenarioName + "\", " +  my_params.front()+ "}";
		      			my_params.pop_front();
		      			outFile << param;
		    		}
			}        
			
			if (phases_suffix[index].empty()){	  //Load phase -> add params
				outFile << TC_ELEMENT_SUB_5 <<  "\t\t\t\t\t\t"	<< ExecutionType << TC_ELEMENT_SUB_6;
			} else {
				outFile << TC_ELEMENT_SUB_5 <<  "\t\t\t\t\t\t"	<< RANGEEXECUTIONTYPE << TC_ELEMENT_SUB_6;
			}		
		
		}	
	}	
		
	outFile << TC_LIST_SUFFIX;
        
	outFile << SC_PARAM_LIST_PREFIX;
		
        bool firstList = true;

	outFile << FINISH_COND_SUB_0;
        
        if (preNeeded) {
                outFile << FINISH_COND_SUB_1_1;
		firstList = false;
		firstElem = true;
		for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                        
                        if (tcDescIter->second.toBeIncluded == false)	continue;
                        
			if (tcDescIter->second.addPre && tcDescIter->second.addLoad) {
				if (firstElem){
					firstElem = false;
				} else {
					outFile << ",";			
				}
				outFile << "\n\t\t\t\t\t\t{ tcFinished := \"" << tcDescIter->first << "_Pre\"}";		
			}
		}
                outFile << FINISH_COND_SUB_1_2;
        }

	if (firstList){
		firstList = false;
	} else {
		outFile << ",";			
	}

	
	outFile << FINISH_COND_SUB_2_1;
	firstElem = true;
	for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                        
		if (tcDescIter->second.toBeIncluded == false)	continue;

		if (tcDescIter->second.addLoad) {
			if (firstElem){
				firstElem = false;
			} else {
				outFile << ",";			
			}
			outFile << "\n\t\t\t\t\t\t{ tcFinished := \"" << tcDescIter->first << "\"}";	
                }	
	}
	outFile << FINISH_COND_SUB_2_2;
        
        if (postNeeded) {
                outFile << "," << FINISH_COND_SUB_3_1;
		firstElem = true;
		for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                        
                        if (tcDescIter->second.toBeIncluded == false)	continue;
                        
			if (tcDescIter->second.addPost && tcDescIter->second.addLoad) {
				if (firstElem){
					firstElem = false;
				} else {
					outFile << ",";			
				}
				outFile << "\n\t\t\t\t\t\t{ tcFinished := \"" << tcDescIter->first << "_Post\"}";		
			}
		}
                outFile << FINISH_COND_SUB_3_2;
        }
        
	outFile << FINISH_COND_SUB_4;
        
        
        firstList = true;

	outFile << CHANGE_ACTIONS_SUB_0;
        
        if (preNeeded) {
                outFile << CHANGE_ACTIONS_SUB_1_1;
		firstList = false;
		firstElem = true;
		for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                        
                        if (tcDescIter->second.toBeIncluded == false)	continue;

			if (tcDescIter->second.addPre && tcDescIter->second.addLoad) {
				if (firstElem){
					firstElem = false;
				} else {
					outFile << ",";			
				}
				outFile << "\n\t\t\t\t\t\t{ startTc := \"" << tcDescIter->first << "_Pre\"}";		
			}
		}
                outFile << CHANGE_ACTIONS_SUB_1_2 <<",";
                
                outFile << CHANGE_ACTIONS_SUB_2_1;
		firstElem = true;
		for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                        
                        if (tcDescIter->second.toBeIncluded == false)	continue;

			if (tcDescIter->second.addPre && tcDescIter->second.addLoad) {
				if (firstElem){
					firstElem = false;
				} else {
					outFile << ",";			
				}
				outFile << "\n\t\t\t\t\t\t{ startTc := \"" << tcDescIter->first << "_Pre\"}";		
			}
		}
                outFile << CHANGE_ACTIONS_SUB_2_2;
        }

	if (firstList){
		firstList = false;
	} else {
		outFile << ",";			
	}

	outFile << CHANGE_ACTIONS_SUB_3_1;
	firstElem = true;
	for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                        
		if (tcDescIter->second.toBeIncluded == false)	continue;

		if (tcDescIter->second.addLoad) {
			if (firstElem){
				firstElem = false;
			} else {
				outFile << ",";			
			}
			outFile << "\n\t\t\t\t\t\t{ startTc := \"" << tcDescIter->first << "\"}";
                }		
	}
	
	outFile << CHANGE_ACTIONS_SUB_3_2 <<",";
        
	outFile << CHANGE_ACTIONS_SUB_4_1;
	firstElem = true;
	for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                        
		if (tcDescIter->second.toBeIncluded == false)	continue;

		if (tcDescIter->second.addLoad) {
			if (firstElem){
				firstElem = false;
			} else {
				outFile << ",";			
			}
			outFile << "\n\t\t\t\t\t\t{ stopTc := \"" << tcDescIter->first << "\"}";
                }		
	}
	outFile << CHANGE_ACTIONS_SUB_4_2;
        
        if (postNeeded) {
                outFile << "," << CHANGE_ACTIONS_SUB_5_1;
		firstElem = true;
		for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                        
                        if (tcDescIter->second.toBeIncluded == false)	continue;

			if (tcDescIter->second.addPost && tcDescIter->second.addLoad) {
				if (firstElem){
					firstElem = false;
				} else {
					outFile << ",";			
				}
				outFile << "\n\t\t\t\t\t\t{ startTc := \"" << tcDescIter->first << "_Post\"}";	
			}
		}
                outFile << CHANGE_ACTIONS_SUB_5_2 <<",";
                
                outFile << CHANGE_ACTIONS_SUB_6_1;
		firstElem = true;
		for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                        
                        if (tcDescIter->second.toBeIncluded == false)	continue;

			if (tcDescIter->second.addPost && tcDescIter->second.addLoad) {
				if (firstElem){
					firstElem = false;
				} else {
					outFile << ",";			
				}
				outFile << "\n\t\t\t\t\t\t{ stopTc := \"" << tcDescIter->first << "_Post\"}";	
			}	
		}
                outFile << CHANGE_ACTIONS_SUB_6_2;
        }
        
 	outFile << CHANGE_ACTIONS_SUB_7;

	outFile << SC_PARAM_LIST_SUFFIX;

	outFile << SCENARIODECLARATORS3_SUFFIX;
	outFile << endl << endl;
        outFile.close();	
}

bool updateDefine()
{
 // Prepare define section....       
        
	updateDefineParam("TCPPORT",intToString(mcPort));
	updateDefineParam("NUMHCS", intToString(lgen.size()));
        
	updateDefineParam("NUMBEROFENTITIES", intToString(1000 + 50 * numOfPTCs));
	
	updateDefineParam("USE_GUI", booleanToString(use_gui));        
	updateDefineParam("MANUALCONTROL", booleanToString(manualControl));
	updateDefineParam("HEADLESSMODE", booleanToString(headlessmode));
	updateDefineParam("SERVERMODE", booleanToString(servermode));
        
	updateDefineParam("SLF_PROXY_MODE", booleanToString(slf_proxy_mode));
	updateDefineParam("LAYER_SCENARIO", booleanToString(layer));
        
	updateDefineParam("SUT_LOAD_IP", vip_oam);
        
        if (loadplotterHost.name.empty()) {
		updateDefineParam("SUT_LOAD_PORT","10000");
 	} 
        else {
		updateDefineParam("SUT_LOAD_PORT",loadplotterPort);
                if (secvip_dia_tcp.empty()){
                	updateDefineParam("SUT_LOAD_IP", "0.0.0.0");
                }
        }
        
	if(!vip_dia_tcp.empty())		updateDefineParam("SUT_DIAMETER_TCP", vip_dia_tcp);
	if(!vip_dia_sctp.empty())		updateDefineParam("SUT_DIAMETER_SCTP", vip_dia_sctp);
	if(!vip_radius.empty())			updateDefineParam("SUT_RADIUS", vip_radius);
    if(!vip_udm.empty())            updateDefineParam("SUT_UDM_IP", vip_udm);
    if(!vip_soap_ldap.empty())      updateDefineParam("SUT_SOAP_LDAP_IP", vip_soap_ldap);
	if(vip_soap.empty())			vip_soap="0.0.0.0";
    updateDefineParam("SUT_SOAP_IP", vip_soap);
         
 	if(!secvip_dia_tcp.empty())		updateDefineParam("SUT_SEC_DIAMETER_TCP", secvip_dia_tcp);
 	if(!secvip_oam.empty())		        updateDefineParam("SUT_SEC_LOAD_IP", secvip_oam);
        if (layer && !secvip_oam.empty())	updateDefineParam("SUT_SEC_LDAP_IP", ExtDB_ip);  
        if (!layer && !secvip_oam.empty())	updateDefineParam("SUT_SEC_LDAP_IP", secvip_oam);  
        
       
        if (layer)			updateDefineParam("NUMOFCPS", "4.0");  
        else				updateDefineParam("NUMOFCPS", "10.0"); 
        
        if (layer)			updateDefineParam("SUT_LDAP_IP", ExtDB_ip);  
        else				updateDefineParam("SUT_LDAP_IP", vip_oam); 
        
        if (slf_proxy_mode)		updateDefineParam("SUT_DIAMETER_PORT", "3872");  
        else				
                if(trafficType==ISMSDA)	updateDefineParam("SUT_DIAMETER_PORT", "3868"); 
        	else			updateDefineParam("SUT_DIAMETER_PORT", "3870");
               
        if (slf_proxy_mode)		updateDefineParam("SUT_RADIUS_PORT", "2813");  
        else				updateDefineParam("SUT_RADIUS_PORT", "1813"); 
        
        if(use_conkeeper)		updateDefineParam("LOAD_SERVER_IP", conkeeperHost.name);
        else				updateDefineParam("LOAD_SERVER_IP", vip_oam);
                
        if (!loadplotterHost.name.empty()) {
 					updateDefineParam("LOAD_SERVER_IP", loadplotterHost.name);
 	} 

        if(use_conkeeper){
					updateDefineParam("DIAMETER_SERVER_SCTP", conkeeperHost.name);
					updateDefineParam("DIAMETER_SERVER_TCP", conkeeperHost.name);
	}
        else{
					updateDefineParam("DIAMETER_SERVER_SCTP", vip_dia_sctp);
					updateDefineParam("DIAMETER_SERVER_TCP", vip_dia_tcp);
	}

        
        if(use_conkeeper)		updateDefineParam("LDAP_SERVER_IP", conkeeperHost.name);
        else			
                if(layer)		updateDefineParam("LDAP_SERVER_IP", ExtDB_ip); 
        	else			updateDefineParam("LDAP_SERVER_IP", vip_oam);
        
        if(layer)
                if(use_conkeeper)	updateDefineParam("SUT_LDAP_PORT", "1389"); 
        	else			updateDefineParam("SUT_LDAP_PORT", "389");
        else				updateDefineParam("SUT_LDAP_PORT", "7323");
              
        
	updateDefineParam("RADIUS_SERVER_IP", vip_radius);
    updateDefineParam("UDM_SERVER_IP", vip_udm);
	updateDefineParam("SOAP_SERVER_IP", vip_soap);
        
        
        if (layer){
               	updateDefineParam("CRED_ADMINISTRATOR", addQuottes("cn=manager,dc=operator,dc=com")); 
               	updateDefineParam("CRED_PASSWORD", addQuottes("MIL1Int_2")); 
        }
        else{
               	updateDefineParam("CRED_ADMINISTRATOR", addQuottes("administratorName=jambala,nodeName=jambala")); 
               	updateDefineParam("CRED_PASSWORD", addQuottes("Pokemon1")); 
        }

                
	if(!loadLevelPre.empty())	updateDefineParam("LOAD_LEVEL_PRE", loadLevelPre);
	if(!loadLevel.empty())		updateDefineParam("LOAD_LEVEL", loadLevel);
	if(!loadLevelPost.empty())	updateDefineParam("LOAD_LEVEL_POST", loadLevelPost);
                                        
	if(!cpsDelta.empty())		updateDefineParam("CPSDELTA", cpsDelta);
	if(!cpsDeltaPre.empty())	updateDefineParam("CPSDELTA_PRE", cpsDeltaPre);
	if(!cpsDeltaLoad.empty())	updateDefineParam("CPSDELTA_LOAD", cpsDeltaLoad);
	if(!cpsDeltaPost.empty())	updateDefineParam("CPSDELTA_POST", cpsDeltaPost);

        if(!numOfCps.empty()){
					updateDefineParam("NUMOFCPS", numOfCps); 
					updateDefineParam("LOCKCPS", booleanToString(true));
					updateDefineParam("ENABLE_REG", booleanToString(false));
	}		
       
}
bool isPreNeeded()
{
	for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                                        
		if (tcDescIter->second.addPre && tcDescIter->second.toBeIncluded) {
                        return true;
       		}
	}
        return false;
}

bool isPostNeeded()
{        
	for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                                        
		if (tcDescIter->second.addPost && tcDescIter->second.toBeIncluded) {
                        return true;
       		}
	}
        return false;
}

bool isAnyTcToBeIncluded()
{        
	for(tcDescIter = tcDesc.begin(); tcDescIter != tcDesc.end(); ++tcDescIter) {
                                        
		if (tcDescIter->second.toBeIncluded)	return true;
	}
        
        return false;
}

void purgeLine(char * line)
{
	char myline[1024];
	strcpy (myline, line);
	int index = 0;
	for (int i = 0; myline[i] != '\0'; i++) {
		if ( myline[i] == '#'){
			line[index] = '\0';
			break;
		} 
		else if ( myline[i] == '\r'){
			line[index] = '\0';
			break;
		} 
		else if (( myline[i] == '/') && (myline[i+1] == '/')){
			line[index] = '\0';
			break;
		} 
		else if (( myline[i] == ' ') || ( myline[i] == '\t')) {}
		else {
			line[index] = myline[i];
			index++;
		}
	}
	line[index] = '\0';
}

bool filterLine (const char * line, string filter, bool after, string & element)
{
	string  myLine(line);  
	int len;
	string::size_type idx;

	idx = myLine.find(filter);
	if (idx == string::npos) {
		return false;

	}
	
	if (after) {
		myLine.erase(0,idx + filter.size());      
	}
	else {
		len = myLine.size();
		myLine.erase(idx, len );  
	}
	element = myLine;
	return  true;
}
string booleanToString(bool value)
{
        if (value) 	return "true";
        else		return "false";

}
string intToString(int value)
{
	stringstream valueString;

	valueString<< value;
	return valueString.str();
}
string addQuottes(string value)
{
	stringstream valueString;

	valueString<< "\""<<value<< "\"";
	return valueString.str();
}
