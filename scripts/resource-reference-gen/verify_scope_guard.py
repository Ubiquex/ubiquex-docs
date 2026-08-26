#!/usr/bin/env python3
"""UBI-190 follow-up: real, live proof that generate_richer_provider
cannot clobber a shared file outside its own declared scope any more,
and that rebuild_provider_index correctly reconstructs the real
aggregate files from the real, current file tree afterward -- the
exact class of incident that shipped three times before this existed
(GCP's landing page clobbered to the last family processed; the real
google_dlp_job rename's own collateral to the provider index; the
founder's own general "make it refuse" finding).

Builds a throwaway docs_root under a real temp directory (never the
real repo), seeds it with a fake "already-published" service (storage,
2 resources) the way an earlier, unrelated regen would have left it,
then calls generate_richer_provider scoped to a DIFFERENT, single new
family (compute, 1 resource) -- the same call shape regen_pages.py's
own per-family loop uses. Every assertion below is a real file-content
comparison, not a mocked call.

Usage:
  python3 verify_scope_guard.py
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_provider_docs
from gen_provider_docs import generate_richer_provider, rebuild_provider_index, _assert_within_scope


def seed_preexisting_corpus(docs_root):
    storage_dir = os.path.join(docs_root, "resource-reference", "testprov", "storage")
    os.makedirs(storage_dir, exist_ok=True)

    with open(os.path.join(storage_dir, "bucket.mdx"), "w") as f:
        f.write('---\ntitle: "testprov_storage_bucket"\ndescription: "test bucket."\n---\n\npre-existing, must survive.\n')
    with open(os.path.join(storage_dir, "object.mdx"), "w") as f:
        f.write('---\ntitle: "testprov_storage_object"\ndescription: "test object."\n---\n\npre-existing, must survive.\n')
    with open(os.path.join(storage_dir, "index.mdx"), "w") as f:
        f.write(
            '---\ntitle: "Storage"\ndescription: "TestProv Storage resource types."\n---\n\n'
            '<CardGroup cols={2}>\n'
            '  <Card title="Bucket" href="/resource-reference/testprov/storage/bucket">\n    testprov_storage_bucket\n  </Card>\n'
            '  <Card title="Object" href="/resource-reference/testprov/storage/object">\n    testprov_storage_object\n  </Card>\n'
            '</CardGroup>\n'
        )
    provider_index = os.path.join(docs_root, "resource-reference", "testprov", "index.mdx")
    with open(provider_index, "w") as f:
        f.write(
            '---\ntitle: "TestProv"\ndescription: "TestProv resource types, grouped by real service."\n---\n\n'
            'TestProv covers 2 resource types.\n\n'
            '<CardGroup cols={2}>\n'
            '  <Card title="Storage" icon="cube" href="/resource-reference/testprov/storage/bucket">\n    2 resource types documented\n  </Card>\n'
            '</CardGroup>\n'
        )


def field(wire_name, required=False, optional=False, computed=False):
    return {
        "WireName": wire_name,
        "Type": {"Kind": 1, "Scalar": 1, "Element": None, "Object": None},
        "Required": required, "Optional": optional, "Computed": computed, "Sensitive": False,
        "Description": f"the {wire_name}", "DescriptionSource": "source",
    }


def main():
    failures = []

    def check(label, condition):
        status = "ok" if condition else "FAIL"
        print(f"[{status}] {label}")
        if not condition:
            failures.append(label)

    tmp = tempfile.mkdtemp(prefix="verify-scope-guard-")
    try:
        docs_root = os.path.join(tmp, "docs_root")
        scratch = os.path.join(tmp, "scratch")
        os.makedirs(scratch, exist_ok=True)
        seed_preexisting_corpus(docs_root)

        pre = {}
        for rel in ("resource-reference/testprov/storage/index.mdx",
                    "resource-reference/testprov/index.mdx",
                    "resource-reference/testprov/storage/bucket.mdx",
                    "resource-reference/testprov/storage/object.mdx"):
            pre[rel] = open(os.path.join(docs_root, rel)).read()

        gen_provider_docs.REAL_SDK_REPO_ID["testcompute"] = "testprov"
        schema = {"testprov_compute_instance": {
            "service": "compute", "localName": "instance",
            "ir": {"Fields": [field("name", required=True), field("id", computed=True)]},
        }}
        schema_path = os.path.join(scratch, "schema.json")
        json.dump(schema, open(schema_path, "w"))
        idents = {"testprov_compute_instance": {
            "go": {"file": "compute/instance.go", "package": "compute", "service_dir": "compute", "binding": "Instance", "config": "InstanceConfig"},
            "py": {"file": "compute/instance.py", "module": "compute.instance", "service_dir": "compute", "binding": "Instance", "config": "InstanceConfig"},
            "ts": {"file": "compute/instance.ts", "service_dir": "compute", "binding": "Instance", "config": "InstanceConfig"},
        }}
        idents_path = os.path.join(scratch, "idents.json")
        json.dump(idents, open(idents_path, "w"))

        generate_richer_provider(
            docs_root=docs_root, scratch_dir=scratch, provider="testprov",
            schema_name="testcompute", provider_display="TestProv", stack_name="example",
            schema_path=schema_path, idents_path=idents_path, bindings_status="local_only",
        )

        for rel, before in pre.items():
            after = open(os.path.join(docs_root, rel)).read()
            check(f"scoped call left {rel} byte-identical (the real bug: it used to rewrite this)", before == after)

        new_page = os.path.join(docs_root, "resource-reference/testprov/compute/instance.mdx")
        check("scoped call wrote its own new resource page", os.path.exists(new_page))

        check(
            "scope guard rejects a path escaping out_root",
            _raises_systemexit(lambda: _assert_within_scope(
                os.path.join(docs_root, "resource-reference", "testprov", "..", "..", "..", "etc", "passwd"),
                os.path.join(docs_root, "resource-reference", "testprov"),
            )),
        )
        check(
            "scope guard allows a real path inside out_root",
            not _raises_systemexit(lambda: _assert_within_scope(new_page, os.path.join(docs_root, "resource-reference", "testprov"))),
        )

        rebuild_provider_index(docs_root=docs_root, provider="testprov", provider_display="TestProv")
        final_index = open(os.path.join(docs_root, "resource-reference/testprov/index.mdx")).read()
        check("rebuild_provider_index's own output mentions the untouched family (Storage)", "Storage" in final_index)
        check("rebuild_provider_index's own output mentions the newly-generated family (Compute)", "Compute" in final_index)
        check("rebuild_provider_index's own output has the real, correct total (3)", "covers 3 resource types" in final_index)
        check(
            "storage's own resource pages are still on disk after rebuild",
            os.path.exists(os.path.join(docs_root, "resource-reference/testprov/storage/bucket.mdx"))
            and os.path.exists(os.path.join(docs_root, "resource-reference/testprov/storage/object.mdx")),
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print(f"\n{len(failures)} check(s) failed: {failures}")
        sys.exit(1)
    print("\nall checks passed")


def _raises_systemexit(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


if __name__ == "__main__":
    main()
