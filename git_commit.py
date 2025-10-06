#!/usr/bin/env python3
import subprocess
import os

os.chdir('/Users/ahmed/Telegram Axis')

# Stage changes
subprocess.run(['git', 'add', '-A'], check=True)

# Commit
subprocess.run(['git', 'commit', '-m', 'Add bowling and darts prediction games'], check=True)

# Push
subprocess.run(['git', 'push', 'origin', 'main'], check=True)

print("✅ Changes committed and pushed successfully!")
