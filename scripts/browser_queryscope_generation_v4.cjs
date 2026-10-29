/* Compatibility entry point for the current case-review UI browser suite. */
const {spawnSync} = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const output = process.env.QUERYSCOPE_BROWSER_OUTPUT || path.join(root, 'work', 'workbench-browser');
const result = spawnSync(process.env.QUERYSCOPE_PYTHON || 'python', [path.join(__dirname, 'browser_queryscope_workbench.py'), '--output', output], {cwd: root, env: process.env, stdio: 'inherit'});
if (result.error) console.error(result.error.message);
process.exit(result.status === null ? 1 : result.status);
