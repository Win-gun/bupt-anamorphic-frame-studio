from studio.scene_design import ring_mesh, FRAME_PROFILE, PRESETS


def test_profile_is_closed_manifold_miter_sweep():
    vv,ff=ring_mesh(8,4,.2)
    assert len(vv)==len(FRAME_PROFILE)*4
    edges={}
    for f in ff:
        for a,b in zip(f,f[1:]+f[:1]):
            e=tuple(sorted((a,b))); edges[e]=edges.get(e,0)+1
    assert set(edges.values())=={2}
    assert len({round(v[2],6) for v in vv})>=5
    assert max(x for x,y,z in vv)==4.2


def test_material_presets_are_physically_distinct():
    assert len(PRESETS)==6
    assert PRESETS['black_titanium']!=PRESETS['gold']
    assert PRESETS['glass'][1]==0


def test_sweep_outward_winding_positive_volume():
    import numpy as np
    vv,ff=ring_mesh(5,3,.18); v=np.asarray(vv)
    volume=0
    for face in ff:
        for i in range(1,len(face)-1):
            volume+=np.dot(v[face[0]],np.cross(v[face[i]],v[face[i+1]]))/6
    assert volume>0
    # Wide, horizontal, foremost molding face looks toward camera (+local Z).
    front=[]
    for f in ff:
        a,b,c=v[list(f[:3])]; n=np.cross(b-a,c-a)
        if min(v[list(f),2])>.04: front.append(n[2])
    assert any(z>0 for z in front)


def test_manual_artwork_contains_without_stretching():
    from studio.scene_design import artwork_size
    assert artwork_size(5,6,16/9,'manual')==(5,5/(16/9))
    assert artwork_size(5,6,16/9,'fill')==(5,6)
