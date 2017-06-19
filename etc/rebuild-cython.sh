#!/bin/bash

if [[ "$OSTYPE" == "darwin"* ]]; then
    find -E catalyst tests -regex '.*\.(c|so)' -exec rm {} +
else
    find catalyst tests -regex '.*\.\(c\|so\)' -exec rm {} +
fi
python setup.py build_ext --inplace
