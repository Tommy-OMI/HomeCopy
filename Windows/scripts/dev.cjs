const { spawn } = require('node:child_process');
const { join } = require('node:path');

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;

const cli = join(__dirname, '..', 'node_modules', 'electron-vite', 'dist', 'cli.js');
const child = spawn(process.execPath, [cli, 'dev'], {
  cwd: join(__dirname, '..'),
  env,
  stdio: 'inherit',
  shell: false
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exit(code ?? 0);
});
