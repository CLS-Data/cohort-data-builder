/* Writing a zip file in the browser, so the download needs no server.

   The 1989 format (a local header per entry, a central directory, an end record), stored
   without compression: no zip64 and no data descriptors, which a few dozen kilobytes of
   scripts cannot need. */

const ZIP_VERSION = 20; // 2.0
const UTF8_NAMES = 0x0800; // file names are UTF-8
const STORED = 0;

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[i] = c >>> 0;
  }
  return table;
})();

/**
 * The CRC-32 checksum zip uses.
 * @param {Uint8Array} bytes The data.
 * @returns {number} The checksum, unsigned.
 */
export function crc32(bytes) {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

/* MS-DOS packed date and time; seconds are halved. */
function dosStamp(d) {
  const time = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1);
  const date = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
  return { time: time & 0xffff, date: date & 0xffff };
}

/**
 * Build a zip archive of text files.
 * @param {Array<[string, string]>} entries `[path, text]` pairs; paths may be nested.
 * @param {Date} [when] The modification time recorded for every entry.
 * @returns {Uint8Array} The zip file's bytes.
 */
export function zip(entries, when = new Date()) {
  const encoder = new TextEncoder();
  const { time, date } = dosStamp(when);
  const locals = [];
  const central = [];
  let offset = 0;

  for (const [path, text] of entries) {
    const name = encoder.encode(path);
    const data = encoder.encode(text);
    const sum = crc32(data);

    const local = new DataView(new ArrayBuffer(30));
    local.setUint32(0, 0x04034b50, true);
    local.setUint16(4, ZIP_VERSION, true);
    local.setUint16(6, UTF8_NAMES, true);
    local.setUint16(8, STORED, true);
    local.setUint16(10, time, true);
    local.setUint16(12, date, true);
    local.setUint32(14, sum, true);
    local.setUint32(18, data.length, true);
    local.setUint32(22, data.length, true);
    local.setUint16(26, name.length, true);
    locals.push(new Uint8Array(local.buffer), name, data);

    const entry = new DataView(new ArrayBuffer(46));
    entry.setUint32(0, 0x02014b50, true);
    entry.setUint16(4, ZIP_VERSION, true);
    entry.setUint16(6, ZIP_VERSION, true);
    entry.setUint16(8, UTF8_NAMES, true);
    entry.setUint16(10, STORED, true);
    entry.setUint16(12, time, true);
    entry.setUint16(14, date, true);
    entry.setUint32(16, sum, true);
    entry.setUint32(20, data.length, true);
    entry.setUint32(24, data.length, true);
    entry.setUint16(28, name.length, true);
    // Regular file, 0644: left at zero, some unzip tools produce unreadable files.
    entry.setUint32(38, (0o100644 << 16) >>> 0, true);
    entry.setUint32(42, offset, true);
    central.push(new Uint8Array(entry.buffer), name);

    offset += 30 + name.length + data.length;
  }

  const size = central.reduce((n, c) => n + c.length, 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true);
  end.setUint16(8, entries.length, true);
  end.setUint16(10, entries.length, true);
  end.setUint32(12, size, true);
  end.setUint32(16, offset, true);

  const parts = [...locals, ...central, new Uint8Array(end.buffer)];
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) {
    out.set(p, at);
    at += p.length;
  }
  return out;
}
