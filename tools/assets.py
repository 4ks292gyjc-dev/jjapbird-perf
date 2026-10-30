# 코스 오브젝트(발판·장애물·둥지) 모델 생성 스크립트 (Blender 5.x)
#
#   blender -b -P tools/assets.py -- out/assets.glb [--render]
#   python3 tools/embed.py out/assets.glb assets-glb
#   열려 있는 블렌더에서 돌리면 'jjassets' 컬렉션에만 다시 만든다(내보내기 없음)
#
# 규칙
# - 좌표는 게임(three.js) 기준: Y 위, 진행 방향 -Z. 이름 하나 = 에셋 하나 = glTF 노드 하나.
# - 각 에셋의 원점·크기는 index.html 의 Level 빌더가 예전에 쓰던 도형과 똑같이 맞춘다.
#   그래서 게임 코드는 충돌체를 그대로 두고 "보이는 메시"만 이 모델로 바꾼다.
#   (unit = 1×1×1 기준으로 만들고 게임이 scale 로 늘리는 것, m = 실제 미터 크기로 만든 것)
# - 재질 tint / tintdark / tintlight 는 게임이 구간 팔레트 색으로 바꿔 칠한다(어둡게 0.72, 밝게 1.25 배).
#   glow 로 시작하는 재질은 스스로 빛난다.

import bpy, math, random, sys, os, importlib
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meshkit; importlib.reload(meshkit)
from meshkit import Kit

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else None
RENDER = '--render' in argv
random.seed(20261030)
TAU = math.tau

kit = Kit('jjassets', {
    'tint': 0x8a8a8a, 'tintdark': 0x636363, 'tintlight': 0xadadad,
    'trim': 0xf2ede2, 'glass': 0x2b3a4f, 'wood': 0x6b4a33, 'woodLight': 0x9a7044, 'brick': 0x8a5a48,
    'stone': 0x8d877d, 'steel': 0x8f969c, 'steelDark': 0x3a3f44, 'dirt': 0x6e5a45, 'straw': 0xd6b779,
    'cloth': 0xb5463a, 'sail': 0xf6f1e6, 'gold': 0xe0b04a, 'panel': 0x24336f, 'black': 0x1c1c1c,
    'yellow': 0xf2c230, 'egg': 0xf6f0e2, 'eggSpot': 0x8a7a60, 'twig': 0x7b5a33, 'twigDark': 0x5a3e22,
    'roofRed': 0x7d4a3a, 'down': 0xfbf7ee, 'glowgold': 0xf4c542,
}, shiny={'glass': (0.15, 0.0), 'steel': (0.45, 0.6), 'gold': (0.3, 0.8), 'panel': (0.25, 0.3),
          'steelDark': (0.5, 0.5)})

_slot = [0]
def Part(name):
    """에셋 하나. 블렌더에서 보기 좋게 격자로 늘어놓지만 게임은 위치를 0으로 되돌린다"""
    i = _slot[0]; _slot[0] += 1
    return kit.Part(name, ((i % 6) * 16.0, 0, -(i // 6) * 16.0))

def jitter(a, b): return random.uniform(a, b)


# ── 떠 있는 바위 (unit): 윗면 y=+0.5 반지름 0.5, 뾰족한 끝 y=-0.5. 예전 뒤집힌 원뿔 자리 ──
p = Part('rock')
n = 11
layers = [(0.5, 0.5), (0.42, 0.49), (0.3, 0.44), (0.12, 0.36), (-0.08, 0.26), (-0.26, 0.15), (-0.4, 0.07)]
rings = []
for y, r in layers:
    rings.append([(math.cos(TAU * j / n) * r * jitter(0.86, 1.08), y + jitter(-0.02, 0.02),
                   math.sin(TAU * j / n) * r * jitter(0.86, 1.08)) for j in range(n)])
rings.append([(jitter(-0.03, 0.03), -0.5, jitter(-0.03, 0.03))])
p.stack(rings, 'tint', paint=lambda k: 'tintlight' if k == 0 else ('tintdark' if k % 2 else 'tint'))
for _ in range(9):   # 옆에 박힌 돌
    a, y = jitter(0, TAU), jitter(-0.3, 0.35)
    r = 0.5 * (0.5 + 0.5 * (y + 0.5)) * 0.92
    p.sphere((math.cos(a) * r, y, math.sin(a) * r), (jitter(0.05, 0.09),) * 3, 'tintdark', seg=5, rings=4)
for _ in range(5):   # 매달린 뿌리
    a = jitter(0, TAU); r = jitter(0.15, 0.32)
    top = (math.cos(a) * r, -0.05, math.sin(a) * r)
    p.loft([(top, 0.012, 0.012), ((top[0] * 1.1, -0.3, top[2] * 1.1), 0.008, 0.008),
            ((top[0] * 1.15, -0.45, top[2] * 1.2), 0.0005, 0.0005)], 'twigDark', 4)
p.build()


# ── 집 벽 (unit): 윗면 y=0, 아래 y=-1, x·z ±0.5. 게임이 (w, h, d) 로 늘린다 ──
p = Part('house_body')
p.box((0, -0.5, 0), (1, 1, 1), 'tint')
p.box((0, -0.95, 0), (1.03, 0.1, 1.03), 'tintdark')                 # 기단
p.box((0, -0.03, 0), (1.02, 0.06, 1.02), 'tintlight')               # 처마 띠
for sx in (-1, 1):
    for sz in (-1, 1): p.box((sx * 0.495, -0.5, sz * 0.495), (0.035, 1, 0.03), 'tintlight')   # 모서리 기둥
def window(c, nx, nz, w):
    """c=창 중심, (nx,nz)=바깥 방향, w=창 너비(unit)"""
    ax = (abs(nz), abs(nx))   # 창이 넓게 퍼지는 축
    def bx(off, size, m):
        p.box((c[0] + nx * off, c[1], c[2] + nz * off),
              (size[0] * ax[0] + size[2] * abs(nx), size[1], size[0] * ax[1] + size[2] * abs(nz)), m)
    bx(0.006, (w + 0.04, 0.32, 0.012), 'trim')
    bx(0.012, (w, 0.26, 0.01), 'glass')
    bx(0.016, (0.012, 0.26, 0.006), 'trim')
    bx(0.016, (w, 0.012, 0.006), 'trim')
    p.box((c[0] + nx * 0.02, c[1] - 0.17, c[2] + nz * 0.02),
          ((w + 0.06) * ax[0] + 0.04 * abs(nx), 0.025, (w + 0.06) * ax[1] + 0.04 * abs(nz)), 'trim')   # 창턱
for sx in (-1, 1):
    for z in (-0.25, 0.25): window((sx * 0.5, -0.45, z), sx, 0, 0.17)
window((0, -0.45, -0.5), 0, -1, 0.2)
p.box((0, -0.72, 0.505), (0.24, 0.52, 0.014), 'trim')               # 문틀
p.box((0, -0.73, 0.513), (0.19, 0.48, 0.01), 'wood')
p.box((0.06, -0.75, 0.52), (0.02, 0.03, 0.01), 'gold')              # 손잡이
p.box((0, -0.45, 0.53), (0.3, 0.025, 0.05), 'tintdark')             # 문 위 차양
p.build()


# ── 지붕 (unit): 처마 y=-1 x ±0.5, 용마루 y=0, z ±0.5. 게임이 (w*1.15, 2, d+0.6) 로 늘린다 ──
p = Part('house_roof')
for s in (-1, 1):
    eave, ridge = Vector((s * 0.53, -1.04, 0)), Vector((0, 0.02, 0))
    p.poly([(eave.x, eave.y, -0.5), (eave.x, eave.y, 0.5), (ridge.x, ridge.y, 0.5), (ridge.x, ridge.y, -0.5)], 0.07, 'tint')
    for k in range(1, 6):   # 기와 줄
        t = k / 6
        q = eave.lerp(ridge, t)
        p.loft([((q.x + s * 0.012, q.y + 0.03, -0.505), 0.012, 0.022), ((q.x + s * 0.012, q.y + 0.03, 0.505), 0.012, 0.022)],
               'tintdark', 4)
p.loft([((0, 0.04, -0.52), 0.035, 0.035), ((0, 0.04, 0.52), 0.035, 0.035)], 'tintdark', 6)        # 용마루
for z in (-0.47, 0.47):                                                                          # 박공 (나무)
    p.poly([(-0.48, -1, z), (0.48, -1, z), (0, -0.03, z)], 0.02, 'wood')
    p.poly([(-0.06, -0.62, z * 1.02), (0.06, -0.62, z * 1.02), (0.06, -0.48, z * 1.02), (-0.06, -0.48, z * 1.02)], 0.01, 'glass')
p.box((0.19, -0.2, -0.23), (0.116, 0.8, 0.105), 'brick')                                       # 굴뚝
p.box((0.19, 0.22, -0.23), (0.14, 0.05, 0.125), 'stone')
p.build()


# ── 컨테이너 (m): 2.6 × 2.6 × 7.5, 중심 원점 ──
p = Part('container')
p.box((0, 0, 0), (2.56, 2.5, 7.4), 'tint')
for z in [i * 0.32 - 3.36 for i in range(22)]:                       # 골판
    for sx in (-1, 1): p.box((sx * 1.29, 0, z), (0.05, 2.3, 0.14), 'tint')
for z in [i * 0.5 - 3.25 for i in range(14)]: p.box((0, 1.26, z), (2.3, 0.04, 0.2), 'tint')
for sx in (-1, 1):
    for sy in (-1, 1):
        p.box((sx * 1.23, sy * 1.23, 0), (0.15, 0.15, 7.5), 'tintdark')      # 위아래 레일
        for sz in (-1, 1):
            p.box((sx * 1.22, 0, sz * 3.68), (0.17, 2.6, 0.15), 'tintdark')   # 모서리 기둥
            p.box((sx * 1.2, sy * 1.2, sz * 3.65), (0.22, 0.22, 0.22), 'steelDark')   # 코너 캐스팅
for sx in (-1, 1):                                                   # 뒷문 두 짝
    p.box((sx * 0.62, 0, 3.73), (1.18, 2.34, 0.05), 'tint')
    for bx in (0.25, 0.9):
        p.cyl((sx * bx, -1.15, 3.79), (sx * bx, 1.15, 3.79), 0.035, 'steel', 6)          # 잠금봉
        p.box((sx * bx + sx * 0.08, -0.2, 3.8), (0.18, 0.05, 0.04), 'steel')
p.box((0, 0, -3.72), (2.3, 2.3, 0.05), 'tint')                     # 앞면 골판
for x in [i * 0.42 - 1.05 for i in range(6)]: p.box((x, 0, -3.76), (0.12, 2.3, 0.05), 'tint')
p.box((1.3, 0.6, -2.4), (0.02, 0.5, 1.2), 'trim')                   # 화물 표지판
p.build()


# ── 나무 (m): 원점 = 땅. 줄기 2.4m, 잎 덩어리 중심 3.2m. 잎 = tint ──
p = Part('tree')
p.loft([((0, -0.1, 0), 0.3, 0.3), ((0.05, 1.0, 0.03), 0.22, 0.22), ((-0.05, 2.0, 0), 0.17, 0.17), ((0, 2.8, 0.05), 0.12, 0.12)], 'wood', 7)
p.loft([((0, 1.6, 0), 0.08, 0.08), ((0.6, 2.3, 0.2), 0.05, 0.05), ((0.9, 2.6, 0.3), 0.0005, 0.0005)], 'wood', 5)
p.loft([((0, 1.9, 0), 0.07, 0.07), ((-0.5, 2.5, -0.3), 0.045, 0.045), ((-0.8, 2.8, -0.4), 0.0005, 0.0005)], 'wood', 5)
def lumpy(k):
    return lambda x, y, z: (x * k, y * k, z * k)
for c, r, m in (((0, 3.0, 0), (1.3, 1.0, 1.3), 'tintdark'), ((0.6, 3.4, 0.3), (0.95, 0.85, 0.95), 'tint'),
                ((-0.6, 3.5, -0.2), (0.9, 0.8, 0.9), 'tint'), ((0.1, 4.0, -0.1), (0.85, 0.75, 0.85), 'tintlight'),
                ((0.2, 3.1, -0.8), (0.7, 0.6, 0.7), 'tint')):
    p.sphere(c, r, m, seg=8, rings=6, warp=lambda x, y, z: (x * jitter(0.9, 1.1), y * jitter(0.9, 1.1), z * jitter(0.9, 1.1)))
p.build()


# ── 섬 윗면 (unit): 예전 원기둥 자리. 반지름 0.5, y -0.5..0.5, 윗면 = 잔디(tint) ──
p = Part('island')
n = 14
top = [(math.cos(TAU * j / n) * 0.5 * jitter(0.94, 1.03), 0.5, math.sin(TAU * j / n) * 0.5 * jitter(0.94, 1.03)) for j in range(n)]
lip = [(x * 1.02, 0.3, z * 1.02) for x, _, z in top]
side = [(x * 0.97, 0.05, z * 0.97) for x, _, z in top]
bot = [(x * 0.9, -0.5, z * 0.9) for x, _, z in top]
p.stack([top, lip, side, bot], 'dirt', paint=lambda k: 'tint' if k == 0 else 'tintdark' if k == 1 else 'dirt')
p.face(list(range(len(p.verts) - n, len(p.verts))), 'dirt')
p.build()


# ── 배 (m): 원점 = 갑판 높이, 선체 z -4.5(뱃머리) .. 4(고물). 선체 = tint ──
p = Part('boat')
hull = [((0, -0.75, 4.05), 1.48, 0.8), ((0, -0.8, 2.5), 1.55, 0.85), ((0, -0.8, 0), 1.55, 0.85),
        ((0, -0.76, -2.0), 1.42, 0.8), ((0, -0.62, -3.4), 0.95, 0.68), ((0, -0.42, -4.5), 0.06, 0.45)]
p.loft(hull, 'tint', 12, phase=0)
p.loft([((0, -0.95, 4.0), 1.5, 0.75), ((0, -1.0, 0), 1.57, 0.8), ((0, -0.95, -3.4), 0.97, 0.62),
        ((0, -0.8, -4.45), 0.07, 0.4)], 'tintdark', 12)                                        # 흘수선 아래
deck = [(-1.45, 3.9), (1.45, 3.9), (1.5, 0), (1.35, -2.0), (0.85, -3.4), (0, -4.4), (-0.85, -3.4), (-1.35, -2.0), (-1.5, 0)]
p.slab(deck, 0.0, 0.1, 'woodLight')
for x in (-1, -0.5, 0, 0.5, 1): p.box((x, 0.055, -0.2), (0.03, 0.01, 7.6 - abs(x) * 2.2), 'wood')   # 갑판 널
for i, (x, z) in enumerate(deck):                                                             # 난간 기둥 + 난간
    p.cyl((x * 0.97, 0.05, z * 0.98), (x * 0.97, 0.6, z * 0.98), 0.04, 'trim', 5)
    x2, z2 = deck[(i + 1) % len(deck)]
    if i != 0: p.loft([((x * 0.97, 0.6, z * 0.98), 0.03, 0.03), ((x2 * 0.97, 0.6, z2 * 0.98), 0.03, 0.03)], 'trim', 4)
p.box((0, 0.7, 2.0), (2.0, 1.4, 2.6), 'trim')                                                 # 선실
p.box((0, 1.46, 2.0), (2.25, 0.12, 2.85), 'tint')
for sx in (-1, 1):
    for z in (1.4, 2.6): p.box((sx * 1.005, 0.85, z), (0.02, 0.45, 0.6), 'glass')
p.box((0, 0.6, 0.69), (0.6, 1.0, 0.03), 'wood')
p.cyl((0, 0, -1), (0, 5.0, -1), 0.12, 'wood', 6)                                              # 돛대
p.cyl((0, 1.4, -1), (0, 1.4, 1.2), 0.07, 'wood', 5)                                          # 붐
p.poly([(0.05, 4.8, -0.95), (0.05, 1.5, 1.1), (0.05, 1.5, -0.95)], 0.05, 'sail')             # 삼각 돛
p.poly([(-0.02, 4.5, -1.05), (-0.02, 1.0, -3.6), (-0.02, 1.0, -1.05)], 0.04, 'sail')
p.box((0, 5.1, -1), (0.05, 0.3, 0.5), 'cloth')                                                # 깃발
p.build()


# ── 소행성 (unit): 예전 정십이면체 자리, 반지름 1. 울퉁불퉁, 얼룩 색. 몸 = tint ──
p = Part('asteroid')
noise = [[jitter(0.86, 1.1) for _ in range(12)] for _ in range(9)]
cnt = [0]
def lump(x, y, z):
    k = noise[cnt[0] // 12 % 9][cnt[0] % 12]; cnt[0] += 1
    return (x * k, y * k, z * k)
p.sphere((0, 0, 0), (1, 1, 1), 'tint', seg=12, rings=9, warp=lump,
         paint=lambda c, k: 'tintdark' if (k * 7) % 5 == 0 else ('tintlight' if (k * 3) % 11 == 0 else None))
p.build()


# ── 인공위성 (m): 몸통 2.6×2.6×3.4 (중심 y -1.3), 태양전지판 x ±4.2 ──
p = Part('satellite')
p.box((0, -1.3, 0), (2.5, 2.5, 3.3), 'trim')
for y in (-2.2, -1.3, -0.4): p.box((0, y, 0), (2.56, 0.04, 3.36), 'steel')                   # 패널 이음
p.box((0, -1.3, -1.85), (2.2, 2.2, 0.4), 'gold')                                             # 단열 포일
for gx in (-0.6, 0.6):
    for gy in (-0.6, 0.6): p.sphere((gx, -1.3 + gy, -2.08), (0.25, 0.25, 0.08), 'gold', seg=6, rings=3)
for sx in (-1, 1):
    p.cyl((sx * 1.25, -0.6, 0), (sx * 1.75, -0.6, 0), 0.08, 'steel', 6)                     # 지지대
    p.box((sx * 4.2, -0.6, 0), (5.0, 0.08, 2.4), 'steelDark')
    for i in range(5):
        for j in range(3):
            p.box((sx * (2.0 + i * 0.98 + 0.25), -0.55, -0.8 + j * 0.8), (0.9, 0.04, 0.72), 'panel')   # 전지 셀
p.loft([((0, 0.05, 1), 0.15, 0.15), ((0, 0.35, 1), 0.6, 0.6), ((0, 0.6, 1), 0.92, 0.92)], 'trim', 12)      # 접시 안테나
p.cyl((0, 0.05, 1), (0, 1.1, 1), 0.04, 'steel', 5)
p.sphere((0, 1.12, 1), (0.08, 0.08, 0.08), 'gold', seg=6, rings=4)
for sx in (-1, 1):
    p.cone((sx * 0.8, -2.55, 1.2), (sx * 0.8, -2.95, 1.2), 0.18, 'steelDark', 6)            # 추력기
p.build()


# ── 파이프 (m): 반지름 1.3, 길이 10 (z), 중심 y -1.3. 지선은 아래로. 몸 = tint ──
p = Part('pipe')
p.cyl((0, -1.3, -5), (0, -1.3, 5), 1.3, 'tint', 14)
for z in (-4.7, 0, 4.7):                                                                     # 플랜지 + 볼트
    p.cyl((0, -1.3, z - 0.25), (0, -1.3, z + 0.25), 1.45, 'tintdark', 14)
    for k in range(10):
        a = TAU * k / 10
        p.cyl((math.cos(a) * 1.38, -1.3 + math.sin(a) * 1.38, z - 0.3), (math.cos(a) * 1.38, -1.3 + math.sin(a) * 1.38, z + 0.3), 0.06, 'steel', 6)
p.cyl((0, -2.0, 3), (0, -7.0, 3), 0.72, 'tint', 10)                                          # 지선
p.cyl((0, -2.5, 3), (0, -2.9, 3), 0.85, 'tintdark', 10)
p.cyl((0, 0, -2.4), (0, 0.5, -2.4), 0.08, 'steel', 6)                                        # 밸브 손잡이
for k in range(10):
    a, b = TAU * k / 10, TAU * (k + 1) / 10
    p.loft([((math.cos(a) * 0.5, 0.52, -2.4 + math.sin(a) * 0.5), 0.04, 0.04),
            ((math.cos(b) * 0.5, 0.52, -2.4 + math.sin(b) * 0.5), 0.04, 0.04)], 'cloth', 4)
for a in (0, TAU / 3, 2 * TAU / 3):
    p.loft([((0, 0.52, -2.4), 0.025, 0.025), ((math.cos(a) * 0.5, 0.52, -2.4 + math.sin(a) * 0.5), 0.025, 0.025)], 'steel', 4)
p.build()


# ── 철골 보 (m): 길이 10, 윗면 y=0, I형 단면 높이 2. 쇠사슬 z -4.4. 몸 = tint ──
p = Part('girder')
p.box((0, -0.15, 0), (1.8, 0.3, 10), 'tint')
p.box((0, -1.0, 0), (0.3, 1.4, 10), 'tint')
p.box((0, -1.85, 0), (1.8, 0.3, 10), 'tint')
for z in [i * 2 - 4 for i in range(5)]:                                                     # 보강판
    for sx in (-1, 1): p.box((sx * 0.5, -1.0, z), (0.7, 1.4, 0.08), 'tintdark')
for z in [i * 1.5 - 3.75 for i in range(6)]:                                                # 경량 구멍
    p.cyl((-0.17, -1.0, z), (0.17, -1.0, z), 0.32, 'steelDark', 8)
for z in [i * 1.0 - 4.5 for i in range(10)]:                                                # 리벳
    for sx in (-1, 1): p.sphere((sx * 0.7, 0.0, z), (0.05, 0.03, 0.05), 'tintdark', seg=5, rings=3)
for i in range(5):                                                                           # 쇠사슬
    y = -2.15 - i * 0.42
    if i % 2 == 0:
        for sx in (-1, 1): p.box((sx * 0.1, y, -4.4), (0.06, 0.42, 0.06), 'steelDark')
        for sy in (-1, 1): p.box((0, y + sy * 0.2, -4.4), (0.26, 0.06, 0.06), 'steelDark')
    else:
        for sz in (-1, 1): p.box((0, y, -4.4 + sz * 0.1), (0.06, 0.42, 0.06), 'steelDark')
        for sy in (-1, 1): p.box((0, y + sy * 0.2, -4.4), (0.06, 0.06, 0.26), 'steelDark')
p.loft([((0, -4.2, -4.4), 0.06, 0.06), ((0, -4.6, -4.4), 0.06, 0.06), ((0.25, -4.8, -4.4), 0.05, 0.05),
        ((0.35, -4.5, -4.4), 0.0005, 0.0005)], 'steelDark', 5)                                 # 갈고리
p.build()


# ── 비계 (m): 4.5×4.5 발판 윗면 y=0, 아래 발판 y -5.5 ──
p = Part('scaffold')
for y in (-0.18, -5.5):
    for i in range(6):
        x = -1.9 + i * 0.76
        p.box((x, y, 0), (0.7, 0.35, 4.5), 'woodLight' if i % 2 else 'wood')
for x in (-1, 1):
    for z in (-1, 1):
        p.cyl((x * 2.03, -6.2, z * 2.03), (x * 2.03, 0.9, z * 2.03), 0.08, 'steel', 6)     # 기둥
        p.box((x * 2.03, -0.38, z * 2.03), (0.22, 0.14, 0.22), 'steelDark')               # 연결쇠
for y in (-3.0, 0.8):                                                                      # 가로대 + 안전 난간
    for s in (-1, 1):
        p.cyl((-2.03, y, s * 2.03), (2.03, y, s * 2.03), 0.05, 'steel', 5)
        p.cyl((s * 2.03, y, -2.03), (s * 2.03, y, 2.03), 0.05, 'steel', 5)
for s in (-1, 1):                                                                          # 대각 보강재
    p.cyl((-2.03, -5.3, s * 2.03), (2.03, -0.4, s * 2.03), 0.045, 'steel', 5)
for i in range(9):                                                                         # 사다리
    p.cyl((1.3, -5.3 + i * 0.6, -2.15), (1.9, -5.3 + i * 0.6, -2.15), 0.03, 'yellow', 4)
for x in (1.3, 1.9): p.cyl((x, -5.5, -2.15), (x, 0.4, -2.15), 0.04, 'yellow', 5)
p.box((0, 0.02, 2.1), (4.3, 0.06, 0.25), 'yellow')                                        # 발끝막이
p.build()


# ── 객차 (m): 원점 = 바닥 중심, 차체 2.8×2.6×4, 지붕 윗면 3.1. 차체 = tint ──
p = Part('railcar')
p.box((0, 1.3, 0), (2.8, 2.6, 4.0), 'tint')
p.box((0, 0.45, 0), (2.86, 0.25, 4.06), 'tintdark')
p.box((0, 2.85, 0), (2.9, 0.5, 4.1), 'trim')
p.loft([((0, 3.1, -2.0), 1.2, 0.12), ((0, 3.1, 2.0), 1.2, 0.12)], 'trim', 8)
for sx in (-1, 1):
    p.box((sx * 1.405, 1.75, 0), (0.02, 0.75, 3.4), 'trim')
    for z in (-1.3, -0.45, 0.45, 1.3): p.box((sx * 1.415, 1.75, z), (0.02, 0.6, 0.72), 'glass')
for sz in (-1, 1):
    p.box((0, 1.35, sz * 2.01), (1.0, 2.1, 0.03), 'tintdark')
    p.box((0, 1.75, sz * 2.03), (0.6, 0.6, 0.02), 'glass')
    for sx in (-1, 1):                                                                       # 바퀴
        for dz in (-0.45, 0.45):
            p.cyl((sx * 1.15, 0.05, sz * 1.3 + dz), (sx * 1.35, 0.05, sz * 1.3 + dz), 0.32, 'steelDark', 10)
p.build()


# ── 움직이는 블록 (m): 5×2.4×2.6 중심 원점, 윗면 경고 줄무늬. 몸 = tint ──
p = Part('mover')
p.box((0, 0, 0), (5.0, 2.4, 2.6), 'tint')
for sx in (-1, 1):
    for sz in (-1, 1): p.box((sx * 2.42, 0, sz * 1.22), (0.2, 2.44, 0.2), 'tintdark')
for i in range(13):                                                                          # 노랑·검정 띠
    x = -2.4 + i * 0.4
    for sz in (-1, 1): p.box((x, 1.05, sz * 1.31), (0.4, 0.3, 0.04), 'yellow' if i % 2 else 'black')
    for sx_ in (-1, 1):
        if abs(x) > 2.2: p.box((sx_ * 2.51, 1.05, 0), (0.04, 0.3, 2.6), 'yellow')
p.box((0, 1.24, 0), (5.05, 0.08, 2.65), 'steelDark')
for x in [i * 0.5 - 2.25 for i in range(10)]:                                              # 미끄럼 방지판
    for z in (-0.7, 0, 0.7): p.box((x, 1.3, z), (0.3, 0.04, 0.12), 'steel')
for sz in (-1, 1):                                                                           # 측면 리벳판
    p.box((0, -0.2, sz * 1.31), (3.6, 1.3, 0.03), 'tintdark')
p.build()


# ── 팬 날개 (unit 길이): y 0→1 (게임이 L 배), 폭 1.3(x), 두께 0.35(z). 몸 = tint ──
p = Part('blade_fan')
p.loft([((0, 0, 0), 0.32, 0.1), ((0, 0.12, 0), 0.6, 0.12), ((0, 0.55, 0), 0.65, 0.1),
        ((0, 0.88, 0), 0.52, 0.08), ((0, 0.97, 0), 0.32, 0.06)], 'tint', 8)
p.loft([((0, 0.885, 0), 0.535, 0.085), ((0, 0.985, 0), 0.3, 0.065)], 'yellow', 8)
p.loft([((0, 0.83, 0), 0.6, 0.09), ((0, 0.86, 0), 0.58, 0.09)], 'black', 8)
p.build()

# ── 풍차 날개 (unit 길이): 나무 살대 + 격자 + 빨간 천 ──
p = Part('blade_sail')
p.box((0, 0.5, 0), (0.2, 1.0, 0.25), 'tint')
for k in range(11):
    y = 0.08 + k * 0.088
    p.box((0.85, y, 0), (1.3, 0.012, 0.08), 'wood')
for x in (0.25, 0.85, 1.45): p.box((x, 0.52, 0), (0.06, 0.88, 0.08), 'wood')
p.box((0.88, 0.58, 0.04), (1.2, 0.68, 0.03), 'cloth')
p.build()

# ── 풍차 탑 (unit): 예전 원뿔 자리. 아래 반지름 0.5(y -0.5) → 위 0.24(y 0.56) ──
p = Part('windmill_tower')
n = 8
p.stack([[(math.cos(TAU * j / n) * r, y, math.sin(TAU * j / n) * r) for j in range(n)]
         for y, r in ((0.56, 0.24), (0.3, 0.3), (-0.2, 0.42), (-0.5, 0.5))], 'stone',
        paint=lambda k: 'trim' if k == 1 else 'stone')
p.box((0, -0.4, -0.47), (0.2, 0.17, 0.03), 'wood')
for y, r in ((0.05, 0.36), (0.38, 0.28)):
    for a in (0.5, 2.6, 4.2):
        p.box((math.cos(a) * r, y, math.sin(a) * r), (0.09, 0.07, 0.09), 'glass')
p.loft([((0, -0.18, 0), 0.43, 0.43), ((0, -0.16, 0), 0.43, 0.43)], 'wood', 8)
p.build()

# ── 풍차 지붕 (m): 예전 원뿔(지름 2.8, 높이 1.4) 자리, 중심 원점 ──
p = Part('windmill_cap')
p.stack([[(math.cos(TAU * j / 10) * r, y, math.sin(TAU * j / 10) * r) for j in range(10)]
         for y, r in ((-0.6, 1.45), (-0.2, 1.2), (0.25, 0.75), (0.6, 0.3))] + [[(0, 0.75, 0)]], 'roofRed',
        paint=lambda k: 'wood' if k == 0 else 'roofRed', cap_top=False)
p.loft([((0, -0.62, 0), 1.48, 1.48), ((0, -0.5, 0), 1.48, 1.48)], 'wood', 10)
p.sphere((0, 0.78, 0), (0.12, 0.12, 0.12), 'gold', seg=6, rings=4)
p.build()


# ── 둥지 (m): 원점 = 둥지 바닥 중심. 나뭇가지 엮은 그릇 + 짚 + 알 셋 ──
p = Part('nest')
p.sphere((0, 0.35, 0), (2.7, 0.4, 2.7), 'straw', seg=12, rings=5)
for i in range(84):
    a = TAU * i / 84 + jitter(-0.05, 0.05)
    r = jitter(2.5, 4.0)
    y = jitter(0.0, 1.5) * (1 - (r - 2.5) / 3)
    tang = Vector((-math.sin(a), 0, math.cos(a)))
    c = Vector((math.cos(a) * r, y + 0.2, math.sin(a) * r))
    L = jitter(1.4, 2.6)
    tilt = Vector((0, jitter(-0.35, 0.35), 0))
    d = (tang * random.choice((-1, 1)) + tilt).normalized() * L / 2
    mid = c + Vector((jitter(-0.1, 0.1), jitter(0.05, 0.15), jitter(-0.1, 0.1)))
    rad = jitter(0.07, 0.13)
    p.loft([(tuple(c - d), rad * 0.6, rad * 0.6), (tuple(mid), rad, rad), (tuple(c + d), rad * 0.5, rad * 0.5)],
           random.choice(('twig', 'twigDark', 'woodLight')), 4)
for k in range(5):                                                                           # 솜털
    a = jitter(0, TAU)
    p.sphere((math.cos(a) * 2.2, 0.85, math.sin(a) * 2.2), (0.25, 0.1, 0.18), 'down', seg=6, rings=4)
for i in range(3):                                                                           # 알
    c = (math.cos(i * 2.1) * 0.9, 0.95, math.sin(i * 2.1) * 0.9)
    p.sphere(c, (0.5, 0.65, 0.5), 'egg', seg=10, rings=8,
             warp=lambda x, y, z: (x * (1 - 0.15 * y / 0.65), y, z * (1 - 0.15 * y / 0.65)))
    for _ in range(7):
        d = Vector((jitter(-1, 1), jitter(-0.4, 1), jitter(-1, 1))).normalized()
        q = Vector(c) + Vector((d.x * 0.47, d.y * 0.6, d.z * 0.47))
        p.sphere(tuple(q), (0.05, 0.05, 0.05), 'eggSpot', seg=4, rings=3)
p.build()


# ── 체크포인트 발판 (m): 12×1.4×12, 윗면 y=0. 돌 바닥 = tint, 네 모서리 금빛 등 ──
p = Part('checkpoint_pad')
p.box((0, -0.72, 0), (12, 1.4, 12), 'tint')
p.box((0, -1.35, 0), (12.3, 0.25, 12.3), 'tintdark')
for i in range(4):
    for j in range(4):
        x, z = -4.35 + i * 2.9, -4.35 + j * 2.9
        if abs(x) < 2 and abs(z) < 2: continue
        p.box((x, 0.0, z), (2.75, 0.06, 2.75), 'tintlight' if (i + j) % 2 else 'tint')
for k in range(24):                                                                          # 가운데 금색 고리
    a = TAU * k / 24
    p.box((math.cos(a) * 2.3, 0.02, math.sin(a) * 2.3), (0.62, 0.06, 0.25), 'gold', ry=-a + math.pi / 2)
p.box((0, 0.0, 0), (3.2, 0.04, 3.2), 'tintlight')
for s in (-1, 1):                                                                            # 테두리
    p.box((s * 5.9, 0.08, 0), (0.25, 0.16, 12), 'tintdark')
    p.box((0, 0.08, s * 5.9), (12, 0.16, 0.25), 'tintdark')
for x in (-5.5, 5.5):
    for z in (-5.5, 5.5):
        p.box((x, 0.25, z), (0.7, 0.5, 0.7), 'stone')
        p.box((x, 0.6, z), (0.5, 0.25, 0.5), 'glowgold')
p.build()


kit.export(OUT, normals=False)   # 게임은 flatShading 재질로 다시 칠하므로 법선 불필요
if RENDER and OUT:
    names = [o.name for o in kit.coll.objects]
    for nm in names:
        ob = bpy.data.objects[nm]
        size = max(ob.dimensions)
        c = ob.location + Vector((0, 0, ob.dimensions.z * 0.0))
        tgt = (c.x, c.z, -c.y)
        dist = size * 1.6 + 1
        kit.render(OUT, 'asset_' + nm, target=tgt, res=360, only=[nm],
                   views=(('a', (tgt[0] + dist * 0.75, tgt[1] + dist * 0.55, tgt[2] - dist * 0.75)),))
