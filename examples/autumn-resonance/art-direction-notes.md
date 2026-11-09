# Autumn Resonance art direction

All variants reuse the exact solid-facade/five-wall geometry and original flat, full-UV 4535 × 2551 artwork. Physical room coordinates feed every procedural material. Variants change only material tint and warm/cool light ratios.

## Actual iteration

First CPU Cycles 3.4.1 render at 0.25 / 64 samples showed an overexposed upper wash and excessive pink illumination. This image was overwritten during iteration; no first-pass image is claimed as retained. The lamp discs did not intersect walls. Reducing physical light power resolved the hotspot while preserving a soft rear-wall shadow.

Final balanced powers (W): ceiling 180, upper-left autumn 95, right smoky blue 85, lower stage reflection 45, rear wash 55, exterior facade 850. Disc diameters are constrained using their oriented analytical support, so the complete emitting surfaces fit the available cavity. The exterior lamp remains parallel to the facade at z=7 m.

Source-poster light colours are restrained artistic approximations of its upper-left autumn light, right stage light, and lower pink stage glow. This is not a claim of physically measured poster luminance.

Materials use sRGB-to-linear base colours, 185/m fine Noise, a narrow-range ColorRamp, Bump distance 0.25 mm and strength 0.30. All walls use the same room-aligned Object coordinate frame. Roughness: walls 0.82, rear 0.88, floor 0.74, cut 0.65; metallic 0; specular 0.18. The display image retains its original emission shader for readability.

The shared backing geometry is a 24 mm slab and 1 mm surface separation (total envelope 25 mm), with actual 6 mm bevel. Opening chamfer is 25 mm. Poster plane is 2.1 m behind the opening and 0.9 m in front of the rear wall.

## Observed visual assessment

Balanced, warm, and cool 0.25 / 64-sample renders were actually opened. Following correction, none showed the first-pass white hotspot, visible triangular emitter-plane artifacts, black rear walls, heavy grain or obvious gradient banding. Five interior surfaces are visible; the complete artwork remains the focus. Warm is slightly terracotta/pink, cool is grey-blue/lavender, balanced is recommended. Microtexture is deliberately subtle at normal viewing scale. Final full-resolution QA is a separate check; these preview observations do not establish full-output texture/moire quality.

`inspect_scene.py` independently reopens the saved editable Blender file. It checks actual linked shader inputs, shared coordinates, zero metallic, bump distance, complete original UVs and unchanged emission, actual bevel dimensions, and 2048 points on each actual transformed emitter circumference. `saved-blend-verification.json` records these results.
