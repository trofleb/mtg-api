import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import Ajv2020, { type ValidateFunction } from "ajv/dist/2020";
import addFormats from "ajv-formats";

/**
 * Runtime validation of every stub response against the committed schema.
 *
 * `tsc` already checks the fixtures against `lib/api-types.ts`, but a type
 * check is compile-time and structural: it cannot see a response assembled at
 * runtime, and TypeScript happily lets an extra property through a spread.
 * The point of the stub is that Tier B tests the frontend against the API's
 * real contract, and a stub that quietly returns something the API never
 * could is worth less than no stub at all - see "The stub can only be as
 * honest as the contract" in fix-ui-issues.md.
 *
 * So the same `openapi.json` the types are generated from is loaded here and
 * every response body is checked against it before it goes out.
 */

/**
 * Walk up from the working directory to the repo's `openapi.json`.
 *
 * Not `import.meta.url` and not `__dirname`: this module is loaded by three
 * runners (tsx as ESM, Vitest through Vite, Playwright's CJS transform) and
 * exactly one of those two identifiers exists in each. Walking up works in
 * all three and does not care which module system won.
 */
function findOpenApiDocument(): string {
  let dir = process.cwd();

  for (let depth = 0; depth < 8; depth++) {
    const candidate = path.join(dir, "openapi.json");
    if (existsSync(candidate)) return candidate;

    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }

  throw new Error(`openapi.json not found above ${process.cwd()}`);
}

const openapiDocument = JSON.parse(readFileSync(findOpenApiDocument(), "utf8"));

// OpenAPI 3.1 schemas are JSON Schema 2020-12, so they compile as-is.
// strict:false because the document carries OpenAPI keywords ("example",
// "discriminator", ...) that Ajv does not know and must not reject.
const ajv = new Ajv2020({ strict: false, allErrors: true });
addFormats(ajv);
ajv.addSchema(openapiDocument, "openapi.json");

const validators = new Map<string, ValidateFunction>();

function validatorFor(schemaName: string): ValidateFunction {
  const cached = validators.get(schemaName);
  if (cached) return cached;

  const compiled = ajv.compile({ $ref: `openapi.json#/components/schemas/${schemaName}` });
  validators.set(schemaName, compiled);
  return compiled;
}

export class StubContractError extends Error {}

/**
 * Return `body` if it matches the named schema; throw a loud error if not.
 *
 * Throwing rather than logging is deliberate: a stub drifting from the schema
 * has to stop the run, or Tier B goes green against a contract that does not
 * exist.
 */
export function validated<T>(schemaName: string, body: T): T {
  const validate = validatorFor(schemaName);

  if (!validate(body)) {
    const detail = (validate.errors ?? [])
      .map((error) => `${error.instancePath || "/"} ${error.message}`)
      .join("; ");
    throw new StubContractError(
      `stub response does not match ${schemaName} in openapi.json: ${detail}`
    );
  }

  return body;
}
