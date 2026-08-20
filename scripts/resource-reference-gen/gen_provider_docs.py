#!/usr/bin/env python3
"""Shared library for resource-reference/<provider> page generation --
never run directly (no __main__ block, on purpose: this file is real,
tracked tooling shared by two real entry points, gen_mechanical_pages.py
(full-provider, sparse, the original AWS/GCP/Azure/Kubernetes corpus
generator) and gen_complete_pages.py (UBI-144's own richer template,
splice-only, one resource or a real batch at a time) -- both driven from
a real schema dump (see README.md's own "Regenerating schema/idents
data" section) + real identifier extraction (extract_idents.py's own
output, a real scan of the already-published SDK bindings repos).

Two real, deliberately separate page shapes live in this one file:
build_resource_page (the ORIGINAL mechanical tier -- a bare fragment,
2 example fields, a one-line markdown description; matches the
established AWS mechanical-tier format exactly, reverse-engineered from
eks/cluster.mdx, sqs/queue-policy.mdx, oam/link.mdx,
pinpoint/adm-channel.mdx, docdbelastic/cluster.mdx, security/group.mdx)
and build_resource_page_complete (UBI-144's own newer template --
complete, runnable programs, a richer real field slice, a real markdown
scenario). The mechanical tier still generates every page this repo's
own corpus doesn't yet have the complete-template treatment for; the
complete tier is the one UBI-144 is rolling out, one real, diverse
batch at a time, splicing ONLY its own Example section into whatever
page already exists rather than regenerating the whole file (see
README.md for why: an existing page's own Input/Output property prose
may already be hand-tuned, and a full regenerate would silently
overwrite it with this file's own generic mechanical descriptions).
"""
import json, os

KIND_INVALID, KIND_SCALAR, KIND_LIST, KIND_SET, KIND_MAP, KIND_OBJECT = 0, 1, 2, 3, 4, 5
SCALAR_INVALID, SCALAR_STRING, SCALAR_NUMBER, SCALAR_BOOL, SCALAR_DYNAMIC = 0, 1, 2, 3, 4


def pascal(wire):
    return "".join(p.capitalize() for p in wire.split("_") if p)


def camel(wire):
    parts = [p for p in wire.split("_") if p]
    if not parts:
        return wire
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def type_str(t):
    k = t["Kind"]
    if k == KIND_SCALAR:
        return {SCALAR_STRING: "string", SCALAR_NUMBER: "number", SCALAR_BOOL: "bool",
                SCALAR_DYNAMIC: "any"}.get(t["Scalar"], "any")
    if k == KIND_LIST:
        return f'list({type_str(t["Element"])})'
    if k == KIND_SET:
        return f'set({type_str(t["Element"])})'
    if k == KIND_MAP:
        return f'map({type_str(t["Element"])})'
    if k == KIND_OBJECT:
        return "object"
    return "any"


def is_object_ish(t):
    """True if t itself, or its Element (for list/set/map), is an object."""
    if t["Kind"] == KIND_OBJECT:
        return True
    if t["Kind"] in (KIND_LIST, KIND_SET, KIND_MAP) and t["Element"] and t["Element"]["Kind"] == KIND_OBJECT:
        return True
    return False


def object_fields_of(t):
    if t["Kind"] == KIND_OBJECT:
        return t["Object"] or []
    if t["Kind"] in (KIND_LIST, KIND_SET, KIND_MAP) and t["Element"]:
        return t["Element"]["Object"] or []
    return []


def eff_flags(f):
    req, opt, comp = f["Required"], f["Optional"], f["Computed"]
    all_false = not req and not opt and not comp
    eff_opt = opt or all_false
    eff_comp = comp or all_false
    return req, eff_opt, eff_comp


def normalize_schema_description(desc):
    """UBI-152: the real provider schema's own Description text, collapsed
    to one line -- real providers (confirmed live: hashicorp/google,
    hashicorp/kubernetes) embed raw newlines/tabs in this prose (e.g. a
    multi-paragraph enum explanation), which would otherwise break a
    ResponseField's own single-line-per-sentence convention every other
    field on the page already follows. Whitespace-only normalization,
    never a content change -- real text in, same real text out, just
    joined onto one line.

    Also downgrades a real em dash (U+2014) to this same repo's own
    established " -- " convention (every doc comment in this codebase
    already uses it, UBI-133's own zero-em-dash rule) -- a typographic
    substitution only, the informational content is unchanged. A real,
    confirmed-live case this mattered for: hashicorp/aws's own
    odb_cloud_vm_cluster description reads "...created or cloned —
    either ECPU or OCPU..." verbatim on the wire.

    Also HTML-entity-escapes real "<"/">"/"{"/"}" characters -- a real,
    confirmed-live MDX parsing break (113 real pages, a full mint
    validate pass), not a hypothetical: real provider description text
    commonly uses literal angle-bracket placeholder notation (e.g.
    google_kms_autokey_config's own real text, "...projects/
    <project_id_or_number>/...") or brace-delimited examples, and raw
    MDX reads "<x>"/"{x}" as an unclosed JSX tag / a live JS expression,
    not literal prose. HTML-entity escaping renders back to the exact
    same visible characters without MDX ever attempting to parse them --
    the same "real text in, same real text out" discipline as the
    whitespace/em-dash handling above, just for MDX's own reserved
    syntax instead of typography."""
    collapsed = " ".join(desc.split())
    collapsed = collapsed.replace("—", " -- ").replace("–", " -- ")
    return (
        collapsed
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("{", "&#123;")
        .replace("}", "&#125;")
    )


def field_desc(f, provider_display):
    req, eff_opt, eff_comp = eff_flags(f)
    if req:
        qualifier = "Required."
    elif eff_opt and eff_comp:
        qualifier = f"Optional; if omitted, computed by {provider_display}."
    elif eff_opt:
        qualifier = "Optional."
    elif eff_comp:
        qualifier = f"Computed by {provider_display} after `ship`."
    else:
        qualifier = "Optional."

    # UBI-152: real, schema-sourced prose (f["Description"], threaded
    # through from the real provider's own wire response -- provider/
    # schema.go -> sdk/codegen/ir.Field -> this JSON dump) takes
    # priority when the real provider actually set one. Genuinely empty
    # for some providers (confirmed live: hashicorp/aws, hashicorp/
    # azurerm both report this empty for nearly every real attribute --
    # a real limitation of what their schema RPCs expose, not a docs
    # gap to paper over) -- those keep exactly today's flag-derived
    # sentence, unchanged. The qualifier is still appended even when
    # real prose exists: it carries real, non-redundant information (the
    # optional-vs-computed-fallback nuance) the "required" badge on
    # ResponseField itself doesn't show.
    desc = normalize_schema_description(f.get("Description") or "")
    if desc:
        return f"{desc} {qualifier}"
    return qualifier


# The real, visible integrity label -- the founder's own requirement,
# already established and shipped for the generated SDK code's own doc
# comments (sdk/codegen/templates/{go,ts,py}, the "(AI-inferred)"
# suffix convention): "the label is the integrity guarantee, make it
# genuinely visible, not a footnote." This is the docs-side half of the
# same requirement, not yet wired in before this session (STATE.md's
# own account of the gap). Deliberately plain, real Markdown bold on
# its own paragraph rather than a custom Mintlify component (Tooltip/
# Badge/etc.) -- zero real, confirmed precedent for any such component
# anywhere in this corpus, and this pipeline's own standing discipline
# is "verified against real schemas/behavior, not assumed"; a component
# this repo's own Mintlify config has never actually rendered is a real
# risk `mint validate` alone would not catch (schema/frontmatter only,
# not component existence). Bold Markdown is guaranteed to render
# distinctly from the plain sentence above it in any Mintlify page.
def ai_inferred_marker(f, pad):
    if f.get("DescriptionSource") != "ai-inferred":
        return ""
    return (
        f"\n\n{pad}  **AI-inferred** -- not sourced from the real "
        "provider schema; generated by ubx's own description pipeline "
        "and never independently verified against the real provider."
    )


# UBI-156: real recursion guard for genuinely self-referential schema
# types (confirmed live: WAFv2 Statement<->AndStatement/OrStatement/
# NotStatement, Cost Category/Budgets/Anomaly-Subscription and/or/not
# rule trees) -- 10 resources measured 4,280-84,577 rendered elements
# before this fix, caught via a real repetition-ratio signal (total
# <ResponseField> count / distinct field-name count) and reverted
# during UBI-152's bulk pass. Two independent, real guards, both
# grounded in direct schema inspection rather than a guessed number:
#
#   1. cycle detection: a field's own WireName already appears among
#      its own object-typed ancestors in the current recursion chain.
#      This is a real, literal type self-reference (WAFv2's own
#      Statement type genuinely contains itself via AndStatement), not
#      a heuristic -- and it is proven zero-risk to already-shipped
#      legitimate content: direct testing against medialive/channel,
#      kinesis/firehose-delivery-stream, and securityhub/insight (the
#      only confirmed-legitimate deep-nesting precedents in this
#      corpus) triggers it zero times on all three, because none of
#      them actually contain a repeated object type in their ancestor
#      chain -- their real depth comes from distinct, non-recursive
#      sibling structure, not self-reference.
#   2. depth backstop (MAX_RESPONSE_FIELD_DEPTH): catches genuinely
#      deep but non-cyclic explosions (QuickSight's ~30 distinct
#      visual types, LexV2Models intent's ~8 distinct dialog branches,
#      each independently re-expanding real, non-repeated structure --
#      confirmed via direct schema walk, not assumed) that cycle
#      detection alone cannot bound, since there is no repeated type to
#      detect. Set to 8 -- the deepest real, confirmed-legitimate
#      nesting this corpus has ever shipped (medialive/channel's own
#      real depth, measured via a live <Expandable> open/close count on
#      its already-published page) -- so it never truncates anything
#      shallower than the deepest real precedent already accepted.
#
# Both guards emit an honest, real reference to the field that
# recurses (never a fabricated type name -- this schema representation
# has no separate type identity, only WireName) rather than silently
# truncating or continuing to unroll indefinitely.
MAX_RESPONSE_FIELD_DEPTH = 8


def render_response_field(f, indent, provider_display, depth=0, ancestor_names=()):
    # Real, found-in-review bug, fixed here rather than left in place:
    # every nested field's own description (and, as of this session,
    # the AI-inferred marker) used to be silently dropped -- the
    # original UBI-144 commit rendered the description line ONLY at
    # depth 0, never inside an <Expandable> block, with no comment
    # explaining why. The identical class of bug (nested descriptions
    # silently discarded below the top level) was already found and
    # fixed once this session's own arc, on the SDK codegen doc-comment
    # side -- recovering 6,613 fields there. Confirmed live for
    # Datadog specifically: ALL 437 of its real AI-inferred fields are
    # nested, zero are top-level -- the old `if not nested` gate would
    # have made the AI-inferred label never appear anywhere in this
    # provider's own real corpus, silently failing the founder's own
    # explicit requirement that it render visibly. Real content only,
    # nothing invented -- this just stops throwing away real data
    # already present in the schema dump.
    pad = " " * indent
    name = f["WireName"]
    t = f["Type"]
    ts = type_str(t)
    req_attr = " required" if f["Required"] else ""
    lines = [f'{pad}<ResponseField name="{name}" type="{ts}"{req_attr}>']
    lines.append(f"{pad}  {field_desc(f, provider_display)}{ai_inferred_marker(f, pad)}")
    if is_object_ish(t):
        inner = sorted(object_fields_of(t), key=lambda x: x["WireName"])
        if inner:
            if name in ancestor_names:
                lines.append(f'{pad}  <Expandable title="properties">')
                lines.append(
                    f'{pad}    <Note>`{name}` recurs here (its own type contains '
                    f"itself); see the `{name}` field's own properties above for "
                    f"the repeating pattern.</Note>"
                )
                lines.append(f"{pad}  </Expandable>")
            elif depth >= MAX_RESPONSE_FIELD_DEPTH:
                lines.append(f'{pad}  <Expandable title="properties">')
                lines.append(
                    f'{pad}    <Note>Nested `{name}` structure continues beyond '
                    f"{MAX_RESPONSE_FIELD_DEPTH} levels of depth; further "
                    f"properties omitted for readability.</Note>"
                )
                lines.append(f"{pad}  </Expandable>")
            else:
                lines.append(f'{pad}  <Expandable title="properties">')
                for inf in inner:
                    lines.append(
                        render_response_field(
                            inf, indent + 4, provider_display,
                            depth + 1, ancestor_names + (name,),
                        )
                    )
                lines.append(f"{pad}  </Expandable>")
    lines.append(f"{pad}</ResponseField>")
    return "\n".join(lines)


def pick_example_fields(fields):
    required = sorted([f for f in fields if f["Required"]], key=lambda f: f["WireName"])
    optional_pure = sorted(
        [f for f in fields if f["Optional"] and not f["Computed"] and not f["Required"]],
        key=lambda f: f["WireName"],
    )
    return required + optional_pure[:2]


# UBI-144 Phase 1: pick_example_fields (above) is the ORIGINAL mechanical-
# tier selection -- required fields plus the first 2 pure-optional ones,
# alphabetically. The ticket's own real complaint is that this shows only
# the bare minimum, never a representative slice of what a resource
# actually configures. pick_richer_example_fields replaces it: every
# required field, PLUS the field literally named "name" if the schema
# declares one (optional+computed in most real AWS resources, but the
# single most load-bearing field in almost any real example -- omitting
# it produced examples that don't even name the thing they create), PLUS
# every pure-optional field, capped at MAX_RICH_FIELDS total so a
# resource with dozens of optional fields (a real case elsewhere in the
# corpus) doesn't produce an unreadable wall of config. Field NAMES are
# 100% real, drawn only from the real schema passed in -- nothing here
# invents a field that doesn't exist.
MAX_RICH_FIELDS = 8

# SCHEMA_SOURCE_LABEL is the real, honest per-provider replacement for
# this file's own old, hardcoded "hashicorp/{schema_name}" text --
# every resource type across all six providers is now sourced through
# ubx-provider-dynamic (see sdk/providers/.ubx/config's own real
# schema_source per [dynamic_providers.<name>] entry), never a
# HashiCorp tfplugin provider, so a page that still said
# "hashicorp/datadog provider schema" would be actively false, not
# just stale. Keyed by the doc URL slug (the same `provider` string
# already threaded through every call site here), one real, accurate
# sentence fragment per provider's own real schema source.
SCHEMA_SOURCE_LABEL = {
    "aws": "the real AWS CloudFormation resource registry",
    "gcp": "real Google Discovery Documents",
    "azure": "the real Azure Resource Manager API specification",
    "kubernetes": "the real Kubernetes OpenAPI specification",
    "github": "the real GitHub REST API OpenAPI specification",
    "datadog": "the real Datadog OpenAPI specification",
}


def schema_source_label(provider):
    """The real, provider-specific schema-source sentence fragment for
    `provider` (a doc URL slug, e.g. "datadog") -- see
    SCHEMA_SOURCE_LABEL's own doc comment for why this replaced a
    hardcoded HashiCorp-provider assumption. Falls back to a real,
    honest, generic phrase (never re-introduces "hashicorp/...") for
    any provider not yet in the table, so a future seventh provider
    fails safe rather than silently lying about its source."""
    return SCHEMA_SOURCE_LABEL.get(provider, "its own real provider schema, via ubx-provider-dynamic")


def pick_richer_example_fields(fields):
    required = sorted([f for f in fields if f["Required"]], key=lambda f: f["WireName"])
    # A real, found-in-review bug: "name" is a real field on MANY
    # resources, but on some (aws_efs_file_system, a real, confirmed
    # example) it's PURE COMPUTED -- Optional=False, Computed=True,
    # derived automatically from the "Name" tag, never a real settable
    # field in the generated Config struct at all. Checking only
    # `WireName == "name"` (this function's own first version) included
    # it anyway, producing a real Go compile error ("unknown field Name
    # in struct literal"). f["Optional"] is the same real settability
    # check the rest of this file's own Input properties selection
    # already uses (eff_flags) -- applied here too now, not
    # independently re-derived a second, looser way.
    name_field = [f for f in fields if f["WireName"] == "name" and f["Optional"] and not f["Required"]]
    # A second real, found-in-review bug: when "name" is genuinely plain
    # optional (Optional=True, Required=False, Computed=False -- e.g.
    # aws_datasync_agent, aws_ivschat_logging_configuration), it satisfies
    # BOTH name_field's filter above AND this optional_pure filter, so it
    # was picked twice -- a real Go compile error ("duplicate field name
    # Name in struct literal"), caught only by the go build verification
    # pass, not gofmt. Excluded here since name_field already covers it.
    optional_pure = sorted(
        [f for f in fields if f["Optional"] and not f["Computed"] and not f["Required"] and f["WireName"] != "name"],
        key=lambda f: f["WireName"],
    )
    picked = required + name_field + optional_pure
    return picked[:MAX_RICH_FIELDS]


# UBI-144 Phase 1: richer, more realistic literal values for the SAME
# real field names pick_richer_example_fields selects -- name-pattern
# heuristics, each one a real, recurring convention across MANY resource
# types in the real schema corpus (never hardcoded to one specific
# resource), documented per-heuristic below. Falls through to the
# original literal_go/literal_ts/literal_py (unchanged) for anything
# these heuristics don't recognize.
def is_json_policy_field(wire):
    # Real, recurring AWS/STS convention: any field literally named
    # "assume_role_policy" is always a JSON-encoded IAM TRUST policy
    # document (has a real "Principal"/"sts:AssumeRole" shape) -- true
    # for aws_iam_role, aws_iam_openid_connect_provider-assuming roles,
    # and every other AWS resource with this exact, standard field
    # name, not unique to one resource.
    return wire == "assume_role_policy"


def is_generic_policy_field(wire):
    # A bare "policy" field (aws_iam_policy, aws_sqs_queue, aws_s3_bucket,
    # aws_kms_key, and many more) is a real, recurring AWS convention
    # too, but a DIFFERENT real JSON shape than a trust policy -- an
    # identity/access policy document (Statement/Effect/Action/Resource,
    # no "Principal", never "sts:AssumeRole"). Deliberately its own
    # heuristic, not folded into is_json_policy_field -- reusing the
    # trust-policy shape here would render real, but SEMANTICALLY WRONG
    # content (a policy document with an STS trust statement makes no
    # sense). "redrive_policy" and other "*_policy"-suffixed fields are
    # deliberately NOT matched here -- their own real JSON shape differs
    # again (e.g. redrive_policy is {deadLetterTargetArn,
    # maxReceiveCount}, already documented in the Input properties
    # section) and guessing wrong would be worse than the generic
    # placeholder fallback.
    return wire == "policy"


def is_arn_like_field(wire):
    # "permissions_boundary" is a real, recurring AWS IAM convention
    # (aws_iam_role/aws_iam_user/aws_iam_group all share it) whose own
    # wire name doesn't end in "_arn" but is always ARN-valued -- named
    # explicitly rather than folded into a looser substring match that
    # could false-positive on an unrelated field elsewhere in the corpus.
    return wire.endswith("_arn") or wire == "arn" or wire == "permissions_boundary"


def is_duration_field(wire):
    return "seconds" in wire or "duration" in wire


def is_path_field(wire):
    # Real AWS IAM convention: role/user/policy "path" is always a
    # slash-delimited namespace string, recurring across every IAM
    # resource type, not unique to aws_iam_role.
    return wire == "path"


def is_description_field(wire):
    return wire == "description"


def resolve_page_path(docs_root, provider, idents):
    """A resource's own real docs-identity path -- the existing .mdx page
    a splice-only generator (gen_complete_pages.py's Example splice,
    UBI-152's Input/Output properties splice) must locate and write back
    into. Shared here so both splice tools resolve the identical path,
    including the UBI-151 escape-undo (a resource whose real,
    wire-derived local name ends in "_test" carries a trailing "_" in
    its real Go filename -- a pure Go-build artifact, not part of the
    resource's own docs identity, undone here) -- extracted from
    gen_complete_pages.py's own generate_one so this logic lives in
    exactly one place, not two copies that could drift the next time a
    _test-suffixed resource is found.

    Returns (out_path, doc_service_dir, go_local, slug).
    """
    go_service_dir = idents["go"]["service_dir"]
    # A real, found-in-review case: a Go package name that collides with
    # a Go keyword/convention ("default", "main") gets a real trailing
    # underscore in the real generated package name/import path
    # (go["service_dir"] == "default_"/"main_") -- but the real docs
    # directory itself was never given that escape, it's just
    # "default"/"main". Stripped ONLY for the doc output path here;
    # go["service_dir"] itself (used for the real Go import path) is
    # untouched, still correctly carries the trailing underscore the
    # real import path needs.
    doc_service_dir = go_service_dir.rstrip("_") or go_service_dir
    go_local = os.path.splitext(os.path.basename(idents["go"]["file"]))[0]
    if go_local.endswith("_test_"):
        go_local = go_local[:-1]
    slug = go_local.replace("_", "-")
    out_path = os.path.join(docs_root, "resource-reference", provider, doc_service_dir, f"{slug}.mdx")
    return out_path, doc_service_dir, go_local, slug


# Real trust-policy preamble, one per language -- a real, valid JSON IAM
# trust policy, constructed (not a raw string literal) the same way the
# ALREADY-PUBLISHED role.mdx page does it today, generalized here to any
# assume_role_policy-shaped field rather than hand-authored once. Stored
# with NO leading indentation -- reindented to match each call site by
# the builder, below, since the same constant is spliced into three
# differently-indented contexts (Go/TS/Python).
TRUST_POLICY_PREAMBLE_GO = """trustPolicy, _ := json.Marshal(map[string]any{
	"Version": "2012-10-17",
	"Statement": []map[string]any{{
		"Effect":    "Allow",
		"Principal": map[string]string{"Service": "ec2.amazonaws.com"},
		"Action":    "sts:AssumeRole",
	}},
})"""
TRUST_POLICY_PREAMBLE_TS = """const trustPolicy = JSON.stringify({
  Version: "2012-10-17",
  Statement: [{
    Effect: "Allow",
    Principal: { Service: "ec2.amazonaws.com" },
    Action: "sts:AssumeRole",
  }],
});"""
TRUST_POLICY_PREAMBLE_PY = """trust_policy = json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ec2.amazonaws.com"},
        "Action": "sts:AssumeRole",
    }],
})"""

# Real access-policy preamble, one per language -- a real, valid IAM
# identity/access policy document (no Principal, no sts:AssumeRole --
# see is_generic_policy_field's own doc comment for why this is a
# DIFFERENT real shape than the trust policy above).
ACCESS_POLICY_PREAMBLE_GO = """accessPolicy, _ := json.Marshal(map[string]any{
	"Version": "2012-10-17",
	"Statement": []map[string]any{{
		"Effect":   "Allow",
		"Action":   "*",
		"Resource": "*",
	}},
})"""
ACCESS_POLICY_PREAMBLE_TS = """const accessPolicy = JSON.stringify({
  Version: "2012-10-17",
  Statement: [{
    Effect: "Allow",
    Action: "*",
    Resource: "*",
  }],
});"""
ACCESS_POLICY_PREAMBLE_PY = """access_policy = json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": "*",
        "Resource": "*",
    }],
})"""


def reindent(block, prefix):
    """Re-indents every line of block (a multi-line string with NO
    leading indentation of its own) by prefix, except the first line
    (already positioned by whatever f-string context it's spliced
    into)."""
    lines = block.split("\n")
    return ("\n" + prefix).join(lines)


def field_literal_with_preamble(f, lang):
    """Returns (preamble_or_None, value_expr) for f's own real value in
    lang ("go"/"ts"/"py") -- richer, name-pattern-driven heuristics for
    real, recurring AWS conventions, falling through to the existing
    mechanical literal_go/literal_ts/literal_py for anything else."""
    wire = f["WireName"]
    t = f["Type"]
    is_string = t["Kind"] == KIND_SCALAR and t["Scalar"] == SCALAR_STRING
    is_number = t["Kind"] == KIND_SCALAR and t["Scalar"] == SCALAR_NUMBER
    is_map = t["Kind"] == KIND_MAP

    if is_string and is_json_policy_field(wire):
        if lang == "go":
            return TRUST_POLICY_PREAMBLE_GO, "string(trustPolicy)"
        if lang == "ts":
            return TRUST_POLICY_PREAMBLE_TS, "trustPolicy"
        return TRUST_POLICY_PREAMBLE_PY, "trust_policy"
    if is_string and wire == "name":
        # The resource's own instance name (the literal "ci-runner"
        # second argument to resource()/ubx.Resource()) IS the real,
        # natural value for a "name" field specifically -- the original
        # literal_go/ts/py's own generic "example-name" fallback exists
        # for every OTHER "*_name"-suffixed field, where no such natural
        # value is available.
        return None, '"ci-runner"'
    if is_string and is_generic_policy_field(wire):
        if lang == "go":
            return ACCESS_POLICY_PREAMBLE_GO, "string(accessPolicy)"
        if lang == "ts":
            return ACCESS_POLICY_PREAMBLE_TS, "accessPolicy"
        return ACCESS_POLICY_PREAMBLE_PY, "access_policy"
    if is_string and is_description_field(wire):
        # Resource-neutral -- real, but never asserts a specific
        # NARRATIVE (a role vs. a queue vs. a bucket all get the same
        # honest, generic descriptor) that would only be true for one
        # resource family.
        return None, '"Managed by ubx."'
    if is_string and is_arn_like_field(wire):
        v = '"arn:aws:iam::123456789012:policy/ci"'
        return None, v
    if is_string and is_path_field(wire):
        return None, '"/ci/"'
    if is_number and is_duration_field(wire):
        return None, "7200"
    if is_map:
        if lang == "go":
            return None, 'map[string]string{"managed-by": "ubx"}'
        if lang == "ts":
            return None, '{ "managed-by": "ubx" }'
        return None, '{"managed-by": "ubx"}'

    fn = {"go": literal_go, "ts": literal_ts, "py": literal_py}[lang]
    return None, fn(f)


def pick_inner_example_field(inner_fields):
    if not inner_fields:
        return None
    by_name = {f["WireName"]: f for f in inner_fields}
    if "name" in by_name:
        return by_name["name"]
    req = sorted([f for f in inner_fields if f["Required"]], key=lambda f: f["WireName"])
    if req:
        return req[0]
    return sorted(inner_fields, key=lambda f: f["WireName"])[0]


def literal_go(f):
    t = f["Type"]
    wire = f["WireName"]
    if t["Kind"] == KIND_SCALAR:
        s = t["Scalar"]
        if s == SCALAR_STRING:
            if wire == "name" or wire.endswith("_name"):
                return f'"example-{wire.replace("_", "-")}"'
            return '"example"'
        if s == SCALAR_NUMBER:
            return "1"
        if s == SCALAR_BOOL:
            return "true"
        return '"example"'
    if t["Kind"] in (KIND_LIST, KIND_SET):
        el = t["Element"]
        if el["Kind"] == KIND_SCALAR and el["Scalar"] == SCALAR_STRING:
            return '[]string{"example"}'
        if el["Kind"] == KIND_OBJECT:
            inner = pick_inner_example_field(el["Object"])
            if inner is None:
                return "[]map[string]any{{}}"
            return f'[]map[string]any{{{{"{inner["WireName"]}": {literal_go(inner)}}}}}'
        return '[]string{"example"}'
    if t["Kind"] == KIND_MAP:
        el = t["Element"]
        if el["Kind"] == KIND_SCALAR and el["Scalar"] == SCALAR_STRING:
            return 'map[string]string{"key": "value"}'
        return 'map[string]any{"key": "value"}'
    if t["Kind"] == KIND_OBJECT:
        inner = pick_inner_example_field(t["Object"])
        if inner is None:
            return "map[string]any{}"
        return f'map[string]any{{"{inner["WireName"]}": {literal_go(inner)}}}'
    return '"example"'


def literal_ts(f):
    t = f["Type"]
    wire = f["WireName"]
    if t["Kind"] == KIND_SCALAR:
        s = t["Scalar"]
        if s == SCALAR_STRING:
            if wire == "name" or wire.endswith("_name"):
                return f'"example-{wire.replace("_", "-")}"'
            return '"example"'
        if s == SCALAR_NUMBER:
            return "1"
        if s == SCALAR_BOOL:
            return "true"
        return '"example"'
    if t["Kind"] in (KIND_LIST, KIND_SET):
        el = t["Element"]
        if el["Kind"] == KIND_SCALAR and el["Scalar"] == SCALAR_STRING:
            return '["example"]'
        if el["Kind"] == KIND_OBJECT:
            inner = pick_inner_example_field(el["Object"])
            if inner is None:
                return "[{}]"
            return f'[{{ {camel(inner["WireName"])}: {literal_ts(inner)} }}]'
        return '["example"]'
    if t["Kind"] == KIND_MAP:
        el = t["Element"]
        if el["Kind"] == KIND_SCALAR and el["Scalar"] == SCALAR_STRING:
            return '{ key: "value" }'
        return '{ key: "value" }'
    if t["Kind"] == KIND_OBJECT:
        inner = pick_inner_example_field(t["Object"])
        if inner is None:
            return "{}"
        return f'{{ {camel(inner["WireName"])}: {literal_ts(inner)} }}'
    return '"example"'


def literal_py(f):
    t = f["Type"]
    wire = f["WireName"]
    if t["Kind"] == KIND_SCALAR:
        s = t["Scalar"]
        if s == SCALAR_STRING:
            if wire == "name" or wire.endswith("_name"):
                return f'"example-{wire.replace("_", "-")}"'
            return '"example"'
        if s == SCALAR_NUMBER:
            return "1"
        if s == SCALAR_BOOL:
            return "True"
        return '"example"'
    if t["Kind"] in (KIND_LIST, KIND_SET):
        el = t["Element"]
        if el["Kind"] == KIND_SCALAR and el["Scalar"] == SCALAR_STRING:
            return '["example"]'
        if el["Kind"] == KIND_OBJECT:
            inner = pick_inner_example_field(el["Object"])
            if inner is None:
                return "[{}]"
            return f'[{{"{inner["WireName"]}": {literal_py(inner)}}}]'
        return '["example"]'
    if t["Kind"] == KIND_MAP:
        el = t["Element"]
        return '{"key": "value"}'
    if t["Kind"] == KIND_OBJECT:
        inner = pick_inner_example_field(t["Object"])
        if inner is None:
            return "{}"
        return f'{{"{inner["WireName"]}": {literal_py(inner)}}}'
    return '"example"'


def wrap_markdown(text, width=65):
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if len(cand) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return "\n".join(lines)


# UBI-144 Phase 2: a real, established multi-resource companion scenario
# exists in the docs corpus ONLY for a small, named set of resource
# families -- reused here, never invented for a family this session
# hasn't actually verified a real, already-published scenario for.
# Every wire type NOT in this dict falls back to
# render_generic_markdown_scenario (below), a real single-resource
# scenario built mechanically from the SAME example_fields driving the
# Go/TS/Python tabs, richer than the original one-line mechanical
# description but never asserting a resource relationship this session
# hasn't confirmed is real.
KNOWN_FAMILY_MARKDOWN = {
    "aws_iam_role": lambda name_val: (
        'Attach a policy allowing it to send messages to '
        '@payments.aws_sqs_queue.pipeline-events.'
    ),
}


def literal_for_markdown(f, val_go):
    """Renders f's own real example value for flowing prose -- strips
    the Go-literal quoting/braces val_go already carries (reusing the
    SAME value every language's own code block shows, not a fourth
    independent rendering), down to plain, readable text. A value that
    isn't a literal at all (a preamble-driven variable reference, e.g.
    "string(trustPolicy)" for a JSON-policy field) never leaks raw Go
    syntax into prose -- falls back to a real, honest, generic
    descriptor instead."""
    v = val_go
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1]
    if v in ("true", "false"):
        return v
    if v.startswith("map[") or v.startswith("[]") or v.startswith("{"):
        return "a set value"
    if v.replace(".", "", 1).lstrip("-").isdigit():
        return v
    return "a real, valid value"


def render_generic_markdown_scenario(wire, example_fields, go_values_by_name):
    """Real, generator-driven prose for the ONE resource this call
    builds -- mechanically substitutes the SAME field names/values
    already driving the Go/TS/Python tabs into a real sentence.
    Deliberately never asserts a companion resource or a relationship
    this session hasn't verified is real (see KNOWN_FAMILY_MARKDOWN's
    own doc comment) -- richer than the original one-line mechanical
    description, but honest about being single-resource where no real,
    established multi-resource scenario is known."""
    parts = []
    name_val = None
    for f in example_fields:
        wn = f["WireName"]
        rendered = literal_for_markdown(f, go_values_by_name[wn])
        phrase = wn.replace("_", " ")
        if wn == "name":
            name_val = rendered
            continue
        parts.append(f"{phrase} {rendered}")
    subject = f'{wire} called "{name_val}"' if name_val else wire
    sentence = f"Create {subject}, with " + ", ".join(parts) + "."
    return wrap_markdown(sentence)


def build_resource_page(wire, service, local, slug, fields, go, py, ts,
                         provider, schema_name, provider_display, go_module, ts_repo, ts_published,
                         py_pypi_root="ubx", bindings_status="published"):
    # bindings_status="local_only" is the real, honest state a brand-new
    # provider is in BEFORE its own ubx-sdk-<name>{,-go,-py,-ts} repos
    # exist at all (confirmed live for datadog/github: `gh repo view`
    # returns zero results for every one of the four, not just
    # "unpublished" -- there is no repo to `git clone` either, unlike
    # ts_published=0's own existing assumption). Every language's own
    # import block shows the real command that produces these exact
    # bindings locally instead of referencing a remote that doesn't
    # exist -- never a fabricated go-gettable/pip-installable path.
    # "published" (the default) reproduces every existing provider's
    # already-shipped page byte-for-byte, unchanged.
    example_fields = pick_example_fields(fields)
    empty = len(example_fields) == 0
    local_only = bindings_status == "local_only"

    go_field_lines = "\n".join(
        f"        {pascal(f['WireName'])}: {literal_go(f)}," for f in example_fields
    )
    go_import_path = f'{go_module}/{schema_name}/{go["service_dir"]}'
    # Real, found-in-review bug: this block calls ubx.Resource(...)
    # below but, before this fix, never imported the ubx runtime
    # package at all ("github.com/ubiquex/ubx-sdk-go/runtime", the
    # SAME import the richer tier's own go_lines already includes) --
    # confirmed live via a real `go build` against this exact block for
    # Datadog ("undefined: ubx"), the first time this tier's own Go
    # example was ever actually compiled rather than just gofmt-checked
    # (every real page currently in the corpus is already on the
    # richer tier, which never had this gap -- this tier's own bare
    # fragment had gone unexercised by a real build until this session).
    go_import = f'import (\n        ubx "github.com/ubiquex/ubx-sdk-go/runtime"\n        "{go_import_path}"\n    )'
    if local_only:
        # A relative import ("./local-sdk/...") is NOT legal Go under
        # module mode -- real, found-in-review correctness bug, caught
        # before this ever reached a real page: the first draft of this
        # branch generated exactly that, which would fail to compile if
        # copy-pasted. The real, correct pattern for "generated locally,
        # not yet published" is a go.mod `replace` directive -- the
        # SAME mechanism this directory's own verify_go_blocks.py
        # already uses to build every example against a local checkout
        # -- pointing the real, eventual module path (go_module) at the
        # real, local output `ubx sdk gen` actually writes.
        go_gen_cmd = f"ubx sdk gen --only {schema_name} --lang go --out ./local-sdk"
        go_replace = f"go.mod: replace {go_module} => ./local-sdk/{schema_name}/sdk/go"
        go_preamble = f"    // {go_gen_cmd}\n    // {go_replace}\n"
    else:
        go_preamble = ""
    if empty:
        go_block = f"""    ```go
{go_preamble}    {go_import}

    cfg := {go["package"]}.{go["config"]}{{}}
    ubx.Resource({go["package"]}.{go["binding"]}, "example", cfg)
    ```"""
    else:
        go_block = f"""    ```go
{go_preamble}    {go_import}

    cfg := {go["package"]}.{go["config"]}{{
{go_field_lines}
    }}
    ubx.Resource({go["package"]}.{go["binding"]}, "example", cfg)
    ```"""

    # Real, found-in-review gap: this tier's own ts_block, unlike the
    # richer tier's (which routes through the real deno_fmt_lines
    # binary check + fence()), was hand-assembled with a guessed
    # import-wrap-at-68-chars heuristic and never actually verified
    # against `deno fmt` -- confirmed live for Datadog: every one of
    # its 20 real ts blocks failed a real `deno fmt --check` (canonical
    # deno style wraps a long import as `import {\n  X,\n} from "...";`,
    # never `import { X } from\n  "...";`). Fixed the same way the
    # richer tier already proves its own TS is real, canonically
    # formatted, not just syntactically plausible: build the RAW lines,
    # run them through the real `deno fmt` binary, use its own output.
    ts_field_lines = [f"  {camel(f['WireName'])}: {literal_ts(f)}," for f in example_fields]
    ts_comment_lines = []
    if local_only:
        ts_gen_cmd = f"ubx sdk gen --only {schema_name} --lang ts --out ./local-sdk"
        ts_import_path = f'./local-sdk/{schema_name}/sdk/typescript/{ts["file"]}'
        ts_comment_lines = [f"// {ts_gen_cmd}"]
    elif ts_published:
        ts_import_path = f'jsr:@ubx/sdk-{schema_name}/{schema_name}/{ts["service_dir"]}/{os.path.splitext(os.path.basename(ts["file"]))[0]}'
    else:
        ts_import_path = f'./{ts_repo}/{ts["file"]}'
        ts_comment_lines = [f"// git clone https://github.com/Ubiquex/{ts_repo}.git"]
    ts_lines = ts_comment_lines + [f'import {{ {ts["binding"]} }} from "{ts_import_path}";', ""]
    if empty:
        ts_lines.append(f'resource({ts["binding"]}, "example", {{}});')
    else:
        ts_lines.append(f'resource({ts["binding"]}, "example", {{')
        ts_lines.extend(ts_field_lines)
        ts_lines.append("});")
    ts_block = fence("typescript", deno_fmt_lines(ts_lines))

    py_field_lines = "\n".join(
        f"        {f['WireName']}={literal_py(f)}," for f in example_fields
    )
    py_module_root = py["module"].rsplit(".", 1)[0]
    py_import_line = f'from {py_module_root} import {py["binding"]}, {py["config"]}'
    if len(py_import_line) > 65:
        py_import = (
            f'from {py_module_root} import (\n'
            f'        {py["binding"]},\n'
            f'        {py["config"]},\n'
            f'    )'
        )
    else:
        py_import = py_import_line
    py_preamble = ""
    if local_only:
        py_gen_cmd = f"ubx sdk gen --only {schema_name} --lang py --out ./local-sdk"
        py_preamble = f"    # {py_gen_cmd}\n    # export PYTHONPATH=./local-sdk/{schema_name}/sdk/python:$PYTHONPATH\n"
    if empty:
        py_block = f"""    ```python
{py_preamble}    {py_import}

    cfg = {py["config"]}()
    ubx.resource({py["binding"]}, "example", cfg)
    ```"""
    else:
        py_block = f"""    ```python
{py_preamble}    {py_import}

    cfg = {py["config"]}(
{py_field_lines}
    )
    ubx.resource({py["binding"]}, "example", cfg)
    ```"""

    if empty:
        md_text = wrap_markdown(f"Provision {wire}, no illustrative fields.")
    else:
        md_fields = ", ".join(f["WireName"] for f in example_fields)
        md_text = wrap_markdown(f"Provision {wire} with {md_fields}.")
    md_block = f"""    ```
    {md_text}
    ```"""

    input_fields = sorted(
        [f for f in fields if f["Required"] or eff_flags(f)[1]], key=lambda f: f["WireName"]
    )
    output_fields = sorted(
        [f for f in fields if eff_flags(f)[2]], key=lambda f: f["WireName"]
    )

    input_block = "\n\n".join(render_response_field(f, 0, provider_display) for f in input_fields)
    output_block = "\n\n".join(render_response_field(f, 0, provider_display) for f in output_fields)

    page = f"""---
title: "{wire}"
description: "Real, generated bindings for `{wire}`."
---

`{wire}` -- real, typed bindings generated directly from
{schema_source_label(provider)}, in every SDK language.

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
  <Tab title="Markdown">
{md_block}
  </Tab>
</Tabs>

## Input properties

{input_block}

## Output properties

{output_block}
"""
    return page


# UBI-144 Phase 1: build_resource_page_complete is the NEW template --
# complete, runnable programs (real package main/func main, real
# stack()/export default wrapper, real if __name__ == "__main__":),
# a richer real field slice (pick_richer_example_fields), and a real,
# multi-resource markdown scenario, instead of build_resource_page's own
# bare, context-free fragments. Deliberately a SEPARATE function, not a
# rewrite of build_resource_page in place -- this is a one-resource
# proof, per the ticket's own explicit phasing requirement, the
# mechanical-tier function stays untouched and still generates the other
# 4648 pages exactly as before until a wider rollout is separately
# approved.
def gofmt_lines(code_lines):
    """Runs a real Go code block through the real `gofmt` binary --
    canonical import ordering, struct-literal field alignment, real
    verification that the block is genuinely valid Go, not just
    visually plausible -- rather than hand-rolling alignment logic that
    would only ever approximate what gofmt itself guarantees exactly."""
    import subprocess
    src = "\n".join(code_lines)
    result = subprocess.run(["gofmt"], input=src, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gofmt rejected generated Go source:\n{result.stderr}\n--- source ---\n{src}")
    return result.stdout.rstrip("\n").split("\n")


def deno_fmt_lines(code_lines):
    """Runs a real TypeScript code block through the real `deno fmt`
    binary (stdin/stdout mode, --ext ts) -- the same real-tool-verifies-
    itself discipline gofmt_lines applies to Go, real confirmation the
    block is genuinely valid, canonically-formatted TypeScript."""
    import subprocess
    src = "\n".join(code_lines)
    result = subprocess.run(
        ["deno", "fmt", "--ext", "ts", "-"], input=src, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"deno fmt rejected generated TS source:\n{result.stderr}\n--- source ---\n{src}")
    return result.stdout.rstrip("\n").split("\n")


def fence(lang, code_lines):
    """Wraps already-correctly-indented CODE lines (no outer MDX indent)
    in a fenced code block, at the 4-space indent every <Tab> body in
    this generator's own output already uses. Some entries in
    code_lines carry embedded "\\n" (a multi-line preamble spliced in as
    one string) -- split those out FIRST so the 4-space MDX prefix
    lands on every real line, not just the first line of each entry."""
    flat = []
    for entry in code_lines:
        flat.extend(entry.split("\n"))
    body = "\n".join("    " + line if line else "" for line in flat)
    return f"    ```{lang}\n{body}\n    ```"


# A real, found-in-review bug (caught auditing GCP ahead of Azure):
# the real, published combined SDK repo's own identity (UBI-138 --
# "ubx-sdk-<X>", one repo per provider, all three languages) is a
# THIRD real concern, independent of both `provider` (the docs URL
# slug -- "gcp", not "google") and `schema_name` (the internal
# path segment inside the repo -- "azurerm", not "azure", for Azure
# specifically). All three happen to collide into the same string for
# aws/google/kubernetes, which is exactly what let this go unnoticed:
# `build_resource_page_complete` hardcoded the Go import's own repo
# name to the literal "aws" for every provider, and separately reused
# `schema_name` for the TS/JSR package name too (correct only by the
# same coincidence). Real, confirmed values, not inferred:
# aws->ubx-sdk-aws/@ubx/sdk-aws, google->ubx-sdk-google/@ubx/sdk-google,
# azure->ubx-sdk-azure/@ubx/sdk-azure,
# kubernetes->ubx-sdk-kubernetes/@ubx/sdk-kubernetes -- passed in
# explicitly as `sdk_repo_id`, never reconstructed from schema_name.
def build_resource_page_complete(wire, service, local, slug, fields, go, py, ts,
                                  provider, schema_name, provider_display,
                                  stack_name, intent_summary, companion_markdown,
                                  sdk_repo_id):
    example_fields = pick_richer_example_fields(fields)

    # --- Go: real, complete program ---
    go_preambles, go_assigns = [], []
    for f in example_fields:
        pre, val = field_literal_with_preamble(f, "go")
        if pre and pre not in go_preambles:
            go_preambles.append(pre)
        go_assigns.append(f"\t\t\t{pascal(f['WireName'])}: {val},")
    go_pkg_import_path = f'github.com/ubiquex/ubx-sdk-{sdk_repo_id}/sdk/go/{schema_name}/{go["service_dir"]}'
    # "json.Marshal(" (not just a "trustPolicy"-prefix check, which
    # missed the SECOND real preamble that also needs this import,
    # accessPolicy -- a real bug this batch's own verification pass
    # caught) -- matches every preamble that actually calls into
    # encoding/json, present or future, not just the one this session
    # happened to write first.
    needs_json = any("json.Marshal(" in p for p in go_preambles)

    go_lines = ["package main", ""]
    go_lines.append("import (")
    if needs_json:
        go_lines.append('\t"encoding/json"')
        go_lines.append("")
    go_lines.append('\tubx "github.com/ubiquex/ubx-sdk-go/runtime"')
    go_lines.append(f'\t{go["package"]} "{go_pkg_import_path}"')
    go_lines.append(")")
    go_lines.append("")
    go_lines.append("func main() {")
    go_lines.append(f'\tubx.Main(ubx.Stack({json.dumps(stack_name)}, func() {{')
    go_lines.append(f'\t\tubx.Intent(ubx.IntentInfo{{Summary: {json.dumps(intent_summary)}}})')
    for pre in go_preambles:
        go_lines.append("")
        go_lines.append("\t\t" + reindent(pre, "\t\t"))
    go_lines.append("")
    go_lines.append(f'\t\tubx.Resource({go["package"]}.{go["binding"]}, "ci-runner", {go["package"]}.{go["config"]}{{')
    go_lines.extend(go_assigns)
    go_lines.append("\t\t})")
    go_lines.append("\t}))")
    go_lines.append("}")
    go_block = fence("go", gofmt_lines(go_lines))

    # --- TypeScript: real, complete program ---
    ts_preambles, ts_assigns = [], []
    for f in example_fields:
        pre, val = field_literal_with_preamble(f, "ts")
        if pre and pre not in ts_preambles:
            ts_preambles.append(pre)
        ts_assigns.append(f"    {camel(f['WireName'])}: {val},")
    ts_import_path = f'jsr:@ubx/sdk-{sdk_repo_id}/{schema_name}/{ts["service_dir"]}/{os.path.splitext(os.path.basename(ts["file"]))[0]}'

    ts_lines = [
        'import { intent, resource, stack } from "@ubx/sdk";',
        f'import {{ {ts["binding"]} }} from "{ts_import_path}";',
        "",
        f'export default stack({json.dumps(stack_name)}, () => {{',
        f'  intent({{ summary: {json.dumps(intent_summary)} }});',
    ]
    for pre in ts_preambles:
        ts_lines.append("")
        ts_lines.append("  " + reindent(pre, "  "))
    ts_lines.append("")
    ts_lines.append(f'  resource({ts["binding"]}, "ci-runner", {{')
    ts_lines.extend(ts_assigns)
    ts_lines.append("  });")
    ts_lines.append("});")
    ts_block = fence("typescript", deno_fmt_lines(ts_lines))

    # --- Python: real, complete program ---
    py_preambles, py_assigns = [], []
    for f in example_fields:
        pre, val = field_literal_with_preamble(f, "py")
        if pre and pre not in py_preambles:
            py_preambles.append(pre)
        py_assigns.append(f"        {f['WireName']}={val},")
    py_module_root = py["module"].rsplit(".", 1)[0]
    needs_json_py = any("json.dumps(" in p for p in py_preambles)

    py_lines = []
    if needs_json_py:
        py_lines.append("import json")
    py_lines.append("import ubx_sdk as ubx")
    py_lines.append(f'from {py_module_root} import {py["binding"]}, {py["config"]}')
    py_lines.append("")
    py_lines.append("def describe():")
    py_lines.append(f'    ubx.intent({json.dumps(intent_summary)})')
    for pre in py_preambles:
        py_lines.append("")
        py_lines.append("    " + reindent(pre, "    "))
    py_lines.append("")
    py_lines.append(f'    ubx.resource({py["binding"]}, "ci-runner", {py["config"]}(')
    py_lines.extend(py_assigns)
    py_lines.append("    ))")
    py_lines.append("")
    py_lines.append('if __name__ == "__main__":')
    py_lines.append(f'    ubx.run({json.dumps(stack_name)}, describe)')
    py_block = fence("python", py_lines)

    md_block = fence("", companion_markdown.split("\n"))

    example_section = f"""## Example

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
  <Tab title="Markdown">
{md_block}
  </Tab>
</Tabs>
"""

    input_fields = sorted(
        [f for f in fields if f["Required"] or eff_flags(f)[1]], key=lambda f: f["WireName"]
    )
    output_fields = sorted(
        [f for f in fields if eff_flags(f)[2]], key=lambda f: f["WireName"]
    )
    input_block = "\n\n".join(render_response_field(f, 0, provider_display) for f in input_fields)
    output_block = "\n\n".join(render_response_field(f, 0, provider_display) for f in output_fields)

    page = f"""---
title: "{wire}"
description: "A complete, runnable {wire} program, in every SDK language."
---

`{wire}` -- real, typed bindings generated directly from
{schema_source_label(provider)}, in every SDK language.
Every tab below is a complete, runnable program, not a fragment, real
enough to save and run exactly as shown.

{example_section}
## Input properties

{input_block}

## Output properties

{output_block}
"""
    return page, example_section


def generate_mechanical_provider(docs_root, scratch_dir, provider, schema_name, provider_display,
                                  go_module, ts_repo, ts_published, schema_path, idents_path,
                                  bindings_status="published"):
    """Full-provider, mechanical-tier generation -- the ORIGINAL AWS/GCP/
    Azure/Kubernetes corpus generator, called from gen_mechanical_pages.py.
    docs_root/scratch_dir are real, caller-supplied paths (never hardcoded
    here) -- UBI-144 Phase 2's own finding: a hardcoded DOCS_ROOT pointing
    at the wrong, disconnected directory is exactly the kind of bug this
    file being real, reviewable, tracked tooling is meant to prevent."""
    schema = json.load(open(schema_path))
    idents = json.load(open(idents_path))

    out_root = os.path.join(docs_root, "resource-reference", provider)
    os.makedirs(out_root, exist_ok=True)

    by_service = {}
    for wire, rec in schema.items():
        service = rec["service"]
        local = rec["localName"]
        by_service.setdefault(service, []).append((wire, local, rec["ir"]["Fields"]))

    nav_groups = []
    card_entries = []

    for service in sorted(by_service.keys()):
        items = sorted(by_service[service], key=lambda x: x[1].replace("_", "-"))
        service_dir = os.path.join(out_root, service)
        os.makedirs(service_dir, exist_ok=True)
        slugs = []
        for wire, local, fields in items:
            slug = local.replace("_", "-")
            slugs.append(slug)
            go = idents[wire]["go"]
            py = idents[wire]["py"]
            ts = idents[wire]["ts"]
            page = build_resource_page(
                wire, service, local, slug, fields, go, py, ts,
                provider, schema_name, provider_display, go_module, ts_repo, ts_published,
                bindings_status=bindings_status,
            )
            with open(os.path.join(service_dir, f"{slug}.mdx"), "w") as fh:
                fh.write(page)

        title = service.title()
        first_page = f"resource-reference/{provider}/{service}/{slugs[0]}"
        # A resource whose own wire-derived local name is literally "index"
        # (real, confirmed: google_firestore_index, and AWS's own live
        # corpus has the identical unresolved collision for
        # aws_resourceexplorer2_index/aws_s3vectors_index/aws_kendra_index)
        # writes to the exact same path a service-level CardGroup landing
        # page would use. Skip the landing page for that one service
        # rather than silently clobbering the real resource page with it --
        # the landing page is optional/orphaned from nav either way (see
        # AWS precedent), the resource page is not.
        index_collision = "index" in slugs

        if len(items) > 1 and not index_collision:
            card_body = f"""---
title: "{title}"
description: "{provider_display} {title} resource types."
---

<CardGroup cols={{2}}>
"""
            for (wire, local, _), slug in zip(items, slugs):
                card_title = local.replace("_", " ").title()
                card_body += f'  <Card title="{card_title}" href="/resource-reference/{provider}/{service}/{slug}">\n    {wire}\n  </Card>\n'
            card_body += "</CardGroup>\n"
            with open(os.path.join(service_dir, "index.mdx"), "w") as fh:
                fh.write(card_body)
        if len(items) > 1:
            pages = [f"resource-reference/{provider}/{service}/{s}" for s in slugs]
            nav_groups.append({
                "group": title, "root": first_page, "expanded": False, "pages": pages,
            })
        else:
            nav_groups.append({
                "group": title, "root": first_page, "expanded": False, "pages": [first_page],
            })

        card_entries.append((title, service, slugs[0], len(items)))

    # top-level provider index.mdx
    idx = f"""---
title: "{provider_display}"
description: "{provider_display} resource types, grouped by real service."
---

{provider_display} covers {len(schema)} resource types (as of the
version this reference was generated from), sourced directly from
{schema_source_label(provider)} via ubx-provider-dynamic, grouped here
the same way the real generated bindings are, mechanically by
`{provider_display}` service boundary (see each generated repo's own
`ServiceAndLocalName`). Every page's field list is parsed directly from
the real provider schema, not hand-authored.

<CardGroup cols={{2}}>
"""
    for title, service, first_slug, count in card_entries:
        noun = "resource type" if count == 1 else "resource types"
        idx += f'  <Card title="{title}" icon="cube" href="/resource-reference/{provider}/{service}/{first_slug}">\n    {count} {noun} documented\n  </Card>\n'
    idx += "</CardGroup>\n"
    with open(os.path.join(out_root, "index.mdx"), "w") as fh:
        fh.write(idx)

    nav_fragment = {
        "group": provider_display,
        "root": f"resource-reference/{provider}/index",
        "pages": nav_groups,
    }
    json.dump(nav_fragment, open(os.path.join(scratch_dir, f"{provider}_nav_fragment.json"), "w"), indent=2)
    print(f"generated {len(schema)} resource pages across {len(by_service)} services for {provider}")
    return len(schema), len(by_service)
