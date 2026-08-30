#!/usr/bin/env python3
"""UBI-102: the Python-side analog of ubiquex's own
provider.AcquireDescriptions (provider/acquiredescriptions.go) --
resolves a provider's own pinned, tagged description-corpus release
(descriptions-<provider>-v<version>, published from this repo) to a
local, verified, cached directory containing <provider>.json. Same
real protocol, deliberately reimplemented rather than shared (no
cross-language import path exists between this repo and ubiquex's own
Go module): download the release's two real assets (snapshot.tar.gz,
SHA256SUMS) from the GitHub API, verify the archive's own SHA-256
against the checksums file, extract, cache by version so a repeat
resolve costs zero network calls.

Usage:
  python3 acquire_descriptions.py <provider> <version> [--cache-root PATH]

Prints the resolved local directory path to stdout on success.
"""
import argparse
import hashlib
import json
import os
import sys
import tarfile
import urllib.request
from io import BytesIO

GITHUB_API_BASE = "https://api.github.com"
NAMESPACE = "Ubiquex"
REPO = "ubiquex-docs"
ARCHIVE_FILENAME = "snapshot.tar.gz"
CHECKSUMS_FILENAME = "SHA256SUMS"


def default_cache_root():
    return os.path.join(os.path.expanduser("~"), ".ubx", "descriptions")


def is_descriptions_dir(d, provider):
    return os.path.isfile(os.path.join(d, f"{provider}.json"))


def http_get_bytes(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch_release(provider, version):
    tag = f"descriptions-{provider}-v{version}"
    url = f"{GITHUB_API_BASE}/repos/{NAMESPACE}/{REPO}/releases/tags/{tag}"
    data = json.loads(http_get_bytes(url))
    assets = {a["name"]: a["browser_download_url"] for a in data.get("assets", [])}
    return tag, assets


def expected_sha256(shasums_content, filename):
    for line in shasums_content.decode("utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == filename:
            return parts[0].lower()
    raise ValueError(f"{filename} not found in {CHECKSUMS_FILENAME}")


def extract_tar_gz(data, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    with tarfile.open(fileobj=BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            cleaned = os.path.normpath(member.name)
            if os.path.isabs(cleaned) or cleaned == ".." or cleaned.startswith(".." + os.sep):
                raise ValueError(f"entry {member.name!r} escapes the archive root")
            if not (member.isfile() or member.isdir()):
                raise ValueError(f"entry {member.name!r} has unsupported type (only regular files and directories are real snapshot content)")
        tar.extractall(dest_dir)  # nosec - membership already validated above


def acquire_descriptions(provider, version, cache_root=None):
    cache_root = cache_root or default_cache_root()
    dest_dir = os.path.join(cache_root, NAMESPACE.lower(), provider, version)

    mirror_dir = os.environ.get("UBX_DESCRIPTIONS_MIRROR")
    if mirror_dir:
        mirrored = os.path.join(mirror_dir, NAMESPACE.lower(), provider, version)
        if is_descriptions_dir(mirrored, provider):
            return mirrored

    if is_descriptions_dir(dest_dir, provider):
        return dest_dir

    tag, assets = fetch_release(provider, version)
    if ARCHIVE_FILENAME not in assets:
        raise ValueError(f"{tag}: no {ARCHIVE_FILENAME} asset")
    if CHECKSUMS_FILENAME not in assets:
        raise ValueError(f"{tag}: no {CHECKSUMS_FILENAME} asset")

    sums_content = http_get_bytes(assets[CHECKSUMS_FILENAME])
    want = expected_sha256(sums_content, ARCHIVE_FILENAME)

    archive_bytes = http_get_bytes(assets[ARCHIVE_FILENAME])
    got = hashlib.sha256(archive_bytes).hexdigest()
    if got != want:
        raise ValueError(f"{ARCHIVE_FILENAME}: SHA256SUMS says {want}, downloaded archive is {got}")

    extract_tar_gz(archive_bytes, dest_dir)
    if not is_descriptions_dir(dest_dir, provider):
        raise ValueError(f"{ARCHIVE_FILENAME} extracted with no real {provider}.json at its root")
    return dest_dir


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("provider")
    ap.add_argument("version")
    ap.add_argument("--cache-root", default=None)
    args = ap.parse_args()
    print(acquire_descriptions(args.provider, args.version, args.cache_root))


if __name__ == "__main__":
    main()
