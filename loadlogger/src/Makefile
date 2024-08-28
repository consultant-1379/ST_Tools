
.SUFFIXES: .cpp .h

CXX = gcc

PLATFORM = LINUX

DEFS =#-D_DEBUG

SFILES = enums.cpp OMTimer.cpp \
         Logger.cpp Telnet.cpp  \
         ConfigReader.cpp TelOrbLoadLogger.cpp \
         TelOrbMemLogger.cpp Functions.cpp loadlogger.cpp

HFILES = $(SFILES:.cpp=.h)

OBJS = $(SFILES:.cpp=.o)

TARGET = loadlogger.3.0

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(LDFLAGS) -o $@ $(OBJS) -lstdc++ -lpthread

.cpp.o:
	$(CXX) -c -g -Wall -D$(PLATFORM) $(DEFS) $<

clean:
	rm -f $(OBJS)
        
install: $(TARGET)
	mkdir -p ${RPM_BUILD_ROOT}/${ST_TOOL_PATH}/bin
	cp $(TARGET) ${RPM_BUILD_ROOT}/${ST_TOOL_PATH}/bin
	mkdir -p ${RPM_BUILD_ROOT}/${ST_TOOL_PATH}/share/loadlogger
	cp ${GIT_PATH}/ST_Tools/loadlogger/cfg/* ${RPM_BUILD_ROOT}/${ST_TOOL_PATH}/share/loadlogger
