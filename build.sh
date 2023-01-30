#!/bin/bash
set -eo pipefail

PACKAGE_NAME=$(awk -F' = ' '{gsub(/"/,"");if($1=="name")print $2}' pyproject.toml)
VERSION=$(poetry version -s)

ZIP_PATH="$PWD/dist/$PACKAGE_NAME-$VERSION.zip"

poetry bundle venv build --clear --without=dev
rm -rf build/lib/python3.*/site-packages/*.dist-info build/lib/python3.*/site-packages/_virtualenv.*
find build -type d -name __pycache__ -exec rm -rf {} \+

mkdir -p dist/
rm -f "$ZIP_PATH"

cd build/lib/python3.*/site-packages/
zip -vr9 "$ZIP_PATH" .
