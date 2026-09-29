#!/usr/bin/env bash

set -euo pipefail

SRC_ROOT="src"
TEST_ROOT="tests/legacy"

find "$SRC_ROOT" -type f \( -name 'test_*.py' -o -name 'conftest.py' \) -print0 |
while IFS= read -r -d '' src_file; do
    # Remove the src/ prefix to get the relative path.
    relative_path="${src_file#"$SRC_ROOT"/}"

    # Remove any "tests/" directory from the target path.
    relative_path="${relative_path//tests\//}"

    # Construct the destination path under test/.
    dest_file="$TEST_ROOT/$relative_path"
    dest_dir="$(dirname "$dest_file")"

    # Don't overwrite an existing file.
    if [[ -e "$dest_file" ]]; then
        echo "ERROR: destination already exists: $dest_file" >&2
        continue
#        exit 1
    fi

    mkdir -p "$dest_dir"

    echo "git mv: $src_file -> $dest_file"
    git mv "$src_file" "$dest_file"
done
