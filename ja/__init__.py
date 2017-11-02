#!/usr/bin/env python3

import subprocess
import os
import enum
import time
import shlex

import click
from ja import frontend
from ja.native import NinjaNativeFrontend

VERSION = '1.0.1'

def run(cmd, silent=False, may_fail=False):
    if silent:
        cmd += " &>/dev/null"
    print('\x1b[1;34m$ ' + cmd + '\x1b[0m')
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError as err:
        if not may_fail:
            raise err

class BuildSystem(enum.Enum):
    MESON = 0
    CMAKE = 1

@click.command(help="""Frontend for ninja focusing on a faster edit, compile, debug cycle.\n
If TARGETS are unspecified, builds the 'default' target (see manual).""")
@click.version_option(version=VERSION)
@click.option('-j', metavar='N', required=False, help='Run N jobs in parallel.', type=int)
@click.option('-t', metavar='TOOL', required=False,
              help='Run a subtool (use -t list to list subtools).')
@click.option('-C', metavar='DIR', required=False,
              help='Change to DIR before doing anything else.')
@click.argument('targets', nargs=-1)
def main(j, t, c, targets):
    ninja_help = ''
    try:
        ninja_help = subprocess.check_output(['ninja', '--help'], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as err:
        ninja_help = err.stdout
    except FileNotFoundError:
        click.secho("Couldn't find ninja command. Please make sure it's on your PATH.", fg='red')
        exit(1)
    if b'--frontend' not in ninja_help:
        click.secho("Your version of ninja doesn't support external frontends.\nSee "
                    "https://github.com/ninja-build/ninja/pull/1210 for more information.",
                    fg='red')
        exit(1)

    if c:
        try:
            os.chdir(c)
        except FileNotFoundError as err:
            click.secho(str(err), fg='red', bold=True)
            exit(1)

    try:
        build_system = None
        build_dir = 'build'
        if not os.path.exists('build.ninja'):
            old_cwd = os.getcwd()
            if os.listdir('.') == []: # Current directory empty?
                build_dir = '.'
                os.chdir('..')

            if os.path.exists('meson.build'):
                build_system = BuildSystem.MESON
            elif os.path.exists('CMakeLists.txt'):
                build_system = BuildSystem.CMAKE

            os.chdir(old_cwd)

        if build_system != None:
            if os.path.isfile(build_dir):
                click.secho("Can't create directory '{}' because a file with that name exists."
                            .format(build_dir), fg='red')
                exit(1)

            if build_dir != '.':
                if not os.path.exists(build_dir):
                    run('mkdir ' + build_dir)
                if os.path.exists(build_dir):
                    run('cd ' + build_dir)
                    os.chdir(build_dir)

            if not os.path.exists('build.ninja'):
                if build_system == BuildSystem.MESON:
                    run('meson ..')
                elif build_system == BuildSystem.CMAKE:
                    run('cmake -GNinja ..')

        if t:
            os.execl('/bin/sh', 'sh', '-c', 'ninja -t ' + t)
        if j:
            targets += ('-j{}'.format(j),)

        native = NinjaNativeFrontend()

        # Only allow one running instance per build directory:
        fifo = 'ja.lock'
        if os.path.exists(fifo):
            print("\x1b[1;36mwaiting for file lock on build directory\x1b[0m")
            while os.path.exists(fifo):
                time.sleep(1)

        os.mkfifo(fifo)
        subprocess.Popen(['ninja --frontend="cat <&3 >{0}; rm {0}" {1}'.format(
            fifo, ' '.join([shlex.quote(x) for x in targets])
        )], shell=True)

        try:
            for msg in frontend.Frontend(open(fifo, 'rb')):
                if native.handle(msg):
                    exit(1)
        except KeyboardInterrupt:
            native.printer.print_on_new_line('\x1b[1;31mbuild stopped: interrupted by user.\x1b[0m\n')
            os.remove(fifo)
            exit(130)

    except subprocess.CalledProcessError as err:
        exit(err.returncode)
