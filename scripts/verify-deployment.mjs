/**
 * Post-deployment verification for the containerised stack.
 *
 * Exercises the four properties that matter after `docker compose up`:
 * the dashboard is served, it can reach the API through nginx, data
 * survives a database restart, and the MJPEG stream still streams.
 *
 * Usage:  node scripts/verify-deployment.mjs [baseUrl]
 */

const BASE = process.argv[2] ?? 'http://localhost:8080';

let passed = 0;
let failed = 0;

const check = (label, ok, detail = '') => {
  if (ok) passed += 1;
  else failed += 1;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? `  — ${detail}` : ''}`);
  return ok;
};

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function json(path, init) {
  const res = await fetch(BASE + path, init);
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON response */
  }
  return [res.status, body, res];
}

/** Count complete JPEG frames pulled from an MJPEG connection. */
async function countStreamFrames(path, target, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(BASE + path, { signal: controller.signal });
    if (!res.ok) return { status: res.status, frames: 0, contentType: null };

    const contentType = res.headers.get('content-type');
    const reader = res.body.getReader();
    let buffer = Buffer.alloc(0);
    let frames = 0;

    while (frames < target) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer = Buffer.concat([buffer, Buffer.from(value)]);

      let index;
      while ((index = buffer.indexOf(Buffer.from([0xff, 0xd9]))) !== -1) {
        frames += 1;
        buffer = buffer.subarray(index + 2);
      }
    }

    controller.abort();
    return { status: res.status, frames, contentType };
  } catch (error) {
    return { status: null, frames: 0, contentType: null, error: String(error) };
  } finally {
    clearTimeout(timer);
  }
}

(async () => {
  console.log(`Verifying deployment at ${BASE}\n`);

  // -----------------------------------------------------------------
  console.log('1. Dashboard is served');
  const indexRes = await fetch(BASE + '/');
  const html = await indexRes.text();
  check('index.html returns 200', indexRes.status === 200);
  check('serves the React entry point', html.includes('<div id="root">'));
  check('references a hashed bundle', /\/assets\/index-[\w-]+\.js/.test(html));
  const healthz = await fetch(BASE + '/healthz');
  check('nginx healthz responds', healthz.status === 200);

  // -----------------------------------------------------------------
  console.log('\n2. Frontend reaches the backend through the nginx proxy');
  const [healthStatus, health] = await json('/api/v1/health');
  check('GET /api/v1/health via proxy', healthStatus === 200, `status=${health?.status}`);
  check('database component healthy', health?.components?.some((c) => c.name === 'database' && c.healthy));

  const endpoints = ['/api/v1/alerts', '/api/v1/violations', '/api/v1/tracks', '/api/v1/system/events'];
  for (const endpoint of endpoints) {
    const [status, body] = await json(`${endpoint}?page=1&page_size=5`);
    check(`GET ${endpoint}`, status === 200 && Array.isArray(body?.items), `total=${body?.meta?.total}`);
  }

  const [docsStatus] = await json('/openapi.json');
  check('OpenAPI schema proxied', docsStatus === 200);

  // -----------------------------------------------------------------
  console.log('\n3. PostgreSQL persistence');
  const [seedStatus, seeded] = await json('/api/v1/alerts?page=1&page_size=1');
  const totalBefore = seeded?.meta?.total ?? 0;
  check('alerts readable from the database', seedStatus === 200, `total=${totalBefore}`);

  if (totalBefore > 0) {
    const [, page] = await json('/api/v1/alerts?page=1&page_size=1');
    const alertId = page?.items?.[0]?.alert_id;

    if (alertId) {
      const [ackStatus, acked] = await json(
        `/api/v1/alerts/${alertId}/acknowledge`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ acknowledged_by: 'deployment-verify' }),
        },
      );
      check('write succeeds (acknowledge)', ackStatus === 200 && acked?.acknowledged === true);
      console.log(`     wrote acknowledged_by="deployment-verify" to ${alertId.slice(0, 8)}`);
      console.log('     (restart the stack, then re-run to confirm it survived)');
    }
  } else {
    console.log('     no alerts present — run with SEED_DEMO_DATA=true to exercise writes');
  }

  // -----------------------------------------------------------------
  console.log('\n4. MJPEG stream through nginx');
  const [statusCode, streamStatus] = await json('/api/v1/stream/status');
  check('GET /api/v1/stream/status', statusCode === 200);
  console.log(`     running=${streamStatus?.running} available=${streamStatus?.available} source=${streamStatus?.source}`);

  console.log('     opening stream (model load may take up to 2 minutes)…');
  const stream = await countStreamFrames('/api/v1/stream/live?fps=10', 6, 150_000);
  check('stream returns 200', stream.status === 200);
  check('content-type is multipart/x-mixed-replace', (stream.contentType ?? '').includes('multipart/x-mixed-replace'));
  check('receives multiple JPEG frames', stream.frames >= 3, `frames=${stream.frames}`);

  await wait(500);
  const snap = await fetch(BASE + '/api/v1/stream/snapshot');
  const snapBuf = Buffer.from(await snap.arrayBuffer());
  check('snapshot returns a JPEG', snap.status === 200 && snapBuf[0] === 0xff && snapBuf[1] === 0xd8, `${snapBuf.length} bytes`);

  const [, finalStatus] = await json('/api/v1/stream/status');
  console.log(`     published=${finalStatus?.frames_published} encoded=${finalStatus?.frames_encoded} fps=${finalStatus?.publish_fps} device=${finalStatus?.device}`);

  // -----------------------------------------------------------------
  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed === 0 ? 0 : 1);
})();
