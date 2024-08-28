#makefile for the DiaProxy

CPPFLAGS_DEBUG = -g -D_DIA_PROXY_LINUX -D_DIA_PROXY_MONITOR #-D_DIA_PROXY_DEBUG #-D_DIA_PROXY_DEBUG_OUT_MESSAGES #-D_DIA_PROXY_DEBUG
OPT_FLAGS = 
BASIC_CPPFLAGS = 
CPPFLAGS = $(OPT_FLAGS) $(BASIC_CPPFLAGS) $(CPPFLAGS_DEBUG) 
LDFLAGS = 
INCLUDES = -I. -I/usr/local/include
LIBS = $(DEBUG_LIBS) -lpthread -lrt 

ifndef DESTDIR
	DESTDIR = $(RPM_BUILD_ROOT)
endif

DIA_PROXY_VERSION = 5.0

SOURCES = DiaMessage.cpp DiaProxy.cpp Logger.cpp AVP.cpp Utils.cpp ProxyThread.cpp ClientThread.cpp ListenerThread.cpp DiaThread.cpp SignalHandling.cpp HearbeatThread.cpp RemoteThread.cpp ReportManagerThread.cpp

DEBUG_OBJECTS =
OBJECTS = $(SOURCES:.cpp=.o) $(DEBUG_OBJECTS)

TARGET = DiaProxy$(DIA_PROXY_VERSION)

all: $(TARGET)
	@echo Building version $(DIA_PROXY_VERSION) 
	make -e $(TARGET)

$(TARGET): $(OBJECTS)
	g++ -g -o $@ $(OBJECTS) $(LIBS)


.cpp.o:
	g++ -g -Wall -c $(CPPFLAGS) $<
	
clean:
	-rm -f $(OBJECTS) $(TARGET)

	
dep: $(SOURCES)
	makedepend $(BASIC_CPPFLAGS) $(SOURCES)

	
install: $(TARGET)
	mkdir -p ${DESTDIR}/${ST_TOOL_PATH}/bin
	cp $(TARGET) ${DESTDIR}/${ST_TOOL_PATH}/bin
	mkdir -p ${DESTDIR}/${ST_TOOL_PATH}/share/DiaProxy
	cp ${GIT_PATH}/ST_Tools/DiaProxy/cfg/* ${DESTDIR}/${ST_TOOL_PATH}/share/DiaProxy
