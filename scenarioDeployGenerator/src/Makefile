#
.SUFFIXES: .cpp .h

CPPFLAGS_DEBUG = -g 

OPT_FLAGS = 

BASIC_CPPFLAGS = 

CPPFLAGS = $(OPT_FLAGS) $(BASIC_CPPFLAGS) $(CPPFLAGS_DEBUG) 

LDFLAGS = 
LIBS = $(DEBUG_LIBS) 

SOURCES = scenarioDeployGenerator.cpp 

DEBUG_OBJECTS =
OBJECTS = $(SOURCES:.cpp=.o) $(DEBUG_OBJECTS)

TARGET = scenarioDeployGenerator

ifndef DESTDIR
	DESTDIR = $(RPM_BUILD_ROOT)
endif
 

all: $(TARGET)
	make -e $(TARGET)

$(TARGET): $(OBJECTS)
	$(CXX) -g -o $@ $(OBJECTS) $(LIBS)


.cpp.o:
	$(CXX) -g -Wall -c $(CPPFLAGS) $<
	
clean:
	-rm -f $(OBJECTS) $(TARGET)

	
install: $(TARGET)
	mkdir -p ${DESTDIR}/${ST_TOOL_PATH}/bin
	cp $(TARGET) ${DESTDIR}/${ST_TOOL_PATH}/bin
