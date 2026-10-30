# 짭새 모델 생성 스크립트 (Blender 4.x)
#
#   blender -b -P tools/bird.py -- out/bird.glb            # 모델만 내보내기
#   blender -b -P tools/bird.py -- out/bird.glb --render    # + 미리보기 PNG (out/bird_*.png)
#
# 내보낸 .glb 는 index.html 맨 아래 <script id="bird-glb"> 에 base64 로 넣는다:
#   base64 -i out/bird.glb   (결과로 그 블록 내용을 통째로 교체)
#
# 좌표는 전부 게임(three.js) 기준으로 적는다: Y 위, -Z 가 새의 정면.
# 부품마다 원점 = 게임 코드의 관절 위치(Bird._build 참고). 게임은 원점에 붙이기만 한다.

import bpy, bmesh, math, sys, os
from mathutils import Vector

#   열려 있는 블렌더에서 돌리면 장면은 그대로 두고 'jjapbird' 컬렉션에만 새를 다시 만든다(내보내기 없음)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else None
RENDER = '--render' in argv

if bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
COLL = bpy.data.collections.get('jjapbird')
if COLL:   # 이전에 만든 새만 지운다
    for ob in list(COLL.objects):
        me = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
else:
    COLL = bpy.data.collections.new('jjapbird')
    bpy.context.scene.collection.children.link(COLL)

# three (x, y, z) → blender (x, -z, y). glTF 내보내기가 다시 Y-up 으로 돌려준다
def B(p): return Vector((p[0], -p[2], p[1]))

# ── 색 (게임 COLORS 와 같은 계열) ──
PALETTE = {
    'body': 0x8a5a3b, 'back': 0x6e4630, 'belly': 0xead7b4, 'head': 0x6e4630,
    'cheek': 0xf3ead8, 'bib': 0x2a1d16, 'beak': 0xf2b33d, 'eye': 0x141414, 'shine': 0xffffff,
    'wingIn': 0x7a4e30, 'wingBar': 0xf1e2c2, 'wingOut': 0x4a3222, 'tail': 0x5a3b27,
    'feet': 0xd9944a,
}
def srgb_to_lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

MATS = {}
def mat(name):
    if name not in MATS:
        h = PALETTE[name]
        rgb = [srgb_to_lin((h >> s) & 255) for s in (16, 8, 0)]
        m = bpy.data.materials.get('jj_' + name) or bpy.data.materials.new('jj_' + name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes['Principled BSDF']
        bsdf.inputs['Base Color'].default_value = (*rgb, 1)
        bsdf.inputs['Roughness'].default_value = 0.85
        bsdf.inputs['Metallic'].default_value = 0
        m.diffuse_color = (*rgb, 1)  # 워크벤치 미리보기용
        MATS[name] = m
    return MATS[name]

# ── 부품 하나 = 메시 하나(여러 재질). 좌표는 관절 기준 상대값 ──
class Part:
    def __init__(self, name, pivot):
        self.name, self.pivot = name, pivot
        self.verts, self.faces, self.fmat, self.mats = [], [], [], []

    def _mi(self, m):
        if m not in self.mats: self.mats.append(m)
        return self.mats.index(m)

    def face(self, idx, m): self.faces.append(idx); self.fmat.append(self._mi(m))

    def sphere(self, c, r, m, seg=10, rings=8, paint=None, warp=None):
        """타원체. paint(face_center_rel, i) → 재질 이름 (없으면 m), warp(x,y,z) → 모양 변형"""
        base = len(self.verts)
        w = warp or (lambda x, y, z: (x, y, z))
        put = lambda x, y, z: self.verts.append(tuple(c[a] + v for a, v in enumerate(w(x, y, z))))
        put(0, r[1], 0)
        for i in range(1, rings):
            th = math.pi * i / rings
            for j in range(seg):
                ph = 2 * math.pi * j / seg
                put(r[0] * math.sin(th) * math.cos(ph), r[1] * math.cos(th), r[2] * math.sin(th) * math.sin(ph))
        bot = len(self.verts); put(0, -r[1], 0)
        ring = lambda i, j: base + 1 + (i - 1) * seg + j % seg
        quads = [[base, ring(1, j + 1), ring(1, j)] for j in range(seg)]
        for i in range(1, rings - 1):
            quads += [[ring(i, j), ring(i, j + 1), ring(i + 1, j + 1), ring(i + 1, j)] for j in range(seg)]
        quads += [[ring(rings - 1, j), ring(rings - 1, j + 1), bot] for j in range(seg)]
        for k, f in enumerate(quads):
            ctr = [sum(self.verts[v][a] for v in f) / len(f) - c[a] for a in range(3)]
            self.face(f, (paint and paint(ctr, k)) or m)

    def cone(self, base_c, tip, radius, m, seg=6, squash=1.0):
        bc, tp = Vector(base_c), Vector(tip)
        ax = (tp - bc).normalized()
        u = ax.cross(Vector((0, 1, 0)) if abs(ax.y) < 0.9 else Vector((1, 0, 0))).normalized()
        v = ax.cross(u)
        b0 = len(self.verts)
        for j in range(seg):
            a = 2 * math.pi * j / seg
            self.verts.append(tuple(bc + u * math.cos(a) * radius + v * math.sin(a) * radius * squash))
        t = len(self.verts); self.verts.append(tuple(tp))
        for j in range(seg): self.face([b0 + j, b0 + (j + 1) % seg, t], m)
        self.face([b0 + j for j in reversed(range(seg))], m)

    def slab(self, outline, y, thick, m, xform=lambda x, z: (x, z)):
        """XZ 평면 다각형을 두께 thick 로 세운 판. outline=[(x,z)], xform 으로 회전·이동"""
        pts = [xform(x, z) for x, z in outline]
        n, b0 = len(pts), len(self.verts)
        for dy in (thick / 2, -thick / 2):
            for x, z in pts: self.verts.append((x, y + dy, z))
        self.face(list(range(b0, b0 + n)), m)
        self.face(list(reversed(range(b0 + n, b0 + 2 * n))), m)
        for i in range(n):
            j = (i + 1) % n
            self.face([b0 + i, b0 + n + i, b0 + n + j, b0 + j], m)

    def build(self):
        me = bpy.data.meshes.new(self.name + '_mesh')
        me.from_pydata([tuple(B(v)) for v in self.verts], [], self.faces)
        for name in self.mats: me.materials.append(mat(name))
        for poly, mi in zip(me.polygons, self.fmat): poly.material_index = mi
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)   # 껍질마다 바깥쪽 법선
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(self.name, me)
        ob.location = B(self.pivot)
        COLL.objects.link(ob)
        return ob

def rot(a, ox=0.0, oz=0.0, sx=1):
    """XZ 평면에서 a 라디안 회전(+면 뒤쪽으로 젖힘) 후 (ox,oz) 로 이동, sx=-1 이면 좌우 반전"""
    c, s = math.cos(a), math.sin(a)
    return lambda x, z: (sx * (x * c - z * s + ox), x * s + z * c + oz)

def feather(L, W):
    """+X 방향으로 뻗은 깃털 윤곽 (끝이 둥글게 뾰족)"""
    return [(0, -W * 0.35), (L * 0.2, -W * 0.5), (L * 0.75, -W * 0.45), (L * 0.95, -W * 0.15), (L, 0.05 * W),
            (L * 0.85, W * 0.5), (L * 0.2, W * 0.5), (0, W * 0.35)]

# ── 몸통: 앞은 통통하고 꼬리 쪽으로 가늘어지는 물방울. 배는 크림색, 등에는 짙은 줄무늬, 작은 발 ──
body = Part('body', (0, 0, 0))
def body_paint(c, k):
    if c[1] < -0.04 and c[2] < 0.4: return 'belly'
    if c[1] > 0.2 and c[2] > -0.35 and k % 3 == 0: return 'back'
    return None
def body_warp(x, y, z):
    t = max(0.0, z / 0.64)              # 0(가운데) → 1(꼬리 끝)
    k = 1 - 0.38 * t * t
    return (x * k * (1.05 if z < 0 else 1), y * k + 0.06 * t * t, z)
body.sphere((0, 0, 0), (0.4, 0.36, 0.64), 'body', seg=12, rings=9, paint=body_paint, warp=body_warp)
for sx in (-1, 1):
    hip, ankle = (sx * 0.12, -0.28, 0.02), (sx * 0.12, -0.57, 0.08)   # 착지 시 발바닥 ≈ 땅(관절 -0.6)
    body.cone(hip, ankle, 0.035, 'feet', seg=4)
    for dx, dz in ((-0.05, -0.15), (0, -0.17), (0.05, -0.15), (0, 0.1)):   # 앞발가락 3 + 뒷발가락 1
        body.cone(ankle, (ankle[0] + sx * dx, -0.6, ankle[2] + dz), 0.022, 'feet', seg=4)
body.build()

# ── 머리: 갈색 정수리, 눈 뒤 밤색 줄, 흰 뺨, 까만 턱받이, 노란 부리, 큰 눈, 작은 깃 ──
head = Part('head', (0, 0.3, -0.68))
def head_paint(c, k):
    if abs(c[0]) < 0.13 and c[1] < -0.1 and c[2] < -0.05: return 'bib'
    if c[2] > -0.08 and 0.0 < c[1] < 0.16 and abs(c[0]) > 0.2: return 'body'
    if c[2] < 0.08 and c[1] < 0.06 and abs(c[0]) > 0.1: return 'cheek'
    return None
head.sphere((0, 0, 0), (0.32, 0.3, 0.33), 'head', seg=12, rings=9, paint=head_paint)
head.cone((0, 0.0, -0.27), (0, -0.05, -0.52), 0.1, 'beak', seg=6, squash=0.75)
for sx in (-1, 1):
    e = Vector((sx * 0.24, 0.08, -0.19))
    head.sphere(tuple(e), (0.078, 0.078, 0.078), 'eye', seg=8, rings=6)
    head.sphere(tuple(e + Vector((sx * 0.04, 0.035, -0.04))), (0.026, 0.026, 0.026), 'shine', seg=6, rings=4)
for dz, h in ((0.0, 0.1), (0.09, 0.07)):   # 머리 깃 (살짝 삐친 정도)
    head.cone((0, 0.27, dz), (0, 0.27 + h, dz + 0.1), 0.05, 'head', seg=5)
head.build()

# ── 꼬리: 깃털 5장 부채꼴 ──
tail = Part('tail', (0, 0.08, 0.55))
for i, a in enumerate((-0.38, -0.19, 0, 0.19, 0.38)):
    L = 0.82 - abs(a) * 0.35
    tail.slab(feather(L, 0.17), 0.012 * (2 - abs(i - 2)), 0.035,
              'tail' if i % 2 == 0 else 'wingOut', rot(math.pi / 2 + a))
tail.build()

# ── 날개: 안쪽 판(어깨 관절) + 바깥쪽 첫째날개깃(팔꿈치 관절). 좌우 대칭 ──
for sx, side in ((-1, 'L'), (1, 'R')):
    inner = Part('wingInner_' + side, (sx * 0.3, 0.14, -0.12))
    mirror = lambda x, z, sx=sx: (sx * x, z)
    inner.slab([(0, -0.26), (0.3, -0.3), (0.75, -0.22), (0.75, 0.36), (0.45, 0.4), (0, 0.34)],
               0, 0.07, 'wingIn', mirror)
    for i in range(5):   # 흰 날개띠: 작은 덮깃 한 줄
        inner.slab(feather(0.17, 0.12), 0.04, 0.02, 'wingBar', rot(math.pi / 2, 0.1 + i * 0.13, -0.02, sx))
    for i in range(5):   # 뒷전의 둘째날개깃
        x0 = 0.06 + i * 0.15
        inner.slab(feather(0.3, 0.17), -0.02, 0.03, 'wingOut', rot(math.pi / 2 - 0.15, x0, 0.25, sx))
    inner.build()

    outer = Part('wingOuter_' + side, (sx * (0.3 + 0.75), 0.14, -0.12))
    outer.slab([(0, -0.22), (0.3, -0.2), (0.3, 0.36), (0, 0.38)], 0, 0.06, 'wingIn', mirror)
    for i, (z0, a, L) in enumerate(((-0.14, 0.0, 0.92), (-0.02, 0.13, 0.86), (0.1, 0.27, 0.78),
                                    (0.21, 0.42, 0.68), (0.31, 0.58, 0.56))):
        outer.slab(feather(L, 0.17), -0.006 * i, 0.035, 'wingOut', rot(a, 0.12, z0, sx))
    outer.build()

if OUT:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in COLL.objects: ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_yup=True, use_selection=True,
                              export_texcoords=False, export_animations=False)
    print('EXPORTED', OUT, os.path.getsize(OUT), 'bytes')

if RENDER and OUT:
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.show_shadows = True
    sc.render.resolution_x = sc.render.resolution_y = 640
    sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.62, 0.83, 0.96)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    target = B((0, 0.1, 0))
    for name, eye in (('front', (2.2, 1.4, -3.2)), ('side', (4.2, 0.6, 0.2)), ('back', (-2.4, 2.4, 3.6))):
        cam.location = B(eye)
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(os.path.dirname(OUT), f'bird_{name}.png')
        bpy.ops.render.render(write_still=True)
    print('RENDERED')
