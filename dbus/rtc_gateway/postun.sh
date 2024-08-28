#!/bin/sh

test -n "$FIRST_ARG" || FIRST_ARG=$1
if [ $FIRST_ARG -ge 1 ]; then
    # Package upgrade, not uninstall
    if test "$YAST_IS_RUNNING" != "instsys" -a "$DISABLE_RESTART_ON_UPDATE" != yes ; then
	/usr/bin/systemctl try-restart rtc_gateway.service >/dev/null 2>&1 || :
    fi 
else # package uninstall
    for service in rtc_gateway.service ; do
	sysv_service=${service%.*}
	rm -f "/var/lib/systemd/migrated/$sysv_service" 2> /dev/null || :
    done
    /usr/bin/systemctl daemon-reload >/dev/null 2>&1 || :
fi

/sbin/service dbus reload