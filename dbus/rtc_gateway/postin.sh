#!/bin/sh

test -n "$FIRST_ARG" || FIRST_ARG=$1
[ -d /var/lib/systemd/migrated ] || mkdir -p /var/lib/systemd/migrated || :
for service in rtc_gateway.service ; do
    sysv_service=${service%.*}
    if [ ! -e "/var/lib/systemd/migrated/$sysv_service" ]; then
	services_to_migrate="$services_to_migrate $sysv_service"
	touch "/var/lib/systemd/migrated/$sysv_service" || :
    fi
done
	
/usr/bin/systemctl daemon-reload >/dev/null 2>&1 || :
if [ -n "$services_to_migrate" ]; then
    /usr/sbin/systemd-sysv-convert --apply $services_to_migrate >/dev/null 2>&1 || :
elif [ $FIRST_ARG -eq 1 ]; then
    /usr/bin/systemctl preset rtc_gateway.service >/dev/null 2>&1 || :
elif [ $FIRST_ARG -gt 1 ]; then
    for service in rtc_gateway.service ; do
	if [ -e "/run/rpm-premount-update-$service-new-in-upgrade" ]; then
	    rm -f "/run/rpm-premount-update-$service-new-in-upgrade"
	    /usr/bin/systemctl preset "$service" >/dev/null 2>&1 || :
	fi
    done
fi
	
if [ -f /var/run/enable_rtc_gateway_service ]; then
    /usr/bin/systemctl --quiet enable rtc_gateway
fi

/sbin/service dbus reload
