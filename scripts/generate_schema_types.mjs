import { readFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { compile, compileFromFile } from "json-schema-to-typescript";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outputDirectory = path.join(root, "apps", "studio", "src", "generated");
const schemas = {
  "claim-boundary": "schemas/claim-boundary/v1.schema.json",
  "domain-pack": "schemas/domain-pack/v1.schema.json",
  failure: "schemas/evidence/failure-v1.schema.json",
  "field-point": "schemas/local-brot/v1.schema.json",
  "field-table": "schemas/field-table/v1.schema.json",
  "run-spec": "schemas/run-spec/v1.schema.json",
  manifest: "schemas/tbx/v1.schema.json",
  "tld-claim-adjudication": "schemas/tld-claim-adjudication/v1.schema.json",
  "tld-domain-pack": "schemas/tld-domain-pack/v1.schema.json",
  "tld-endpoint-table": "schemas/tld-endpoint-table/v1.schema.json",
  "tld-independent-verification": "schemas/independent-verification/v1.schema.json",
  "tld-ladder-registry": "schemas/tld-ladder-registry/v1.schema.json",
  "tld-perturbation-contract": "schemas/tld-perturbation-contract/v1.schema.json",
  "tld-preregistration-result": "schemas/tld-preregistration-result/v1.schema.json",
  "tld-release-source": "schemas/tld-release-source/v1.schema.json",
  "tld-run-contract": "schemas/tld-run-contract/v1.schema.json",
  "tld-tbx-profile": "schemas/tld-tbx-profile/v1.schema.json",
  "tld-trajectory-trace": "schemas/tld-trajectory-trace/v1.schema.json",
};
const check = process.argv.includes("--check");
const mismatches = [];

await mkdir(outputDirectory, { recursive: true });
for (const [name, relativeSchema] of Object.entries(schemas)) {
  const source = path.join(root, relativeSchema);
  const options = {
    bannerComment: "/* Generated from the canonical repository schema. Do not edit by hand. */",
    cwd: root,
    format: true,
    style: { singleQuote: false },
    unknownAny: false,
  };
  let generated;
  if (name === "field-table") {
    const schema = JSON.parse(await readFile(source, "utf8"));
    const pointSchema = JSON.parse(await readFile(path.join(root, schemas["field-point"]), "utf8"));
    schema.properties.points.items = pointSchema;
    generated = await compile(schema, "TorusFieldTable", options);
  } else {
    generated = await compileFromFile(source, options);
  }
  const target = path.join(outputDirectory, `${name}.d.ts`);
  if (check) {
    const existing = await readFile(target, "utf8").catch(() => "");
    if (existing !== generated) mismatches.push(path.relative(root, target));
  } else {
    await writeFile(target, generated, "utf8");
  }
}

if (mismatches.length) {
  console.error(`Generated schema types are stale: ${mismatches.join(", ")}`);
  process.exitCode = 1;
} else {
  console.log(check ? "Generated schema types are current." : "Generated browser schema types.");
}
