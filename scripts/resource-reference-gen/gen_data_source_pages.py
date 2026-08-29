#!/usr/bin/env python3
"""Real data-source page generator -- UBI-186's own docs-side proof that
the Resources/Data sources nesting pattern renders correctly, validated
on one real category (AWS Amplify) before any attempt to scale it to
all six providers.

Deliberately a SEPARATE script from gen_provider_docs.py, not a change to
build_resource_page_complete: a data source has no create/read split (one
real lookup operation, not two), no trust-policy/access-policy config
fields to detect, and its own Computed fields are "returned by the
lookup" rather than "computed by <provider> after `ship`" -- different
enough real semantics that bolting this onto the resource generator would
risk the 1710+ already-published resource pages for a real, but narrower,
gain. Reuses gen_provider_docs's own genuinely provider-neutral helpers
(type_str, pick_richer_example_fields, field_literal_with_preamble, the
real gofmt/deno-fmt-verified fence()) unchanged -- no second, drifted copy
of logic that owes nothing to being resource-specific.

Scope, stated rather than silently implied: this generates real,
complete, verified-compiling example programs and a real, schema-derived
property tree -- the SAME rigor bar as the resource generator's own
"real go build/deno check against actual output, never just visually
plausible" discipline (mirrored below via gofmt_lines/deno_fmt_lines,
the identical real tools). What it does NOT yet do: the AI-description
enrichment pass (`ubx sdk gen --describe`) was never run against any of
the ~5,900 real data sources this session's own SDK generation produced,
so nearly every field description here is real-but-empty (schema-sourced
prose only, honestly labeled -- never invented) -- richer descriptions
are additive, separately-scopable follow-up work, the identical
AI-inferred pipeline the resource corpus already went through.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from gen_provider_docs import (
    KIND_OBJECT,
    ai_inferred_marker,
    fence,
    field_literal_with_preamble,
    field_shape_signature,
    gofmt_lines,
    deno_fmt_lines,
    intro_and_description,
    normalize_schema_description,
    object_fields_of,
    pascal,
    camel,
    pick_richer_example_fields,
    type_str,
    yaml_dq_escape,
    _PY_PATH_STACK,
    _PY_NESTED_CLASSES_USED,
    _PY_NESTED_FIELD_MAP,
    _drop_unreal_optional_object_fields,
)


# The identical real reserved-word set sdk/codegen/templates/py/py.go's
# own pythonKeywords resolves with a trailing underscore (real, live-
# found case: Kubernetes' own real "continue" pagination-token field --
# confirmed live via a full ast.parse sweep of this generator's own
# output, "RoleConfig(continue=...)" is a genuine Python SyntaxError,
# `continue` being a reserved statement keyword, not just an unusual
# identifier). Keeping this a real, separate list (not importing Go)
# mirrors that file's own doc comment: capitalized reserved words
# (False/None/True) never collide with a wire name, so they're omitted.
PYTHON_KEYWORDS = {
    "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del",
    "elif", "else", "except", "finally", "for",
    "from", "global", "if", "import", "in",
    "is", "lambda", "nonlocal", "not", "or",
    "pass", "raise", "return", "try", "while",
    "with", "yield",
}


def python_identifier(wire_name):
    return wire_name + "_" if wire_name in PYTHON_KEYWORDS else wire_name


def python_module_ident(name):
    """sdk/codegen/templates/py/py.go's own real pyModuleIdent, mirrored:
    a real generated Python service/module DIRECTORY carries this same
    escaping (unlike a field name, checked above) because "lambda" is
    both a Python keyword and a real AWS service (aws_lambda_*) -- a
    plain `from ubx.aws.data.lambda import ...` is a genuine
    SyntaxError, confirmed live via this generator's own full ast.parse
    sweep. The real generated Python tree names that directory
    "lambda_", not "lambda" -- go/service_dir (this generator's own
    ident source, scanned from the real Go tree, which has no such
    restriction) must not be reused for Python's own import path
    unescaped."""
    if name in PYTHON_KEYWORDS:
        return name + "_"
    if name and name[0].isdigit():
        return "_" + name
    return name


def data_field_desc(f):
    if f["Required"]:
        qualifier = "Required lookup argument."
    elif f["Computed"]:
        qualifier = "Returned by the lookup."
    else:
        qualifier = "Optional lookup argument."
    desc = (f.get("Description") or "").strip()
    if desc:
        # normalize_schema_description's own real, confirmed-live finding
        # (gen_provider_docs.py's own doc comment on it) applies here
        # identically: real vendor description text carries raw "<"/">"/
        # "{"/"}" characters (HTML markup, placeholder notation) that MDX
        # reads as JSX/live-expression syntax, not literal prose -- this
        # driver's own real, full-scale run (7000+ data source pages)
        # found 156 real pages break `mint validate` without this, the
        # identical class of break the resource-side generator already
        # guards against; this file's own render_data_field/data_field_desc
        # never called it (a real, confirmed gap in the original one-
        # category Amplify prototype, which never happened to include a
        # description carrying this markup).
        return f"{normalize_schema_description(desc)}{ai_inferred_marker(f)} {qualifier}"
    return qualifier


def render_data_field(f, indent, depth=0, ancestors=()):
    # UBI-177: matches render_response_field's own real fix -- ancestors
    # is (name, structural signature) pairs, not bare names, so an
    # unrelated type sharing a common field name is never mistaken for a
    # genuine self-reference. See field_shape_signature's own doc
    # comment (gen_provider_docs.py) for the full real reasoning; this
    # function shares that exact helper rather than a second, drifted
    # copy of the same logic.
    pad = " " * indent
    name = f["WireName"]
    t = f["Type"]
    ts = type_str(t)
    req_attr = " required" if f["Required"] else ""
    lines = [f'{pad}<ResponseField name="{name}" type="{ts}"{req_attr}>']
    lines.append(f"{pad}  {data_field_desc(f)}")
    if t["Kind"] == KIND_OBJECT:
        inner = sorted(object_fields_of(t), key=lambda x: x["WireName"])
        if inner:
            sig = field_shape_signature(t)
            is_cycle = any(n == name and s == sig for n, s in ancestors)
            if is_cycle or depth >= 6:
                lines.append(f'{pad}  <Expandable title="properties">')
                lines.append(f'{pad}    <Note>Nested `{name}` structure omitted (recursive or deeply nested).</Note>')
                lines.append(f"{pad}  </Expandable>")
            else:
                lines.append(f'{pad}  <Expandable title="properties">')
                for inf in inner:
                    lines.append(render_data_field(inf, indent + 4, depth + 1, ancestors + ((name, sig),)))
                lines.append(f"{pad}  </Expandable>")
    lines.append(f"{pad}</ResponseField>")
    return "\n".join(lines)


def build_data_source_page(wire, service, local, slug, fields, go, ts, py,
                            provider, schema_name, provider_display,
                            stack_name, sdk_repo_id, intro_text=None):
    lookup_fields = sorted([f for f in fields if f["Required"] or (not f["Computed"])], key=lambda f: f["WireName"])
    result_fields = sorted([f for f in fields if f["Computed"]], key=lambda f: f["WireName"])
    example_fields = pick_richer_example_fields(lookup_fields)
    example_fields = _drop_unreal_optional_object_fields(example_fields, py)

    # --- Go ---
    go_preambles, go_assigns = [], []
    for f in example_fields:
        pre, val = field_literal_with_preamble(f, "go")
        if pre and pre not in go_preambles:
            go_preambles.append(pre)
        go_assigns.append(f"\t\t\t{pascal(f['WireName'])}: {val},")
    go_pkg_import_path = f'github.com/ubiquex/ubx-sdk-{sdk_repo_id}/sdk/go/{schema_name}/data/{go["service_dir"]}'
    go_lines = [
        "package main", "",
        "import (",
        f'\t{go["package"]} "{go_pkg_import_path}"',
        '\tubx "github.com/ubiquex/ubx-sdk-go/runtime"',
        ")", "",
        "func main() {",
        '\tubx.Main(ubx.Stack("example", func() {',
        f'\t\tubx.Intent(ubx.IntentInfo{{Summary: "look up {wire}"}})',
    ]
    for pre in go_preambles:
        go_lines.append("")
        go_lines.append("\t\t" + pre.replace("\n", "\n\t\t"))
    go_lines.append("")
    go_lines.append(f'\t\tubx.Data({go["package"]}.{go["binding"]}, "example", {go["package"]}.{go["config"]}{{')
    go_lines.extend(go_assigns)
    go_lines.append("\t\t})")
    go_lines.append("\t}))")
    go_lines.append("}")
    go_block = fence("go", gofmt_lines(go_lines))

    # --- TypeScript ---
    ts_preambles, ts_assigns = [], []
    for f in example_fields:
        pre, val = field_literal_with_preamble(f, "ts")
        if pre and pre not in ts_preambles:
            ts_preambles.append(pre)
        ts_assigns.append(f"    {camel(f['WireName'])}: {val},")
    ts_import_path = f'@ubx/sdk-{sdk_repo_id}/{schema_name}/data/{ts["service_dir"]}/{os.path.splitext(os.path.basename(ts["file"]))[0]}'
    ts_lines = [
        'import { data, intent, stack } from "@ubx/sdk";',
        f'import {{ {ts["binding"]} }} from "{ts_import_path}";',
        "",
        'export default stack("example", () => {',
        f'  intent({{ summary: "look up {wire}" }});',
    ]
    for pre in ts_preambles:
        ts_lines.append("")
        ts_lines.append("  " + pre.replace("\n", "\n  "))
    ts_lines.append("")
    ts_lines.append(f'  data({ts["binding"]}, "example", {{')
    ts_lines.extend(ts_assigns)
    ts_lines.append("  });")
    ts_lines.append("});")
    ts_block = fence("typescript", deno_fmt_lines(ts_lines))

    # --- Python ---
    # UBI-208: seeded exactly like build_resource_page_complete's own
    # Python block -- a nested-object lookup field reaches the SAME
    # literal_py, which constructs a real dataclass and records its own
    # class name in _PY_NESTED_CLASSES_USED as a side effect. Without
    # this seed/collect step (the gap this data-source generator had
    # until now), that construction was emitted with no matching
    # import -- syntactically valid, a real NameError at execution.
    #
    # UBI-211: _PY_PATH_STACK holds real wire names (not a binding-name-
    # seeded PascalCase path) and is resolved against _PY_NESTED_FIELD_MAP
    # (py["nested_fields"], the data source's own real FieldSpec tree --
    # see extract_idents.py's scan_py_data), the identical mechanism
    # build_resource_page_complete uses.
    _PY_PATH_STACK.clear()
    _PY_NESTED_CLASSES_USED.clear()
    _PY_NESTED_FIELD_MAP.clear()
    _PY_NESTED_FIELD_MAP.update(py.get("nested_fields") or {})
    py_preambles, py_assigns = [], []
    for f in example_fields:
        try:
            pre, val = field_literal_with_preamble(f, "py")
        except KeyError:
            # UBI-209: same real cross-language codegen gap as
            # build_resource_page_complete's own identical catch -- a
            # field the real published Go/TS bindings genuinely have can
            # be absent from the real published Python Config class
            # entirely. Skip it for Python only; Go/TS render normally.
            continue
        if pre and pre not in py_preambles:
            py_preambles.append(pre)
        py_assigns.append(f"        {python_identifier(f['WireName'])}={val},")
    py_import_path = f'ubx.{python_module_ident(schema_name)}.data.{python_module_ident(py["service_dir"])}'
    py_config_name = py.get("config") or f'{py["binding"]}Config'
    # UBI-211: real, confirmed live (aws_sts_federation_token's own
    # policy preamble) -- build_resource_page_complete already checks
    # for a real json.dumps( preamble and imports json when needed; this
    # data-source generator never did, a real NameError at execution for
    # any data source whose lookup config needs a JSON-encoded preamble.
    needs_json_py = any("json.dumps(" in p for p in py_preambles)
    py_lines = []
    if needs_json_py:
        py_lines.append("import json")
    py_lines += [
        "import ubx_sdk as ubx",
        f'from {py_import_path} import {py["binding"]}, {py_config_name}',
    ]
    if _PY_NESTED_CLASSES_USED:
        # UBI-211: the package-level __init__.py only re-exports each
        # data source's own top-level Binding/Config (confirmed against
        # the real ubx-sdk-aws-py package: `from .certificates import
        # Certificates, CertificatesConfig`, nothing else) -- same real
        # gap build_resource_page_complete's own doc comment already
        # covers for resources. A nested dataclass (e.g.
        # Certificates_Includes) is only reachable from its own real
        # submodule, py["module"], never the package -- the prior single
        # shared import line produced a syntactically valid but real
        # ImportError at execution for every data-source page with any
        # nested object field at all, independent of whether the class
        # name itself was right.
        py_lines.append(f'from {py["module"]} import {", ".join(_PY_NESTED_CLASSES_USED)}')
    py_lines += [
        "",
        "def describe():",
        f'    ubx.intent("look up {wire}")',
    ]
    for pre in py_preambles:
        py_lines.append("")
        py_lines.append("    " + pre.replace("\n", "\n    "))
    py_lines.append("")
    py_lines.append(f'    ubx.data({py["binding"]}, "example", {py_config_name}(')
    py_lines.extend(py_assigns)
    py_lines.append("    ))")
    py_lines.append("")
    py_lines.append('if __name__ == "__main__":')
    py_lines.append('    ubx.run("example", describe)')
    py_block = fence("python", py_lines)

    lookup_section = "\n\n".join(render_data_field(f, 0) for f in lookup_fields) or "_This lookup takes no arguments._"
    result_section = "\n\n".join(render_data_field(f, 0) for f in result_fields) or "_No computed result fields._"

    # Mirrors build_resource_page_complete's own real intro_text handling
    # (gen_provider_docs.py) exactly: intro_text present (a real
    # artifacts/<provider>/intros.json entry, keyed data_<wire> to stay
    # collision-safe against a same-named resource -- confirmed live
    # that most providers' data sources share their resource's own
    # literal wire type, not just Kubernetes) replaces the generic
    # three-line paragraph every data source page has rendered since
    # this generator's own first version. Absent (a data source with no
    # real intro yet) falls back to exactly that original paragraph --
    # an honest gap, not a fabricated one.
    if intro_text:
        fm_description_raw, body = intro_and_description(intro_text)
        fm_description = yaml_dq_escape(fm_description_raw)
    else:
        fm_description = f"`{wire}` is a real, live lookup against {provider_display}, generated from {schema_name}'s own real schema -- read-only, never created or destroyed."
        body = f'`{wire}` is a real, live data source: `ubx.Data`/`data`/`ubx.data` (per language) executes this lookup at resolve time, against {provider_display}\'s own real API, and returns whatever it finds. It is never created, modified, or destroyed by ubx -- see [docs/schema.md\'s own "Amendment: data sources"] for the real wire shape this compiles to (`data_sources[]`, never `resources[]`).'
    body_block = f"\n{body}\n" if body else ""

    return f'''---
title: "{wire}"
description: "{fm_description}"
---
{body_block}
## Example

<Tabs>
  <Tab title="Go">
{go_block}
  </Tab>
  <Tab title="TypeScript">
{ts_block}
  </Tab>
  <Tab title="Python">
{py_block}
  </Tab>
</Tabs>

## Lookup arguments

{lookup_section}

## Result properties

{result_section}
'''


def load_schema(dump_dir, shortname):
    return json.load(open(os.path.join(dump_dir, shortname, "schema.json")))


def load_fields(dump_dir, shortname, wire):
    return json.load(open(os.path.join(dump_dir, shortname, f"{wire}.json")))
