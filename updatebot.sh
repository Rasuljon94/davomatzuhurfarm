#!/bin/bash
cd ~/davomatzuhurfarm/
git pull origin master
source ~/davomatenv/bin/activate
pkill -f main.py
screen -S davomatbot -dm python main.py
