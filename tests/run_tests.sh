#!/bin/sh

cp ../src/unifi_tracker/unifi_tracker.py .

python3 test_diff.py
python3 test_diff_by_ap.py
python3 test_property_setters.py
