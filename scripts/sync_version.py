#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version Sync Script
Reads version from version.py and updates web/package.json.
"""
import os
import re
import json
import sys

def sync_version():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    version_file = os.path.join(root_dir, 'version.py')
    package_file = os.path.join(root_dir, 'web', 'package.json')

    if not os.path.exists(version_file):
        print(f"Error: {version_file} not found.")
        return False

    # 1. Read version from version.py
    with open(version_file, 'r', encoding='utf-8') as f:
        content = f.read()
        match = re.search(r'__backend_version__\s*=\s*["\']([^"\']+)["\']', content)
        if not match:
            print("Error: Could not find __backend_version__ in version.py")
            return False
        version = match.group(1)

    print(f"Syncing version: {version}")

    # 2. Update web/package.json
    if os.path.exists(package_file):
        with open(package_file, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            if data.get('version') != version:
                data['version'] = version
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
                print(f"Updated {package_file} to v{version}")
            else:
                print(f"{package_file} is already up to date.")
    else:
        print(f"Skip: {package_file} not found.")

    return True

if __name__ == "__main__":
    if sync_version():
        sys.exit(0)
    else:
        sys.exit(1)
