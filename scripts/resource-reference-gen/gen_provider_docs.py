#!/usr/bin/env python3
"""Shared library for resource-reference/<provider> page generation --
never run directly (no __main__ block, on purpose: this file is real,
tracked tooling shared by three real entry points: gen_new_provider_pages.py
(full-provider, a brand-new provider with no existing pages at all),
regen_pages.py (one real family at a time, looping generate_richer_provider
once per [dynamic_providers.<family>] entry -- the call shape that made the
scope-leak bugs below real and live, not hypothetical), and
gen_complete_pages.py (touch up one resource or a real batch at a time
on an ALREADY-GENERATED provider, splicing ONLY the Example section --
never used to onboard a new provider) -- all driven from a real
schema dump (see README.md's own "Regenerating schema/idents data"
section) + real identifier extraction (extract_idents.py's own output,
a real scan of the already-published SDK bindings repos, or a real
local `ubx sdk gen` output for a provider with none published yet).

build_resource_page_complete is the ONLY real page-building function
in this file -- complete, runnable programs (real package main/func
main, real stack()/export default wrapper, real
if __name__ == "__main__":), a richer real field slice, a real markdown
scenario. Its own former sibling, build_resource_page (a bare fragment,
2 example fields, no package/func wrapper -- the ORIGINAL AWS/GCP/
Azure/Kubernetes corpus generator, and the shape this session generated
Datadog's own first, WRONG pass in), is removed entirely: a real `go
build` against its own literal output failed outright, and a resource
whose example can't compile as shown must never be selectable as final
output again, the founder's own explicit instruction. Every real,
currently-live page across all six providers is on the complete tier.

Scope discipline (added after three real incidents -- see this
function's own doc comment and rebuild_provider_index's below): a
third real entry point, regen_pages.py, calls generate_richer_provider
ONCE PER real [dynamic_providers.<family>] entry, one real family's own
resources at a time. generate_richer_provider's own schema argument is
therefore, structurally, always ONE family's slice -- never the whole
provider corpus -- even on a run whose families_file happens to list
every family. It must never derive a SHARED, cross-family file (the
provider-level index.mdx, a per-service index.mdx) from that slice
alone: doing so silently discards every other family's own already-
published card entries, keeping only whichever family a given call
happened to process. rebuild_provider_index exists for exactly this
reason -- ground truth is the real, current file tree, not any one
call's own partial schema.
"""
import glob, json, os

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
# same requirement.
#
# A real, found-in-review regression in this marker's own first
# version: a full three-line explanation repeated on EVERY real
# AI-inferred field. A page with dozens of inferred fields (a real,
# confirmed case, not hypothetical) drowned its own real content in
# identical boilerplate -- the founder's own direct correction. Fixed
# to a short, inline suffix on the description line itself, bold for
# visual distinction (guaranteed to render distinctly in any Mintlify
# page, no custom component needed) but genuinely NOT a paragraph.
#
# A second real, found-in-review regression (UBI-175 Phase 6, live-
# confirmed on docs.ubiquex.io): this inline marker's own first version
# ALSO kept a once-per-page <Note> callout repeating the same
# explanation a second time, immediately before "## Input properties"
# -- the inline marker was meant to REPLACE that callout, not run
# alongside it. Removed; the inline marker alone is the real, visible
# integrity label now.
def ai_inferred_marker(f):
    if f.get("DescriptionSource") != "ai-inferred":
        return ""
    return " **(AI-inferred)**"


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
    lines.append(f"{pad}  {field_desc(f, provider_display)}{ai_inferred_marker(f)}")
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


# UBI-144 Phase 1: the mechanical tier's own original field selection
# (required fields plus the first 2 pure-optional ones, alphabetically)
# is gone -- removed along with build_resource_page itself (see git
# history; a bare fragment must never be selectable as final output
# again, the founder's own explicit instruction). The ticket's own real
# complaint was that selection showed only the bare minimum, never a
# representative slice of what a resource actually configures.
# pick_richer_example_fields replaces it: every
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


def yaml_dq_escape(s):
    """Escapes a real string for use inside a double-quoted YAML scalar
    (frontmatter's own `description: "..."` shape) -- backslash first,
    then double-quote, in that order, so an already-escaped quote never
    gets re-escaped. Backticks and colons need no escaping inside a
    double-quoted YAML string, which is exactly why this codebase's own
    frontmatter already uses double quotes rather than plain scalars."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


# UBI-175 Phase 6: the real fix for the "three-line AI boilerplate"
# defect (STATE.md's own name for it) -- every page's own opening
# paragraph was, until this function existed, a single hardcoded
# template (see build_resource_page_complete's own fallback branch,
# below) identical across every resource of a provider except for the
# wire name and a provider-level schema-source label substituted in.
# Zero real, resource-specific content ever appeared there, regardless
# of how much real analysis went into that resource's own
# artifacts/<provider>/intros.json entry. This turns a full, real intro
# paragraph (already reviewed, hand-verified, per-resource prose -- see
# ubiquex-docs' own artifacts/<provider>/intros.json) into a short,
# real frontmatter description: the intro's own first sentence,
# verbatim, capped at 155 characters if that sentence alone runs longer
# than that. Truncation prefers the last real clause boundary (a comma)
# still inside the limit -- a bare word-boundary cut alone produced
# real, found-in-review awkward output ("...and more, that..." for
# aws_launch_template, stopping mid-clause on a dangling conjunction) --
# falling back to a word boundary only when no comma exists in range. A
# real intro missing entirely for a given wire (not yet written, or
# genuinely excluded) returns None -- the caller's own fallback to
# today's generic paragraph is what happens next, not a fabricated
# substitute invented here.
#
# Second real, found-in-review bug (GitHub regeneration): this corpus's
# intros lean heavily on "X, real Y" appositives ("tracks the real,
# asynchronous process..."), and this style's own first comma often sits
# right after a bare low-content word ("real", "the", "a", "own", "one",
# ...) with nothing else before it -- `rfind` picked exactly that comma,
# producing a dangling "...the real..." fragment. Now walks every comma
# in range and keeps the rightmost one NOT immediately preceded by a
# low-content word; the same check also applies to the word-boundary
# fallback (which itself can land on a bare stopword purely from where
# the hard 152-char cutoff happens to fall).
_FRONTMATTER_TRUNCATION_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "real", "own", "same",
    "one", "this", "that", "its", "has", "have", "only", "not", "it",
}


# Real, found-in-review defect: naive intro_text.split(". ", 1) treated
# "e.g. "/"i.e. "/"etc. " as a sentence boundary (a real ". " substring
# occurs inside each), truncating the frontmatter subtitle mid-
# parenthetical on 175 real Phase C intros (93 GCP, 82 Azure) that use
# one of these abbreviations -- e.g. google_apigee_datastore's own
# intro cut to '...target (e.g.' with the rest of the sentence orphaned
# into the body. _sentence_split below is abbreviation-aware so these
# don't get treated as sentence ends.
_ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.")


def _sentence_split(text):
    """Returns (first_sentence, rest) split at the first real ". "
    sentence boundary -- one NOT immediately preceded by a known
    abbreviation (see _ABBREVIATIONS)."""
    search_from = 0
    while True:
        pos = text.find(". ", search_from)
        if pos == -1:
            return text, ""
        preceding = text[:pos + 1]
        if any(preceding.endswith(abbr) for abbr in _ABBREVIATIONS):
            search_from = pos + 1
            continue
        return text[:pos], text[pos + 2:]


def frontmatter_description_from_intro(intro_text):
    first, _ = _sentence_split(intro_text)
    first = first.strip()
    if not first.endswith((".", "!", "?")):
        first += "."
    if len(first) > 155:
        window = first[:152]
        comma_cut = -1
        search_from = 0
        while True:
            pos = window.find(", ", search_from)
            if pos == -1:
                break
            preceding = window[:pos].rsplit(None, 1)
            preceding_word = preceding[-1].strip(",;:'").lower() if preceding else ""
            if preceding_word not in _FRONTMATTER_TRUNCATION_STOPWORDS:
                comma_cut = pos
            search_from = pos + 1
        if comma_cut > 40:  # a real clause boundary, not a near-immediate one
            body = first[:comma_cut]
        else:
            words = window.split(" ")
            words.pop()  # the hard char cutoff likely split this one mid-word
            while len(words) > 1 and words[-1].strip(",;:'").lower() in _FRONTMATTER_TRUNCATION_STOPWORDS:
                words.pop()
            body = " ".join(words).rstrip(",;:")
        first = body.rstrip().rstrip("-").rstrip() + "..."
    return first


# UBI-175 Phase 6, found-in-review defect (real, live-confirmed on
# docs.ubiquex.io's own datadog_monitor page): fm_description is
# derived from intro_text's own first sentence, and body used to
# render intro_text in full, unchanged -- whenever the first sentence
# fits under frontmatter_description_from_intro's 155-char cap
# untouched (the common case), fm_description ends up an exact,
# complete copy of that sentence, which then rendered a SECOND time as
# body's own opening line. Mintlify renders frontmatter `description`
# as a visible subtitle directly under the page title, so a reader saw
# the identical sentence twice, back to back, not a subtle SEO-only
# overlap. Strips that same, exact, matching prefix from the body so
# the subtitle and body cover distinct text.
#
# Two cases intentionally left unstripped, both real: a TRUNCATED
# fm_description (ends in "...") is a partial teaser, never a literal
# substring of intro_text at that position (the "..." isn't in the
# source text), so there's nothing to strip and no duplication to fix.
# And a single-sentence intro_text (rare but real) would have nothing
# left after stripping its own entire content -- kept whole rather than
# reduced to an empty body.
def intro_and_description(intro_text):
    fm_description = frontmatter_description_from_intro(intro_text)
    exact_prefix_match = intro_text.startswith(fm_description)
    if exact_prefix_match and len(intro_text) > len(fm_description):
        body_intro = intro_text[len(fm_description):].lstrip()
    elif exact_prefix_match:
        # UBI-175 Phase 6, found-in-review edge case (live-confirmed:
        # google_compute_target_https_proxy and 24 others, 25/1983
        # intros corpus-wide): a genuinely single-sentence intro_text
        # under the 155-char cap means fm_description IS the entire
        # intro, verbatim -- there is no "rest of the sentence" left to
        # show as a distinct body paragraph, so showing it a second
        # time would be the exact same literal-duplicate bug this
        # function exists to fix, not a smaller version of it. Empty
        # body_intro tells the caller to render no body paragraph at
        # all for this resource, relying on the frontmatter subtitle
        # alone.
        body_intro = ""
    else:
        body_intro = intro_text
    return fm_description, body_intro


def real_intro_for(provider, wire, intros_by_provider):
    """Looks up wire's own real intro in intros_by_provider (a real,
    already-loaded {provider: {wire: text}} map -- callers load
    artifacts/<provider>/intros.json themselves rather than this
    function reaching into the filesystem, so a golden-page generator
    and a future full-provider regeneration can share one real,
    in-memory lookup instead of re-reading the same file per resource).
    Returns None (not an empty string) when this provider has no real
    intros loaded, or this specific wire has no real entry yet -- the
    caller's own fallback path, not a fabricated placeholder here.

    UBI-175 Step 2, found-in-review: 4 of AWS's own pre-existing
    hand-authored intros (aws_vpc, aws_ecr_repository, aws_iam_policy,
    aws_iam_role) carry literal embedded newlines from an earlier
    session's hard-wrapped authoring -- frontmatter_description_from_
    intro's own `first.strip()` only trims the ends, so those newlines
    survived straight into the YAML frontmatter `description: "..."`
    value and broke it across multiple malformed lines (caught by
    verify_regen_corpus.py's real frontmatter check, not assumed fine).
    Collapsing whitespace once here, at the single real chokepoint
    every intro passes through before either frontmatter or body
    rendering, fixes both call sites at once rather than patching each
    downstream user of this text separately."""
    text = (intros_by_provider.get(provider) or {}).get(wire)
    return " ".join(text.split()) if text else text


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
        # The resource's own instance name (the literal "example"
        # second argument to resource()/ubx.Resource()) IS the real,
        # natural value for a "name" field specifically -- the original
        # literal_go/ts/py's own generic "example-name" fallback exists
        # for every OTHER "*_name"-suffixed field, where no such natural
        # value is available.
        return None, '"example"'
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
        v = '"arn:aws:iam::123456789012:policy/example"'
        return None, v
    if is_string and is_path_field(wire):
        return None, '"/example/"'
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
        '@example.aws_sqs_queue.pipeline-events.'
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


# UBI-144 Phase 1: build_resource_page_complete is the ONLY real page-
# building function left in this file -- complete, runnable programs
# (real package main/func main, real stack()/export default wrapper,
# real if __name__ == "__main__":), a richer real field slice
# (pick_richer_example_fields), and a real, multi-resource markdown
# scenario. Its own former sibling, build_resource_page (the ORIGINAL
# mechanical tier -- bare, context-free fragments, no package/func
# wrapper at all), is REMOVED entirely, not just unused: a real `go
# build` against its own output failed outright ("expected 'package',
# found 'import'"), and a resource whose example can't even compile as
# shown must never be selectable as final output again. Every real,
# currently-live page across all six providers is on this tier.
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
                                  sdk_repo_id, bindings_status="published",
                                  intro_text=None):
    # bindings_status="local_only" -- real, honest state for a brand-new
    # provider with zero published ubx-sdk-<name>{,-go,-py,-ts} repos
    # (confirmed live via `gh repo view` for datadog/github, not
    # assumed). This tier never had this branch before this session,
    # because it had only ever been used for the four already-
    # published providers -- a real, previously-untested gap, not
    # carried over from the mechanical tier by copy-paste.
    local_only = bindings_status == "local_only"
    example_fields = pick_richer_example_fields(fields)

    # --- Go: real, complete program ---
    go_preambles, go_assigns = [], []
    for f in example_fields:
        pre, val = field_literal_with_preamble(f, "go")
        if pre and pre not in go_preambles:
            go_preambles.append(pre)
        go_assigns.append(f"\t\t\t{pascal(f['WireName'])}: {val},")
    go_module_major = REAL_SDK_GO_MODULE_MAJOR.get(schema_name, "")
    go_module_major_seg = f"{go_module_major}/" if go_module_major else ""
    go_pkg_import_path = f'github.com/ubiquex/ubx-sdk-{sdk_repo_id}/sdk/go/{go_module_major_seg}{schema_name}/{go["service_dir"]}'
    # "json.Marshal(" (not just a "trustPolicy"-prefix check, which
    # missed the SECOND real preamble that also needs this import,
    # accessPolicy -- a real bug this batch's own verification pass
    # caught) -- matches every preamble that actually calls into
    # encoding/json, present or future, not just the one this session
    # happened to write first.
    needs_json = any("json.Marshal(" in p for p in go_preambles)

    go_lines = []
    if local_only:
        go_gen_cmd = f"ubx sdk gen --only {schema_name} --lang go --out ./local-sdk"
        go_replace = f"go.mod: replace github.com/ubiquex/ubx-sdk-{sdk_repo_id}/sdk/go => ./local-sdk/{schema_name}/sdk/go"
        go_lines.append(f"// {go_gen_cmd}")
        go_lines.append(f"// {go_replace}")
    go_lines.append("package main")
    go_lines.append("")
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
    go_lines.append(f'\t\tubx.Resource({go["package"]}.{go["binding"]}, "example", {go["package"]}.{go["config"]}{{')
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
    ts_lines = []
    if local_only:
        ts_gen_cmd = f"ubx sdk gen --only {schema_name} --lang ts --out ./local-sdk"
        ts_import_path = f'./local-sdk/{schema_name}/sdk/typescript/{ts["file"]}'
        ts_lines.append(f"// {ts_gen_cmd}")
    else:
        # UBI-143: TypeScript now publishes to npm (@ubx/sdk-<repo id>),
        # not JSR -- a bare specifier, matching Go's real module import
        # path and Python's real package import above exactly (neither
        # shows an install command either; both assume the reader has
        # already `go get`/`pip install`ed the real published package).
        # npm has no jsr:-style protocol specifier that resolves inline
        # without a prior install step, so the parallel here is "already
        # npm installed" + a bare import, never a registry-prefixed one.
        ts_import_path = f'@ubx/sdk-{sdk_repo_id}/{schema_name}/{ts["service_dir"]}/{os.path.splitext(os.path.basename(ts["file"]))[0]}'

    ts_lines.extend([
        'import { intent, resource, stack } from "@ubx/sdk";',
        f'import {{ {ts["binding"]} }} from "{ts_import_path}";',
        "",
        f'export default stack({json.dumps(stack_name)}, () => {{',
        f'  intent({{ summary: {json.dumps(intent_summary)} }});',
    ])
    for pre in ts_preambles:
        ts_lines.append("")
        ts_lines.append("  " + reindent(pre, "  "))
    ts_lines.append("")
    ts_lines.append(f'  resource({ts["binding"]}, "example", {{')
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
    if local_only:
        py_gen_cmd = f"ubx sdk gen --only {schema_name} --lang py --out ./local-sdk"
        py_lines.append(f"# {py_gen_cmd}")
        py_lines.append(f"# export PYTHONPATH=./local-sdk/{schema_name}/sdk/python:$PYTHONPATH")
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
    py_lines.append(f'    ubx.resource({py["binding"]}, "example", {py["config"]}(')
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

    # UBI-175 Phase 6, found-in-review defect (real, live-confirmed on
    # docs.ubiquex.io's own datadog_monitor page): input_fields is
    # Required-or-effectively-Optional, output_fields is effectively-
    # Computed -- correct as far as it goes, and it DOES produce a real,
    # meaningfully different Output section for resources with genuine
    # computed-only fields (confirmed: datadog_application_key_response's
    # own hash/owner appear in Output only, never Input). But a resource
    # whose real schema marks nearly every field BOTH Optional AND
    # Computed at once (confirmed live: datadog_monitor's own id/name/
    # priority/tags/... -- a real, accurate reflection of Datadog's own
    # shared request/response schema, not a code bug) ends up with an
    # Output section that is a pure subset of Input, contributing zero
    # fields a reader hasn't already just read once. output_only_fields
    # is what Output would show that Input genuinely doesn't -- when
    # that's empty, the split itself carries no real information for
    # this resource, so the page renders one combined "## Properties"
    # section instead of two near-identical ones.
    input_names = {f["WireName"] for f in input_fields}
    output_only_fields = [f for f in output_fields if f["WireName"] not in input_names]
    has_real_output_split = bool(output_only_fields)

    if has_real_output_split:
        properties_section = f"""## Input properties

{input_block}

## Output properties

{output_block}
"""
    else:
        properties_section = f"""## Properties

{input_block}
"""

    # UBI-175 Phase 6: intro_text present (a real artifacts/<provider>/
    # intros.json entry, threaded in by the caller) replaces the old,
    # generic three-line paragraph with real, resource-specific prose,
    # and the frontmatter description becomes a short summary derived
    # from that intro's own first sentence rather than a templated "A
    # complete, runnable..." line repeated on every page. intro_text
    # absent (a resource with no real intro yet) falls back to exactly
    # today's generic paragraph -- an honest gap, not a fabricated one,
    # and zero behavior change for any existing caller that never passes
    # intro_text at all.
    if intro_text:
        fm_description_raw, body = intro_and_description(intro_text)
        fm_description = yaml_dq_escape(fm_description_raw)
        # UBI-175 Phase 6, found-in-review defect (live-confirmed): the
        # generic "Real, typed bindings generated directly from..."
        # sentence used to always follow the real intro as a second
        # paragraph -- leftover template text once a real, resource-
        # specific intro already exists. Only shown in the fallback
        # branch below now, for a resource with no real intro at all.
    else:
        # UNCHANGED from before intro_text existed -- a resource with no
        # real intro yet falls back to exactly today's single generic
        # paragraph (the wire name doing double duty as the only
        # resource-specific content).
        fm_description = f"A complete, runnable {wire} program, in every SDK language."
        body = (
            f"`{wire}` -- real, typed bindings generated directly from\n"
            f"{schema_source_label(provider)}, in every SDK language.\n"
            f"Every tab below is a complete, runnable program, not a fragment, real\n"
            f"enough to save and run exactly as shown."
        )

    # body is empty exactly when intro_and_description found a genuinely
    # single-sentence intro_text with nothing left to show as a distinct
    # paragraph (see its own doc comment) -- skip the body slot entirely
    # rather than leave a stray blank line where it would have been.
    body_block = f"\n{body}\n" if body else ""
    page = f"""---
title: "{wire}"
description: "{fm_description}"
---
{body_block}
{example_section}
{properties_section}"""
    return page, example_section


# REAL_SDK_REPO_ID is the real, confirmed per-provider identity of the
# combined SDK repo (UBI-138 -- "ubx-sdk-<X>", one repo per provider,
# all three languages), verified directly against the real GitHub org,
# NEVER reconstructed from schema_name (which is the wire-type prefix /
# the repo's own INTERNAL path segment, not its identity -- diverges
# from this for Azure specifically: schema_name "azurerm", repo id
# "azure"). Every provider must add a real, confirmed entry here before
# its own richer-template pages can be generated -- no inferred/
# guessed fallback, by design. Moved here from gen_complete_pages.py
# (its own former sole owner) since generate_richer_provider now needs
# it too -- one real, shared table, not two that could drift.
REAL_SDK_REPO_ID = {
    "aws": "aws",
    "google": "google",
    "azurerm": "azure",
    "kubernetes": "kubernetes",
    "datadog": "datadog",
    "github": "github",
    # UBI-175 Phase 4: azure's own OpenAPI/ARM-Compute-sourced schema_name
    # ("azure", [dynamic_providers.azure] in sdk/providers/.ubx/config) is
    # a genuinely different real identity from "azurerm" above -- 19
    # resources, zero overlap with the published ubx-sdk-azure-* repos'
    # own azurerm_* content. No real ubx-sdk-azure-compute repo exists or
    # is expected to (bindings_status=local_only is the only real mode
    # this schema_name is ever generated under) -- "azure" here is a
    # locally-consistent path segment matching the real local `ubx sdk
    # gen --only azure` output already on disk, not a claim about a
    # published repo.
    "azure": "azure",
}

# REAL_SDK_GO_MODULE_MAJOR -- real, confirmed Go module major-version path
# segment per schema_name, verified live against the real Go module proxy
# (proxy.golang.org), not inferred. Only needed once a provider's real
# published Go module has crossed into v2+ (Go module semantics require
# the major version in the import path from v2 onward) -- aws confirmed
# live at v2.1.0 with module path .../sdk/go/v2 (UBI-202: go_pkg_import_path
# below omitted this for every provider, so aws's own generated Go examples
# named a package path -- .../sdk/go/aws/<service> -- that `go get` can't
# resolve against the real, live v2 module; every other provider verified
# still pre-v2, no segment needed, absent here reads as "" by default).
REAL_SDK_GO_MODULE_MAJOR = {
    "aws": "v2",
}


def _assert_within_scope(path, allowed_root):
    """Hard refusal, not a soft warning: path must resolve to a real
    descendant of allowed_root, or this raises and the caller's own run
    stops before writing anything unaccounted for. Guards against a
    slug/service value (wire-derived, but never fully trusted -- a
    future provider's own real naming could produce "..", an empty
    string, or an absolute-looking segment) resolving outside the one
    directory a given call is allowed to touch. Real, not decorative:
    verify_scope_guard.py's own real, checked-in run proves this
    actually raises on a crafted "../" path, not just on paper."""
    real_path = os.path.realpath(path)
    real_root = os.path.realpath(allowed_root)
    if real_path != real_root and not real_path.startswith(real_root + os.sep):
        raise SystemExit(
            f"scope guard: refusing to write {path!r} -- resolves to {real_path!r}, "
            f"outside the declared scope root {real_root!r}"
        )


def generate_richer_provider(docs_root, scratch_dir, provider, schema_name, provider_display,
                              stack_name, schema_path, idents_path, bindings_status="published",
                              intros_by_provider=None):
    """Full-provider, richer-tier generation -- the ONLY real page-
    writing path this generator has (its own former sibling,
    generate_mechanical_provider, is removed entirely along with
    build_resource_page -- see git history and gen_provider_docs.py's
    own module docstring). Builds a complete richer-tier page directly
    for a resource with NO existing page yet -- unlike
    gen_complete_pages.py's own generate_one, which only ever splices
    onto an already-generated page and is not usable to onboard a new
    provider at all (confirmed live: it hard-skips with "no existing
    page... run gen_mechanical_pages.py first", the exact trap this
    function exists to remove).
    docs_root/scratch_dir are real, caller-supplied paths (never hardcoded
    here) -- UBI-144 Phase 2's own finding: a hardcoded DOCS_ROOT pointing
    at the wrong, disconnected directory is exactly the kind of bug this
    file being real, reviewable, tracked tooling is meant to prevent.

    Declared scope is exactly schema's own (service, local) pairs --
    nothing else. This function never writes resource-reference/<provider>/
    index.mdx or any resource-reference/<provider>/<service>/index.mdx:
    those are shared, cross-call aggregate files a single schema slice
    (one family, per regen_pages.py's own real call shape) cannot safely
    reconstruct -- three real, live incidents (the GCP landing page
    clobbered to just the last family processed; the google_dlp_job
    rename's own collateral to the provider index; and the general risk
    the founder named directly) all trace to this function once building
    those files unconditionally from schema alone. Call
    rebuild_provider_index (below) explicitly, separately, whenever the
    real aggregate files need to reflect the real, current file tree --
    it derives them from what is ACTUALLY on disk, never from one call's
    own partial view."""
    if schema_name not in REAL_SDK_REPO_ID:
        raise SystemExit(
            f"no real, confirmed SDK repo id for schema_name {schema_name!r} in "
            "REAL_SDK_REPO_ID -- add it (verified against the real GitHub org) before generating"
        )
    sdk_repo_id = REAL_SDK_REPO_ID[schema_name]

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

            example_fields = pick_richer_example_fields(fields)
            go_values_by_name = {}
            for f in example_fields:
                _, val = field_literal_with_preamble(f, "go")
                go_values_by_name[f["WireName"]] = val

            if wire in KNOWN_FAMILY_MARKDOWN:
                primary = wrap_markdown(
                    render_generic_markdown_scenario(wire, example_fields, go_values_by_name).replace("\n", " ")
                )
                name_val = go_values_by_name.get("name", '"example"').strip('"')
                companion = wrap_markdown(KNOWN_FAMILY_MARKDOWN[wire](name_val))
                companion_markdown = primary + "\n\n" + companion
            else:
                companion_markdown = render_generic_markdown_scenario(wire, example_fields, go_values_by_name)

            page, _ = build_resource_page_complete(
                wire=wire, service=service, local=local, slug=slug, fields=fields,
                go=go, py=py, ts=ts, provider=provider, schema_name=schema_name,
                provider_display=provider_display, stack_name=stack_name,
                intent_summary=f"{stack_name} own {local.replace('_', ' ')}",
                companion_markdown=companion_markdown, sdk_repo_id=sdk_repo_id,
                bindings_status=bindings_status,
                intro_text=real_intro_for(provider, wire, intros_by_provider or {}),
            )
            resource_page_path = os.path.join(service_dir, f"{slug}.mdx")
            _assert_within_scope(resource_page_path, out_root)
            with open(resource_page_path, "w") as fh:
                fh.write(page)

        title = service.title()
        first_page = f"resource-reference/{provider}/{service}/{slugs[0]}"
        # A resource whose own wire-derived local name is literally "index"
        # (real, confirmed: google_firestore_index, and AWS's own live
        # corpus has the identical unresolved collision for
        # aws_resourceexplorer2_index/aws_s3vectors_index/aws_kendra_index)
        # would write to the exact same path a service-level CardGroup
        # landing page uses -- rebuild_provider_index's own identical
        # guard skips the landing page for that one service rather than
        # clobbering the real resource page with it. Computed here too
        # (unused for a write any more, this function no longer writes
        # that file at all -- kept only so card_entries/nav_groups below
        # still reflect it correctly for this call's own return value).
        index_collision = "index" in slugs

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

    # UBI-190 follow-up: resource-reference/<provider>/index.mdx and
    # resource-reference/<provider>/<service>/index.mdx are NEVER
    # written here any more -- see this function's own doc comment.
    # Three real incidents (GCP's landing page clobbered to the last
    # family processed; google_dlp_job's rename discarding the other
    # families' own provider-index cards; the founder's own general
    # scope-leak finding) all trace to building those two files from
    # schema alone, which -- every real caller confirmed (regen_pages.py
    # loops one real family per call; even gen_new_provider_pages.py's
    # own "brand-new provider" case is only actually complete the FIRST
    # time it runs) -- is never guaranteed to be the provider's own
    # complete, real corpus. Call rebuild_provider_index explicitly
    # after this function, once real page-writing is done, to derive
    # both files from the real, current file tree instead.
    nav_fragment = {
        "group": provider_display,
        "root": f"resource-reference/{provider}/index",
        "pages": nav_groups,
    }
    json.dump(nav_fragment, open(os.path.join(scratch_dir, f"{provider}_nav_fragment.json"), "w"), indent=2)
    print(f"generated {len(schema)} resource pages across {len(by_service)} services for {provider} "
          f"(resource-reference/{provider}/index.mdx and any resource-reference/{provider}/<service>/index.mdx "
          f"NOT touched -- call rebuild_provider_index explicitly if this call's own family is meant to be "
          f"the provider's real, complete corpus)")
    return len(schema), len(by_service)


def _read_page_title(path):
    """Pulls the real "title: ..." frontmatter value straight back out
    of an already-generated page -- the same real wire type
    build_resource_page_complete wrote there in the first place, so
    ground-truth reconstruction never has to re-derive it from the
    filename (a slug is lossy: hyphens replace underscores, and
    real_intro_for/card rendering both need the real wire, not a
    guessed reversal of that replacement). Frontmatter is always the
    first few lines (---, title, description, ---) -- reads a small,
    fixed window rather than the whole file."""
    with open(path) as fh:
        head = [fh.readline() for _ in range(5)]
    for line in head:
        line = line.rstrip("\n")
        if line.startswith('title: "') and line.endswith('"'):
            return line[len('title: "'):-1]
    raise ValueError(f"{path}: no real \"title: \\\"...\\\"\" frontmatter line found in the first 5 lines")


def rebuild_provider_index(docs_root, provider, provider_display):
    """The real fix for the scope-leak class generate_richer_provider's
    own doc comment names: derives resource-reference/<provider>/
    index.mdx and every resource-reference/<provider>/<service>/
    index.mdx from the REAL, CURRENT file tree on disk -- never from
    any one generation call's own partial schema. Safe to call after
    ANY generate_richer_provider run, whether that run covered one
    family or every family, because it never trusts what a single call
    claims to have generated -- it reads what is actually there.

    Deliberately independent of generate_richer_provider's own
    schema/idents inputs -- this function's only real input is the
    file tree itself, exactly the ground truth a card listing is
    supposed to reflect. Byte-compatible with the format
    generate_richer_provider used to write directly (same CardGroup
    markup, same title-casing, same "N resource type(s) documented"
    wording) so running this after a normal generation produces no
    unrelated diff on services this run didn't touch."""
    out_root = os.path.join(docs_root, "resource-reference", provider)
    if not os.path.isdir(out_root):
        raise SystemExit(f"rebuild_provider_index: {out_root!r} does not exist -- nothing to rebuild")

    card_entries = []
    services_written = 0

    for service_dir in sorted(glob.glob(os.path.join(out_root, "*"))):
        if not os.path.isdir(service_dir):
            continue
        service = os.path.basename(service_dir)
        # "data" is UBI-178 piece 4's own real, separate namespace
        # (resource-reference/<provider>/data/<service_dir>/...) --
        # not a provider-level service directory itself, skipped here
        # the same way it is everywhere else a provider's own top-level
        # service list is enumerated.
        if service == "data":
            continue

        resource_paths = sorted(
            p for p in glob.glob(os.path.join(service_dir, "*.mdx"))
            if os.path.basename(p) != "index.mdx"
        )
        if not resource_paths:
            continue

        items = []
        for p in resource_paths:
            slug = os.path.splitext(os.path.basename(p))[0]
            wire = _read_page_title(p)
            local = slug.replace("-", "_")
            items.append((wire, local, slug))

        title = service.title()
        slugs = [slug for _, _, slug in items]
        index_collision = "index" in slugs

        if len(items) > 1 and not index_collision:
            card_body = f"""---
title: "{title}"
description: "{provider_display} {title} resource types."
---

<CardGroup cols={{2}}>
"""
            for wire, local, slug in items:
                card_title = local.replace("_", " ").title()
                card_body += f'  <Card title="{card_title}" href="/resource-reference/{provider}/{service}/{slug}">\n    {wire}\n  </Card>\n'
            card_body += "</CardGroup>\n"
            index_path = os.path.join(service_dir, "index.mdx")
            _assert_within_scope(index_path, out_root)
            with open(index_path, "w") as fh:
                fh.write(card_body)
            services_written += 1

        card_entries.append((title, service, slugs[0], len(items)))

    total_resources = sum(count for _, _, _, count in card_entries)
    idx = f"""---
title: "{provider_display}"
description: "{provider_display} resource types, grouped by real service."
---

{provider_display} covers {total_resources} resource types (as of the
version this reference was generated from), sourced directly from
{schema_source_label(provider)} via ubx-provider-dynamic, grouped here
the same way the real generated bindings are, mechanically by
`{provider_display}` service boundary (see each generated repo's own
`ServiceAndLocalName`). Every page's field list is parsed directly from
the real provider schema, not hand-authored.

<CardGroup cols={{2}}>
"""
    # card_entries is already in service-sorted order (built while
    # walking sorted(glob.glob(...)) above) -- no re-sort here, matching
    # generate_richer_provider's own original iteration order exactly.
    for title, service, first_slug, count in card_entries:
        noun = "resource type" if count == 1 else "resource types"
        idx += f'  <Card title="{title}" icon="cube" href="/resource-reference/{provider}/{service}/{first_slug}">\n    {count} {noun} documented\n  </Card>\n'
    idx += "</CardGroup>\n"
    provider_index_path = os.path.join(out_root, "index.mdx")
    _assert_within_scope(provider_index_path, out_root)
    with open(provider_index_path, "w") as fh:
        fh.write(idx)

    print(f"rebuild_provider_index: {provider}: {len(card_entries)} services, {total_resources} resource types, "
          f"{services_written} per-service index.mdx written, provider index.mdx rebuilt from the real file tree")
    return len(card_entries), total_resources
