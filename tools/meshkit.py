# 블렌더 모델 스크립트 공용 도구 (bird.py, assets.py 가 사용)
# 좌표는 게임(three.js) 기준: Y 위, -Z 정면. 블렌더에 넣을 때만 변환한다.

import bpy, bmesh, math, os
from mathutils import Vector

def B(p):
    """three (x, y, z) → blender (x, -z, y). glTF 내보내기가 다시 Y-up 으로 돌려준다"""
    return Vector((p[0], -p[2], p[1]))

def srgb_to_lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def rot(a, ox=0.0, oz=0.0, sx=1):
    """XZ 평면에서 a 라디안 회전(+면 뒤쪽으로 젖힘) 후 (ox,oz) 로 이동, sx=-1 이면 좌우 반전"""
    c, s = math.cos(a), math.sin(a)
    return lambda x, z: (sx * (x * c - z * s + ox), x * s + z * c + oz)

def feather(L, W):
    """+X 방향으로 뻗은 깃털 윤곽 (끝이 둥글게 뾰족)"""
    return [(0, -W * 0.35), (L * 0.2, -W * 0.5), (L * 0.75, -W * 0.45), (L * 0.95, -W * 0.15), (L, 0.05 * W),
            (L * 0.85, W * 0.5), (L * 0.2, W * 0.5), (0, W * 0.35)]


class Kit:
    """컬렉션 하나 + 이름 붙은 색 팔레트. 같은 스크립트를 다시 돌리면 그 컬렉션만 새로 만든다"""

    def __init__(self, coll_name, palette, shiny=None):
        if bpy.app.background and not bpy.data.collections.get(coll_name):
            bpy.ops.wm.read_factory_settings(use_empty=True)
        coll = bpy.data.collections.get(coll_name)
        if coll:
            for ob in list(coll.objects):
                me = ob.data
                bpy.data.objects.remove(ob)
                if me and me.users == 0: bpy.data.meshes.remove(me)
        else:
            coll = bpy.data.collections.new(coll_name)
            bpy.context.scene.collection.children.link(coll)
        self.coll, self.palette, self.shiny, self.mats = coll, palette, shiny or {}, {}
        kit = self

        class Part(_Part):
            def __init__(self, name, pivot=(0, 0, 0)):
                super().__init__(kit, name, pivot)
        self.Part = Part

    def mat(self, name):
        if name not in self.mats:
            h = self.palette[name]
            rgb = [srgb_to_lin((h >> s) & 255) for s in (16, 8, 0)]
            m = bpy.data.materials.get('jj_' + name) or bpy.data.materials.new('jj_' + name)
            m.use_nodes = True
            bsdf = m.node_tree.nodes['Principled BSDF']
            rough, metal = self.shiny.get(name, (0.85, 0))
            bsdf.inputs['Base Color'].default_value = (*rgb, 1)
            bsdf.inputs['Roughness'].default_value = rough
            bsdf.inputs['Metallic'].default_value = metal
            m.diffuse_color = (*rgb, 1)  # 워크벤치 미리보기용
            self.mats[name] = m
        return self.mats[name]

    def export(self, out, normals=True):
        """normals=False: 법선 없이 정점을 공유해 파일을 크게 줄인다(게임이 flatShading 재질로 그릴 때만)"""
        if not out: return
        os.makedirs(os.path.dirname(out), exist_ok=True)
        bpy.ops.object.select_all(action='DESELECT')
        for ob in self.coll.objects: ob.select_set(True)
        bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_yup=True, use_selection=True,
                                  export_texcoords=False, export_animations=False,
                                  export_normals=normals)
        print('EXPORTED', out, os.path.getsize(out), 'bytes')

    def render(self, out, prefix, target, views, res=640, only=None):
        """워크벤치로 미리보기 PNG. only=[오브젝트 이름] 이면 그것만 보이게"""
        sc = bpy.context.scene
        sc.render.engine = 'BLENDER_WORKBENCH'
        sc.display.shading.color_type = 'MATERIAL'
        sc.display.shading.light = 'STUDIO'
        sc.display.shading.show_shadows = True
        sc.render.resolution_x = sc.render.resolution_y = res
        if not sc.world: sc.world = bpy.data.worlds.new('w')
        sc.world.color = (0.62, 0.83, 0.96)
        cam = bpy.data.objects.get('jj_cam') or bpy.data.objects.new('jj_cam', bpy.data.cameras.new('jj_cam'))
        if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
        sc.camera = cam
        for ob in self.coll.objects: ob.hide_render = bool(only) and ob.name not in only
        t = B(target)
        for name, eye in views:
            cam.location = B(eye)
            cam.rotation_euler = (t - cam.location).to_track_quat('-Z', 'Y').to_euler()
            sc.render.filepath = os.path.join(os.path.dirname(out), f'{prefix}_{name}.png')
            bpy.ops.render.render(write_still=True)
        print('RENDERED', prefix)


class _Part:
    """메시 하나(여러 재질). 좌표는 pivot 기준 상대값"""

    def __init__(self, kit, name, pivot):
        self.kit, self.name, self.pivot = kit, name, pivot
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

    def loft(self, secs, m, n=6, phase=0.0):
        """단면을 이어 붙인 관. secs=[(중심, 가로반지름, 세로반지름)], 반지름이 ~0 이면 뾰족한 끝"""
        cs = [Vector(s[0]) for s in secs]
        rings = []
        for i, (c, w, h) in enumerate(zip(cs, (s[1] for s in secs), (s[2] for s in secs))):
            t = (cs[min(i + 1, len(cs) - 1)] - cs[max(i - 1, 0)]).normalized()
            ref = Vector((0, 1, 0)) if abs(t.y) < 0.9 else Vector((0, 0, -1))
            rt = t.cross(ref).normalized(); up = rt.cross(t).normalized()
            b0 = len(self.verts)
            for j in range(n):
                a = 2 * math.pi * j / n + phase
                self.verts.append(tuple(c + rt * math.cos(a) * w + up * math.sin(a) * h))
            rings.append(b0)
        for a, b in zip(rings, rings[1:]):
            for j in range(n): self.face([a + j, a + (j + 1) % n, b + (j + 1) % n, b + j], m)
        self.face([rings[0] + j for j in reversed(range(n))], m)
        self.face([rings[-1] + j for j in range(n)], m)

    def cone(self, base_c, tip, radius, m, seg=6, squash=1.0):
        self.loft([(base_c, radius, radius * squash), (tip, 0.0005, 0.0005)], m, seg)

    def cyl(self, a, b, r, m, seg=8):
        self.loft([(a, r, r), (b, r, r)], m, seg, phase=math.pi / seg)

    def box(self, c, size, m, ry=0.0, rx=0.0, rz=0.0):
        """중심 c, 크기 size=(w,h,d) 상자. 회전은 Y→X→Z 순 (라디안)"""
        hx, hy, hz = (s / 2 for s in size)
        from mathutils import Euler
        R = Euler((rx, ry, rz), 'YXZ').to_matrix()
        b0 = len(self.verts)
        for sx_, sy_, sz_ in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                              (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)):
            v = R @ Vector((sx_ * hx, sy_ * hy, sz_ * hz)) + Vector(c)
            self.verts.append(tuple(v))
        for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 4, 7, 3)):
            self.face([b0 + i for i in f], m)

    def slab(self, outline, y, thick, m, xform=lambda x, z: (x, z), tilt=0.0):
        """XZ 평면 다각형을 두께 thick 로 세운 판. outline=[(x,z)], xform 으로 회전·이동, tilt 는 z 에 따른 y 기울기"""
        pts = [xform(x, z) for x, z in outline]
        n, b0 = len(pts), len(self.verts)
        for dy in (thick / 2, -thick / 2):
            for x, z in pts: self.verts.append((x, y + dy + z * tilt, z))
        self.face(list(range(b0, b0 + n)), m)
        self.face(list(reversed(range(b0 + n, b0 + 2 * n))), m)
        for i in range(n):
            j = (i + 1) % n
            self.face([b0 + i, b0 + n + i, b0 + n + j, b0 + j], m)

    def poly(self, pts, thick, m):
        """3D 공간의 볼록 평면 다각형을 법선 방향으로 thick 만큼 두께를 준 판 (돛·박공처럼 세운 판)"""
        P = [Vector(p) for p in pts]
        nrm = (P[1] - P[0]).cross(P[2] - P[0]).normalized() * (thick / 2)
        n, b0 = len(P), len(self.verts)
        for d in (nrm, -nrm):
            for p in P: self.verts.append(tuple(p + d))
        self.face(list(range(b0, b0 + n)), m)
        self.face(list(reversed(range(b0 + n, b0 + 2 * n))), m)
        for i in range(n):
            j = (i + 1) % n
            self.face([b0 + i, b0 + n + i, b0 + n + j, b0 + j], m)

    def stack(self, rings, m, paint=None, cap_top=True):
        """세로로 쌓은 고리들(위→아래)로 만든 덩어리. rings=[[(x,y,z)...], ...] 각 고리 점 개수 같음.
        마지막 고리의 점이 하나면 뾰족한 끝. paint(고리번호) → 재질"""
        idx = []
        for ring in rings:
            b0 = len(self.verts)
            self.verts.extend(tuple(p) for p in ring)
            idx.append(list(range(b0, b0 + len(ring))))
        n = len(idx[0])
        if cap_top: self.face(list(reversed(idx[0])), (paint and paint(0)) or m)
        for k, (a, b) in enumerate(zip(idx, idx[1:])):
            mm = (paint and paint(k)) or m
            for j in range(n):
                if len(b) == 1: self.face([a[j], a[(j + 1) % n], b[0]], mm)
                else: self.face([a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]], mm)

    def build(self, bevel=0.0):
        """bevel>0 이면 모서리를 살짝 깎아 빛을 받게 한다(로우폴리에서 가장 싸게 '고급스러워' 보이는 방법)"""
        me = bpy.data.meshes.new(self.name + '_mesh')
        me.from_pydata([tuple(B(v)) for v in self.verts], [], self.faces)
        for name in self.mats: me.materials.append(self.kit.mat(name))
        for poly, mi in zip(me.polygons, self.fmat): poly.material_index = mi
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)     # 뾰족한 끝점 합치기
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)          # 껍질마다 바깥쪽 법선
        if bevel > 0:
            sharp = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0) > 0.6]
            bmesh.ops.bevel(bm, geom=sharp, offset=bevel, segments=1, affect='EDGES', clamp_overlap=True)
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(self.name, me)
        ob.location = B(self.pivot)
        self.kit.coll.objects.link(ob)
        return ob
