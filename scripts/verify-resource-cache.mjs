import assert from "node:assert/strict";
import { createResourceCache } from "../src/resource-cache.ts";
let resolve,
  calls = 0;
const cache = createResourceCache(() => {
  calls++;
  return new Promise((r) => {
    resolve = r;
  });
});
const a = cache.get("/catalog"),
  b = cache.get("/catalog");
assert.equal(calls, 1, "parallel reads should share one request");
resolve({ version: 1 });
await Promise.all([a, b]);
assert.equal((await cache.get("/catalog")).version, 1);
assert.equal(calls, 1);
cache.clear();
const old = cache.get("/catalog");
const resolveOld = resolve;
cache.clear();
const fresh = cache.get("/catalog");
const resolveFresh = resolve;
resolveFresh({ version: 3 });
await fresh;
resolveOld({ version: 2 });
await old;
assert.equal(
  cache.peek("/catalog").version,
  3,
  "an older read cannot repopulate invalidated data",
);
let attempts = 0;
const errors = createResourceCache(async () => {
  attempts++;
  if (attempts === 1) throw Error("temporary");
  return 2;
});
await assert.rejects(errors.get("/parts"));
assert.equal(await errors.get("/parts"), 2);
let now = 0;
const original = Date.now;
Date.now = () => now;
try {
  let reads = 0;
  const ttl = createResourceCache(async () => ++reads, 30);
  assert.equal(await ttl.get("/catalog"), 1);
  now = 29;
  assert.equal(await ttl.get("/catalog"), 1);
  now = 31;
  assert.equal(await ttl.get("/catalog"), 2);
  ttl.clear(["/catalog"]);
  assert.equal(await ttl.get("/catalog"), 3);
} finally {
  Date.now = original;
}
console.log(
  "PASS cache deduplication, bounded freshness, mutation/session invalidation, old-response protection and failure retry.",
);
