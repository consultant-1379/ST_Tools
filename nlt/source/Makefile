#makefile for the Network layer translator

CPPFLAGS_DEBUG = -g  #-D_NLT_DEBUG
OPT_FLAGS = 
BASIC_CPPFLAGS = 
CPPFLAGS = $(OPT_FLAGS) $(BASIC_CPPFLAGS) $(CPPFLAGS_DEBUG) 
LDFLAGS = 
INCLUDES = -I. -I/usr/local/ssl/include -I/usr/local/include
LFLAGS      = -L/usr/local/ssl/lib -L/usr/local/lib
SSLLIBS = `pkg-config libssl --libs`
CRYPTO = `pkg-config libcrypto --libs`
LIBS = $(DEBUG_LIBS) -lpthread -lrt -lst_tools -lconfig++ $(SSLLIBS) $(CRYPTO)

SOURCES = networkLayerTranslator.cpp listenerThread.cpp signalThread.cpp connectionThread.cpp

DEBUG_OBJECTS =
OBJECTS = $(SOURCES:.cpp=.o) $(DEBUG_OBJECTS)

TARGET = networkLayerTranslator

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
	mkdir -p ${DESTDIR}/${ST_TOOL_PATH}/share/nlt
	cp ${GIT_PATH}/ST_Tools/nlt/cfg/* ${DESTDIR}/${ST_TOOL_PATH}/share/nlt
