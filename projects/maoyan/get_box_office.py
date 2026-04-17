"""
猫眼电影票房数据获取脚本
纯 requests 实现，不依赖浏览器自动化
逆向链路：signKey(MD5) + mygsig(MD5) + uid(csrf) + 字体反爬(Pillow渲染匹配)
"""

import hashlib
import base64
import math
import random
import time
import re
import json
import sys
from io import BytesIO
from collections import OrderedDict
from urllib.parse import urlparse, parse_qs

import requests
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont


# 常量
SIGN_KEY_SECRET = "A013F70DB97834C0A5492378BD76C53A"
MYGSIG_PREFIX = "581409236#"
CHANNEL_ID = 40009
API_URL = "https://piaofang.maoyan.com/i/api/dashboard-ajax"
PAGE_URL = "https://piaofang.maoyan.com/dashboard"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/147.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# 签名生成
# ---------------------------------------------------------------------------

def generate_sign_key(timestamp, index, ua_b64):
    """
    signKey 算法：拼接固定参数后做 MD5
    对应 JS: getQueryKey 函数
    """
    param_str = (
        f"method=GET&timeStamp={timestamp}&User-Agent={ua_b64}"
        f"&index={index}&channelId={CHANNEL_ID}&sVersion=2&key={SIGN_KEY_SECRET}"
    )
    return hashlib.md5(param_str.encode()).hexdigest()


def generate_mygsig(query_params, path, ts, ts1):
    """
    mygsig 算法：
    1. 将 URL 查询参数解析为对象
    2. 加入 path 字段
    3. 按 key 的 toLowerCase().localeCompare() 排序
    4. 提取值，用 _ 连接
    5. 前缀 "581409236#"，后缀 "$" + 时间戳
    6. MD5 哈希得到 ms1
    """
    # 将查询参数和 path 合并后排序
    all_params = dict(query_params)
    all_params["path"] = path
    sorted_keys = sorted(all_params.keys(), key=lambda k: k.lower())
    values = []
    for k in sorted_keys:
        v = all_params[k]
        # 如果值是对象则 JSON 序列化
        if isinstance(v, (dict, list)):
            v = json.dumps(v, separators=(",", ":"), ensure_ascii=False)
        values.append(str(v))
    joined = "_".join(values)

    # 拼接最终待哈希字符串
    hash_input = f"{MYGSIG_PREFIX}{joined}${ts}"
    ms1 = hashlib.md5(hash_input.encode()).hexdigest()

    return json.dumps({
        "m1": "0.0.3",
        "m2": 0,
        "m3": "0.0.67_tool",
        "ms1": ms1,
        "ts": ts,
        "ts1": ts1,
    }, separators=(",", ":"))


# ---------------------------------------------------------------------------
# 游客态初始化
# ---------------------------------------------------------------------------

def init_session():
    """
    初始化会话：访问主页获取 csrf/uid，设置 Cookie
    返回 (session, uid, uuid, ts1)
    """
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    # 生成 uuid（模拟 _lxsdk_cuid 格式）
    uuid = _generate_lxsdk_cuid()
    session.cookies.set("_lxsdk_cuid", uuid, domain="piaofang.maoyan.com")
    session.cookies.set("_lxsdk", uuid, domain="piaofang.maoyan.com")
    session.cookies.set("_lx_utm", "utm_source=google&utm_medium=organic",
                        domain="piaofang.maoyan.com")

    # 访问主页获取 csrf token
    resp = session.get(PAGE_URL, timeout=15)
    resp.raise_for_status()

    csrf_match = re.search(r'name="csrf"\s+content="([^"]+)"', resp.text)
    uid = csrf_match.group(1) if csrf_match else ""

    # ts1 为页面初始化时间戳
    ts1 = int(time.time() * 1000)

    return session, uid, uuid, ts1


def _generate_lxsdk_cuid():
    """生成模拟 _lxsdk_cuid 格式的标识符"""
    part1 = "".join(random.choices("0123456789abcdef", k=16))
    part2 = "".join(random.choices("0123456789abcdef", k=12))
    part3 = "".join(random.choices("0123456789abcdef", k=12))
    part4 = "".join(random.choices("0123456789abcdef", k=4))
    return f"{part1}-{part2}-{part3}-1fa400-{part1}{part4}"


# ---------------------------------------------------------------------------
# 字体反爬解码
# ---------------------------------------------------------------------------

def decode_html_entities(text):
    """HTML 实体解码（如 &#xe3df; → Unicode 字符）"""
    return re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), text)


def decode_font_with_pillow(woff_bytes):
    """
    用 Pillow 渲染字体中的每个 PUA 字形，与参考数字模板做像素匹配
    返回: {unicode_codepoint: digit}
    """
    font = TTFont(BytesIO(woff_bytes))
    cmap = font.getBestCmap()

    # 导出为 ttf 供 Pillow 使用
    ttf_buf = BytesIO()
    font.save(ttf_buf)
    ttf_buf.seek(0)

    try:
        pil_font = ImageFont.truetype(ttf_buf, 40)
    except Exception:
        return {}

    # 生成 0-9 参考模板（用系统 Arial 字体渲染）
    ref_templates = {}
    try:
        ref_font = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        ref_font = ImageFont.load_default()

    for digit in range(10):
        img = Image.new("L", (50, 60), 255)
        draw = ImageDraw.Draw(img)
        draw.text((5, 5), str(digit), font=ref_font, fill=0)
        ref_templates[digit] = _image_fingerprint(img)

    # 渲染每个 PUA 字符并匹配
    pua_images = {}
    for code, glyph_name in cmap.items():
        if code < 0xE000:
            continue
        char = chr(code)
        img = Image.new("L", (50, 60), 255)
        draw = ImageDraw.Draw(img)
        draw.text((5, 5), char, font=pil_font, fill=0)
        pua_images[code] = _image_fingerprint(img)

    # 贪心匹配
    scores = []
    for code, fp in pua_images.items():
        for digit, ref_fp in ref_templates.items():
            match_count = sum(a == b for a, b in zip(fp, ref_fp))
            scores.append((code, digit, match_count))

    scores.sort(key=lambda x: x[2], reverse=True)
    mapping = {}
    used_digits = set()
    for code, digit, _ in scores:
        if code in mapping or digit in used_digits:
            continue
        mapping[code] = digit
        used_digits.add(digit)

    return mapping


def _image_fingerprint(img):
    """将图像转为二值指纹序列"""
    pixels = list(img.getdata())
    return [1 if p < 128 else 0 for p in pixels]


def decode_number(encoded_text, mapping):
    """用映射表将 PUA 编码字符替换为实际数字"""
    result = []
    for ch in encoded_text:
        code = ord(ch)
        if code in mapping:
            result.append(str(mapping[code]))
        else:
            result.append(ch)
    return "".join(result)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def fetch_box_office():
    """获取猫眼电影票房数据"""
    # 1. 初始化会话
    session, uid, uuid, ts1 = init_session()

    # 2. 构建 signKey
    ua_b64 = base64.b64encode(USER_AGENT.encode()).decode()
    timestamp = int(time.time() * 1000)
    index = math.floor(random.random() * 1000 + 1)
    sign_key = generate_sign_key(timestamp, index, ua_b64)

    # 3. 构建 URL 查询参数（有序，与 JS Object.keys 一致）
    query_params = OrderedDict([
        ("orderType", "0"),
        ("uuid", uuid),
        ("timeStamp", str(timestamp)),
        ("User-Agent", ua_b64),
        ("index", str(index)),
        ("channelId", str(CHANNEL_ID)),
        ("sVersion", "2"),
        ("signKey", sign_key),
        ("WuKongReady", "h5"),
    ])

    # 4. 生成 mygsig
    ts = int(time.time() * 1000)
    path = "/i/api/dashboard-ajax"
    mygsig = generate_mygsig(query_params, path, ts, ts1)

    # 5. 发送请求
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": PAGE_URL,
        "m-appkey": "fe_com.sankuai.movie.fe.ipro",
        "m-traceid": str(random.randint(10**18, 10**19 - 1)),
        "uid": uid,
        "mygsig": mygsig,
        "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    resp = session.get(API_URL, params=query_params, headers=headers, timeout=15)

    if resp.status_code != 200:
        print(f"请求失败，状态码: {resp.status_code}")
        return []

    data = resp.json()

    if not data.get("movieList", {}).get("status"):
        print("接口返回异常")
        return []

    movie_list = data["movieList"]["data"]["list"]

    # 6. 解码字体反爬
    font_style = data.get("fontStyle", "")
    font_mapping = {}
    woff_match = re.search(r'url\(["\']?([^"\')]+\.woff)["\']?\)', font_style)
    if woff_match:
        woff_url = woff_match.group(1)
        if woff_url.startswith("//"):
            woff_url = "https:" + woff_url
        try:
            woff_resp = requests.get(woff_url, timeout=10)
            woff_resp.raise_for_status()
            font_mapping = decode_font_with_pillow(woff_resp.content)
        except Exception as e:
            print(f"字体解码失败: {e}")

    # 7. 组装结果
    results = []
    for movie in movie_list:
        info = {
            "name": movie["movieInfo"]["movieName"],
            "release": movie["movieInfo"]["releaseInfo"],
            "box_rate": movie["boxRate"],
            "show_count": movie["showCount"],
            "show_rate": movie["showCountRate"],
            "total_box": movie["sumBoxDesc"],
            "total_split": movie["sumSplitBoxDesc"],
        }
        raw_box = movie.get("boxSplitUnit", {}).get("num", "")
        if raw_box:
            decoded = decode_html_entities(raw_box)
            info["daily_box"] = decode_number(decoded, font_mapping) or "——"
        else:
            info["daily_box"] = ""
        results.append(info)

    return results


def print_results(movies):
    """格式化输出票房数据"""
    if not movies:
        print("未获取到票房数据")
        return

    print("=" * 90)
    print(f"{'排名':<4} {'电影名':<22} {'当日票房':<12} {'累计票房':<14} {'票房占比':<10} {'上映信息'}")
    print("-" * 90)
    for i, m in enumerate(movies, 1):
        name = m["name"][:20]
        daily = m.get("daily_box", "")
        daily_display = f"{daily}万" if daily and daily != "——" else "——"
        print(
            f"{i:<4} {name:<22} {daily_display:<12} "
            f"{m['total_box']:<14} {m['box_rate']:<10} {m['release']}"
        )
    print("=" * 90)
    print(f"共 {len(movies)} 部电影")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    print("正在获取猫眼电影票房数据...")
    data = fetch_box_office()
    print_results(data)
