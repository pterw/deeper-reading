import {mkdirSync, rmdirSync} from 'node:fs';
import path from 'node:path';
import {InstallerError, physicalPath} from './manifest.js';

// Shared with Python _target_lock: atomic mkdir, sibling of the physical
// target, fail on contention. No timeout/PID-based stealing of live locks.
export function withTargetLock(targetRoot, operation) {
  const target = physicalPath(targetRoot);
  const lock = path.join(path.dirname(target), `.${path.basename(target)}.install-lock`);
  try {
    mkdirSync(path.dirname(target), {recursive:true});
    mkdirSync(lock);
  } catch (error) {
    if (error.code === 'EEXIST') {
      throw new InstallerError(`installation target is locked: ${lock}; retry after the active operation finishes`);
    }
    throw new InstallerError(`cannot acquire installation lock: ${lock}: ${error.message}`);
  }
  try {
    return operation(target);
  } finally {
    // Release only a directory this invocation created; never recursive delete.
    try { rmdirSync(lock); }
    catch (error) { throw new InstallerError(`cannot release installation lock: ${lock}: ${error.message}`); }
  }
}
