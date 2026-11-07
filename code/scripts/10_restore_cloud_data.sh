#!/usr/bin/env bash
# Restore the original training corpora after cloning; preserve existing local files.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${PROJECT_ROOT}"
sha256sum --check cloud-data/SHA256SUMS
# --skip-old-files makes repeated execution safe for existing local datasets.
tar --extract --gzip --file cloud-data/training-data.tar.gz --skip-old-files
printf '%s\n' '训练语料已恢复；已有文件保持原样。'
