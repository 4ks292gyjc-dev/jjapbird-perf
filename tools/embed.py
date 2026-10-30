# .glb 를 index.html 안의 <script type="text/plain" id="..."> 블록에 base64 로 넣는다 (없으면 </body> 앞에 새로 만듦)
#   python3 tools/embed.py out/bird.glb bird-glb
import sys, base64, re, textwrap, os

glb, block_id = sys.argv[1], sys.argv[2]
html = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.html')
b64 = '\n'.join(textwrap.wrap(base64.b64encode(open(glb, 'rb').read()).decode(), 120))
block = (f'<!-- 모델 {block_id} (tools/ 의 블렌더 스크립트로 생성한 .glb 의 base64) -->\n'
         f'<script type="text/plain" id="{block_id}">\n{b64}\n</script>\n')
s = open(html, encoding='utf-8').read()
pat = re.compile(r'<!-- (?:새 모델|모델 ' + re.escape(block_id) + r') [^\n]*-->\n<script type="text/plain" id="'
                 + re.escape(block_id) + r'">.*?</script>\n', re.S)
s, n = pat.subn(lambda m: block, s)
if n == 0: s = s.replace('</body>', block + '</body>')
open(html, 'w', encoding='utf-8').write(s)
print(f'{block_id}: {len(b64) // 1024} KB base64', '(replaced)' if n else '(added)')
