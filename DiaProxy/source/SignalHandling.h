void signal_all_and_exit(uint sig);

void signal_client_threads(uint sig);

void check_signals(const char *thread, int fd, int pos);

void * handler(void *);
void * _ReportManagerThread(void *);
