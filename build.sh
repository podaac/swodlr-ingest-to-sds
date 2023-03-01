#!/bin/bash
set -eo pipefail

PACKAGE_NAME=$(awk -F' = ' '{gsub(/"/,"");if($1=="name")print $2}' pyproject.toml)
VERSION=$(poetry version -s)

ROOT_PATH="$PWD"
ZIP_PATH="$ROOT_PATH/dist/$PACKAGE_NAME-$VERSION.zip"

poetry bundle venv build --clear --without=dev

cd build/lib/python3.*/site-packages
touch podaac/__init__.py
rm -rf *.dist-info _virtualenv.*
find . -type d -name __pycache__ -exec rm -rf {} \+

mkdir -p "$ROOT_PATH/dist/"
rm -f "$ZIP_PATH"
zip -vr9 "$ZIP_PATH" .
