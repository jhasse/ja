#!/usr/bin/env python

from __future__ import print_function

import collections
import ctypes
import os
import re
import struct
import sys
import datetime
from zlib import adler32
import humanize
import click
from ja import frontend

class SlidingRateInfo(object):
    def __init__(self, n=32):
        self.rate = -1
        self.last_update = -1
        self.times = collections.deque(maxlen=n)

    def update_rate(self, update_hint, time_millis):
        if update_hint == self.last_update:
            return

        self.last_update = update_hint

        if len(self.times) == self.times.maxlen:
            self.times.popleft()
        self.times.append(time_millis)
        if self.times[-1] != self.times[0]:
            self.rate = len(self.times) / ((self.times[-1] - self.times[0]) / 1e3)

strip_ansi_re = re.compile(r'\x1B\[[^a-zA-Z]*[a-zA-Z]')
def strip_ansi_escape_codes(output):
    return strip_ansi_re.sub('', output)

class NinjaNativeFrontend:
    def __init__(self):
        self.total_edges = 0
        self.running_edges = 0
        self.started_edges = 0
        self.finished_edges = 0
        self.running = collections.OrderedDict()
        self.last_started_edge = None

        self.time_millis = 0

        self.progress_status_format = os.getenv('NINJA_STATUS', ' ETA: %a ')
        self.current_rate = SlidingRateInfo()
        self.console_locked = False

        self.printer = LinePrinter()
        self.verbose = False

    def handle(self, msg):
        handled = False
        edge_failed = False
        if msg.HasField("total_edges"):
            handled = True
            self.total_edges = msg.total_edges.total_edges

        if msg.HasField("build_started"):
            handled = True
            self.verbose = msg.build_started.verbose
            self.current_rate = SlidingRateInfo(msg.build_started.parallelism)
            self.running_edges = 0
            self.started_edges = 0
            self.finished_edges = 0
            self.running = {}

        if msg.HasField("build_finished"):
            handled = True
            self.printer.set_console_locked(False)

            hours = int(self.time_millis / (3600 * 1e3))
            minutes = int((self.time_millis % (3600 * 1e3)) / (60 * 1e3))
            seconds = (self.time_millis % (60 * 1e3)) / 1e3
            if hours > 0:
                time_passed = '{}h{}m{}s'.format(hours, minutes, int(seconds))
            elif minutes > 0:
                time_passed = '{}m{}s'.format(minutes, int(seconds))
            else:
                time_passed = '{:.3f}s'.format(seconds)
            self.printer.print_line("\x1b[1;32mfinished {} job{} in {}.\x1b[0m".format(
                self.total_edges,
                's' if self.total_edges != 1 else '',
                time_passed
            ), LinePrinter.LINE_FULL)

        if msg.HasField("edge_started"):
            handled = True
            self.started_edges += 1
            self.running_edges += 1
            self.running[msg.edge_started.id] = msg.edge_started
            self.last_started_edge = msg.edge_started
            self.time_millis = msg.edge_started.start_time
            if msg.edge_started.console or self.printer.smart_terminal:
                self.print_status(msg.edge_started)
            if msg.edge_started.console:
                self.printer.set_console_locked(True)

        if msg.HasField("edge_finished"):
            handled = True
            self.finished_edges += 1
            self.time_millis = msg.edge_finished.end_time

            edge_started = self.running[msg.edge_finished.id]

            if edge_started.console:
                self.printer.set_console_locked(False)

            if not edge_started.console:
                self.print_status(edge_started)

            self.running_edges -= 1
            del self.running[msg.edge_finished.id]

            template = '\x1b[1;34m{}\x1b[0m' if msg.edge_finished.output != '' else None
            if msg.edge_finished.status != 0:
                template = '\x1b[1;31m{{}}\x1b[0;31m failed with exit code {}.\x1b[0m'.format(
                    msg.edge_finished.status)
                edge_failed = True

            if template:
                self.printer.print_line('', LinePrinter.LINE_ELIDE)
                if self.verbose or msg.edge_finished.output == '':
                    # Print the command that is spewing before printing its output.
                    self.printer.print_line(template.format(edge_started.command),
                                            LinePrinter.LINE_FULL)

                # ninja sets stdout and stderr of subprocesses to a pipe, to be able to
                # check if the output is empty. Some compilers, e.g. clang, check
                # isatty(stderr) to decide if they should print colored output.
                # To make it possible to use colored output with ninja, subprocesses should
                # be run with a flag that forces them to always print color escape codes.
                # To make sure these escape codes don't show up in a file if ninja's output
                # is piped to a file, ninja strips ansi escape codes again if it's not
                # writing to a |smart_terminal_|.
                # (Launching subprocesses in pseudo ttys doesn't work because there are
                # only a few hundred available on some systems, and ninja can launch
                # thousands of parallel compile commands.)
                # TODO: There should be a flag to disable escape code stripping.
                if not self.printer.smart_terminal:
                    msg.edge_finished.output = strip_ansi_escape_codes(msg.edge_finished.output)

                # rstrp('\n') because the build output contains a trailing newline most of the time
                # which isn't needed:
                self.printer.print_line(msg.edge_finished.output.rstrip('\n'), LinePrinter.LINE_FULL)

            # We wouldn't want to print the status for an edge that has finished, therefore reprint
            # the status line with an edge that is running:
            if not edge_failed and self.running:
                running_edge = list(self.running.values())[0]
                if running_edge.console or self.printer.smart_terminal:
                    self.print_status(running_edge)
                if running_edge.console:
                    self.printer.set_console_locked(True)

        if msg.HasField("message"):
            handled = True
            # TODO(colincross): get the enum values from proto
            if msg.message.level == 0:
                prefix = ''
                color = 'green'
            elif msg.message.level == 1:
                prefix = 'warning: '
                color = 'magenta'
            elif msg.message.level == 2:
                prefix = 'error: '
                color = 'red'
                edge_failed = True
            self.printer.print_line(
                click.style(prefix + msg.message.message, fg=color, bold=True),
                LinePrinter.LINE_FULL
            )

        if not handled:
            pass

        return edge_failed


    def format_progress_status(self, fmt):
        out = ''
        fmt_iter = iter(fmt)
        for c in fmt_iter:
            if c == '%':
                c = next(fmt_iter)
                if c == '%':
                    out += c
                elif c == 's':
                    out += str(self.started_edges)
                elif c == 't':
                    out += str(self.total_edges)
                elif c == 'r':
                    out += str(self.running_edges)
                elif c == 'u':
                    out += str(self.total_edges - self.started_edges)
                elif c == 'f':
                    out += str(self.finished_edges)
                elif c == 'o':
                    if self.time_millis > 0:
                        rate = self.finished_edges / (self.time_millis / 1e3)
                        out += '{:.1f}'.format(rate)
                    else:
                        out += '?'
                elif c == 'c':
                    self.current_rate.update_rate(self.finished_edges, self.time_millis)
                    if self.current_rate.rate == -1:
                        out += '?'
                    else:
                        out += '{:.1f}'.format(self.current_rate.rate)
                elif c == 'p':
                    out += '{:3d}%'.format((100 * self.finished_edges) // self.total_edges)
                elif c == 'e':
                    out += '{:.3f}'.format(self.time_millis / 1e3)
                elif c == 'a':
                    if self.finished_edges > 0:
                        out += humanize.naturaldelta(
                            datetime.timedelta(seconds=self.time_millis / self.finished_edges * \
                            (self.total_edges - self.finished_edges) / 1e3)
                        )
                    else:
                        out += '?'
                else:
                    raise Exception('unknown placeholder '' + c +'' in $NINJA_STATUS')
            else:
                out += c
        out = '{:17}'.format(out)
        bar_end = round((len(out) * self.finished_edges) / self.total_edges)
        if self.total_edges == 1:
            return '' # No need for a progress bar if there's only one edge
        return '\x1b[0;36m▕\x1b[1;37;46m' + out[:bar_end] + '\x1b[0m\x1b[1m' + out[bar_end:] + \
               '\x1b[0;36m▏\x1b[0m'

    def print_status(self, edge_started):
        to_print = edge_started.desc
        words = to_print.split(' ')
        try:
            # We hash the first word and the first character of the third word:
            hash_number = adler32((words[0] + words[2][:1]).encode()) % 10
        except IndexError:
            hash_number = 0
        to_print = "\x1b[{};3{}m{}\x1b[0m".format(
            1 if hash_number > 4 else 0, hash_number % 5 + 2, to_print,
        )
        if self.verbose or to_print == '':
            to_print = edge_started.command

        to_print = self.format_progress_status(self.progress_status_format) + to_print

        self.printer.print_line(to_print, LinePrinter.LINE_FULL if self.verbose else LinePrinter.LINE_ELIDE)


ansi_escape = re.compile(r'\x1b[^m]*m')
def elide_middle(status, width):
    margin = 1 # Space for "…".
    status_stripped = ansi_escape.sub('', status)
    if len(status_stripped) + margin > width:
        elide_size = (width - margin) // 2

        escapes = []
        added_len = 0 # total number of characters
        for m in ansi_escape.finditer(status):
            escapes += [(m.start() - added_len, m.group())]
            added_len += len(m.group())

        status = status_stripped[0:elide_size] + "…" + status_stripped[-elide_size:]

        added_len = 0
        # We need to put all ANSI escape codes back in:
        for escape in escapes:
            pos = escape[0]
            if pos > elide_size:
                pos -= len(status_stripped) - width
                if pos < width - elide_size:
                    pos = width - elide_size
            pos += added_len
            status = status[:pos] + escape[1] + status[pos:]
            added_len += len(escape[1])
    return status

class LinePrinter(object):
    LINE_FULL = 1
    LINE_ELIDE = 2

    def __init__(self):
        # Whether we can do fancy terminal control codes.
        self.smart_terminal = False

        # Whether the caret is at the beginning of a blank line.
        self.have_blank_line = True

        # Whether console is locked.
        self.console_locked = False

        # Buffered current line while console is locked.
        self.line_buffer = ''

        # Buffered line type while console is locked.
        self.line_type = self.LINE_FULL

        # Buffered console output while console is locked.
        self.output_buffer = ''

        if os.name == 'windows':
            STD_OUTPUT_HANDLE = -11
            self.console = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            csbi = ctypes.create_string_buffer(22)
            self.smart_terminal = ctypes.windll.kernel32.GetConsoleScreenBufferInfo(self.console, csbi)
        else:
            term = os.getenv('TERM')
            self.smart_terminal = os.isatty(1) and term != '' and term != 'dumb'

    def print_line(self, to_print, line_type):
        if self.console_locked:
            self.line_buffer = to_print
            self.line_type = line_type

        if self.smart_terminal:
            sys.stdout.write('\r') # Print over previous line, if any.

        if self.smart_terminal and line_type == self.LINE_ELIDE:
            if os.name == 'windows':
                csbi = ctypes.create_string_buffer(22)
                ctypes.windll.kernel32.GetConsoleScreenBufferInfo(self.console, csbi)
                (cols, rows) = struct.unpack('hh', csbi.raw)
                to_print = elide_middle(to_print, cols)
                # TODO: windows support
                # We don't want to have the cursor spamming back and forth, so instead of
                # printf use WriteConsoleOutput which updates the contents of the buffer,
                # but doesn't move the cursor position.
                sys.stdout.write(to_print)
                sys.stdout.flush()
            else:
                # Limit output to width of the terminal if provided so we don't cause
                # line-wrapping.
                import fcntl, termios
                winsize = fcntl.ioctl(0, termios.TIOCGWINSZ, '\0'*4)
                (rows, cols) = struct.unpack('hh', winsize)
                to_print = elide_middle(to_print, cols)
                sys.stdout.write(to_print)
                sys.stdout.write('\x1B[K')  # Clear to end of line.
                sys.stdout.flush()

            self.have_blank_line = False
        else:
            sys.stdout.write(to_print + "\n")
            sys.stdout.flush()

    def print_or_buffer(self, to_print):
        if self.console_locked:
            self.output_buffer += to_print
        else:
            sys.stdout.write(to_print)
            sys.stdout.flush()

    def print_on_new_line(self, to_print):
        if self.console_locked or self.line_buffer != '':
            self.output_buffer += self.line_buffer + '\n'
            self.line_buffer = ""
        if not self.have_blank_line:
            self.print_or_buffer('\n')
        if to_print != '':
            self.print_or_buffer(to_print)
        self.have_blank_line = to_print == "" or to_print[0] == '\n'

    def set_console_locked(self, locked):
        if locked == self.console_locked:
            return

        if locked:
            self.print_on_new_line('\n')

        self.console_locked = locked

        if not locked:
            self.print_on_new_line(self.output_buffer)
            if self.line_buffer != '':
                self.print_line(self.line_buffer, self.line_type)
            self.output_buffer = ""
            self.line_buffer = ""

def main():
    native = NinjaNativeFrontend()
    for msg in frontend.Frontend():
        native.handle(msg)

if __name__ == '__main__':
    main()
