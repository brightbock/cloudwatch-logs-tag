#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

PIP="$(which pip3)" || PIP="pip"

TMPDIR="$(mktemp -d -t lambda_package_layer.XXXXXXXXXX)" || exit 1

HERE="$(dirname "$( realpath "$0" )" )"

$PIP install --target "${TMPDIR}/python" -r "${HERE}/requirements.txt"

cd "${TMPDIR}"

rm -f "${HERE}/package.zip"

zip -r "${HERE}/package.zip" .

cd /

rm -rf "${TMPDIR}"
