import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { fileURLToPath } from "node:url";

async function source(relativePath) {
  return readFile(fileURLToPath(new URL(relativePath, import.meta.url)), "utf8");
}

test("upload and review states clear stale UI only after a successful decision", async () => {
  const app = await source("../src/App.tsx");
  const outcome = await source("../src/features/upload/DocumentOutcome.tsx");

  assert.match(app, /Reviewing your resource\. This may take a few seconds to a few minutes/);
  assert.match(app, /document\.data\.status === "CONTRIBUTOR_REVIEW_REQUIRED"/);
  assert.match(app, /removeQueries\(\{ queryKey: \["contributor-review", documentId\] \}\)/);
  assert.match(app, /setUploadResetKey/);
  assert.match(outcome, /Applying your update and adding the resource/);
  assert.match(outcome, /Saving your decision/);
});

test("search requests are scoped to the submitted query", async () => {
  const search = await source("../src/features/search/KnowledgeSearch.tsx");

  assert.match(search, /useQuery/);
  assert.match(search, /queryKey: \["knowledge-search", submittedQuery\]/);
  assert.doesNotMatch(search, /useMutation/);
});

test("search form has an explicit submit control for keyboard submission", async () => {
  const search = await source("../src/features/search/KnowledgeSearch.tsx");

  assert.match(search, /<form className="trusted-search-form" onSubmit={submit}>/);
  assert.match(search, /<button\s+type="submit"/);
  assert.match(search, /onKeyDown={submitFromKeyboard}/);
});

test("document requests map network failures to a safe message", async () => {
  const documents = await source("../src/api/documents.ts");

  assert.match(documents, /We could not reach the service\. Please try again\./);
  assert.match(documents, /We could not finish that request\. Please try again\./);
});
