import json, subprocess, sys, hashlib
from pathlib import Path
folder=Path(sys.argv[1]); fps=int(sys.argv[2]); expected=int(sys.argv[3]); duration=float(sys.argv[4])
r=json.loads((folder/'report.json').read_text());d=r['dynamics'];assert r['passed'] and d['passed'];assert len(d['frames'])==expected
color='scale=in_range=pc:out_range=tv:out_color_matrix=bt709,pad=ceil(iw/2)*2:ceil(ih/2)*2,setparams=range=limited:color_primaries=bt709:color_trc=iec61966-2-1:colorspace=bt709'
probes={}
for kind, video in [('led', 'led.mp4'), ('view','target.mp4')]:
    images=sorted((folder/'frames').glob(kind+'_*.png'));assert len(images)==expected
    cmd=['ffmpeg','-y','-framerate',str(fps),'-i',str(folder/'frames'/(kind+'_%04d.png')),'-t',str(duration),'-r',str(fps),'-c:v','libx264','-pix_fmt','yuv420p','-vf',color,'-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','iec61966-2-1','-movflags','+faststart',str(folder/video)]
    with (folder/(kind+'-encode.log')).open('w') as log: subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=log,check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(folder/video)]))
    (folder/(kind+'-ffprobe.json')).write_text(json.dumps(probe,indent=2))
    stream=probe['streams'][0];assert int(stream['nb_read_frames'])==expected;assert (stream['width'],stream['height'])==(546,390);assert abs(float(probe['format']['duration'])-duration)<.01
    probes[video]={'frames':int(stream['nb_read_frames']),'width':stream['width'],'height':stream['height'],'duration_s':float(probe['format']['duration']),'fps':stream['r_frame_rate'],'color_range':stream['color_range'],'color_space':stream['color_space']}
hold=[f for f in d['frames'] if f['motion']['stage']=='stable_hold']
assert len({tuple(f['translation_m']) for f in hold})==1
assert len({tuple(f['light_energies_w']) for f in hold})==1
hashes={k:len({hashlib.sha256((folder/'frames'/(k+'_%04d.png'%f['index'])).read_bytes()).hexdigest() for f in hold}) for k in ('view','led')}
summary={'passed':True,'render_engine':r['engine'],'poster_original_pixels':r['artwork']['poster_original_pixels'],'timing':d['timing'],'verification':d['verification_summary'],'numeric_checks':d['verification'],'all_frame_geometry_passed':all(f['geometry']['passed'] for f in d['frames']),'min_front_clearance_m':min(f['geometry']['front_safety_clearance_m'] for f in d['frames']),'min_rear_clearance_m':min(f['geometry']['rear_clearance_m'] for f in d['frames']),'min_opening_margin_ndc':min(f['geometry']['opening_margin_ndc'] for f in d['frames']),'hold_frames':len(hold),'hold_transform_light_fixed':True,'hold_unique_png_hashes':hashes,'videos':probes,'labels':{'led.mp4':'Inverse-projected LED canvas animation','target.mp4':'3D scene animation; direct source camera view, not independently re-rendered LED simulation'},'elapsed_render_seconds':r['elapsed_seconds'],'limitations':['Preview uses eight Cycles samples per actual 3D frame at 1/8 nominal pixel resolution.','Independent LED camera and coverage checks are sampled checkpoints; all-frame geometry safety is analytic.','Nominal screen geometry is not field calibration.']}
(folder/'motion-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
