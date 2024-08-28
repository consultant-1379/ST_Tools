#makefile for the ConKeeper

#
.SUFFIXES: .cpp .h


# Operating system (Linux or SunOs)
OSNAME = $(shell uname)

# SYSTEM nickname
SYSTEM_Linux=linux
SYSTEM_SunOS=solaris

SYSTEM=$(SYSTEM_$(OSNAME))

OFFICIAL_DIRECTORY = /tsp/3rdParty/DiameterProxy/

CPPFLAGS_DEBUG = -D_CON_KEEPER_DEBUG

OPT_FLAGS = 
BASIC_CPPFLAGS = 

CPPFLAGS = $(OPT_FLAGS) $(BASIC_CPPFLAGS) $(CPPFLAGS_DEBUG) 

LDFLAGS = 

INCLUDES = -I. -I/usr/local/include

LIBS = $(DEBUG_LIBS) -lpthread 


SOURCES = ConnectionKeeper.cpp ControlThread.cpp DiameterClientThread.cpp DiameterServerThread.cpp LdapClientThread.cpp AVP.cpp LdapServerThread.cpp ListenerThread.cpp LoadClientThread.cpp LoadServerThread.cpp HearbeatThread.cpp DiaMessage.cpp SignalHandling.cpp Utils.cpp logger.cpp RemoteThread.cpp

DEBUG_OBJECTS =
OBJECTS = $(SOURCES:.cpp=.o) $(DEBUG_OBJECTS)

TARGET = ConKeeper


all: $(TARGET)
	make -e $(TARGET)

$(TARGET): $(OBJECTS)
	$(CXX) -g -o $@ $(OBJECTS) $(LIBS)


.cpp.o:
	$(CXX) -g -Wall -c $(CPPFLAGS) $<
	
clean:
	-rm -f $(OBJECTS) $(TARGET)


install: $(TARGET)
	mkdir -p ${RPM_BUILD_ROOT}/${ST_TOOL_PATH}/bin
	cp $(TARGET) ${RPM_BUILD_ROOT}/${ST_TOOL_PATH}/bin
	mkdir -p ${RPM_BUILD_ROOT}/${ST_TOOL_PATH}/share/conKeeper
	cp ${GIT_PATH}/ST_Tools/conKeeper/cfg/* ${RPM_BUILD_ROOT}/${ST_TOOL_PATH}/share/conKeeper
