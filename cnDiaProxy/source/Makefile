#makefile for the cnDiaProxy

CPPFLAGS_DEBUG = -g -D_DIA_PROXY_LINUX -D_DIA_PROXY_MONITOR  -D_DIA_PROXY_DEBUG 
OPT_FLAGS = 
BASIC_CPPFLAGS = 
CPPFLAGS = $(OPT_FLAGS) $(BASIC_CPPFLAGS) $(CPPFLAGS_DEBUG) 
LDFLAGS =

INCLUDES = -I. -I/usr/local/ssl/include -I/usr/local/include
LFLAGS      = -L/usr/local/ssl/lib -L/usr/local/lib
SSLLIBS = `pkg-config libssl --libs`
CRYPTO = `pkg-config libcrypto --libs`
LIBS = $(DEBUG_LIBS) -lpthread -lrt -lst_tools -lconfig++ $(SSLLIBS) $(CRYPTO)


ifndef DESTDIR
	DESTDIR = $(RPM_BUILD_ROOT)
endif

SOURCES = DiaMessage.cpp cnDiaProxy.cpp AVP.cpp Utils.cpp ProxyThread.cpp ClientThread.cpp ListenerThread.cpp DiaThread.cpp SignalHandling.cpp RemoteThread.cpp ReportManagerThread.cpp

DEBUG_OBJECTS =
OBJECTS = $(SOURCES:.cpp=.o) $(DEBUG_OBJECTS)

TARGET = cnDiaProxy

all: $(TARGET)
	make -e $(TARGET)

$(TARGET): $(OBJECTS)
	g++ -g -o $@ $(OBJECTS) $(LFLAGS) $(LIBS)


.cpp.o:
	g++ -Wall -c $(INCLUDES) $(CPPFLAGS) $<

clean:
	-rm -f $(OBJECTS) $(TARGET)


dep: $(SOURCES)
	makedepend $(BASIC_CPPFLAGS) $(SOURCES)

	
install: $(TARGET)
	mkdir -p ${DESTDIR}/${ST_TOOL_PATH}/bin
	cp $(TARGET) ${DESTDIR}/${ST_TOOL_PATH}/bin
	mkdir -p ${DESTDIR}/${ST_TOOL_PATH}/share/cnDiaProxy
	cp ${GIT_PATH}/ST_Tools/cnDiaProxy/cfg/* ${DESTDIR}/${ST_TOOL_PATH}/share/cnDiaProxy
