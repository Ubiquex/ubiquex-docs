// Command dump_schema is real, tracked tooling for UBI-144's own
// resource-reference generator (gen_provider_docs.py) -- dumps one or
// more real resource types' own IR (sdk/codegen/ir.FromSchema, the
// SAME shared translator Go/TS/Python bindings codegen already uses)
// from a real, cached provider schema, one JSON file per resource type.
//
// SUPERSEDED for every real provider now that all six (aws, azure,
// datadog, github, google, kubernetes) source through
// ubx-provider-dynamic rather than a HashiCorp tfplugin binary: this
// tool only ever calls provider.Launch, which has no equivalent path
// at all for a [dynamic_providers.<name>] entry, and it never applies
// checked-in-descriptions enrichment either way (every dump it
// produces reports DescriptionSource "source"/"" only, never
// "ai-inferred", regardless of what sdk/providers/descriptions/*.json
// actually has). Use `ubx sdk gen --dump-ir` instead (see this
// directory's own README.md, step 1) -- same real IR translator, same
// per-resource JSON shape, works for both provider kinds, and applies
// real enrichment. Kept in tree, not deleted, in case a future session
// needs to dump a resource type from a real, non-dynamic-provider
// tfplugin source this repo doesn't otherwise declare -- but a normal
// docs-corpus session should not reach for this file.
//
// This file lives in ubiquex-docs (the docs repo) but can only run
// from WITHIN a real ubiquex checkout -- it imports ubiquex's own
// internal packages (provider, sdk/codegen/ir), which aren't a public,
// go-gettable module. See this repo's own scripts/resource-reference-gen/
// README.md for the real, exact command.
//
// Usage (from within ~/Ubiquex/ubiquex, or wherever your real ubiquex
// checkout lives):
//
//	go run /path/to/ubiquex-docs/scripts/resource-reference-gen/dump_schema.go \
//	    <source> <version> <out-dir> <wire_type> [<wire_type> ...]
//
// Example (the real command this session used for the AWS batches):
//
//	go run .../dump_schema.go hashicorp/aws 6.54.0 /tmp/schema-dump \
//	    aws_iam_role aws_sqs_queue aws_s3_bucket
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/ubiquex/ubiquex/provider"
	"github.com/ubiquex/ubiquex/sdk/codegen/ir"
)

func main() {
	if len(os.Args) < 5 {
		fmt.Fprintln(os.Stderr, "usage: dump_schema.go <source> <version> <out-dir> <wire_type> [<wire_type> ...]")
		os.Exit(2)
	}
	source := os.Args[1]
	version := os.Args[2]
	outDir := os.Args[3]
	wireTypes := os.Args[4:]

	ctx := context.Background()
	parsed, err := provider.ParseSource(source)
	if err != nil {
		panic(err)
	}
	result, err := provider.Acquire(ctx, parsed, version)
	if err != nil {
		panic(err)
	}
	client, err := provider.Launch(ctx, result.Path)
	if err != nil {
		panic(err)
	}
	defer client.Close()
	schemas, err := client.Provider.Schema(ctx)
	if err != nil {
		panic(err)
	}

	if err := os.MkdirAll(outDir, 0o755); err != nil {
		panic(err)
	}

	for _, wire := range wireTypes {
		sch, ok := schemas.Resources[wire]
		if !ok {
			fmt.Fprintf(os.Stderr, "no such resource type %q in %s@%s\n", wire, source, version)
			continue
		}
		rt, err := ir.FromSchema(wire, sch)
		if err != nil {
			panic(err)
		}
		out, err := json.MarshalIndent(rt.Fields, "", "  ")
		if err != nil {
			panic(err)
		}
		outPath := outDir + "/" + wire + ".json"
		if err := os.WriteFile(outPath, out, 0o644); err != nil {
			panic(err)
		}
		fmt.Printf("%s: %d fields -> %s\n", wire, len(rt.Fields), outPath)
	}
}
