#!/bin/sh

if [ "$1" != "only-seedbot" ]; then
    echo "Running DB Migrations"
    aerich upgrade || exit 1
    echo "DB Migrations successful"
fi

if [ "$1" = "only-migrations" ]; then
    exit 0
fi

echo "Running seedbot"
exec seedbot
