import shutil
import subprocess
from pathlib import Path

import pytest


def test_older_replica_snapshots_cannot_overwrite_newer_live_activity():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for the dashboard JavaScript regression test')
    html = (Path(__file__).parents[1] / 'voiceflow/web/ui/index.html').read_text()
    code = html.split('let latestStatusTimestamp = -1;', 1)[1].split('function updateLiveSession', 1)[0]
    script = '''
const assert = require('node:assert/strict');
const elements = {'status-dot':{}, 'status-text':{}};
const document = {getElementById: id => elements[id]};
let latestStatusTimestamp = -1;
''' + code + '''
updateStatusDot('recording', 1000);
updateStatusDot('idle', 0); // Another replica has never handled this activity.
assert.equal(elements['status-text'].textContent, 'Recording…');
updateStatusDot('processing', 2000);
updateStatusDot('recording', 1000); // An older request completed late.
assert.equal(elements['status-text'].textContent, 'Processing…');
updateStatusDot('idle', 3000);
updateStatusDot('processing', 2000);
updateStatusDot(undefined, 9999); // Failed or unauthorized status response.
assert.equal(elements['status-text'].textContent, 'Idle');
'''
    subprocess.run([node, '-e', script], check=True, capture_output=True, text=True)
