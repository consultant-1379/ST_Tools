#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <iostream>
#include <netdb.h>
#include <fcntl.h>
#include <unistd.h>

#include "netcon.h"

using namespace std;

NetworkConnection::NetworkConnection(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::NetworkConnection()" << endl;    
#endif
    fd=-1;
    ipv6=false;
}

NetworkConnection::~NetworkConnection(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::~NetworkConnection()" << endl;    
#endif

    if (fd != -1){
        close(fd);
        fd=-1;
    }
}

bool NetworkConnection::setNonblocking(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::setNonblocking()" << endl;    
#endif

    int status = fcntl(fd, F_SETFL, fcntl(fd, F_GETFL, 0) | O_NONBLOCK);

    if (status == -1){
        errsv = errno;
        error.clear();
        error.str("");
        error << "NetConLib: Failed setting O_NONBLOCK" << endl;
        error <<"\tError: " << strerror(errsv) << endl;
        return false;
    }

    return true;
}

bool NetworkConnection::set_local_addr(const char *hostname){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::set_local_addr(const char *hostname)" << endl;    
#endif

    if (ipv6){
        bzero(&local_addr.v6, sizeof(local_addr.v6));
        local_addr.v6.sin6_family = AF_INET6;

        if (inet_pton(AF_INET6,hostname, &local_addr.v6.sin6_addr.s6_addr) !=1){
            errsv = errno;
            error.clear();
            error.str("");
            error << "NetConLib:  (IPv6) Failed to get sockaddr_in6 for  "<< hostname << " Error: " <<strerror(errsv) << endl;
            return false;
        }        
    }
    else {
        bzero(&local_addr.v4, sizeof(local_addr.v4));
        local_addr.v4.sin_family = AF_INET;
        struct hostent *host;
        if ( (host = gethostbyname(hostname)) == NULL ){
            errsv = errno;
            error.clear();
            error.str("");
            error << "NetConLib:  (IPv4) Failed to get sockaddr_in for  "<< hostname << " Error: " <<strerror(errsv) << endl;
            return false;
        }
        local_addr.v4.sin_addr.s_addr = *(long*)(host->h_addr);
    }


    return true;    
}
bool NetworkConnection::set_local_addr(int port){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::set_local_addr(int port)" << endl;    
#endif

    if (ipv6){
        bzero(&local_addr.v6, sizeof(local_addr.v6));
        local_addr.v6.sin6_family = AF_INET6;
        local_addr.v6.sin6_port = htons(port);
    }
    else {
        bzero(&local_addr.v4, sizeof(local_addr.v4));
        local_addr.v4.sin_family = AF_INET;
        local_addr.v4.sin_port = htons(port);
    }

    return true;    
}
bool NetworkConnection::set_local_addr(const char *hostname, int port){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::set_local_addr(const char *hostname, int port)" << endl;    
#endif

    if (ipv6){
        bzero(&local_addr.v6, sizeof(local_addr.v6));
        local_addr.v6.sin6_family = AF_INET6;
        local_addr.v6.sin6_port = htons(port);

        if (inet_pton(AF_INET6,hostname, &local_addr.v6.sin6_addr.s6_addr) !=1){
            errsv = errno;
            error.clear();
            error.str("");
            error << "NetConLib:  (IPv6) Failed to get sockaddr_in6 for  "<< hostname << " Error: " <<strerror(errsv) << endl;
            return false;
        }        
    }
    else {
        bzero(&local_addr.v4, sizeof(local_addr.v4));
        local_addr.v4.sin_family = AF_INET;
        local_addr.v4.sin_port = htons(port);
        struct hostent *host;
        if ( (host = gethostbyname(hostname)) == NULL ){
            errsv = errno;
            error.clear();
            error.str("");
            error << "NetConLib:  (IPv4) Failed to get sockaddr_in for  "<< hostname << " Error: " <<strerror(errsv) << endl;
            return false;
        }
        local_addr.v4.sin_addr.s_addr = *(long*)(host->h_addr);
    }

    return true;    
}

bool NetworkConnection::bind_socket(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::bind_socket()" << endl;    
#endif

    if (ipv6){
        if (bind(fd, (struct sockaddr*)&local_addr.v6, sizeof(local_addr.v6)) != 0 ){
            errsv = errno;
            error.clear();
            error.str("");
            error << "NetConLib: Error bind IPv6 socket: "<<strerror(errsv)  << endl;
            return false;
        }
    }
    else {
        if (bind(fd, (struct sockaddr*)&local_addr.v4, sizeof(local_addr.v4)) != 0 ){
            errsv = errno;
            error.clear();
            error.str("");
            error << "NetConLib: Error bind  IPv4 socket"<<strerror(errsv)  << endl;
            return false;
        }
    }
    return true;
}

bool NetworkConnection::openListener(const char *hostname, int port, int backlog){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::openListener(const char *hostname, int port, int backlog)" << endl;    
#endif

    const int on = 1;
    setNonblocking();
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, (const void*)&on, (socklen_t)sizeof(on));

    if (hostname == NULL)   set_local_addr(port);
    else                    set_local_addr(hostname, port);

    if (!bind_socket())   return false;

    if ( listen(fd,backlog) != 0 ){
        errsv = errno;
        error.clear();
        error.str("");
        error << "NetConLib: Error openning listener: " << strerror(errsv) << endl;
        return false;
    }
    return true;
    
}

string NetworkConnection::get_local_peer_str(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::get_local_peer_str()" << endl;    
#endif

    stringstream peer;
    char buffer[100];
    socklen_t len ;
    if (ipv6) {
        len = sizeof(local_addr.v6);
        if (getsockname(fd, (struct sockaddr *)&local_addr.v6, &len) == -1){
            errsv=errno;
            peer << "Error getsockname: " << strerror(errsv) <<endl;
        }
        else{
            if (inet_ntop(AF_INET6, &local_addr.v6.sin6_addr, buffer, sizeof(buffer)) == NULL){
                errsv=errno;
                peer << "Error inet_ntop: " << strerror(errsv) <<endl;
            }
            else {
                peer << "[" <<buffer << "] : "<<ntohs(local_addr.v6.sin6_port);
            }
        }
    }
    else {
        len = sizeof(local_addr.v4);
        if (getsockname(fd, (struct sockaddr *)&local_addr.v4, &len) == -1){
            errsv=errno;
            peer << "Error getsockname: " << strerror(errsv) <<endl;
        }
        else{
            if (inet_ntop(AF_INET, &local_addr.v4.sin_addr, buffer, sizeof(buffer)) == NULL){
                errsv=errno;
                peer << "Error inet_ntop: " << strerror(errsv) <<endl;
            }
            else {
                peer << buffer <<" : "<<ntohs(local_addr.v4.sin_port);
            }
        }
    }
    return peer.str();
}

string NetworkConnection::get_remote_peer_str(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::get_remote_peer_str()" << endl;    
#endif

    stringstream peer;
    char buffer[100];
    if (ipv6) {
        if (inet_ntop(AF_INET6, &remote_addr.v6.sin6_addr, buffer, sizeof(buffer)) == NULL){
            errsv=errno;
            peer << "Error inet_ntop: " << strerror(errsv) <<endl;
        }
        else {
            peer << "[" <<buffer << "] : "<<ntohs(remote_addr.v6.sin6_port);
        }
    }
    else {
        if (inet_ntop(AF_INET, &remote_addr.v4.sin_addr, buffer, sizeof(buffer)) == NULL){
            errsv=errno;
            peer << "Error inet_ntop: " << strerror(errsv) <<endl;
        }
        else {
            peer << buffer <<" : "<<ntohs(remote_addr.v4.sin_port);
        }
    }
    return peer.str();

}

int NetworkConnection::server_accept(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::server_accept()" << endl;    
#endif
    
    int client_fd;
    if (ipv6) {
        socklen_t len = sizeof(remote_addr.v6);
        client_fd = accept(fd, (struct sockaddr*)&remote_addr.v6, &len);
    }
    else {
        socklen_t len = sizeof(remote_addr.v4);
        client_fd = accept(fd, (struct sockaddr*)&remote_addr.v4, &len);
    }
    
    return client_fd;
    
}

bool NetworkConnection::client_connect(const char *hostname, int port){   
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::client_connect(const char *hostname, int port)" << endl;    
#endif
    
    if (ipv6){
        bzero(&remote_addr.v6, sizeof(remote_addr.v6));
        remote_addr.v6.sin6_family = AF_INET6;
        remote_addr.v6.sin6_port = htons(port);

        if (inet_pton(AF_INET6,hostname, &remote_addr.v6.sin6_addr.s6_addr) !=1){
            errsv = errno;
            error.clear();
            error.str("");
            error << "NetConLib:  (IPv6) Failed to get sockaddr_in6 for  "<< hostname << " Error: " <<strerror(errsv) << endl;
            return false;
        }        
        if ( connect(fd, (struct sockaddr*)&remote_addr.v6, sizeof(remote_addr.v6)) != 0 ){
            errsv = errno;
            error.clear();
            error.str("");
            error << "NetConLib:  (IPv6) Failed to connect to  "<< hostname << " Error: " <<strerror(errsv) << endl;
            return false;
        }
    }

    else {
        bzero(&remote_addr.v4, sizeof(remote_addr.v4));
        remote_addr.v4.sin_family = AF_INET;
        remote_addr.v4.sin_port = htons(port);

        struct hostent *host;
        if ( (host = gethostbyname(hostname)) == NULL ){
            errsv = errno;
            error.clear();
            error.str("");
            error << "NetConLib:  (IPv4) Failed to get sockaddr_in6 for  "<< hostname << " Error: " <<strerror(errsv) << endl;
            return false;
        }

        remote_addr.v4.sin_addr.s_addr = *(long*)(host->h_addr);
        if ( connect(fd, (struct sockaddr*)&remote_addr.v4, sizeof(remote_addr.v4)) != 0 ){
            errsv = errno;
            error.clear();
            error.str("");
            error << "NetConLib:  (IPv4) Failed to connect to  "<< hostname << " Error: " <<strerror(errsv) << endl;
            return false;
        }
    }
    
    return true;
}


int NetworkConnection::client_write(const char *buffer, int buffer_len){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::client_write(const char *buffer, int buffer_len)" << endl;    
#endif

    int bytes = send(fd,buffer,buffer_len, 0);   
    errsv = errno;
    return bytes;
}

int NetworkConnection::client_read(char *buffer, int buffer_len){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  NetworkConnection::client_read(char *buffer, int buffer_len)" << endl;    
#endif

    memset(buffer, 0, buffer_len);    

    int bytes = recv(fd,buffer,buffer_len,0);
    errsv = errno;
    return bytes;
                    
}

////////////////////////   SCTP   ///////////////

SCTP_NetworkConnection::SCTP_NetworkConnection(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  SCTP_NetworkConnection::SCTP_NetworkConnection()" << endl;    
#endif

    fd = socket(AF_INET, SOCK_STREAM, IPPROTO_SCTP);
}

SCTP_NetworkConnection::SCTP_NetworkConnection(int socket){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  SCTP_NetworkConnection::SCTP_NetworkConnection(int socket)" << endl;    
#endif

    fd = socket;
}

SCTP_NetworkConnection::SCTP_NetworkConnection(bool p_ipv6){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  SCTP_NetworkConnection::SCTP_NetworkConnection(bool p_ipv6)" << endl;    
#endif

    ipv6 = p_ipv6;

    if (p_ipv6)     fd = socket(AF_INET6, SOCK_STREAM, IPPROTO_SCTP);
    else            fd = socket(AF_INET, SOCK_STREAM, IPPROTO_SCTP);
}

SCTP_NetworkConnection::SCTP_NetworkConnection(int socket,bool p_ipv6){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  SCTP_NetworkConnection::SCTP_NetworkConnection(int socket,bool p_ipv6)" << endl;    
#endif

    fd = socket;
    ipv6 = p_ipv6;
    
}

SCTP_NetworkConnection::~SCTP_NetworkConnection(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  SCTP_NetworkConnection::~SCTP_NetworkConnection()" << endl;    
#endif

    if (fd != -1){
        close(fd);
        fd=-1;
    }
}

NetworkConnection * SCTP_NetworkConnection::accept_client(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  SCTP_NetworkConnection::accept_client()" << endl;    
#endif

    int client = NetworkConnection::server_accept();
    SCTP_NetworkConnection * con = new SCTP_NetworkConnection(client, ipv6);
    con->remote_addr = remote_addr;
    con->NetworkConnection::setNonblocking();
    
    return (NetworkConnection *)con;
    
}

bool SCTP_NetworkConnection::client_connect(const char *hostname, int port){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  SCTP_NetworkConnection::client_connect(const char *hostname, int port)" << endl;    
#endif

    if (NetworkConnection::client_connect(hostname, port)){
       return  NetworkConnection::setNonblocking();
    }
    
    return false;
            
}

////////////////////////   DTLS   ///////////////

DTLS_NetworkConnection::DTLS_NetworkConnection(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::DTLS_NetworkConnection()" << endl;    
#endif

    fd = socket(AF_INET, SOCK_STREAM, IPPROTO_SCTP);
    ssl = NULL;
    bio = NULL;
    ctx = NULL;
}

DTLS_NetworkConnection::DTLS_NetworkConnection(int socket){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::DTLS_NetworkConnection(int socket)" << endl;    
#endif
    
    fd = socket;
    ipv6 = false;
    ssl = NULL;
    bio = NULL;
    ctx = NULL;
}

DTLS_NetworkConnection::DTLS_NetworkConnection(bool p_ipv6){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::DTLS_NetworkConnection(bool p_ipv6)" << endl;    
#endif
    
    ipv6 = p_ipv6;
    if (p_ipv6)     fd = socket(AF_INET6, SOCK_STREAM, IPPROTO_SCTP);
    else            fd = socket(AF_INET, SOCK_STREAM, IPPROTO_SCTP);

    ssl = NULL;
    bio = NULL;
    ctx = NULL;
}

DTLS_NetworkConnection::DTLS_NetworkConnection(int socket, bool p_ipv6){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::DTLS_NetworkConnection(int socket, bool p_ipv6)" << endl;    
#endif

    fd = socket;
    ipv6 = p_ipv6;
    ssl = NULL;
    bio = NULL;
    ctx = NULL;
}

DTLS_NetworkConnection::~DTLS_NetworkConnection(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::~DTLS_NetworkConnection()" << endl;    
#endif

   if (ssl){
        SSL_free(ssl);
    }
    if (fd != -1){
        close(fd);
        fd=-1;
    }
    if (ctx){
        SSL_CTX_free(ctx);
    }
}

bool DTLS_NetworkConnection::shutdown_received(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::shutdown_received()" << endl;    
#endif

    return SSL_get_shutdown(ssl);
}

bool DTLS_NetworkConnection::set_method_name(string name){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::set_method_name(string name)" << endl;    
#endif

    if (name == "DTLS")            method_name = name;
    else {
        error.clear();
        error.str("");
        error << "NetConLib: ERROR: Not allowed value for ssl protocol: " << name<< endl;
        error << "Allowed values:  DTLS" << endl;
        return false;
    }
    return true;
   
}
bool DTLS_NetworkConnection::openListener(const char *hostname, int port, int backlog){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::openListener(const char *hostname, int port, int backlog)" << endl;    
#endif

    bio = BIO_new_dgram_sctp(fd, BIO_NOCLOSE);
    if (!bio) {
        error.clear();
        error.str("");
        error  << "ERROR: in DTLS_NetworkConnection::openListener  BIO_new_dgram_sctp" << endl;        
        return false;
    }
    
    return NetworkConnection::openListener(hostname, port, backlog);

}

bool DTLS_NetworkConnection::init_client_SSL(struct Credentials cred_client){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::init_client_SSL(struct Credentials cred_client)" << endl;    
#endif

    SSL_METHOD const *method;
    if (method_name == "DTLS")            method = DTLS_client_method();
    else                                  method = DTLS_client_method();
    
    ctx = SSL_CTX_new(method);
    if ( ctx == NULL ){
        error.clear();
        error.str("");
        error  << "SSL_CTX_new : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }

    if (!LoadClientCertificates(ctx, cred_client)) {

        error.clear();
        error.str("");
        error  << "LoadClientCertificates : " << ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }

    ssl = SSL_new(ctx);
    bio = BIO_new_dgram_sctp(fd, BIO_CLOSE);
    if (!bio) {
        error.clear();
        error.str("");
        error  << "BIO_new_dgram_sctp : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }
    return true;
    
}

bool DTLS_NetworkConnection::init_server_SSL(struct Credentials cred_server, bool request_credentials){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::init_server_SSL(struct Credentials cred_server, bool request_credentials)" << endl;    
#endif

    SSL_METHOD const *method;
    if (method_name == "DTLS")           method = DTLS_server_method();
    else                                  method = DTLS_server_method();

    ctx = SSL_CTX_new(method);
    if ( ctx == NULL ){
        error.clear();
        error.str("");
        error  << "SSL_CTX_new : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }
    
    if (!LoadServerCertificates(ctx, cred_server, request_credentials)) {

        error.clear();
        error.str("");
        error  << "LoadServerCertificates : " << ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }

    ssl = SSL_new(ctx);
    int pid = getpid();
    if( !SSL_CTX_set_session_id_context(ctx, (const unsigned char*)&pid, sizeof pid) ){
        error.clear();
        error.str("");
        error  << "SSL_CTX_set_session_id_context : " << ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }

    return true;
    
}
NetworkConnection * DTLS_NetworkConnection::accept_client(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::accept_client()" << endl;    
#endif

    int client = NetworkConnection::server_accept();
    DTLS_NetworkConnection * con = new DTLS_NetworkConnection(client, ipv6);
    con->remote_addr = remote_addr;
    con->ssl = SSL_new(ctx);
    if (!con->ssl) {
        error.clear();
        error.str("");
        error  << "DTLS_NetworkConnection::accept SSL_new : " << ERR_error_string(ERR_get_error(), NULL) << endl;
        delete con;
        return NULL;
    }
    
    con->bio = BIO_new_dgram_sctp(client, BIO_NOCLOSE);
    if (!con->bio) {
        error.clear();
        error.str("");
        error << "NetConLib: DTLS_NetworkConnection::accept BIO_new_dgram_sctp : " << ERR_error_string(ERR_get_error(), NULL) << endl;
        delete con;
        return NULL;
    }

    SSL_set_bio(con->ssl, con->bio, con->bio);

    if (SSL_accept(con->ssl) <= 0) {
        error.clear();
        error.str("");
        error << "NetConLib: DTLS_NetworkConnection::accept SSL_accept : " << ERR_error_string(ERR_get_error(), NULL) << endl;
        delete con;
        return NULL;
    }
    
#ifdef _NET_CON_DEBUG
    ShowCerts(con->ssl);
#endif
 
 return (NetworkConnection *)con;
    
}

bool DTLS_NetworkConnection::client_connect(const char *hostname, int port){   
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::client_connect(const char *hostname, int port)" << endl;    
#endif
    
    if (!NetworkConnection::client_connect(hostname, port)) return false;

    SSL_set_bio(ssl, bio, bio);
    if ( SSL_connect(ssl) == FAIL ) {  
        error.clear();
        error.str("");
        error << "NetConLib: SSL_connect fails" << ERR_error_string(ERR_get_error(), NULL) << endl;
        return false; 
    }

    memset(&sinfo, 0, sizeof(struct bio_dgram_sctp_sndinfo));
    BIO_ctrl(bio, BIO_CTRL_DGRAM_SCTP_SET_SNDINFO, sizeof(struct bio_dgram_sctp_sndinfo), &sinfo);

#ifdef _NET_CON_DEBUG
    ShowCerts(ssl);
#endif

    return true;
}

bool DTLS_NetworkConnection::client_disconnect(){   
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::client_disconnect()" << endl;    
#endif
    
    if (ssl){
        SSL_shutdown(ssl);
    }
    
    return true;
}

int DTLS_NetworkConnection::client_write(const char *buffer, int buffer_len){   
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::client_write(const char *buffer, int buffer_len)" << endl;    
#endif

    memset(&sinfo, 0, sizeof(struct bio_dgram_sctp_sndinfo));
    BIO_ctrl(bio, BIO_CTRL_DGRAM_SCTP_SET_SNDINFO, sizeof(struct bio_dgram_sctp_sndinfo), &sinfo);

    int bytes = SSL_write(ssl, buffer, buffer_len);

    switch (SSL_get_error(ssl, bytes)) {
        case SSL_ERROR_NONE:
#ifdef _NET_CON_DEBUG
            cout << "NET_CON_DEBUG   SSL_ERROR_NONE " << endl;
            BIO_ctrl(bio, BIO_CTRL_DGRAM_SCTP_GET_SNDINFO, sizeof(struct bio_dgram_sctp_sndinfo), &sinfo);
            cout << "NET_CON_DEBUG   Wrote " << bytes << " bytes, stream: " ;
            cout << sinfo.snd_sid << ", ppid: " << sinfo.snd_ppid << endl;
#endif
            break;
        case SSL_ERROR_WANT_WRITE:
#ifdef _NET_CON_DEBUG
            cout << "NET_CON_DEBUG   SSL_ERROR_WANT_WRITE set errsv = EAGAIN" << endl;
#endif
            errsv = EAGAIN;
            break;
        case SSL_ERROR_WANT_READ:
#ifdef _NET_CON_DEBUG
            cout << "NET_CON_DEBUG   SSL_ERROR_WANT_READ : Just try again" << endl;
#endif
            break;
        case SSL_ERROR_SYSCALL:
            error.clear();
            error.str("");
            error << "NetConLib:  SSL_ERROR_SYSCALL Socket write error" << endl;
            return -1;
        case SSL_ERROR_SSL:
            error.clear();
            error.str("");
            error << "NetConLib:  SSL_ERROR_SSL write error: " << ERR_error_string(ERR_get_error(), NULL) << endl;
            return -1;
        default:
            error.clear();
            error.str("");
            error << "NetConLib:  Unexpected error while writing " << endl;
            return -1;
    }
    return bytes;
    
}
int DTLS_NetworkConnection::ssl_pending_bytes(){
#ifdef _NET_CON_DEBUG
//     cout << "NET_CON_DEBUG  DTLS_NetworkConnection::ssl_pending_bytes()" << endl;    
#endif
    
    if (ssl)    return SSL_pending(ssl);
    else        return 0;
    
}

int DTLS_NetworkConnection::client_read(char *buffer, int buffer_len){   
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  DTLS_NetworkConnection::client_read(char *buffer, int buffer_len)" << endl;    
#endif

//     time_t clk= time(NULL);
//     std::string timestamp (ctime(&clk));
//     cout << "client_read start time" << timestamp << endl;
    
    memset(buffer, 0, buffer_len);    
    int bytes;
    bool keep_reading = true;
    while (keep_reading) {
        memset(&rinfo, 0, sizeof(struct bio_dgram_sctp_rcvinfo));
        BIO_ctrl(bio, BIO_CTRL_DGRAM_SCTP_SET_RCVINFO, sizeof(struct bio_dgram_sctp_rcvinfo), &rinfo);
        bytes = SSL_read(ssl, buffer, buffer_len);
        switch (SSL_get_error(ssl, bytes)) {
            case SSL_ERROR_NONE:
#ifdef _NET_CON_DEBUG
                cout << "NET_CON_DEBUG   SSL_ERROR_NONE " << endl;
                BIO_ctrl(bio, BIO_CTRL_DGRAM_SCTP_GET_RCVINFO, sizeof(struct bio_dgram_sctp_rcvinfo), &rinfo);
                cout << "NET_CON_DEBUG   Read " << bytes << " bytes, stream: " ;
                cout << rinfo.rcv_sid << ", ppid: " << rinfo.rcv_ppid << endl,
#endif
                keep_reading = false;
                break;
            case SSL_ERROR_WANT_READ:
#ifdef _NET_CON_DEBUG
                cout << "NET_CON_DEBUG   SSL_ERROR_WANT_READ : Just try again" << endl;
#endif
                break;
            case SSL_ERROR_ZERO_RETURN:
#ifdef _NET_CON_DEBUG
                cout << "NET_CON_DEBUG   SSL_ERROR_ZERO_RETURN " << endl;
#endif
                keep_reading = false;
                break;
            case SSL_ERROR_SYSCALL:
                error.clear();
                error.str("");
                error << "NetConLib:  SSL_ERROR_SYSCALL Socket read error" << endl;
                return -1;;
            case SSL_ERROR_SSL:
                error.clear();
                error.str("");
                error << "NetConLib:  SSL_ERROR_SSL read error: " << ERR_error_string(ERR_get_error(), NULL) << endl;
                return -1;;
            default:
                error.clear();
                error.str("");
                error << "NetConLib:  Unexpected error while writing " << endl;
                return -1;
        }
    } 
//     timestamp = ctime(&clk);
//     cout << "client_read stop time" << timestamp << endl;
    return bytes;
}

////////////////////////   TCP   ///////////////

TCP_NetworkConnection::TCP_NetworkConnection(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TCP_NetworkConnection::TCP_NetworkConnection()" << endl;    
#endif
    fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
}

TCP_NetworkConnection::TCP_NetworkConnection(int socket){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TCP_NetworkConnection::TCP_NetworkConnection(int socket)" << endl;    
#endif

    fd = socket;
}

TCP_NetworkConnection::TCP_NetworkConnection(bool p_ipv6){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TCP_NetworkConnection::TCP_NetworkConnection(bool p_ipv6)" << endl;    
#endif
    
    ipv6 = p_ipv6;
    
    if (p_ipv6)     fd = socket(AF_INET6, SOCK_STREAM, IPPROTO_TCP);
    else            fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
}

TCP_NetworkConnection::TCP_NetworkConnection(int socket, bool p_ipv6){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TCP_NetworkConnection::TCP_NetworkConnection(int socket, bool p_ipv6)" << endl;    
#endif

    fd = socket;
    ipv6 = p_ipv6;
}

TCP_NetworkConnection::~TCP_NetworkConnection(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TCP_NetworkConnection::~TCP_NetworkConnection()" << endl;    
#endif
    if (fd != -1){
        close(fd);
        fd=-1;
    }
}

NetworkConnection * TCP_NetworkConnection::accept_client(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TCP_NetworkConnection::accept_client()" << endl;    
#endif

    int client = NetworkConnection::server_accept();
    TCP_NetworkConnection * con = new TCP_NetworkConnection(client, ipv6);

    con->remote_addr = remote_addr; 
    
    con->NetworkConnection::setNonblocking();
    
    return (NetworkConnection *)con;
    
}

bool TCP_NetworkConnection::client_connect(const char *hostname, int port){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TCP_NetworkConnection::client_connect(const char *hostname, int port)" << endl;    
#endif

    if (NetworkConnection::client_connect(hostname, port)){
       return  NetworkConnection::setNonblocking();
    }
    
    return false;
            
}

////////////////////////   TLS   ///////////////
TLS_NetworkConnection::TLS_NetworkConnection(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::TLS_NetworkConnection()" << endl;    
#endif
    fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    ssl = NULL;
    ctx = NULL;
}

TLS_NetworkConnection::TLS_NetworkConnection(int socket){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::TLS_NetworkConnection(int socket)" << endl;    
#endif
    
    fd = socket;
    ssl = NULL;
    ctx = NULL;
}

TLS_NetworkConnection::TLS_NetworkConnection(bool p_ipv6){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::TLS_NetworkConnection(bool p_ipv6)" << endl;    
#endif

    ipv6 = p_ipv6;
    if (p_ipv6)     fd = socket(AF_INET6, SOCK_STREAM, IPPROTO_TCP);
    else            fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);

    ssl = NULL;
    ctx = NULL;
}

TLS_NetworkConnection::TLS_NetworkConnection(int socket, bool p_ipv6){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::TLS_NetworkConnection(int socket, bool p_ipv6)" << endl;    
#endif
    
    fd = socket;
    ipv6 = p_ipv6;
    ssl = NULL;
    ctx = NULL;
}


TLS_NetworkConnection::~TLS_NetworkConnection(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::~TLS_NetworkConnection()" << endl;    
#endif
    if (ssl){
        SSL_free(ssl);
    }
    if (fd != -1){
        close(fd);
        fd=-1;
    }
    if (ctx){
        SSL_CTX_free(ctx);
    }
}

bool TLS_NetworkConnection::set_method_name(string name){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::set_method_name(string name)" << endl;    
#endif
    if (name == "TLSv1_2")          method_name = name;
    else if (name == "SSLv23")      method_name = name;
    else {
        error.clear();
        error.str("");
        error << "NetConLib: ERROR: Not allowed value for ssl protocol: " << name<< endl;
        error << "Allowed values:  TLSv1  SSLv23" << endl;
        return false;
    }
    return true;
   
}

bool TLS_NetworkConnection::init_client_SSL(struct Credentials cred_client){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::init_client_SSL(struct Credentials cred_client)" << endl;    
#endif
    
    SSL_METHOD const *method;

    if (method_name == "TLSv1_2")         method = TLSv1_2_client_method();
    else                                  method = SSLv23_client_method();

    ctx = SSL_CTX_new(method);
    if ( ctx == NULL ){
        error.clear();
        error.str("");
        error << "NetConLib: SSL_CTX_new : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }

    if (!LoadClientCertificates(ctx, cred_client)) {

        error.clear();
        error.str("");
        error  << "LoadClientCertificates : " << ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }

    ssl = SSL_new(ctx);
    if ( ssl == NULL ){
        error.clear();
        error.str("");
        error << "NetConLib: SSL_new : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }


    return true;    
}

bool TLS_NetworkConnection::init_server_SSL(struct Credentials cred_server, bool request_credentials){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::init_server_SSL(struct Credentials cred_server, bool request_credentials)" << endl;    
#endif

    SSL_METHOD const *method;

    if (method_name == "TLSv1_2")         method = TLSv1_2_server_method();
    else                                  method = SSLv23_server_method();

    ctx = SSL_CTX_new(method);
    if ( ctx == NULL ){
        error.clear();
        error.str("");
        error << "NetConLib: SSL_CTX_new : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }

    if (!LoadServerCertificates(ctx, cred_server, request_credentials)) {

        error.clear();
        error.str("");
        error  << "LoadServerCertificates : " << ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }

    ssl = SSL_new(ctx);
    if ( ssl == NULL ){
        error.clear();
        error.str("");
        error << "NetConLib: SSL_new : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }

    return true;
    
}

NetworkConnection *  TLS_NetworkConnection::accept_client(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::accept_client" << endl;    
#endif

    int client = NetworkConnection::server_accept();
    TLS_NetworkConnection * con = new TLS_NetworkConnection(client,ipv6);
    con->remote_addr = remote_addr;

    con->ssl = SSL_new(ctx);
    if (!con->ssl) {
        error.clear();
        error.str("");
        error << "NetConLib: TLS_NetworkConnection::accept SSL_new : " << ERR_error_string(ERR_get_error(), NULL) << endl;
        delete con;
        return NULL;
    }
    
    SSL_set_fd(con->ssl, client);
 
    if (SSL_accept(con->ssl) <= 0) {
        error.clear();
        error.str("");
        error << "NetConLib: TLS_NetworkConnection::accept SSL_accept : " << ERR_error_string(ERR_get_error(), NULL) << endl;
        delete con;
        return NULL;
    }
 
#ifdef _NET_CON_DEBUG
    ShowCerts(con->ssl);
#endif

    return (NetworkConnection *)con;
    
}

bool TLS_NetworkConnection::client_connect(const char *hostname, int port){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::client_connect(const char *hostname, int port)" << endl;    
#endif

    if (!NetworkConnection::client_connect(hostname, port)) return false;

    SSL_set_fd(ssl, fd); 

    if ( SSL_connect(ssl) == FAIL ) { 
        error.clear();
        error.str("");
        error << "NetConLib: SSL_connect fails: " << ERR_error_string(ERR_get_error(), NULL) << endl;
        return false; 
    }

#ifdef _NET_CON_DEBUG
    ShowCerts(ssl);
#endif

    return true;    
}

bool TLS_NetworkConnection::client_disconnect(){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::client_disconnect()" << endl;    
#endif
}

int TLS_NetworkConnection::client_write(const char *buffer, int buffer_len){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::client_write(const char *buffer, int buffer_len)" << endl;
#endif

    int bytes = SSL_write(ssl,buffer,buffer_len);   
    errsv = errno;
    return bytes;
}

int TLS_NetworkConnection::ssl_pending_bytes(){
#ifdef _NET_CON_DEBUG
//     cout << "NET_CON_DEBUG  TLS_NetworkConnection::ssl_pending_bytes()" << endl;    
#endif
    
    if (ssl)    return SSL_pending(ssl);
    else        return 0;
    
}
int TLS_NetworkConnection::client_read(char *buffer, int buffer_len){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  TLS_NetworkConnection::client_read(char *buffer, int buffer_len)" << endl;
#endif
    memset(buffer, 0, buffer_len);    

    int bytes = SSL_read(ssl,buffer,buffer_len);
    return bytes;

    
}
        
///////////////////////////////////////////////////////////////////////////////////
///////////////         Common functions
///////////////////////////////////////////////////////////////////////////////////


string get_nic_ip_to_dest_host(string host)
{
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  get_nic_ip_to_dest_host(string host)" << endl;
#endif
    
    string nic_ip = "";
    string name_data = tmpnam(NULL);
    string name_log = tmpnam(NULL);
    string cmd = "ip route get " + host + " 2>" + name_log + "|  sed -nr 's/.*src \([^ ]*\).*/\\1/p' 1> " + name_data;

    if(system(cmd.c_str())!=0){
        cout << "NetConLib: ERROR-> There is some problem reading nic ip to " << host << ". Analyze " << name_log << endl;
        return nic_ip;
    }

    ifstream inFile;
    inFile.open (name_data.c_str());
    if (!inFile) {
        cout << "NetConLib: ERROR-> " << name_data<< " can not be opened" << endl;
        return nic_ip;
    }
    string line;
    while (getline(inFile, line)){
        nic_ip = line;
    }
    inFile.close();
    if (nic_ip.empty()){
        cout << "NetConLib: ERROR-> There is some problem reading nic ip to " << host  << endl;
        return nic_ip;
    }
    cmd = "rm " + name_data + " " + name_log;
    system(cmd.c_str());
    return nic_ip;
}

bool is_ipv4(const char *src) {
    char buf[16];
    if (inet_pton(AF_INET, src, buf)) {
        return true;
    }
    return false;
}

bool is_ipv6(const char *src) {
    char buf[16];
    if (inet_pton(AF_INET6, src, buf)) {
        return true;
    }
    return false;
}

///////////////////////////////////////////////////////////////////////////////////
///////////////         SSL functions
///////////////////////////////////////////////////////////////////////////////////

int passwd_cb(char *buf,int size,int rwflag,void *userdata)
{
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  passwd_cb(char *buf,int size,int rwflag,void *userdata)" << endl;
#endif

  char *password=(char*)userdata;
  int password_length;
  
  password_length = strlen(password);

  if ((password_length + 1) > size) {
    cout << "NetConLib: ERROR-> passwd_cb : Password specified by environment variable is too big" << endl;
    return 0;
  }
  
  strcpy(buf,password);
  return password_length;
  
} 

int verify_callback(int ok, X509_STORE_CTX *store) {
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  verify_callback(int ok, X509_STORE_CTX *store)" << endl;
#endif
    
    char data[256];

    if (!ok) {
        X509 *cert = X509_STORE_CTX_get_current_cert(store);
        int  depth = X509_STORE_CTX_get_error_depth(store);
        int  err = X509_STORE_CTX_get_error(store);

        cout << "NetConLib: verify_callback-> Error with certificate at depth: "<< depth << endl;
        X509_NAME_oneline(X509_get_issuer_name(cert), data, 256);
        cout << "NetConLib: verify_callback-> issuer  = " << data << endl;
        X509_NAME_oneline(X509_get_subject_name(cert), data, 256);
        cout << "NetConLib: verify_callback-> subject = " << data << endl;
        cout << "NetConLib: verify_callback-> err " << err << ":" << X509_verify_cert_error_string(err) << endl;
    }

    return ok;
}


bool LoadServerCertificates(SSL_CTX* ctx, struct Credentials cred, bool request_credentials){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  LoadServerCertificates(SSL_CTX* ctx, struct Credentials cred, bool request_credentials)" << endl;
#endif

    if (request_credentials){
    /* Set the CA file location for the server */
        if (!SSL_CTX_load_verify_locations(ctx, (char*)cred.CA_File.c_str(), NULL)) {
            cout << "NetConLib: ERROR-> SSL_CTX_load_verify_locations : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
            return false;
        }

        /* Load the client's CA file location as well */
        SSL_CTX_set_client_CA_list(ctx, SSL_load_client_CA_file((char*)cred.CA_File.c_str()));
    }

    /* set the local certificate from CertFile */
    if ( SSL_CTX_use_certificate_file(ctx, (char*)cred.CertFile.c_str(), SSL_FILETYPE_PEM) != 1 ){
        cout << "NetConLib: ERROR-> SSL_CTX_use_certificate_file : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }
    
    /* set the local passwd  */
    if (!cred.password.empty()){
        SSL_CTX_set_default_passwd_cb_userdata(ctx, (void*) cred.password.c_str());
        SSL_CTX_set_default_passwd_cb(ctx,passwd_cb);
    }
    
    /* set the private key from KeyFile (may be the same as CertFile) */
    if ( SSL_CTX_use_PrivateKey_file(ctx, (char*)cred.KeyFile.c_str(), SSL_FILETYPE_PEM) <= 0  ){
        cout << "NetConLib: ERROR-> SSL_CTX_use_PrivateKey_file : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }
    /* verify private key */
    if ( SSL_CTX_check_private_key(ctx) != 1){
        cout << "NetConLib: ERROR-> SSL_CTX_check_private_key : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        cout << "NetConLib: ERROR-> Private key does not match the public certificate" << endl;
        return false;
    }

    /* We won't handle incomplete read/writes due to renegotiation */
    SSL_CTX_set_mode(ctx, SSL_MODE_AUTO_RETRY);

    if (request_credentials){

        /* Specify that we need to verify the client as well */
        SSL_CTX_set_verify(ctx,
                        SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT,
                        verify_callback);

        /* We accept only certificates signed only by the CA himself */
        SSL_CTX_set_verify_depth(ctx, 1);
    
    }
    else {
        SSL_CTX_set_verify(ctx, SSL_VERIFY_NONE, NULL);
    }

    return true;
}

bool LoadClientCertificates(SSL_CTX* ctx, struct Credentials cred){
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  LoadClientCertificates(SSL_CTX* ctx, struct Credentials cred)" << endl;
#endif

    /* Set the CA file location for the server */
    if (!SSL_CTX_load_verify_locations(ctx, (char*)cred.CA_File.c_str(), NULL)) {
        cout << "NetConLib: ERROR-> SSL_CTX_load_verify_locations : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }

    /* set the local certificate from CertFile */
    if ( SSL_CTX_use_certificate_file(ctx, (char*)cred.CertFile.c_str(), SSL_FILETYPE_PEM) != 1  ){
        cout << "NetConLib: ERROR-> SSL_CTX_use_certificate_file : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }
    
    /* set the local passwd  */
    if (!cred.password.empty()){
        SSL_CTX_set_default_passwd_cb_userdata(ctx, (void*) cred.password.c_str());
        SSL_CTX_set_default_passwd_cb(ctx,passwd_cb);
    }
    
    /* set the private key from KeyFile (may be the same as CertFile) */
    if ( SSL_CTX_use_PrivateKey_file(ctx, (char*)cred.KeyFile.c_str(), SSL_FILETYPE_PEM) != 1  ){
        cout << "NetConLib: ERROR-> SSL_CTX_use_PrivateKey_file : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        return false;
    }
    /* verify private key */
    if ( SSL_CTX_check_private_key(ctx) != 1){
        cout << "NetConLib: ERROR-> SSL_CTX_check_private_key : " <<ERR_error_string(ERR_get_error(), NULL) << endl;
        cout << "NetConLib: ERROR-> Private key does not match the public certificate" << endl;
        return false;
    }

    /* We won't handle incomplete read/writes due to renegotiation */
    SSL_CTX_set_mode(ctx, SSL_MODE_AUTO_RETRY);

    /* Specify that we need to verify the server's certificate */
    SSL_CTX_set_verify(ctx, SSL_VERIFY_PEER, verify_callback);

    /* We accept only certificates signed only by the CA himself */
    SSL_CTX_set_verify_depth(ctx, 1);


    return true;    
}

bool rand_initialize() {
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  rand_initialize()" << endl;
#endif

    while (!RAND_status()) {
        struct timeval tv;
        if (gettimeofday(&tv, NULL) != -1 ) RAND_seed( &tv.tv_usec, sizeof(tv.tv_usec));
        else {
            cout << "NetConLib: ERROR-> Can't get time to seed PRNG." << endl;
            return false;
        }
    }
    return true;
}

void ShowCerts(SSL* ssl) {
#ifdef _NET_CON_DEBUG
    cout << "NET_CON_DEBUG  ShowCerts(SSL* ssl)" << endl;
#endif

    X509 *cert;
    char *line;
    cert = SSL_get_peer_certificate(ssl); /* Get certificates (if available) */
    if ( cert != NULL ) {
        cout << "NetConLib: SSL certificates:" << endl;
        line = X509_NAME_oneline(X509_get_subject_name(cert), 0, 0);
        cout << "NetConLib: Subject: "<< line << endl;
        free(line);
        line = X509_NAME_oneline(X509_get_issuer_name(cert), 0, 0);
        cout << "NetConLib: Issuer: "<< line << endl;
        free(line);
        X509_free(cert);
    }
    else
        cout << "NetConLib: No certificates." << endl;
}


