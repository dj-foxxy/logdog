#!/usr/bin/env python2
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from argparse import ArgumentParser
import subprocess
import sys

from foxxy.os import find_executable

def logcat(adb_path=None):
    if adb_path is None:
        adb_path = find_executable('adb')
    logcat = subprocess.Popen((adb_path, 'logcat'),
                              stdout=subprocess.PIPE).stdout.readline
    while True:
        yield logcat()

def build_argument_parser():
    argument_parser = ArgumentParser()
    return argument_parser

def main(argv=None):
    if argv is None:
        argv = sys.argv
    argument_parser = build_argument_parser()
    arguments = argument_parser.parse_args(args=argv[1:])

    for line in logcat():
        print(line)
    return 0

if __name__ == '__main__':
    exit(main())

