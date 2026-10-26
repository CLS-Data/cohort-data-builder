import assert from "node:assert/strict";
import { test } from "node:test";
import { crc32, zip } from "../../site/js/core/zip.js";

const enc = new TextEncoder();
const dec = new TextDecoder();

/* Read a zip back through its central directory. */
function unzip(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const end = bytes.length - 22;
  assert.equal(view.getUint32(end, true), 0x06054b50, "end record");
  const count = view.getUint16(end + 10, true);
  const size = view.getUint32(end + 12, true);
  let at = view.getUint32(end + 16, true);
  assert.equal(at + size, end, "central directory sits just before the end record");
  const out = [];
  for (let i = 0; i < count; i++) {
    assert.equal(view.getUint32(at, true), 0x02014b50, "central header");
    const flags = view.getUint16(at + 8, true);
    const method = view.getUint16(at + 10, true);
    const crc = view.getUint32(at + 16, true);
    const length = view.getUint32(at + 20, true);
    const nameLength = view.getUint16(at + 28, true);
    const local = view.getUint32(at + 42, true);
    const name = dec.decode(bytes.subarray(at + 46, at + 46 + nameLength));
    assert.equal(view.getUint32(local, true), 0x04034b50, "local header");
    assert.equal(view.getUint16(local + 26, true), nameLength);
    const start = local + 30 + nameLength + view.getUint16(local + 28, true);
    const data = bytes.subarray(start, start + length);
    out.push({ name, flags, method, crc, text: dec.decode(data), data });
    at += 46 + nameLength + view.getUint16(at + 30, true) + view.getUint16(at + 32, true);
  }
  return out;
}

test("crc32 of a known string", () => {
  assert.equal(crc32(enc.encode("The quick brown fox jumps over the lazy dog")), 0x414fa339);
  assert.equal(crc32(new Uint8Array()), 0);
});

test("zip round-trips nested paths and UTF-8 names, stored, with CRCs", () => {
  const entries = [
    ["proj/README.md", "# Hello\n"],
    ["proj/R/merge.R", "x <- 1\n"],
    ["proj/data/café.txt", "naïve ✓\n"],
  ];
  const bytes = zip(entries, new Date(2026, 9, 26, 12, 0, 0));
  assert.ok(bytes instanceof Uint8Array);
  const back = unzip(bytes);
  assert.deepEqual(
    back.map((e) => [e.name, e.text]),
    entries,
  );
  for (const e of back) {
    assert.equal(e.method, 0, "stored");
    assert.ok(e.flags & 0x0800, "UTF-8 flag");
    assert.equal(e.crc, crc32(e.data));
  }
});

test("an empty zip is just an end record", () => {
  const bytes = zip([]);
  assert.equal(bytes.length, 22);
  assert.deepEqual(unzip(bytes), []);
});
