"""Verify public HTTPS upload and the native client's WSS protocol without logging credentials."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
import wave
from pathlib import Path

import numpy as np
import requests

from voiceflow.core.cloud_client import CloudTranscriptionSession


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True)
    parser.add_argument('--sample', type=Path, required=True)
    args = parser.parse_args()
    token = subprocess.check_output([
        'gcloud', 'secrets', 'versions', 'access', 'latest',
        '--secret=hush-team-token', '--project=hush-milestone-2-20260922',
    ], text=True).strip()
    base = f'https://{args.host}'
    headers = {'Authorization': f'Bearer {token}', 'Origin': base}
    readiness = requests.get(base + '/ready', timeout=20)
    readiness.raise_for_status()
    print(json.dumps({'readiness': readiness.json()}), flush=True)
    started = time.monotonic()
    response = requests.post(base + '/transcribe', data=args.sample.read_bytes(),
                             headers={**headers, 'Content-Type': 'audio/wav',
                                      'X-Hush-Filename': 'milestone5-https-verification.wav'},
                             timeout=90)
    response.raise_for_status()
    result = response.json()
    assert result.get('text') and result.get('history_id'), 'Upload did not produce saved speech'
    print(json.dumps({'https_upload': result, 'elapsed_seconds': round(time.monotonic() - started, 2)}), flush=True)
    with wave.open(str(args.sample)) as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, 16000)
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2').astype(np.float32) / 32768
    session = CloudTranscriptionSession(base_url=base, token=token,
                                       client_id='milestone5-verification', app_context={'app': 'Milestone 5'},
                                       cleanup_level='none').start()
    for offset in range(0, len(samples), 16000):
        session.send_audio(samples[offset:offset + 16000])
    final = session.finish()
    assert final.get('text'), 'WSS did not return a transcript'
    print(json.dumps({'wss_result': final, 'latency_ms': session.latency_metrics}), flush=True)
    history = requests.get(base + '/history?limit=50', headers=headers, timeout=20)
    history.raise_for_status()
    assert any(entry['id'] == result['history_id'] for entry in history.json())
    assert requests.get(base + '/history', timeout=20).status_code == 401
    redirect = requests.get(f'http://{args.host}/', allow_redirects=False, timeout=20)
    assert redirect.status_code == 301 and redirect.headers['Location'].startswith(base)
    print(json.dumps({'saved_history': True, 'unauthorized_history_rejected': True,
                      'http_redirect': redirect.status_code, 'location': redirect.headers['Location']}), flush=True)


if __name__ == '__main__':
    main()
