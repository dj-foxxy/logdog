#!/usr/bin/env python3
from argparse import ArgumentParser
from xml.dom.minidom import parse
import os
import subprocess
import sys

ANDROID_MANIFEST = 'AndroidManifest.xml'
ACTION_MAIN = 'android.intent.action.MAIN'
CATEGORY_LAUNCHER = 'android.intent.category.LAUNCHER'

def find_android_manifest():
    dir = os.path.abspath(os.getcwd())
    while True:
        for item in os.listdir(dir):
            if item == ANDROID_MANIFEST:
                manifest_path = os.path.realpath(
                        os.path.join(dir, ANDROID_MANIFEST))
                if os.path.isfile(manifest_path):
                    return manifest_path
        if dir == '/':
            raise ValueError('Cannot find Android manifest')
        dir = os.path.split(dir)[0]

def extract_main_activity(manifest_path):
    manifest_dom = parse(manifest_path)
    manifest = manifest_dom.getElementsByTagName('manifest')
    if len(manifest) != 1:
        raise ValueError('More than one manifest element')
    manifest = manifest[0]

    package = manifest.getAttribute('package')
    if not package:
        raise ValueError('manifest element has not attribute package')

    activity_name = None

    for activity in manifest.getElementsByTagName('activity'):
        for intent_filter in activity.getElementsByTagName('intent-filter'):
            action = intent_filter.getElementsByTagName('action')
            if len(action) != 1:
                continue
            action = action[0].getAttribute('android:name')
            if action != ACTION_MAIN:
                continue
            category = intent_filter.getElementsByTagName('category')
            if len(category) != 1:
                continue
            category = category[0].getAttribute('android:name')
            if category != CATEGORY_LAUNCHER:
                continue
            activity_name = activity.getAttribute('android:name')
            break
        if activity_name is not None:
            break

    if activity_name is None:
        raise ValueError('mainifest does not contains a main activity.')

    return  package, activity_name

def launch_activity(package, activity):
    join = '' if activity.startswith('.') else '.'
    args = ('adb', 'shell', 'am', 'start', '-a', ACTION_MAIN, '-n',
            '%s/%s%s%s' % (package, package, join, activity))
    subprocess.check_call(args)

def main(args=None):
    if args is None:
        args = sys.argv
    ap = ArgumentParser()
    args = ap.parse_args(args=args[1:])
    manifest_path = find_android_manifest()
    if manifest_path is None:
        return 1
    package, activity = extract_main_activity(manifest_path)
    launch_activity(package, activity)
    return 0

if __name__ == '__main__':
    exit(main())

