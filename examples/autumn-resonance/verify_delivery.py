"""Verify the shipped evidence; run with .venv/bin/python from repository root."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'examples/autumn-resonance'
read = lambda p: json.loads((BASE / p).read_text())
final = read('final/report.json')
assert final['passed'] and final['atlas_pixels'] == [4368, 3120]
assert Image.open(BASE / 'final/atlas.png').size == (4368, 3120)
assert final['metrics']['foreground_coverage'] == 1
assert read('final/saved-blend-verification.json')['status'] == 'PASS'
assert read('control-bindings.json')['passed']
assert read('variants/balanced/face-visibility.json')['all_five_visible']
assert read('ui-check.json')['passed']
variant_geometries=[]
for v in ['balanced','warm','cool']:
    r=read(f'variants/{v}/report.json')
    assert r['passed'] and r['engine'].endswith('CYCLES')
    variant_geometries.append((r['config']['camera'],r['config']['screen'],r['artwork']['composition'],r['artwork']['architectural_geometry']))
assert variant_geometries[0] == variant_geometries[1] == variant_geometries[2]
animation=read('motion-preview/animation.json')
assert animation['passed'] and len(animation['frames']) == 180
assert all(f['geometry']['passed'] for f in animation['frames'])
assert len(animation['verification']) == 7
assert read('motion-preview/saved-animation-verification.json')['passed']
for kind in ['view','led']:
    probe=read(f'motion-preview/{kind}-ffprobe.json')
    stream=next(s for s in probe['streams'] if s['codec_type']=='video')
    assert int(stream['nb_frames']) == 180
    assert stream['r_frame_rate'] == '24/1'
    assert abs(float(stream['duration'])-7.5)<1e-5
    assert [stream['width'],stream['height']] == [546,390]
assert '139 passed' in (BASE/'tests.txt').read_text()
print('DELIVERY_EVIDENCE_PASS: full atlas, same-geometry variants, full-UV shader, 5 faces, real controls, 180 frames, 7 remaps and tests')

manifest = read('manifest.json')
for entry in manifest['files']:
    payload = (BASE / entry['path']).read_bytes()
    assert len(payload) == entry['bytes']
    assert hashlib.sha256(payload).hexdigest() == entry['sha256'], entry['path']
print('MANIFEST_HASHES_PASS:', len(manifest['files']))
