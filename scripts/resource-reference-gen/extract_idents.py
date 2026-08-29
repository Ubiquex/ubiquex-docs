import re, glob, json, os, sys

def resolve_config_go(text, binding):
    # A real, found-in-review collision: when a resource's own naive
    # "<Binding>Config" name collides with ANOTHER real resource's own
    # binding VAR name in the same package (e.g. google_workstations_
    # workstation's naive "WorkstationConfig" collides with sibling
    # google_workstations_workstation_config's own `var WorkstationConfig
    # = ubx.ResourceBinding{...}`), the real codegen renames the LOSING
    # side's own Config struct with a trailing underscore
    # (`WorkstationConfig_`) rather than guess-deriving it, read the
    # real declared type straight out of the source (same discipline
    # `binding` above already uses for the binding var itself).
    if not binding:
        return None
    naive = binding + "Config"
    if re.search(r"\btype " + re.escape(naive) + r" struct\b", text):
        return naive
    if re.search(r"\btype " + re.escape(naive) + r"_ struct\b", text):
        return naive + "_"
    return naive

def resolve_config_py(text, binding):
    if not binding:
        return None
    naive = binding + "Config"
    if re.search(r"^class " + re.escape(naive) + r":", text, re.M):
        return naive
    if re.search(r"^class " + re.escape(naive) + r"_:", text, re.M):
        return naive + "_"
    return naive

def scan_go(root, provider):
    out = {}
    for f in sorted(glob.glob(root + f"/{provider}/**/*.go", recursive=True)):
        # NOT filtering "*_test.go" here -- real, confirmed finding: these
        # SDK repos carry zero genuine Go unit tests, but DO carry real
        # generated resource files whose own wire-derived local name
        # happens to end in "_test" (google_network_management_connectivity_test,
        # azurerm's application_insights_web_test/insights_standard_web_test)
        # -- a blanket "_test.go" skip silently drops real resources. The
        # WireType-match requirement below is what actually distinguishes
        # a real generated file from anything else.
        #
        # Same reasoning applies to a real "doc.go" filter, found-in-
        # review: `f.endswith("doc.go")` is a substring-suffix check, not
        # an exact-filename check, so it also matched real resource files
        # like "apigee_apidoc.go" (google_apigee_apidoc, confirmed real,
        # confirmed to have a real WireType), silently dropping them from
        # idents extraction and from every downstream page that resource
        # was ever supposed to get. The genuine package-doc-comment file
        # has no WireType at all, so the match check below already skips
        # it correctly -- the filter was both wrong and redundant.
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
        if not bm:
            # UBI-203, real, confirmed live (Datadog's datadog_monitor,
            # Kubernetes' kubernetes_apps_replica_set): a resource and its
            # own same-named data source can share the identical
            # WireType -- the `m` match above fires on either file, but
            # only a real `ubx.ResourceBinding{...}` declaration is what
            # THIS scanner's every real caller wants (data sources go
            # through the separate, already-safe scan_go_data in
            # gen_all_data_source_pages.py). Registering a null
            # binding/config here used to let a DataSourceBinding file
            # silently win or lose a same-wire race depending on
            # glob.glob()'s own undefined order -- skip it outright
            # instead, so the outcome is correct, not merely sorted.
            continue
        binding = bm.group(1)
        pkg_m = re.search(r'^package (\w+)', text, re.M)
        rel = os.path.relpath(f, root)
        service_dir = rel.split("/")[1]
        if wire in out:
            raise SystemExit(
                f"scan_go: {wire!r} claimed by both {out[wire]['file']!r} and {rel!r} -- "
                "two real ResourceBinding files sharing one WireType, refusing rather than "
                "silently picking one (UBI-203)"
            )
        out[wire] = {
            "file": rel,
            "package": pkg_m.group(1) if pkg_m else None,
            "service_dir": service_dir,
            "binding": binding,
            "config": resolve_config_go(text, binding),
        }
    return out

def scan_py(root, provider):
    out = {}
    for f in sorted(glob.glob(root + f"/ubx/{provider}/**/*.py", recursive=True)):
        if f.endswith("__init__.py"):
            continue
        text = open(f).read()
        m = re.search(r'wire_type="([^"]+)"', text)
        if not m:
            continue
        wire = m.group(1)
        bm = re.search(r'^(\w+) = ubx\.ResourceBinding\(', text, re.M)
        if not bm:
            # UBI-203: same real resource/data-source WireType collision
            # as scan_go above -- skip a DataSourceBinding file outright
            # rather than register a null binding/config that could win
            # a same-wire race depending on glob order.
            continue
        binding = bm.group(1)
        rel = os.path.relpath(f, root)
        service_dir = rel.split("/")[2]
        module = rel[len("ubx/"):-3].replace("/", ".")
        if wire in out:
            raise SystemExit(
                f"scan_py: {wire!r} claimed by both {out[wire]['file']!r} and {rel!r} -- "
                "two real ResourceBinding files sharing one WireType, refusing rather than "
                "silently picking one (UBI-203)"
            )
        out[wire] = {
            "file": rel,
            "module": "ubx." + module,
            "service_dir": service_dir,
            "binding": binding,
            "config": resolve_config_py(text, binding),
        }
    return out

def scan_ts(root, provider):
    out = {}
    for f in sorted(glob.glob(root + f"/{provider}/**/*.ts", recursive=True)):
        # Same real "doc.ts" bug as scan_go's own "doc.go" filter above
        # (a substring-suffix check, not an exact-filename check) --
        # removed for the same reason: the wireType-match requirement
        # below already correctly excludes the genuine doc-comment file,
        # which carries no wireType at all.
        text = open(f).read()
        m = re.search(r'wireType:\s*"([^"]+)"', text)
        if not m:
            continue
        wire = m.group(1)
        bm = re.search(r'export const (\w+): ResourceBinding', text)
        if not bm:
            # UBI-203: same real resource/data-source WireType collision
            # as scan_go above -- skip a DataSourceBinding file outright
            # rather than register a null binding/config that could win
            # a same-wire race depending on glob order.
            continue
        binding = bm.group(1)
        rel = os.path.relpath(f, root)
        service_dir = rel.split("/")[1]
        if wire in out:
            raise SystemExit(
                f"scan_ts: {wire!r} claimed by both {out[wire]['file']!r} and {rel!r} -- "
                "two real ResourceBinding files sharing one WireType, refusing rather than "
                "silently picking one (UBI-203)"
            )
        out[wire] = {
            "file": rel,
            "service_dir": service_dir,
            "binding": binding,
            "config": binding + "Config",
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
