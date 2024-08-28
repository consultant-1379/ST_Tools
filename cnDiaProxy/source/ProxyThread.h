#include "cnDiaProxy.h"
void* _ProxyThread(void *arg);

bool is_process_alive(pthread_t* process_id);
int displayStatistic(void *connection, int index);
