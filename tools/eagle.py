# 경찰 독수리(Tripo 원본 .glb)를 게임용으로 가공 (Blender 5.x)
#
#   blender -b -P tools/eagle.py -- 원본.glb eagle.glb
#
# - 삼각형 약 37만 → 3만 남짓 (더 줄이면 날개에 구멍이 남) (뼈대 가중치는 유지)
# - 텍스처 2048 → 512, roughness/metal 맵은 빼고 값으로
# - 게임 좌표에 맞춤: 정면 -Z(three), 날개폭 SPAN, 발바닥 y = FEET
# 게임(index.html Bird)은 이 파일의 뼈 이름(bone_5~8 날개, tripo::Head_0 머리, tripo::Tail_0 꼬리)을 쓴다.

import bpy, sys, os
from mathutils import Vector

src, out = sys.argv[sys.argv.index('--') + 1:][:2]
SPAN, FEET, TRIS = 3.0, -0.6, 30000

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
for o in list(bpy.data.objects):
    if o.type == 'MESH' and not o.vertex_groups: bpy.data.objects.remove(o)   # 뼈대에 안 붙은 떠돌이 구(Icosphere)

arm = bpy.data.objects['Armature']
meshes = [o for o in bpy.data.objects if o.type == 'MESH']

# 1) 메시 줄이기: 큰 메시만, 전체가 TRIS 근처가 되게 같은 비율로
total = sum(len(o.data.polygons) for o in meshes)
for o in meshes:
    n = len(o.data.polygons)
    if n < 2000: continue
    ratio = max(0.01, TRIS / total)
    mod = o.modifiers.new('dec', 'DECIMATE'); mod.ratio = ratio
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=mod.name)

# 2) 텍스처 줄이기 + roughness/metal 맵 대신 값
for img in bpy.data.images:
    if img.size[0] > 512: img.scale(512, 512)
for m in bpy.data.materials:
    if not m.use_nodes: continue
    bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf: continue
    for name, val in (('Roughness', 0.8), ('Metallic', 0.0)):
        for l in list(bsdf.inputs[name].links): m.node_tree.links.remove(l)
        bsdf.inputs[name].default_value = val

# 3) 위치·방향·크기: 뼈대 루트(Armature 의 부모 빈 객체)를 옮긴다
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
s = SPAN / (mx.x - mn.x)
root = arm.parent or arm
while root.parent: root = root.parent
cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
root.location = (root.location.x - cx, root.location.y - cy, root.location.z - mn.z)
pivot = bpy.data.objects.new('eagle', None)          # 게임이 붙잡는 최상위 노드
bpy.context.scene.collection.objects.link(pivot)
root.parent = pivot
pivot.scale = (s, s, s)
pivot.rotation_euler = (0, 0, 3.14159265)             # 블렌더 -Y 정면 → three -Z 정면
pivot.location = (0, 0, FEET)
bpy.context.view_layer.update()

os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_yup=True, export_skins=True,
                          export_animations=False, export_image_format='JPEG', export_jpeg_quality=80)
tris = 0
for o in meshes:
    o.data.calc_loop_triangles(); tris += len(o.data.loop_triangles)
print('EAGLE', out, os.path.getsize(out), 'bytes', tris, 'tris', 'scale', round(s, 3))
