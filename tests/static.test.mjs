import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const glb = fs.readFileSync(new URL('../rigged_hand.glb', import.meta.url));
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];

assert.ok(script, 'inline JavaScript exists');
new Function(script);
assert.equal(glb.subarray(0, 4).toString(), 'glTF', 'GLB magic');
assert.ok(glb.length < 2_000_000, 'mobile GLB is under 2 MB');

for (const id of ['display-mode', 'mirror-toggle', 's-model-scale', 's-smoothing', 's-curl']) {
  assert.match(html, new RegExp(`id=["']${id}["']`), `${id} control exists`);
}
for (const mode of ['camera', 'overlay', 'model', 'landmarks', 'skeleton']) {
  assert.match(html, new RegExp(`value=["']${mode}["']`), `${mode} mode exists`);
}
for (const bone of ['wristR', 'handR', 'thumb3R', 'index3R', 'middle3R', 'ring3R', 'pinky3R']) {
  assert.match(html, new RegExp(`\\b${bone}\\b`), `${bone} mapping exists`);
}
assert.match(html, /new THREE\.GLTFLoader\(\)\.load\('rigged_hand\.glb'/, 'rigged GLB path');
assert.match(html, /Emma L\. D\. Lieker/, 'downloaded model attribution exists');
assert.match(html, /CC BY-NC 4\.0/, 'downloaded model license exists');
console.log('static.test.mjs: PASS');
