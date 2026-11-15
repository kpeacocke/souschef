#!/usr/bin/env bash
# Deliberately incomplete control flow and quote; never executed by tests.
set -euo pipefail
if [[ -f /etc/example-app.conf ]]; then
  printf '%s\n' "configuration exists
  systemctl reload nginx
