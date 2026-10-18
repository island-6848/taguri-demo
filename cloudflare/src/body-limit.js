// Reading a request body with a byte cap (issue #123).
//
// `request.arrayBuffer()` buffers the whole body before anyone can look at its size, so a
// request without Content-Length (or with a false one) could make the Worker hold far more
// than the cap. This reads chunk by chunk and stops — cancelling the stream — as soon as the
// running total passes `cap`. Returns the bytes, or null when the body is over the cap.
export async function readCapped(request, cap) {
  const reader = request.body?.getReader();
  if (!reader) return new Uint8Array(0);
  let size = 0; const chunks = [];
  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > cap) {
      try { await reader.cancel(); } catch { /* the stream is dropped either way */ }
      return null;
    }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return bytes;
}
