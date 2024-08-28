#ifndef NETWORK_CONNECTION_H
#define NETWORK_CONNECTION_H
#include "openssl/ssl.h"
#include "openssl/err.h"
#include <openssl/rand.h>
#include <netinet/in.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <sys/time.h>
#include <time.h>

#define FAIL    -1

using namespace std;

string get_nic_ip_to_dest_host(string host);
bool is_ipv4(const char *src);
bool is_ipv6(const char *src);

int passwd_cb(char *buf,int size,int rwflag,void *userdata);
int verify_callback(int ok, X509_STORE_CTX *store);
void ShowCerts(SSL* ssl);
bool rand_initialize();
bool LoadServerCertificates(SSL_CTX* ctx, struct Credentials cred, bool request_credentials);
bool LoadClientCertificates(SSL_CTX* ctx, struct Credentials cred);


typedef union {
  struct sockaddr_in v4;
  struct sockaddr_in6 v6;
} SockAddr;

struct Credentials {
    string CertFile;
    string KeyFile;
    string CA_File;
    string password;
};

class NetworkConnection {
    public:
        NetworkConnection();
        virtual ~NetworkConnection();
        
        bool set_local_addr(const char *hostanme);
        bool set_local_addr(int port);
        bool set_local_addr(const char *hostanme, int port);
        string get_local_peer_str();
        string get_remote_peer_str();
        int get_fd(){return fd;};
        bool is_ipv6() {return ipv6;};
        bool setNonblocking();
        bool bind_socket();
        string get_error_str(){return error.str();};
        int get_errsv(){return errsv;};
        
        virtual SSL * get_ssl(){};
        virtual SSL_CTX * get_ctx(){};
        virtual bool init_client_SSL(struct Credentials cred_client) {};
        virtual bool init_server_SSL(struct Credentials cred_server, bool request_credentials) {};
        virtual bool set_method_name(string name){};        
        virtual bool openListener(const char *hostname, int port, int backlog=10);
        virtual int server_accept();
        virtual NetworkConnection *  accept_client(){};
        virtual bool client_connect(const char *hostname, int port) ;
        virtual bool client_disconnect(){};
        virtual int client_write(const char *buffer, int buffer_len);
        virtual int client_read(char *buffer, int buffer_len);
        virtual bool shutdown_received(){return false;};
        virtual int ssl_pending_bytes(){return 0;};

protected:
        int fd;
        bool ipv6;
        SockAddr local_addr;
        SockAddr remote_addr;
        stringstream error;
        int errsv;
};


class TCP_NetworkConnection : public NetworkConnection {
    public:
        TCP_NetworkConnection();
        TCP_NetworkConnection(int socket);
        TCP_NetworkConnection(bool p_ipv6);
        TCP_NetworkConnection(int socket,bool p_ipv6);
        ~TCP_NetworkConnection();

        NetworkConnection * accept_client();
        bool client_connect(const char *hostname, int port);

    private:
};

class TLS_NetworkConnection : public NetworkConnection {
    public:
        TLS_NetworkConnection();
        TLS_NetworkConnection(int socket);
        TLS_NetworkConnection(bool p_ipv6);
        TLS_NetworkConnection(int socket,bool p_ipv6);
        ~TLS_NetworkConnection();

        bool init_client_SSL(struct Credentials cred_client);
        bool init_server_SSL(struct Credentials cred_server, bool request_credentials);
        NetworkConnection *  accept_client();
        bool client_connect(const char *hostname, int port);
        bool client_disconnect();
        int client_write(const char *buffer, int buffer_len);
        int client_read(char *buffer, int buffer_len);
        bool set_method_name(string name);        
        SSL_CTX * get_ctx() {return ctx;};
        SSL * get_ssl(){return ssl;};
        int ssl_pending_bytes();

    private:
        SSL *ssl;
        SSL_CTX *ctx;
        string method_name;
};

class SCTP_NetworkConnection : public NetworkConnection {
    public:
        SCTP_NetworkConnection();
        SCTP_NetworkConnection(int socket);
        SCTP_NetworkConnection(bool p_ipv6);
        SCTP_NetworkConnection(int socket,bool p_ipv6);
        ~SCTP_NetworkConnection();

        NetworkConnection * accept_client();
        bool client_connect(const char *hostname, int port);

    private:
};

class DTLS_NetworkConnection : public NetworkConnection {
    public:
        DTLS_NetworkConnection();
        DTLS_NetworkConnection(int socket);
        DTLS_NetworkConnection(bool p_ipv6);
        DTLS_NetworkConnection(int socket,bool p_ipv6);
        ~DTLS_NetworkConnection();
        
        bool init_client_SSL(struct Credentials cred_client);
        bool init_server_SSL(struct Credentials cred_server, bool request_credentials);
        NetworkConnection *  accept_client();
        bool client_connect(const char *hostname, int port);
        bool openListener(const char *hostname, int port, int backlog=10);
        bool client_disconnect();
        int client_write(const char *buffer, int buffer_len);
        int client_read(char *buffer, int buffer_len);
        bool shutdown_received();
        bool set_method_name(string name);
        SSL_CTX * get_ctx() {return ctx;};
        SSL * get_ssl(){return ssl;};
        int ssl_pending_bytes();

    private:
        SSL *ssl;
        BIO *bio;
        SSL_CTX *ctx;
        string method_name;

        struct bio_dgram_sctp_sndinfo sinfo;
        struct bio_dgram_sctp_rcvinfo rinfo;
    
};


#endif
