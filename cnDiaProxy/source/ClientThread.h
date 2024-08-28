
#include "netcon.h"

void* _ClientThread(void *arg);
void resetAndExit (clientThread *myClient);
void closeClient (clientThread *myClient, ClientConnection *myConnection);
int findConnection(uint app_id);
int findTransaction();
bool sendPendingMessage(NetworkConnection *net_con);
bool addMessageAsPending(int socket, struct Message message);
void findSocketsWithPendingMessages(clientThread * myClient);
void cleanPendingMessages(int socket);
;

