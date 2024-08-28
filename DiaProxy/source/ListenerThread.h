void* _ListenerThread(void *arg);
void close_server_socket ();
int findConnection();
void resetAndExit (int fail);
int addConnectionToClientThread(int clientConnection);
