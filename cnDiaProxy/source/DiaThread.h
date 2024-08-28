#include "cnDiaProxy.h"

void* _DiaThread(void *arg);

int add_response(puchar pb,DiaServerConnection *myConnection);

void generatehae(DIAMETER_HEADER *head);

int generate_wdr(puchar pb, DiaServerConnection *myConnection);

int createCER(uchar *cermsg, DiaServerConnection *connection );

int createDPR(uchar *dprmsg, DiaServerConnection *connection );

void send_WDR_or_DPR_Answer (DiaServerConnection *myConnection, uchar *buff);

void send_Watchdog_Request (DiaServerConnection *myConnection);

void resetAndExit (DiaServerConnection *myConnection, ConnectionStatus status);


int read_message_body (DiaServerConnection *myConnection, int bytes_to_read, puchar *p_head, int *dp_size);
int findUsedClient();
int findUsedClientWaitingAnswer();
