#!/usr/bin/env python2.7
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from argparse import ArgumentParser
import fcntl
import os
import re
import struct
import subprocess
import sys
import termios

from foxxy.os import find_executable

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

parse_line = re.compile('^([A-Z])/([^\(]+)\(([^\)]+)\): (.*)$').match

def get_term_dim():
    '''Get the width and height of the terminal.'''
    data = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, '\0\0\0\0')
    # The dimensions are returned (height, width), so we swap them.
    return struct.unpack('hh', data)[::-1]

class Logdog(object):
    default_adb_path = find_executable('adb', no_raise=True)

    def __init__(self, log_file):
        self._log_file = log_file

    def __iter__(self):
        def log_iter():
            while True:
                line = self._log_file.readline()
                if not line:
                    break
                yield line
        return log_iter()

    def _format_line(self, line):
        match = parse_line(line)
        if not match:
            return line
        tagtype, tag, owner, message = match.groups()

    @classmethod
    def from_adb(cls, adb_path=None):
        if adb_path is None:
            adb_path = cls.default_adb_path
        logcat = subprocess.Popen((adb_path, 'logcat'), stdout=subprocess.PIPE)
        return cls(logcat.stdout)

    @classmethod
    def from_stdin(cls):
        return cls(sys.stdin)

def format(fg=None, bg=None, bright=False, bold=False, dim=False, reset=False):
    # manually derived from http://en.wikipedia.org/wiki/ANSI_escape_code#Codes
    codes = []
    if reset:
        codes.append('0')
    else:
        if fg is not None:
            codes.append('3%d' % (fg))
        if bg is not None:
            if bright:
                codes.append('10%d' % (bg))
            else:
                codes.append('4%d' % (bg))
        if bold:
            codes.append('1')
        elif dim:
            codes.append('2')
        else:
            codes.append('22')
    return '\033[%sm' % ';'.join(codes)

def indent_wrap(message, indent=0, width=80):
    wrap_area = width - indent
    parts = []
    current = 0
    while current < len(message):
        next = min(current + wrap_area, len(message))
        parts.append(message[current:next])
        if next < len(message):
            parts.append('\n%s' % (' ' * indent))
        current = next
    return ''.join(parts)

LAST_USED = [RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE]
KNOWN_TAGS = {}

def allocate_color(tag):
    global LAST_USED, KNOWN_TAGS
    if tag not in KNOWN_TAGS:
        KNOWN_TAGS[tag] = LAST_USED[0]
    color = KNOWN_TAGS[tag]
    LAST_USED.remove(color)
    LAST_USED.append(color)
    return color

allocate_color('dalvikvm')
allocate_color('Process')
allocate_color('ActivityManager')
allocate_color('ActivityThread')

TAGTYPE_WIDTH = 3
TAG_WIDTH = 10
PROCESS_WIDTH = -1 # 8 or -1
HEADER_SIZE = TAGTYPE_WIDTH + 1 + TAG_WIDTH + 1 + PROCESS_WIDTH + 1

TAGTYPES = {
    'V': '%s%s%s ' % (format(fg=WHITE, bg=BLACK), 'V'.center(TAGTYPE_WIDTH), format(reset=True)),
    'D': '%s%s%s ' % (format(fg=BLACK, bg=BLUE), 'D'.center(TAGTYPE_WIDTH), format(reset=True)),
    'I': '%s%s%s ' % (format(fg=BLACK, bg=GREEN), 'I'.center(TAGTYPE_WIDTH), format(reset=True)),
    'W': '%s%s%s ' % (format(fg=BLACK, bg=YELLOW), 'W'.center(TAGTYPE_WIDTH), format(reset=True)),
    'E': '%s%s%s ' % (format(fg=BLACK, bg=RED), 'E'.center(TAGTYPE_WIDTH), format(reset=True)),
}

def do(logdog):
    for line in logdog:
        match = parse_line(line)
        if not match:
            continue

        tagtype, tag, owner, message = match.groups()
        linebuf = []

        # center process info
        if PROCESS_WIDTH > 0:
            owner = owner.strip().center(PROCESS_WIDTH)
            linebuf.append('%s%s%s ' % (format(fg=BLACK, bg=BLACK, bright=True),
                                               owner, format(reset=True)))

        # right-align tag title and allocate color if needed
        tag = tag.strip()
        color = allocate_color(tag)
        tag = tag[-TAG_WIDTH:].rjust(TAG_WIDTH)
        linebuf.append('%s%s %s' % (format(fg=color, dim=False), tag,
                                    format(reset=True)))

        # write out tagtype colored edge
        if not tagtype in TAGTYPES:
            break
        linebuf.append(TAGTYPES[tagtype])

        # insert line wrapping as needed
        message = indent_wrap(message, HEADER_SIZE, get_term_dim()[0])
        linebuf.append(message)

        print(''.join(linebuf))

def build_argument_parser():
    argument_parser = ArgumentParser()
    add = argument_parser.add_argument
    add('-s', '--stdin', action='store_true')
    return argument_parser

def main(argv=None):
    if argv is None:
        argv = sys.argv
    args = build_argument_parser().parse_args(args=argv[1:])

    while True:
        if args.stdin:
            logdog = Logdog.from_stdin()
        else:
            logdog = Logdog.from_adb()

        try:
            do(logdog)
        except KeyboardInterrupt:
            break

if __name__ == '__main__':
    exit(main())

