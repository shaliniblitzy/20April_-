// test/hello.test.js — Smoke test for the GET /hello endpoint.
//
// Verifies the tutorial's single feature promise: GET /hello returns HTTP 200
// with the plain-text body "Hello world" and a Content-Type of "text/plain".
// Uses ONLY Node.js built-ins (node:test, node:assert, node:http,
// node:child_process, node:path) so the project stays zero-devDependency.
//
// Strategy: spawn server.js on a fixed test-only port (3001), wait for the
// TCP listener, issue a real HTTP GET /hello, assert, then kill the child.

// Built-in imports (Rule R-8 — no npm packages allowed in this file).
const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const { spawn } = require('node:child_process');
const path = require('node:path');

// Fixed test-only port. Using 3001 to avoid collision with the default
// development port (3000). The server reads PORT from process.env and binds
// here when we spawn it below. If 3001 is occupied the test fails with a
// clear ECONNREFUSED — free the port or change TEST_PORT.
const TEST_PORT = 3001;

// httpGet: issue an HTTP GET and resolve with { statusCode, headers, body }.
// Wraps http.request in a Promise so the test can use async/await. The body
// is collected as a UTF-8 string before resolving; any request error rejects.
function httpGet(hostname, port, requestPath) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      { hostname, port, path: requestPath, method: 'GET' },
      (res) => {
        let body = '';
        res.setEncoding('utf8');
        res.on('data', (chunk) => { body += chunk; });
        res.on('end', () => {
          resolve({ statusCode: res.statusCode, headers: res.headers, body });
        });
      }
    );
    req.on('error', reject);
    req.end();
  });
}

// waitForServer: poll the port every 100ms until any HTTP response confirms
// the TCP listener is up, or until timeoutMs elapses. Using a connect-retry
// loop (not a fixed sleep) makes the test reliable across slow and fast hosts.
async function waitForServer(port, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.request(
          { hostname: 'localhost', port, path: '/', method: 'GET' },
          (res) => {
            res.resume(); // drain the body to free the socket
            resolve();
          }
        );
        req.on('error', reject);
        req.end();
      });
      return; // Any successful HTTP round-trip means the server is ready.
    } catch (err) {
      // ECONNREFUSED, ECONNRESET, etc. — server not ready yet; retry.
      await new Promise((r) => setTimeout(r, 100));
    }
  }
  throw new Error(`Server on port ${port} did not become ready within ${timeoutMs}ms`);
}

test('GET /hello returns 200 with body "Hello world" and Content-Type text/plain', async (t) => {
  // Resolve the path to server.js: test/hello.test.js → ../server.js.
  const serverPath = path.join(__dirname, '..', 'server.js');

  // Spawn the Express server as an independent Node.js child process.
  //   process.execPath: reuse the same Node.js binary running this test.
  //   env.PORT:         override to our test-only port (inherit the rest).
  //   stdio:            ignore stdin; pipe stdout/stderr so the child does
  //                     not inherit the test runner's TTY.
  const child = spawn(process.execPath, [serverPath], {
    env: { ...process.env, PORT: String(TEST_PORT) },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  // Register teardown BEFORE any await so it runs even if the test throws.
  // The exitCode/killed guard avoids a redundant SIGTERM after the process
  // has already exited on its own.
  t.after(() => {
    if (child.exitCode === null && !child.killed) {
      child.kill('SIGTERM');
    }
  });

  // Wait up to 5 seconds for the subprocess to start accepting HTTP connections.
  await waitForServer(TEST_PORT, 5000);

  // Issue the real GET /hello request against the spawned server.
  const res = await httpGet('localhost', TEST_PORT, '/hello');

  // Express's res.send() defaults to HTTP 200 OK when no status is set.
  assert.equal(res.statusCode, 200, 'Expected HTTP 200 OK for GET /hello');

  // Rule R-1: body must be the exact literal 11-character string "Hello world".
  assert.equal(res.body, 'Hello world', 'Expected response body to be exactly "Hello world"');

  // Rule R-9: Content-Type must include "text/plain" (full value is typically
  // "text/plain; charset=utf-8"), so a regex substring match is appropriate.
  assert.match(
    res.headers['content-type'] || '',
    /text\/plain/,
    'Expected Content-Type header to include "text/plain"'
  );
});
