#makefile for the LoadPlotter

.SUFFIXES: .cpp .h

PLATFORM = LINUX

DEFS =#-D_DEBUG

SFILES = loadplotter.cpp SignalHandling.cpp UtilsLoadMeas.cpp UtilsSsh.cpp  ControlThread.cpp \
         logger.cpp ClientThread_CBA.cpp RemoteThread.cpp


HFILES = $(SFILES:.cpp=.h)

OBJS = $(SFILES:.cpp=.o)

ifndef DESTDIR
	DESTDIR = $(RPM_BUILD_ROOT)
endif

TARGET = LoadPlotter

all: $(TARGET)
	make -e $(TARGET)

$(TARGET): $(OBJS)
	g++ $(LDFLAGS) -o $@ $(OBJS) -lstdc++ -lpthread -lutil -lrt  

.cpp.o:
	g++ -c -g -Wall -D$(PLATFORM) $(DEFS) $<

clean:
	rm -f $(OBJS) $(TARGET)

install: $(TARGET)
	mkdir -p ${DESTDIR}/${ST_TOOL_PATH}/bin
	cp $(TARGET) ${DESTDIR}/${ST_TOOL_PATH}/bin
	mkdir -p ${DESTDIR}/${ST_TOOL_PATH}/share/loadplotter
	cp ${GIT_PATH}/ST_Tools/loadplotter/cfg/* ${DESTDIR}/${ST_TOOL_PATH}/share/loadplotter
