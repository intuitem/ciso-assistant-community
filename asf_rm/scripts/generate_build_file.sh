#!/bin/bash

# This script generates a version file for the current build.
# It is used by the build system to determine the version of the
# current build.

# The version file is composed of the following attributes:
#   - version: the marketing version of the build
#   - build: <branch name>.<commit hash>.<commit timestamp>
#   - development: true if the build is a development build, false otherwise
#   - commit: the commit hash of the current build
#   - timestamp: the timestamp of the current build

# The script outputs a JSON file with the above attributes.

get_version() {
    # Get the marketing version of the current build.
    # The version is stored in <project root>/asf_rm/meta.json.
    # The version is stored in the "version" attribute.

    local version=$(cat asf_rm/meta.json | jq -r '.version')
    echo $version
}

get_commit_hash() {
    git rev-parse HEAD
}

get_commit_timestamp() {
    git show -s --format=%cI HEAD
}

get_branch_name() {
    git rev-parse --abbrev-ref HEAD
}

get_build() {
    echo "$(get_branch_name).$(get_commit_hash).$(get_commit_timestamp)"
}

main() {
    local version=$(get_version)
    local build=$(get_build)

    echo "{
        \"version\": \"$version\",
        \"build\": \"$build\"
}"
}

main "$@"