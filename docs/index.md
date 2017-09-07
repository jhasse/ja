# Differences between *ja* and *ninja*

## Immediately exists after the first failure

*ja* runs *ninja* in the background. When the first failure occurs (e.g. a file failed to compile) it will display it's output and exit. When a file has a syntax error, you can therefore immediately reuse the command prompt to edit the file without having to wait for other jobs to finish (they will run in the background though).

## Makes sure you won't run it twice

*ja* locks the build directory so that you won't be able to accidentely compile twice, e.g. in different terminals.

## Colored output

*ja* will display a jobs description with colors, similar to CMake's `make` output. That way you can easily distinguish compiling from linking, etc. When a job fails this is indicated by coloring the jobs command line in bold red.

## Progress bar and ETA

A nice progress bar makes compiling fun! Also *ja* will display an approximation of the time left. Since *ja* runs independently from *ninja*, this output will be updated in real-time, even if the jobs itself take a long time to finish.

## Automatically configures CMake or Meson projects

When running *ja* from a directory without out a `ninja.build` file, but with a `CMakeLists.txt` or `meson.build` file, it will create a `build/` directory for you, run `cmake -GNinja ..` or `meson ..` inside that directory and start building after that.
