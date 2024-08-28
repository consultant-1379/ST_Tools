#makefile for the ConKeeper

#
.SUFFIXES: .cpp .h


# Operating system (Linux or SunOs)
OSNAME = $(shell uname)

# SYSTEM nickname
SYSTEM_Linux=linux
SYSTEM_SunOS=solaris

SYSTEM=$(SYSTEM_$(OSNAME))

CPPFLAGS = 

INCLUDES = -I. -I/usr/local/include

LIBS = $(DEBUG_LIBS) -lpthread 

ifndef DESTDIR
	DESTDIR = $(RPM_BUILD_ROOT)
endif

SOURCES = remote_control.cpp UDP_remoteControl.cpp

DEBUG_OBJECTS =
OBJECTS = $(SOURCES:.cpp=.o) $(DEBUG_OBJECTS)

TARGET = RemoteControl

all: $(TARGET)
#	@echo Building version $(DIA_PROXY_VERSION) 
	make -e $(TARGET)

$(TARGET): $(OBJECTS)
#	$(CXX) -g -o $@ $(OBJECTS) $(LIBS)
	$(CXX) -o $@ $(OBJECTS) $(LIBS)


.cpp.o:
#	$(CXX) -g -Wall -c $(CPPFLAGS) $<
	$(CXX) -Wall -c $(CPPFLAGS) $<
	
clean:
	-rm -f $(OBJECTS) $(TARGET)

	
install: $(TARGET)
	mkdir -p ${DESTDIR}/${ST_TOOL_PATH}/bin
	cp $(TARGET) ${DESTDIR}/${ST_TOOL_PATH}/bin
