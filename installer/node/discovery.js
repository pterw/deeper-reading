// Keep these host contracts in parity with installer/adapters/discovery.py.
// Unknown output fails closed; names in descriptions/paths are never evidence.
export function discoveryState(host, output, skillName) {
  if (host === 'copilot') {
    let rows;
    try { rows = JSON.parse(output); } catch { return 'failed'; }
    if (!Array.isArray(rows) || rows.some(row => !row || typeof row !== 'object'
      || typeof row.name !== 'string' || !row.name || typeof row.enabled !== 'boolean')) return 'failed';
    return rows.some(row => row.name === skillName && row.enabled) ? 'verified' : 'missing';
  }
  const lines = output.replace(/\x1b\[[0-9;]*m/g, '').split(/\r?\n/);
  if (lines.at(-1) === '') lines.pop();
  if (lines.length === 1 && lines[0] === 'No skills discovered.') return 'missing';
  if (lines[0] !== 'Discovered Agent Skills:') return 'failed';
  let found = false, count = 0, index = 1;
  while (index < lines.length) {
    if (!lines[index].trim()) {index++; continue;}
    const record = /^(\S+) \[(Enabled|Disabled)\](?: \[Built-in\])?$/.exec(lines[index]);
    if (!record || index + 2 >= lines.length || !lines[index + 1].startsWith('  Description: ')) return 'failed';
    index += 2;
    while (index < lines.length && !lines[index].startsWith('  Location:    ')) index++;
    if (index === lines.length || !lines[index].slice(15).trim()) return 'failed';
    found ||= record[1] === skillName && record[2] === 'Enabled';
    count++;
    index++;
    if (index < lines.length && lines[index].trim()) return 'failed';
  }
  return count ? (found ? 'verified' : 'missing') : 'failed';
}
