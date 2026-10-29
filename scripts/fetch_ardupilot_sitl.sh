#!/usr/bin/env bash
set -euo pipefail
# Copyright (c) 2026 Arpan Bom. All rights reserved.
destination="${1:-/tmp/ardupilot-sitl}"
mkdir -p "$destination"
base='https://firmware.ardupilot.org/Copter/stable/SITL_x86_64_linux_gnu'
fetch() {
  curl --fail --location --retry 3 --retry-all-errors --connect-timeout 20 --max-time 180 "$1" --output "$2"
}
fetch "$base/arducopter" "$destination/arducopter"
fetch "$base/git-version.txt" "$destination/git-version.txt"
revision="$(sed -nE 's/.*([0-9a-fA-F]{40}).*/\1/p' "$destination/git-version.txt" | head -1)"
if [[ ! "$revision" =~ ^[0-9a-fA-F]{40}$ ]]; then
  echo 'No full commit hash found in git-version.txt' >&2
  exit 1
fi
fetch "https://raw.githubusercontent.com/ArduPilot/ardupilot/$revision/Tools/autotest/default_params/copter.parm" "$destination/copter.parm"
chmod +x "$destination/arducopter"
cat "$destination/git-version.txt"
sha256sum "$destination/arducopter" "$destination/git-version.txt" "$destination/copter.parm"
