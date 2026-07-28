import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { fileURLToPath } from "node:url";

test("document outcomes do not render an Important ideas section", async () => {
  const component = await readFile(
    fileURLToPath(new URL("../src/features/upload/DocumentOutcome.tsx", import.meta.url)),
    "utf8",
  );

  assert.doesNotMatch(component, /<ReportSection title="Important ideas">/);
});

test("approved outcomes separate optional suggestions from blocking attention", async () => {
  const component = await readFile(
    fileURLToPath(new URL("../src/features/upload/DocumentOutcome.tsx", import.meta.url)),
    "utf8",
  );

  assert.match(component, /const isApproved = document\.status === "APPROVED"/);
  assert.match(component, /<ReportSection title="Suggestions for improvement">/);
  assert.match(component, /These optional suggestions did not prevent this resource/);
  assert.match(component, /approvedSuggestions\.length > 0/);
  assert.match(component, /findingsForAttention\.length > 0/);
});

test("approved limited verification uses a safe accepted message", async () => {
  const component = await readFile(
    fileURLToPath(new URL("../src/features/upload/DocumentOutcome.tsx", import.meta.url)),
    "utf8",
  );

  assert.match(
    component,
    /External references could not be checked right now\. The document was accepted based on the available evidence\./,
  );
  assert.match(component, /finding\.code === "GROUNDING_FAILED"/);
  assert.doesNotMatch(component, /Google Search Grounding/);
  assert.doesNotMatch(component, /HTTP 429/);
});

test("failed outcomes do not render partial approval or review sections", async () => {
  const component = await readFile(
    fileURLToPath(new URL("../src/features/upload/DocumentOutcome.tsx", import.meta.url)),
    "utf8",
  );

  assert.match(component, /const isFailed = document\.status === "FAILED"/);
  assert.match(component, /!isFailed && document\.analysis/);
  assert.match(component, /!isFailed && informationalFindings\.length > 0/);
  assert.match(component, /!isFailed && review && onDecision/);
});

test("review and rejected outcomes preserve their distinct semantics", async () => {
  const component = await readFile(
    fileURLToPath(new URL("../src/features/upload/DocumentOutcome.tsx", import.meta.url)),
    "utf8",
  );

  assert.match(component, /CONTRIBUTOR_REVIEW_REQUIRED: \{\s+title: "Your review is needed"/);
  assert.match(component, /ADMIN_REVIEW_REQUIRED: \{\s+title: "Needs further review"/);
  assert.match(component, /REJECTED: \{\s+title: "Not added to your knowledge base"/);
  assert.match(component, /document\.status === "CONTRIBUTOR_REVIEW_REQUIRED" \? reviewBlockers/);
});

test("outcome sections require non-empty data before rendering", async () => {
  const component = await readFile(
    fileURLToPath(new URL("../src/features/upload/DocumentOutcome.tsx", import.meta.url)),
    "utf8",
  );

  assert.match(component, /informationalFindings\.length > 0/);
  assert.match(component, /approvedSuggestions\.length > 0/);
  assert.match(component, /findingsForAttention\.length > 0/);
  assert.match(component, /document\.grounded_claim_verifications\?\.length/);
});
