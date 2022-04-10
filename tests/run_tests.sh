#!/bin/sh

cp ../src/unifi_tracker/unifi_tracker.py .

python test_diff.py
python test_property_setters.py