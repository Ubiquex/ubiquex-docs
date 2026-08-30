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


def has_published_pin(release_name):
    """UBI-222: real, live check against the GitHub API for whether
    ANY descriptions-<release_name>-v* release has ever been published
    -- the signal resolve_descriptions_path uses to decide whether the
    local artifacts/<provider>/descriptions.json fallback is still
    honest to take. A provider with zero real releases has never been
    migrated; falling back for it is the same, correct, unchanged
    behavior this function has always had. A provider with at least
    one real release has its real, richer content living ONLY in that
    release -- silently falling back to the local file for it is
    exactly the invisible gap UBI-222 found: 401 real, previously-
    published resource pages dropped from a real regeneration run
    because nothing in CI ever set the env var pinning them, and the
    fallback made that look like a clean run instead of a missing
    wire-up."""
    url = f"{GITHUB_API_BASE}/repos/{NAMESPACE}/{REPO}/releases?per_page=100"
    try:
        data = json.loads(http_get_bytes(url))
    except Exception as e:
        raise RuntimeError(
            f"could not check {NAMESPACE}/{REPO}'s own published releases to decide "
            f"whether {release_name!r} has a real descriptions pin: {e}"
        ) from e
    prefix = f"descriptions-{release_name}-v"
    return any(r.get("tag_name", "").startswith(prefix) for r in data)


def resolve_descriptions_path(provider_key, docs_root, release_name=None):
    """UBI-102: a pinned corpus (env UBX_DESCRIPTIONS_PIN_<PROVIDER>=<version>,
    keyed by this repo's own docs-internal provider_key, e.g. "gcp")
    takes priority over this repo's own local artifacts/<provider>/
    descriptions.json. Shared by both regen_pages.py (resource pages)
    and gen_all_data_source_pages.py (data source pages, all six
    providers) so the two real docs-generation pipelines can never
    resolve a given provider's pin differently.

    UBI-222: an unset env var is ONLY ever treated as "not migrated
    yet" -- checked live via has_published_pin, never assumed from the
    env var's absence alone. A provider with a real, published pin and
    no env var set is a caller bug (CI never wired it up), and this
    function now refuses to paper over it with a stale local file --
    the exact silent fallback that let a real CI gap regenerate 401
    previously-published pages as "missing," deleting them, without a
    single loud failure anywhere. The prior version of this function
    treated an unset env var as unconditionally safe; it wasn't.

    release_name is the real published SDK repo's own short name
    (ubiquex's own sdk/providers/.ubx/config "NAMING" rule -- the
    [dynamic_providers.<name>] table key IS github.com/ubiquex/ubx-sdk-
    <name>), used for the release tag and the file the acquired archive
    is expected to contain. It differs from provider_key exactly once,
    for GCP: docs' own internal key is "gcp" (its artifacts/ directory,
    its own PROVIDERS dict), but the real published repo, and so
    provider.AcquireDescriptions's own tag on the Go side, is "google"
    (ubiquex/sdk/providers/.ubx/config's own real, live-repo-name
    precedent). Defaults to provider_key for the five providers where
    the two names are already identical."""
    release_name = release_name or provider_key
    pin_version = os.environ.get(f"UBX_DESCRIPTIONS_PIN_{provider_key.upper()}")
    if pin_version:
        pinned_dir = acquire_descriptions(release_name, pin_version)
        return os.path.join(pinned_dir, f"{release_name}.json")
    if has_published_pin(release_name):
        raise RuntimeError(
            f"{provider_key}: a real, published descriptions-{release_name}-v* "
            f"release exists, but UBX_DESCRIPTIONS_PIN_{provider_key.upper()} is "
            f"not set -- refusing to silently fall back to the stale local "
            f"artifacts/{provider_key}/descriptions.json (UBI-222: this exact "
            f"fallback is what let 401 real, previously-published pages get "
            f"dropped from a real regeneration run without a single loud "
            f"failure). Set the env var to the version this run should pin."
        )
    return os.path.join(docs_root, "artifacts", provider_key, "descriptions.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("provider")
    ap.add_argument("version")
    ap.add_argument("--cache-root", default=None)
    args = ap.parse_args()
    print(acquire_descriptions(args.provider, args.version, args.cache_root))


if __name__ == "__main__":
    main()
