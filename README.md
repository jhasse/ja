# Differences between *ja* and *ninja*

## Immediately exists after the first failure

*ja* runs *ninja* in the background. When the first failure occurs (e.g. a file failed to compile)
it will display it's output and exit. When a file has a syntax error, you can therefore immediately
reuse the command prompt to edit the file without having to wait for other jobs to finish (they will
run in the background though).

## Makes sure you won't run it twice

*ja* locks the build directory so that you won't be able to accidentely compile twice, e.g. in
different terminals.

## Colored output

*ja* will display a jobs description with colors, similar to CMake's `make` output. That way you can
easily distinguish compiling from linking, etc.

## Progress bar and ETA

A nice progress bar makes compiling fun! Also *ja* will display an approximation of the time left.
But when your build has failed *ja* won't display any unneeded information as your compiler messages
include everything that's needed anyway.

## Automatically configures CMake or Meson projects

When running *ja* from a directory without out a `ninja.build` file, but with a `CMakeLists.txt` or
`meson.build` file, it will create a `build/` directory for you, run `cmake -GNinja ..` or
`meson ..` inside that directory and start building after that.

## See when a job gets stuck

*ninja* status output shows you the command which was started last. When a previous command gets
stuck, you won't be able to identify it though (see
[ninja bug #1158](https://github.com/ninja-build/ninja/issues/1158))! *ja* avoids this problem by
always showing a command that is still running in its status output.

# Installation

*ja* is NOT a fork of *ninja*, it's a frontend written in Python which runs alongside. Until
https://github.com/ninja-build/ninja/pull/1210 is merged you'll need to build *ninja* from source
though:

```sh
git clone https://github.com/colincross/ninja
cd ninja
git checkout serialize
./configure.py --bootstrap
sudo install ninja /usr/local/bin
```

*ja* can be installed via Python's package manager:

```sh
sudo pip3 install ja
```
