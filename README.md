# 20April_-

A minimal Node.js tutorial project that exposes a single HTTP endpoint — `GET /hello` — which returns the plain-text body `Hello world`. It is built on [Express](https://expressjs.com/) 5.x running on the Node.js 22 LTS runtime and is intentionally kept tiny so that a first-time Node.js learner can read every file end-to-end.

## Prerequisites

- **Node.js 22.x LTS or later** (`>=22.0.0`) — download from [nodejs.org](https://nodejs.org/)
- **npm 10.x or later** — bundled with the Node.js 22 installer, no separate install required

Verify your versions before continuing:

```bash
node --version   # should print v22.x.x (or newer)
npm --version    # should print 10.x.x (or newer)
```

## Install

From the repository root, install the single runtime dependency (Express):

```bash
npm install
```

This reads `package.json`, downloads Express and its transitive dependencies into `node_modules/`, and writes `package-lock.json` to pin the exact dependency tree for reproducible installs.

## Run

Start the HTTP server with:

```bash
npm start
```

This runs `node server.js`. The server listens on port **`3000`** by default. If that port is already in use, set the `PORT` environment variable to override it (for example `PORT=8080 npm start`). On startup the server logs the following line to stdout:

```
Server is running on http://localhost:3000/
```

Press `Ctrl-C` to stop the server.

## Verify

With the server running, issue a request to the `/hello` endpoint using `curl` (or any HTTP client):

```bash
curl http://localhost:3000/hello
```

Expected output — the literal 11-character string, with no trailing newline added by the server:

```
Hello world
```

The HTTP response uses status `200 OK` and `Content-Type: text/plain; charset=utf-8`. Requests to any other path return the Express default `404 Not Found` response.

## Project Layout

| File | Purpose |
|------|---------|
| `server.js` | Express application entry point; registers the `/hello` route and binds the TCP listener |
| `package.json` | npm manifest declaring the `express` dependency, `npm start` / `npm test` scripts, and the `>=22.0.0` Node.js engine requirement |
| `package-lock.json` | Auto-generated lock file pinning the transitive dependency tree for reproducible installs |
| `.gitignore` | Excludes `node_modules/`, environment files, npm logs, and editor/OS artifacts from version control |
| `test/hello.test.js` | Smoke test using Node.js's built-in `node:test` runner to verify the `/hello` endpoint |
| `README.md` | This file |

## Testing

Run the smoke test with:

```bash
npm test
```

This invokes `node --test`, which discovers and executes files under `test/`. The test spawns `server.js` as a subprocess on port `3001` (by overriding the `PORT` environment variable), issues a `GET /hello` request, asserts that the response status is `200`, the body equals `Hello world`, and the `Content-Type` header includes `text/plain`, then cleanly terminates the subprocess with `SIGTERM`. The test relies solely on Node.js built-ins (`node:test`, `node:assert/strict`, `node:http`) — there are zero external test framework dependencies.
