// server.js — Minimal Node.js + Express tutorial server.
// Exposes GET /hello, responding with the plain-text body "Hello world".

// Import the Express framework (CommonJS require; Express 5.x is the ACTIVE LTS line).
const express = require('express');

// Instantiate an Express application — the central object that routes requests.
const app = express();

// Resolve the listening port: honor the PORT environment variable if set,
// otherwise fall back to 3000, the conventional default for Node.js tutorials.
const PORT = process.env.PORT || 3000;

// Register the single route: GET /hello -> 200 text/plain "Hello world".
// res.type() sets Content-Type: text/plain; charset=utf-8.
// res.send() writes the body and closes the response with default status 200.
app.get('/hello', (req, res) => {
  res.type('text/plain').send('Hello world');
});

// Bind the TCP listener. Express emits a 404 by default for any unmatched path.
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}/`);
});
