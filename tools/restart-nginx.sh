#!/usr/bin/env bash

SOURCES_DIR=/home/pythonsponge/deployed

rm /etc/nginx/sites-available/*
rm /etc/nginx/sites-enabled/*
cp $SOURCES_DIR/server/config/nginx/sites-available/* /etc/nginx/sites-available
cp $SOURCES_DIR/server/config/nginx/sites-available/* /etc/nginx/sites-enabled

systemctl stop nginx
systemctl start nginx
