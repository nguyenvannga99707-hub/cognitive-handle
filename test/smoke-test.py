#!/usr/bin/env python3
"""认知抓手 · 冒烟测试
推给真人前：python3 smoke-test.py --quick  （30秒，检查结构+JS+CDN）
完整验证：  python3 smoke-test.py            （含API连通+Supabase）

exit 0=全绿 | 1=警告 | 2=阻断
"""

import subprocess, sys, re

RED='\033[91m';GREEN='\033[92m';YELLOW='\033[93m';RESET='\033[0m'
PASS=WARN=FAIL=0
FULL='--quick' not in sys.argv

def check(name, ok, detail=""):
    global PASS,WARN,FAIL
    if ok is True: print(f"  {GREEN}\u2713{RESET} {name}");PASS+=1
    elif ok=="WARN":print(f"  {YELLOW}\u26a0{RESET} {name} {detail}");WARN+=1
    else:print(f"  {RED}\u2717{RESET} {name} {detail}");FAIL+=1

def run(cmd, timeout=30):
    try:
        r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=timeout)
        return r.stdout.strip(),r.stderr.strip(),r.returncode
    except:return "","TIMEOUT",-1

REPO='/home/xiangshujun/.hermes/projects/cognitive-handle'
with open(f'{REPO}/index.html') as f: html=f.read()

# ====== 1. HTML结构 ======
print("\n===== HTML关键元素 =====")
for name,pat in [
    ('error-banner组件', 'error-banner'),
    ('showError函数', 'function showError'),
    ('drill失败反馈"挖不动"', '\u6316\u4e0d\u52a8'),
    ('passcode守卫!_restored', '!_restored'),
    ('DEMOS声明', 'const DEMOS'),
    ('续命锁屏跳过', '_restored ? layer <='),
    ('catch安全getDemo', 'catch(e2)'),
    ('finally不覆盖error', "btn.classList.contains('error')"),
    ('DeepSeek Key', "atob('Mzk0"),
    ('Supabase URL', 'huxjrjovoxwoolxmdgub'),
]:
    check(name, pat in html)

# 额外验证：DEMOS和_dk必须在IIFE(setTimeout)之前初始化
if 'const DEMOS' in html and 'URL 参数检测' in html:
    check('  DEMOS在IIFE之前(位置)', html.index('const DEMOS') < html.index('URL 参数检测'))
if 'const _dk' in html and 'URL 参数检测' in html:
    check('  _dk在IIFE之前(位置)', html.index('const _dk') < html.index('URL 参数检测'))

# ====== 2. JS语法 ======
print("\n===== JS语法 =====")
tmp='/tmp/ch-smoke.js'
with open(tmp,'w') as f: f.write(html[html.index('<script>')+8:html.index('</script>')])
out,err,code=run(f'node --check {tmp}')
check("node --check",code==0,err[:80] if err else "")

# ====== 3. CDN版本 ======
print("\n===== CDN版本 =====")
out,_,code=run("powershell.exe -Command \"(iwr 'https://nguyenvannga99707-hub.github.io/cognitive-handle/' -UseBasicParsing -TimeoutSec 15).Content\"")
if code==0 and out:
    cdn_v=re.search(r'<!-- (v[\d.]+)',out)
    local_v=re.search(r'<!-- (v[\d.]+)',html)
    if cdn_v and local_v:
        match=cdn_v.group(1)==local_v.group(1)
        check(f"CDN={cdn_v.group(1)} == 本地={local_v.group(1)}", match)
    local_h,_=run(f'git -C {REPO} rev-parse --short HEAD')
    pages,_=run(f"cd {REPO} && gh api repos/nguyenvannga99707-hub/cognitive-handle/pages/builds --jq '.[0]|.commit[:8]' 2>/dev/null")
    if pages and local_h:
        check("Pages commit="+local_h, pages==local_h, f"Pages:{pages}" if pages!=local_h else "")
else: check("CDN\u53ef\u8bbf\u95ee","WARN","powershell\u6216\u7f51\u7edc\u95ee\u9898")

# ====== 4. 完整模式：API + Supabase ======
if FULL:
    print("\n===== API\u8fde\u901a (--full) =====")
    import base64
    dk=re.search(r"atob\('([^']+)'\)",html)
    if dk:
        key='sk-'+base64.b64decode(dk.group(1)).decode()
        # Write temp script to avoid key in process list
        with open('/tmp/ch-api-test.sh','w') as f:
            f.write(f'#!/bin/bash\ncurl -s --max-time 12 -H "Content-Type: application/json" -H "Authorization: Bearer *** -d \'{{"model":"deepseek-chat","messages":[{{"role":"user","content":"1"}}],"max_tokens":1}}\' https://api.deepseek.com/v1/chat/completions\n')
        out,_,_=run('bash /tmp/ch-api-test.sh')
        if 'choices' in out: check("DeepSeek API",True)
        elif '401' in out: check("DeepSeek API",False,"Key\u5931\u6548")
        elif '429' in out: check("DeepSeek API","WARN","\u9650\u6d41")
        else: check("DeepSeek API","WARN",out[-60:].replace('\n',''))

    print("\n===== Supabase =====")
    sb_match=re.search(r"SB_KEY\s*=\s*\[([^\]]+)\]\.join\(''\)",html)
    if sb_match:
        parts=re.findall(r"'([^']*)'",sb_match.group(1))
        sb_key=''.join(parts)
        with open('/tmp/ch-sb-test.sh','w') as f:
            f.write(f'#!/bin/bash\ncurl -s --max-time 10 -H "apikey: *** t=session_start&limit=1"\n')
        out,_,_=run('bash /tmp/ch-sb-test.sh')
        if '200' in out or 'session_start' in out: check("Supabase",True)
        else: check("Supabase","WARN",out[-80:].replace('\n',''))

# ====== \u603b\u7ed3 ======
print(f"\n{'='*40}")
print(f"  {GREEN}\u2713 {PASS}{RESET}  {YELLOW}\u26a0 {WARN}{RESET}  {RED}\u2717 {FAIL}{RESET}")
if FAIL:print(f"\n{RED}\u274c \u4e0d\u901a\u8fc7\uff01\u4fee\u597d\u518d\u63a8\u771f\u4eba\u3002{RESET}");sys.exit(2)
elif WARN:print(f"\n{YELLOW}\u26a0 \u6709\u8b66\u544a\uff0c\u5efa\u8bae\u68c0\u67e5\u3002{RESET}");sys.exit(1)
else:print(f"\n{GREEN}\u2705 \u5168\u7eff\uff0c\u53ef\u4ee5\u63a8\u3002{RESET}");sys.exit(0)
