# 30April_12345

A minimal Node.js HTTP tutorial built with **Express.js**. The server exposes two HTTP `GET` endpoints — `/` returning `Hello world` and `/good-evening` returning `Good evening` — and listens on a configurable TCP port. The project is intentionally tutorial-scoped: a single application file, a single runtime dependency, and no build step.

## Prerequisites

- **Node.js version 18 or higher** (matches the `engines.node` constraint declared in `package.json`).
- **npm**, which is bundled with Node.js.

## Installation

```bash
npm install
```

This installs the `express` runtime dependency declared in `package.json`.

## Running the Server

```bash
npm start
```

The `start` script maps to `node server.js`. By default, the server listens on port **3000**. The port can be overridden by setting the `PORT` environment variable before launching the server:

```bash
PORT=8080 npm start
```

## Endpoints

| Method | Path            | Response body  |
| ------ | --------------- | -------------- |
| `GET`  | `/`             | `Hello world`  |
| `GET`  | `/good-evening` | `Good evening` |

## Usage Examples

```bash
curl http://localhost:3000/
# => Hello world

curl http://localhost:3000/good-evening
# => Good evening
```
