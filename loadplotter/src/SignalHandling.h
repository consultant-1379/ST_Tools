void signal_all_and_exit(unsigned int sig);

void signal_client_threads(unsigned int sig);

void check_signals(const char *thread, int fd, int pos);

void * handler(void *);
