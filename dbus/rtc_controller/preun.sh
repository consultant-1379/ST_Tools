#!/bin/sh

test -n "$FIRST_ARG" || FIRST_ARG=$1
if [ $FIRST_ARG -eq 0 ]; then
    # Package removal, not upgrade
    /usr/bin/systemctl --no-reload disable rtc_controller.service > /dev/null 2>&1 || :
    /usr/bin/systemctl stop rtc_controller.service > /dev/null 2>&1 || :
fi
