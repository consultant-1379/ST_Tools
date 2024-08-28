#include "DiaProxy.h"

void* _DiaThread(void *arg);

int add_response(puchar pb);

void generatehae(DIAMETER_HEADER *head);

int generate_wdr(puchar pb);

int createCER(uchar *cermsg, struct CER_DATA *cerdata, DiaServerConnection *connection );

void send_WDR_or_DPR_Answer (DiaServerConnection *myConnection, uchar *buff);

void send_Watchdog_Request (DiaServerConnection *myConnection);

void resetAndExit (DiaServerConnection *myConnection, ConnectionStatus status);


int read_message_body (DiaServerConnection *myConnection, int bytes_to_read, puchar *p_head,fd_set fds, int *dp_size);
int findUsedClient();
int findUsedClientWaitingAnswer();
