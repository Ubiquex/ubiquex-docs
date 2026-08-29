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

FIELD_SPEC_ENTRY_RE = re.compile(
    r'"(\w+)":\s*ubx\.FieldSpec\(\s*wire_name="([^"]+)"\s*(?:,\s*kind="(\w+)"\s*)?(?:,\s*fields=(_\w+)\s*)?,?\s*\)',
    re.S,
)


def _py_fields_blocks(text, root_binding_kind):
    """UBI-211: maps every real `_XxxFields = {...}` dict variable name
    to its own list of (py_field_name, wire_name, kind,
    referenced_fields_var_or_None) entries, plus a synthetic "__root__"
    key for the real ResourceBinding/DataSourceBinding's own top-level
    fields={...} block -- ground truth for what class name the real
    codegen actually minted for a given nested field, read directly
    rather than reconstructed by a second, path-based naming
    implementation (the UBI-197 divergence risk this sidesteps)."""
    blocks = {}
    for m in re.finditer(r'^(_\w+Fields) = \{\n(.*?)\n\}\n', text, re.M | re.S):
        blocks[m.group(1)] = FIELD_SPEC_ENTRY_RE.findall(m.group(2))
    root_m = re.search(
        r'= ubx\.' + root_binding_kind + r'\(\s*\n\s*wire_type="[^"]+",\s*\n\s*fields=\{\n(.*?)\n    \},\n\)',
        text, re.S,
    )
    if root_m:
        blocks["__root__"] = FIELD_SPEC_ENTRY_RE.findall(root_m.group(1))
    return blocks


def _class_name_from_fields_var(var):
    assert var.startswith("_") and var.endswith("Fields"), var
    return var[1:-len("Fields")]


def _build_nested_field_map(blocks, fields_var, visited=frozenset(), depth=0):
    # A real generated file is finite source, not a runtime cycle, but a
    # genuinely self-referential schema shape (Kubernetes PodSpec, see
    # UBI-177) means this guard is defensive, not decorative.
    if fields_var in visited or depth > 40:
        return {}
    visited = visited | {fields_var}
    out = {}
    for py_name, wire_name, kind, ref in blocks.get(fields_var, []):
        node = {}
        if ref:
            node["class"] = _class_name_from_fields_var(ref)
            node["fields"] = _build_nested_field_map(blocks, ref, visited, depth + 1)
        out[wire_name] = node
    return out


def parse_nested_fields(text, root_binding_kind):
    """Real per-wire nested-class name map, keyed by real wire name at
    each level (see gen_provider_docs.py's literal_py, which walks this
    with the field's own real wire-name path rather than a computed
    PascalCase path). Returns None if the file carries no matching root
    binding block at all."""
    blocks = _py_fields_blocks(text, root_binding_kind)
    if "__root__" not in blocks:
        return None
    return _build_nested_field_map(blocks, "__root__")


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
            "nested_fields": parse_nested_fields(text, "ResourceBinding"),
        }
    return out


def scan_py_data(root, provider):
    """UBI-211: the data-source counterpart to scan_py, scoped to the
    real /data/ subtree the same way gen_all_data_source_pages.py's own
    scan_go_data is -- data-source idents are otherwise built purely by
    naming convention (idents_for()), never by scanning the real .py
    file, so this is the only source of a real nested_fields map for
    data-source pages."""
    out = {}
    for f in sorted(glob.glob(root + f"/ubx/{provider}/data/**/*.py", recursive=True)):
        if f.endswith("__init__.py"):
            continue
        text = open(f).read()
        m = re.search(r'wire_type="([^"]+)"', text)
        if not m:
            continue
        wire = m.group(1)
        bm = re.search(r'^(\w+) = ubx\.DataSourceBinding\(', text, re.M)
        if not bm:
            continue
        binding = bm.group(1)
        rel = os.path.relpath(f, root)
        if wire in out:
            raise SystemExit(
                f"scan_py_data: {wire!r} claimed by both {out[wire]['file']!r} and {rel!r} -- "
                "two real DataSourceBinding files sharing one WireType, refusing rather than "
                "silently picking one (UBI-203)"
            )
        module = rel[len("ubx/"):-3].replace("/", ".")
        out[wire] = {
            "file": rel,
            "module": "ubx." + module,
            "binding": binding,
            "config": resolve_config_py(text, binding),
            "nested_fields": parse_nested_fields(text, "DataSourceBinding"),
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
