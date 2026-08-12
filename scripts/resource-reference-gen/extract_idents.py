import re, glob, json, os, sys

def scan_go(root, provider):
    out = {}
    for f in glob.glob(root + f"/{provider}/**/*.go", recursive=True):
        # NOT filtering "*_test.go" here -- real, confirmed finding: these
        # SDK repos carry zero genuine Go unit tests, but DO carry real
        # generated resource files whose own wire-derived local name
        # happens to end in "_test" (google_network_management_connectivity_test,
        # azurerm's application_insights_web_test/insights_standard_web_test)
        # -- a blanket "_test.go" skip silently drops real resources. The
        # WireType-match requirement below is what actually distinguishes
        # a real generated file from anything else.
        if f.endswith("doc.go"):
            continue
        text = open(f).read()
        m = re.search(r'WireType:\s*"([^"]+)"', text)
        if not m:
            continue
        wire = m.group(1)
        # binding var: `var <Name> = ubx.ResourceBinding{` -- unambiguous,
        # unlike searching for "type \w+Config struct" which also matches
        # nested types whose own local name happens to end in "...Config"
        # (e.g. kubernetes_pod_v1's real "spec.dns_config" nested block ->
        # PodV1_Spec_DnsConfig, declared BEFORE the real top-level
        # PodV1Config in the file -- a real, confirmed collision, not
        # hypothetical).
        bm = re.search(r'var (\w+) = ubx\.ResourceBinding\{', text)
        pkg_m = re.search(r'^package (\w+)', text, re.M)
        rel = os.path.relpath(f, root)
        service_dir = rel.split("/")[1]
        binding = bm.group(1) if bm else None
        out[wire] = {
            "file": rel,
            "package": pkg_m.group(1) if pkg_m else None,
            "service_dir": service_dir,
            "binding": binding,
            "config": (binding + "Config") if binding else None,
        }
    return out

def scan_py(root, provider):
    out = {}
    for f in glob.glob(root + f"/ubx/{provider}/**/*.py", recursive=True):
        if f.endswith("__init__.py"):
            continue
        text = open(f).read()
        m = re.search(r'wire_type="([^"]+)"', text)
        if not m:
            continue
        wire = m.group(1)
        bm = re.search(r'^(\w+) = ubx\.ResourceBinding\(', text, re.M)
        rel = os.path.relpath(f, root)
        service_dir = rel.split("/")[2]
        module = rel[len("ubx/"):-3].replace("/", ".")
        binding = bm.group(1) if bm else None
        out[wire] = {
            "file": rel,
            "module": "ubx." + module,
            "service_dir": service_dir,
            "binding": binding,
            "config": (binding + "Config") if binding else None,
        }
    return out

def scan_ts(root, provider):
    out = {}
    for f in glob.glob(root + f"/{provider}/**/*.ts", recursive=True):
        if f.endswith("doc.ts"):
            continue
        text = open(f).read()
        m = re.search(r'wireType:\s*"([^"]+)"', text)
        if not m:
            continue
        wire = m.group(1)
        bm = re.search(r'export const (\w+): ResourceBinding', text)
        rel = os.path.relpath(f, root)
        service_dir = rel.split("/")[1]
        binding = bm.group(1) if bm else None
        out[wire] = {
            "file": rel,
            "service_dir": service_dir,
            "binding": binding,
            "config": (binding + "Config") if binding else None,
        }
    return out


def main():
    provider = sys.argv[1]
    go_root = os.path.expanduser(sys.argv[2])
    py_root = os.path.expanduser(sys.argv[3])
    ts_root = os.path.expanduser(sys.argv[4])
    out_path = sys.argv[5]

    go = scan_go(go_root, provider)
    py = scan_py(py_root, provider)
    ts = scan_ts(ts_root, provider)

    print("go:", len(go), "py:", len(py), "ts:", len(ts))

    wires = set(go) | set(py) | set(ts)
    missing = [w for w in wires if w not in go or w not in py or w not in ts]
    print("missing from one lang:", missing)

    combined = {}
    for w in wires:
        combined[w] = {"go": go.get(w), "py": py.get(w), "ts": ts.get(w)}

    json.dump(combined, open(out_path, "w"), indent=2)
    print("wrote", len(combined), "entries to", out_path)


if __name__ == "__main__":
    main()
