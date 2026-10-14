// MD5 of a UTF-8 string, hex (hashlib.md5(s.encode("utf-8")).hexdigest()). The Worker's
// crypto.subtle has no MD5; the record screens use it only to make the same small,
// fixed wobbles as the Python figures (never for security).
const K = Array.from({length: 64}, (_, i) => Math.floor(Math.abs(Math.sin(i + 1)) * 2 ** 32) >>> 0);
const S = [7, 12, 17, 22, 5, 9, 14, 20, 4, 11, 16, 23, 6, 10, 15, 21];
export function md5hex(str) {
  const bytes = new TextEncoder().encode(str);
  const n = ((bytes.length + 8) >> 6) + 1;
  const w = new Uint32Array(n * 16);
  bytes.forEach((b, i) => { w[i >> 2] |= b << ((i % 4) * 8); });
  w[bytes.length >> 2] |= 0x80 << ((bytes.length % 4) * 8);
  const bits = bytes.length * 8;
  w[n * 16 - 2] = bits >>> 0;
  w[n * 16 - 1] = Math.floor(bits / 2 ** 32);
  let [a0, b0, c0, d0] = [0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476];
  for (let blk = 0; blk < n * 16; blk += 16) {
    let [a, b, c, d] = [a0, b0, c0, d0];
    for (let i = 0; i < 64; i++) {
      let f, g;
      if (i < 16) { f = (b & c) | (~b & d); g = i; }
      else if (i < 32) { f = (d & b) | (~d & c); g = (5 * i + 1) % 16; }
      else if (i < 48) { f = b ^ c ^ d; g = (3 * i + 5) % 16; }
      else { f = c ^ (b | ~d); g = (7 * i) % 16; }
      const s = S[(i >> 4) * 4 + (i % 4)];
      const t = (a + f + K[i] + w[blk + g]) >>> 0;
      [a, d, c] = [d, c, b];
      b = (b + ((t << s) | (t >>> (32 - s)))) >>> 0;
    }
    a0 = (a0 + a) >>> 0; b0 = (b0 + b) >>> 0; c0 = (c0 + c) >>> 0; d0 = (d0 + d) >>> 0;
  }
  return [a0, b0, c0, d0].map(x => Array.from({length: 4}, (_, i) => ((x >>> (i * 8)) & 0xff).toString(16).padStart(2, '0')).join('')).join('');
}
