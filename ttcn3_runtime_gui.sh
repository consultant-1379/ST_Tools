#!/bin/sh


USAGE="usage: $0 [ [listen runtime-GUI_listen_portnumber] [reconnect runtime-GUI_reconnect_portnumber] | [connect runtime-GUI_remote_host:port] ] [runtime-GUI_xul_file]"

while [ "$#" -gt "0" ]
do
  if [ "$1" = "connect" ]
    then
      shift
      CONNECT="-connect $1"
    else
      if [ "$1" = "listen" ]
        then
          shift
          PORTNR="-listenport $1"
        else
          if [ "$1" = "reconnect" ]
            then
              shift
              RECONNECTPORT="-reconnectport $1"
            else
              XULPATH=$1
          fi
      fi
  fi
  shift
done

#echo "CONNECT: $CONNECT"
#echo "RECONNECTPORT: $RECONNECTPORT"
#echo "PORTNR:  $PORTNR"
#echo "XUL:     $XULPATH"

if [ "$PORTNR" = "-listenport " ]
  then
    echo "Using default listenPort 11420"
fi

PLATFORM_ID=`uname -s`
echo "Native unix/linux platform (${PLATFORM_ID}) detected..."

if [ "$XULPATH" != "" ]
    then
        # Getting absolute pathname of $1
        LASTDIR=`pwd`
        cd `dirname $XULPATH`
        XULFILE=`pwd`"/"`basename $XULPATH`
        XULFILE="file://${XULFILE}"
        cd ${LASTDIR}
fi

exec java -jar ${ST_TOOL_PATH}/bin/TitanRuntimeGUI.jar ${PORTNR} ${RECONNECTPORT} ${CONNECT} ${XULFILE} &


