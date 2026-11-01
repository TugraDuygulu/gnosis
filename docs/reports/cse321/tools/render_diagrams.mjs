// Optional: npm install --prefix /tmp/gnosis-diagram-runtime @viz-js/viz@3.9.0 @resvg/resvg-js@2.6.2
// node docs/reports/cse321/tools/render_diagrams.mjs /tmp/gnosis-diagram-runtime
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
const runtime=process.argv[2];
if(!runtime) throw new Error('Pass the optional documentation-renderer directory.');
const {instance}=await import(pathToFileURL(path.resolve(runtime,'node_modules/@viz-js/viz/lib/viz-standalone.mjs')));
const {Resvg}=await import(pathToFileURL(path.resolve(runtime,'node_modules/@resvg/resvg-js/index.js')));
const viz=await instance();
const dir=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../diagrams');
for(const name of (await fs.readdir(dir)).filter(n=>n.endsWith('.dot'))){
 const svg=viz.renderString(await fs.readFile(path.join(dir,name),'utf8'),{format:'svg',engine:'dot'});
 await fs.writeFile(path.join(dir,name.replace('.dot','.svg')),svg);
 await fs.writeFile(path.join(dir,name.replace('.dot','.png')),new Resvg(svg,{fitTo:{mode:'width',value:2000}}).render().asPng());
}
const workflow=await fs.readFile(path.join(dir,'grade-workflow.svg'),'utf8');
await fs.writeFile(path.join(dir,'grade-workflow.png'),new Resvg(workflow,{fitTo:{mode:'width',value:2400}}).render().asPng());
console.log('Rendered component/class views and the separately source-derived sequence export.');
