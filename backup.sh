#!/bin/bash

if [ "$1" == "dump" ] ; then
    mongodump -v --host $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q --filter "name=rssnews_db_1")):27017 --db 'feed' --out=./backup/
    mongodump -v --host $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q --filter "name=rssnews_db_1")):27017 --db 'saved' --out=./backup/
fi

if [ "$1" == "restore" ] ; then
    mongorestore --drop -v --host $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q --filter "name=rssnews_db_1")):27017 --db 'feed' ./backup/feed/
    mongorestore --drop -v --host $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker ps -q --filter "name=rssnews_db_1")):27017 --db 'saved' ./backup/feed/
fi
