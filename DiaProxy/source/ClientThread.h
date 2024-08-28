void* _ClientThread(void *arg);
void resetAndExit (clientThread *myClient);
void closeClient (clientThread *myClient, ClientConnection *myConnection);
int findTransaction();
bool sendPendingMessage(int socket);
bool addMessageAsPending(int socket, struct Message message);
void discardPendingMessages(int socket, int nofmessages);
int findSocketsWithPendingMessages(fd_set * fd_write, clientThread * myClient);
void cleanPendingMessages(int socket);
;

