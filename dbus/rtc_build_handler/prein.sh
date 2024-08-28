#!/bin/sh

test -n "$FIRST_ARG" || FIRST_ARG=$1

# disable migration if initial install under systemd
[ -d /var/lib/systemd/migrated ] || mkdir -p /var/lib/systemd/migrated || :
if [ $FIRST_ARG -eq 1 ]; then
    for service in rtc_build_handler.service ; do
	sysv_service=${service%.*}
	touch "/var/lib/systemd/migrated/$sysv_service" || :
    done
else
    if [ $FIRST_ARG -gt 1 ]; then
	for service in rtc_build_handler.service ; do
	    if [ ! -e "/usr/lib/systemd/system/$service" ]; then
		touch "/run/rpm-premount-update-$service-new-in-upgrade"
	    fi
	done
    fi
    for service in rtc_build_handler.service ; do
	sysv_service=${service%.*}
	if [ ! -e "/var/lib/systemd/migrated/$sysv_service" ]; then
	    services_to_migrate="$services_to_migrate $sysv_service"
	fi
    done
    if [ -n "$services_to_migrate" ]; then
	/usr/sbin/systemd-sysv-convert --save $services_to_migrate >/dev/null 2>&1 || :
    fi
fi
