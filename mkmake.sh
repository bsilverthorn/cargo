#!/bin/sh

# be verbose
set -v

# create the relevant directories
mkdir build
pushd build

mkdir debug
mkdir release
mkdir development

# create the debug build tree
pushd debug
cmake -DCMAKE_BUILD_TYPE=Debug ../../src
popd

# create the release build tree
pushd release
cmake -DCMAKE_BUILD_TYPE=Release ../../src
popd

# create the development build tree
pushd development
cmake -DCMAKE_BUILD_TYPE=Development ../../src
popd

# the "active" symlink
ln -s development active

# done
popd

