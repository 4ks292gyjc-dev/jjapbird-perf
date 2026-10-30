# 짭새(경찰 독수리) 모델 생성 스크립트 (Blender 5.x)
#
#   blender -b -P tools/bird.py -- out/bird.glb            # 모델만 내보내기
#   blender -b -P tools/bird.py -- out/bird.glb --render    # + 미리보기 PNG (out/bird_*.png)
#   열려 있는 블렌더에서 돌리면 장면은 그대로 두고 'jjapbird' 컬렉션에만 새를 다시 만든다(내보내기 없음)
#
# 내보낸 .glb 는 index.html 안에 base64 로 넣는다:  python3 tools/embed.py out/bird.glb bird-glb
#
# 좌표는 전부 게임(three.js) 기준으로 적는다: Y 위, -Z 가 새의 정면.
# 부품마다 원점 = 게임 코드의 관절 위치(Bird._build 참고). 게임은 원점에 붙이기만 한다.

import bpy, math, sys, os
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meshkit import Kit, rot, feather, B

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else None
RENDER = '--render' in argv

# ── 색: 흰머리독수리 + 경찰 제복 ──
kit = Kit('jjapbird', {
    'feather': 0x3d2b1f, 'featherMid': 0x5b4331, 'white': 0xf4f1ea, 'beak': 0xf2b02e,
    'iris': 0xf5c518, 'pupil': 0x111111, 'shine': 0xffffff,
    'navy': 0x1f2a4a, 'navyDark': 0x141c33, 'gold': 0xe8b931, 'shirt': 0xa9c8e8,
    'visor': 0x101216, 'feet': 0xf0b429, 'claw': 0x1a1a1a,
}, shiny={'gold': (0.35, 0.6), 'visor': (0.3, 0)})
Part = kit.Part

# ── 몸통: 남색 제복 상의(벨트·단추·배지·넥타이) + 꼬리 쪽은 갈색 깃털, 남색 바지와 노란 발 ──
RB = (0.4, 0.37, 0.68)
def body_warp(x, y, z):
    t = max(0.0, z / RB[2])             # 0(가운데) → 1(꼬리 끝)
    k = 1 - 0.4 * t * t
    return (x * k * (1.05 if z < 0 else 1), y * k + 0.05 * t * t, z)
def body_paint(c, k):
    if c[2] > 0.36: return 'feather'
    if -0.27 < c[1] < -0.17: return 'navyDark'        # 벨트
    return None
def front(x, y, out=0.0):
    """몸통 앞면 위의 점 (x, y) — 단추·배지 붙이는 자리"""
    q = max(0.0, 1 - (x / (RB[0] * 1.05)) ** 2 - (y / RB[1]) ** 2)
    return (x, y, -RB[2] * math.sqrt(q) - out)
body = Part('body', (0, 0, 0))
body.sphere((0, 0, 0), RB, 'navy', seg=14, rings=10, paint=body_paint, warp=body_warp)
for y in (0.02, -0.1):                                  # 금단추
    body.sphere(front(0.07, y, 0.005), (0.025, 0.025, 0.02), 'gold', seg=6, rings=4)
body.sphere(front(0, -0.22, 0.01), (0.06, 0.04, 0.02), 'gold', seg=6, rings=4)          # 버클
body.sphere(front(-0.19, 0.06, 0.005), (0.055, 0.065, 0.02), 'gold', seg=6, rings=5)   # 가슴 배지
body.loft([(front(0, 0.2, -0.01), 0.075, 0.02), (front(0, 0.12, 0.012), 0.05, 0.015)], 'shirt', 6)  # 셔츠 깃
body.loft([(front(0, 0.14, 0.015), 0.025, 0.012), (front(0, 0.0, 0.02), 0.035, 0.012),
           (front(0, -0.08, 0.02), 0.001, 0.001)], 'navyDark', 4)                        # 넥타이
for sx in (-1, 1):
    hip, knee, ankle = (sx * 0.13, -0.2, 0.05), (sx * 0.13, -0.42, 0.06), (sx * 0.13, -0.56, 0.08)
    body.loft([(hip, 0.085, 0.085), (knee, 0.07, 0.07)], 'navy', 6)                     # 바지
    body.loft([(knee, 0.04, 0.04), (ankle, 0.035, 0.035)], 'feet', 5)
    for dx, dz in ((-0.06, -0.14), (0, -0.16), (0.06, -0.14), (0, 0.1)):               # 발가락 + 검은 발톱
        tip = (ankle[0] + sx * dx, -0.6, ankle[2] + dz)
        body.cone(ankle, tip, 0.025, 'feet', seg=4)
        body.loft([(tip, 0.016, 0.016), ((tip[0], -0.63, tip[2] + (0.035 if dz < 0 else -0.035)), 0.0005, 0.0005)], 'claw', 4)
body.build()

# ── 머리: 흰 머리, 노란 갈고리 부리, 매서운 눈썹뼈, 노란 눈, 경찰 모자 ──
head = Part('head', (0, 0.3, -0.68))
head.sphere((0, 0, -0.04), (0.25, 0.24, 0.29), 'white', seg=12, rings=9)
head.loft([((0, -0.02, -0.22), 0.09, 0.075), ((0, -0.01, -0.31), 0.08, 0.07), ((0, -0.03, -0.39), 0.06, 0.055),
           ((0, -0.08, -0.45), 0.04, 0.04), ((0, -0.15, -0.46), 0.02, 0.022), ((0, -0.19, -0.43), 0.0005, 0.0005)],
          'beak', 6)                                                                    # 윗부리 (아래로 휜 갈고리)
head.loft([((0, -0.09, -0.21), 0.07, 0.03), ((0, -0.11, -0.34), 0.045, 0.022), ((0, -0.12, -0.4), 0.0005, 0.0005)],
          'beak', 5)                                                                    # 아랫부리
for sx in (-1, 1):
    e = Vector((sx * 0.185, 0.04, -0.17))
    head.sphere(tuple(e), (0.05, 0.05, 0.05), 'iris', seg=8, rings=6)
    head.sphere(tuple(e + Vector((sx * 0.03, 0, -0.02))), (0.027, 0.027, 0.027), 'pupil', seg=6, rings=4)
    head.sphere(tuple(e + Vector((sx * 0.04, 0.025, -0.03))), (0.012, 0.012, 0.012), 'shine', seg=4, rings=3)
    head.loft([((sx * 0.07, 0.115, -0.25), 0.03, 0.025), ((sx * 0.17, 0.11, -0.19), 0.05, 0.035),
               ((sx * 0.23, 0.07, -0.08), 0.0005, 0.0005)], 'white', 5)               # 눈썹뼈 (화난 눈매)
# 경찰 모자: 남색 위로 벌어지는 몸통 + 검은 띠 + 반짝이는 챙 + 금색 모자 배지
head.loft([((0, 0.15, 0.0), 0.215, 0.235), ((0, 0.22, -0.01), 0.25, 0.27), ((0, 0.27, -0.02), 0.3, 0.32),
           ((0, 0.285, -0.02), 0.27, 0.29), ((0, 0.29, -0.02), 0.0005, 0.0005)], 'navy', 14)
head.loft([((0, 0.15, 0.0), 0.222, 0.242), ((0, 0.2, -0.008), 0.24, 0.26)], 'navyDark', 14)
head.slab([(-0.2, -0.12), (-0.16, -0.27), (0, -0.36), (0.16, -0.27), (0.2, -0.12), (0, -0.2)],
          0.2, 0.025, 'visor', tilt=0.15)
head.sphere((0, 0.235, -0.27), (0.05, 0.055, 0.015), 'gold', seg=6, rings=5)
head.build()

# ── 꼬리: 흰 깃털 7장 부채꼴 ──
tail = Part('tail', (0, 0.08, 0.55))
for i, a in enumerate((-0.48, -0.32, -0.16, 0, 0.16, 0.32, 0.48)):
    L = 0.86 - abs(a) * 0.3
    tail.slab(feather(L, 0.2), 0.01 * (3 - abs(i - 3)), 0.035, 'white', rot(math.pi / 2 + a))
tail.build()

# ── 날개: 안쪽 = 제복 소매(어깨 견장, 팔꿈치 쪽 금색 계급줄), 바깥쪽 = 갈색 손가락깃 ──
for sx, side in ((-1, 'L'), (1, 'R')):
    inner = Part('wingInner_' + side, (sx * 0.3, 0.14, -0.12))
    mirror = lambda x, z, sx=sx: (sx * x, z)
    inner.slab([(0, -0.26), (0.3, -0.3), (0.75, -0.22), (0.75, 0.36), (0.45, 0.4), (0, 0.34)],
               0, 0.08, 'navy', mirror)
    inner.slab([(0.02, -0.2), (0.24, -0.22), (0.24, 0.18), (0.02, 0.2)], 0.045, 0.02, 'gold', mirror)    # 견장
    for x0 in (0.58, 0.66):                                                                             # 계급줄
        inner.slab([(x0, -0.22), (x0 + 0.045, -0.22), (x0 + 0.045, 0.35), (x0, 0.35)], 0.045, 0.015, 'gold', mirror)
    for i in range(6):   # 소매 밖으로 나온 갈색 둘째날개깃
        inner.slab(feather(0.42, 0.2), -0.03, 0.03, 'feather', rot(math.pi / 2 - 0.12, 0.04 + i * 0.13, 0.26, sx))
    inner.build()

    outer = Part('wingOuter_' + side, (sx * (0.3 + 0.75), 0.14, -0.12))
    outer.slab([(0, -0.22), (0.32, -0.2), (0.32, 0.36), (0, 0.38)], 0, 0.06, 'featherMid', mirror)
    for i, (z0, a, L) in enumerate(((-0.15, -0.05, 1.0), (-0.05, 0.08, 0.96), (0.05, 0.2, 0.9),
                                    (0.15, 0.33, 0.82), (0.24, 0.47, 0.72), (0.32, 0.62, 0.6))):
        outer.slab(feather(L, 0.15), -0.006 * i, 0.035, 'feather', rot(a, 0.14, z0, sx))
    outer.build()

kit.export(OUT)
if RENDER and OUT:
    kit.render(OUT, 'bird', target=(0, 0.1, -0.2),
               views=(('front', (1.6, 0.9, -2.6)), ('side', (3.6, 0.5, -0.2)), ('back', (-2.2, 2.2, 3.4))))
