cmake_minimum_required(VERSION 3.5)
project(st_tools)

include(GNUInstallDirs)
include(CPackComponent)

file(GLOB_RECURSE EDV_INCLUDE_FILES "*.h")
# set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -D_NET_CON_DEBUG")

# Change OFF for ON to enable debug
OPTION(DEFINE_DEBUG
  "Build the project using debugging code"
  ON)

IF(DEFINE_DEBUG)
  MESSAGE("Adding Debug flag...")
  ADD_DEFINITIONS(-D_NET_CON_DEBUG)
  SET(CMAKE_BUILD_TYPE Debug)
  MESSAGE("Build type is " ${CMAKE_BUILD_TYPE})
ENDIF(DEFINE_DEBUG)


add_library(st_tools SHARED logger.cpp netcon.cpp)
set_target_properties(st_tools PROPERTIES
  PUBLIC_HEADER "${EDV_INCLUDE_FILES}"
  VERSION 1.0
  SOVERSION 1
)
install(TARGETS st_tools
  LIBRARY
    DESTINATION "${CMAKE_INSTALL_LIBDIR}"
    COMPONENT Libraries
    NAMELINK_SKIP
  PUBLIC_HEADER
    DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
    COMPONENT Development
)
install(TARGETS st_tools
  LIBRARY
    DESTINATION "${CMAKE_INSTALL_LIBDIR}"
    COMPONENT Development
    NAMELINK_ONLY
)


