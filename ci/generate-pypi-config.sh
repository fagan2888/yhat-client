#!/bin/bash

echo "
[distutils]
index-servers =
    pypi

[pypi]
username=${PYPI_USERNAME}
password=${PYPI_PASSWORD}
"
