#!/bin/bash
cd ~/davomatzuhurfarm/
git pull origin main
source ~/davomatenv/bin/activate
screen -S davomatbot -dm python main.py
