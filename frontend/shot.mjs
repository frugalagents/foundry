import { chromium } from 'playwright';
import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { extname, join } from 'node:path';

const ROOT = new URL('./out/', import.meta.url).pathname;
const PORT = 4599;
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.png': 'image/png', '.ico': 'image/x-icon', '.txt': 'text/plain' };

const server = http.createServer(async (req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p.endsWith('/')) p += 'index.html';
  let file = join(ROOT, p);
  if (!existsSync(file)) { // try trailing-slash export dir
    const alt = join(ROOT, p + '/index.html');
    if (existsSync(alt)) file = alt; else if (existsSync(file + '.html')) file += '.html';
  }
  try {
    const buf = await readFile(file);
    res.writeHead(200, { 'content-type': MIME[extname(file)] ?? 'application/octet-stream' });
    res.end(buf);
  } catch { res.writeHead(404); res.end('nf: ' + p); }
});
await new Promise((r) => server.listen(PORT, r));

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1680, height: 1000 }, deviceScaleFactor: 2 });
// Fake, unsigned JWT with a far-future exp so the client auth guard passes.
const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
const jwt = `${b64({ alg: 'none' })}.${b64({ exp: 4102444800, email: 'demo@local', 'cognito:groups': ['admin'] })}.x`;
await context.addCookies([
  { name: 'id_token', value: jwt, domain: 'localhost', path: '/' },
  { name: 'access_token', value: jwt, domain: 'localhost', path: '/' },
]);
const page = await context.newPage();
page.on('console', (m) => { if (m.type() === 'error') console.log('PAGE ERR:', m.text()); });
page.on('pageerror', (e) => console.log('PAGE EXC:', e.message));

const url = `http://localhost:${PORT}/architecture/?type=coding&bp=${encodeURIComponent('Acme coding platform')}&desc=${encodeURIComponent('Enterprise coding agents')}`;
await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForTimeout(2500); // let React Flow lay out + fitView

await page.screenshot({ path: '/tmp/canvas.png' });
console.log('shot: /tmp/canvas.png');

// selected-block view: click the Model Providers node
const prov = page.locator('text=Model Providers').first();
if (await prov.count()) { await prov.click(); await page.waitForTimeout(800); await page.screenshot({ path: '/tmp/canvas-sel.png' }); console.log('shot: /tmp/canvas-sel.png'); }

await browser.close();
server.close();
