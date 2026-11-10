"""Verify the shipped model and render evidence from the repository root."""
import json,hashlib
from pathlib import Path
from PIL import Image
BASE=Path(__file__).resolve().parent
read=lambda name:json.loads((BASE/name).read_text())
a=read('acceptance.json');r=read('final/report.json')
assert r['passed'] and r['atlas_pixels']==[4368,3120]
assert Image.open(BASE/'final/atlas.png').size==(4368,3120)
assert r['metrics']['foreground_coverage']==1
assert r['artwork']['uv_crop']==[0,0,1,1]
assert r['artwork']['architectural_geometry']['projected_decoration_guard_all_pass']
assert read('final/saved-scene-verification.json')['packed_png_identical_to_original']
assert read('visibility/visibility.json')['all_groups_visible_on_led']
assert read('ui-check.json')['passed']
assert '154 passed' in (BASE/'tests.txt').read_text()
for entry in read('manifest.json')['files']:
 data=(BASE/entry['path']).read_bytes()
 assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256'],entry['path']
print('SYMPHONY_DELIVERY_PASS: full LED, original packed PNG, actual mesh layers, visibility, browser and tests')
