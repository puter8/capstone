"""Apply only the three model settings to the existing local backend dotenv."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'data/models/full-corpus-fhc/improvement/release_candidate'


def main():
    validation = json.loads((TARGET / 'prototype_validation.json').read_text(encoding='utf-8'))
    assert validation['status'] == 'PASS_LOCAL_PROTOTYPE_MODEL_AND_BACKEND_INFERENCE'
    assert all(v <= 13 for v in validation['mae'].values())
    assert hashlib.sha256((TARGET / 'model.joblib').read_bytes()).hexdigest() == validation['model_sha256']
    settings = {
        'PALLY_AXIS_ANALYZER': 'researched',
        'PALLY_RESEARCHED_MODEL_PATH': 'data/models/full-corpus-fhc/improvement/release_candidate/model.joblib',
        'PALLY_RESEARCHED_ENCODER_PATH': 'data/models/minilm-base',
    }
    path = ROOT / 'backend/.env'
    original = path.read_bytes()
    content = original.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in content else '\n'
    pattern = re.compile(r'^\s*(?:export\s+)?(' + '|'.join(settings) + r')\s*=')
    output, seen = [], set()
    for line in content.splitlines(keepends=True):
        match = pattern.match(line)
        if match:
            key = match.group(1)
            if key not in seen:
                output.append(key + '=' + settings[key] + newline)
                seen.add(key)
        else:
            output.append(line)
    for key, value in settings.items():
        if key not in seen:
            if output and not output[-1].endswith(('\n', '\r')):
                output.append(newline)
            output.append(key + '=' + value + newline)
    updated = ''.join(output).encode('utf-8')
    if original.startswith(b'\xef\xbb\xbf'):
        updated = b'\xef\xbb\xbf' + updated
    if path.read_bytes() != original:
        raise RuntimeError('Backend dotenv changed during activation')
    path.write_bytes(updated)
    from dotenv import dotenv_values
    actual = dotenv_values(path)
    assert all(actual.get(k) == v for k, v in settings.items())
    result = {'status': 'LOCAL_STARTUP_CONFIG_ACTIVATED', 'settings': settings,
              'model_sha256': validation['model_sha256'],
              'only_model_keys_changed': True, 'production_deployed': False,
              'existing_server_restarted': False,
              'note': 'A running backend must restart to load the new startup configuration.'}
    (TARGET / 'activation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
