#include "remote_control.h"
#include "UDP_remoteControl.h"

using namespace std;



int main(int argc, char* argv[])
{ 

       	applicationData myData;
	myData.port = -1;
	myData.waitingTimer = 5;
        myData.destination_host =  "";
        myData.commandFile = "";
        myData.destination_ip  = "";               
        stringstream errorString;
        
        if (!parseCommandLine(argc, argv, &myData)){
                displayHelp();
       		exit (1);                
        }        
        
//         cout << "Application configuration:" << endl;
//         cout << "Destination host: "<< myData.destination_host << endl;
//         cout << "Destination Port: " << myData.port <<endl;
                      
	int errsv = 0;

	if (myData.commands.empty()) {
                if (!readCommandFile (&myData)){
                	displayHelp();
       			exit (1);  
                }              
        }                
 		
        string command="";
        int time = 5;
        while (!myData.commands.empty()) {
		command = myData.commands.front();
                myData.commands.pop_front();
                
//                 cout << "Command sent:\t" << command << endl; 
                
//  		cout << "Answer received:\t" << sendCommand(myData.destination_host, myData.port, command, myData.waitingTimer) << endl;              
        cout << sendCommand(myData.destination_host, myData.port, command, myData.waitingTimer) << endl;              
                
        }        
       	return 0;
}


bool filterLine (char * line, string filter, bool after, string & element)
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

bool readCommandFile (applicationData *dataPtr)
{
	string command;
        char line [1024];
        ifstream inFile;
        
        inFile.open (dataPtr->commandFile.c_str());
        
        if (!inFile) {
		cout << "Failed to open file: " << dataPtr->commandFile <<endl;
		return false;
	}
        
	while(inFile) {
		inFile.getline(line, 1024);
                purgeLine(line);
		command = line;
		if (!command.empty() )	dataPtr->commands.push_back(command);        	
  	}

	inFile.close();
        
        if (dataPtr->commands.empty()){
                cout <<"ERROR: Not commands found on: " << dataPtr->commandFile << endl;
		return false;
        }
        
	return true;       
        
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
//                else if (( myline[i] == ' ') || ( myline[i] == '\t')) {
//                }
                else {
                        line[index] = myline[i];
                        index++;
                }
        }
        line[index] = '\0';
}


bool parseCommandLine (int argc, char **argv, applicationData *dataPtr)
{
                        
	for(int i=1;i<argc;i++){ 
                               
 		if(strcmp(argv[i],"-h") == 0){ 
			i++;
			if(argc == i){ 
				return false;
			}
                        dataPtr->destination_host = argv [i];  
		} 
                
               	else if(strcmp(argv[i],"-p") == 0){ 
			i++;
			if(argc == i){ 
				return false;
			}
			dataPtr->port = atoi (argv[i]);
        	}  
                      
               	else if(strcmp(argv[i],"-t") == 0){ 
			i++;
			if(argc == i){ 
				return false;
			}
			dataPtr->waitingTimer = atoi (argv[i]);
        	}  
                      
               	else if(strcmp(argv[i],"-f") == 0){ 
			i++;
			if(argc == i){ 
				return false;
			}
                        if (dataPtr->commands.empty()) {
                        	dataPtr->commandFile = argv[i];  
                        }
        	}
                        
               	else if(strcmp(argv[i],"-c") == 0){ 
			i++;
			if(argc == i){ 
				return false;
			}
                        if (dataPtr->commandFile.empty()) {
				string command =  argv[i];
                        	dataPtr->commands.push_back(command);
                        }
        	}        
		else { 
			return false;
        	}                       
        }  
        
        return true;     
}

void displayHelp()
{
	cout << endl << "Command line error."<< endl << endl;
        
//	cout << "Usage:\t\t./RemoteControl -h <hostname> -p <port> [-c <\"command\"> | -f <file>]"<< endl<< endl<< endl;
	cout << "Usage:\t\t./RemoteControl -h <hostname> -p <port> [-c <\"command\"> | -f <file>] [-t <time>]"<< endl<< endl<< endl;
	cout << "\t\t-h <hostname> \t\t\tHost where tool to be controlled is running"<< endl<< endl  ;
	cout << "\t\t-p <port> \t\t\tWellknown tool UDP port"<< endl<< endl  ;
	cout << "\t\t[-c <\"command\"> ]\t\tSingle command to be executed"<< endl<< endl  ;
	cout << "\t\t[-f <file> ]\t\t\tFile with commands"<< endl<< endl  ;
	cout << "\t\t[-t <time> ]\t\t\tTimer in seconds for waiting answer"<< endl<< endl  ;
	cout << " "<< endl<< endl  ;
                
}
