#makefile for the CpsMonitor

.SUFFIXES: .cpp .h

CXX = gcc

PLATFORM = LINUX

DEFS =#-D_DEBUG

SFILES = CpsMonitor.cpp logger.cpp SignalHandling.cpp


HFILES = $(SFILES:.cpp=.h)

OBJS = $(SFILES:.cpp=.o)

TARGET = CpsMonitor

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(LDFLAGS) -o $@ $(OBJS) -lstdc++ -lpthread -lutil -lrt 

.cpp.o:
	$(CXX) -c -g -Wall -D$(PLATFORM) $(DEFS) $<

clean:
	rm -f $(OBJS)


install: $(TARGET)
	mkdir -p ${RPM_BUILD_ROOT}/${ST_TOOL_PATH}/bin
	cp $(TARGET) ${RPM_BUILD_ROOT}/${ST_TOOL_PATH}/bin
	mkdir -p ${RPM_BUILD_ROOT}/${ST_TOOL_PATH}/share/CpsMonitor
	cp ${GIT_PATH}/ST_Tools/CpsMonitor/cfg/* ${RPM_BUILD_ROOT}/${ST_TOOL_PATH}/share/CpsMonitor
