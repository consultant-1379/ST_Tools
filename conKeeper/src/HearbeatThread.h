#include "DiaProxy.h"

void* _HearbeatThread(void *arg);

bool checkConnection(char * connection_host);

int createCER(uchar *cermsg, struct CER_DATA *cerdata);

bool receive_CEA (int localSockId);

void resetExit (int fail);


