// Local stand-in for the Apps Script /exec URL, running the real relay/Code.gs.
// Usage: node tests/relay-server.js [port] [delayMs]   (prints "READY <port>")
const http = require('http');
const { makeContext } = require('./relay-harness');
const ctx = makeContext();
const port = parseInt(process.argv[2] || '0', 10), delay = parseInt(process.argv[3] || '0', 10);
let down = false;
const srv = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://x');
  const cors = { 'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json' };
  if (u.pathname === '/__down') { down = u.searchParams.get('v') === '1'; res.writeHead(200, cors); return res.end('{}'); }
  if (down) { res.writeHead(503, cors); return res.end('{}'); }
  let body = '';
  req.on('data', c => body += c);
  req.on('end', () => setTimeout(() => {
    const params = Object.fromEntries(u.searchParams.entries());
    const out = req.method === 'POST' ? ctx.doPost({ parameter: params, postData: { contents: body } }) : ctx.doGet({ parameter: params });
    res.writeHead(200, cors); res.end(out.getContent());
  }, delay));
});
srv.listen(port, '127.0.0.1', () => console.log('READY ' + srv.address().port));
