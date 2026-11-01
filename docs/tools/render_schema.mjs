// Optional documentation renderer; no application dependency.
// npm install --prefix /tmp/gnosis-diagram-runtime @viz-js/viz@3.9.0 @resvg/resvg-js@2.6.2
// node docs/tools/render_schema.mjs /tmp/gnosis-diagram-runtime
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';
const runtime = process.argv[2];
if (!runtime) throw new Error('Pass the directory containing the optional renderer node_modules.');
const {instance} = await import(pathToFileURL(path.resolve(runtime, 'node_modules/@viz-js/viz/lib/viz-standalone.mjs')));
const {Resvg} = await import(pathToFileURL(path.resolve(runtime, 'node_modules/@resvg/resvg-js/index.js')));
const viz = await instance();
const diagrams = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../diagrams');
for (const file of (await fs.readdir(diagrams)).filter(f => f.endsWith('.dot'))) {
    const stem = file.slice(0, -4);
    const svg = viz.renderString(await fs.readFile(path.join(diagrams, file), 'utf8'), {format:'svg', engine:'dot'});
    await fs.writeFile(path.join(diagrams, stem+'.svg'), svg);
    const png = new Resvg(svg, {fitTo:{mode:'width', value:2400}}).render().asPng();
    await fs.writeFile(path.join(diagrams, stem+'.png'), png);
}
console.log('Rendered four SVG exports and PNG previews from the same inventory as Mermaid.');
