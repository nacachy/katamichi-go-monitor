import requests
from bs4 import BeautifulSoup

URL = "https://cp.toyota.jp/rentacar/"

response = requests.get(
    URL,
    timeout=30,
    headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0 Safari/537.36"
        )
    },
)

response.raise_for_status()

html = response.text

with open("katamichi.html", "w", encoding="utf-8") as f:
    f.write(html)

print("ページ取得成功")
print(f"HTMLサイズ: {len(html):,} bytes")
print()

soup = BeautifulSoup(html, "html.parser")

# ページ内のテキストを取得
text = soup.get_text("\n", strip=True)
lines = [line.strip() for line in text.splitlines() if line.strip()]

# 車両情報に関係しそうな行を表示
keywords = [
    "車両番号",
    "出発店舗",
    "返却店舗",
    "出発期間",
    "車種",
    "岩手県",
    "宮城県",
    "福島県",
    "東京都",
    "東京",
]

print("===== 片道GO関連テキスト =====")

count = 0

for i, line in enumerate(lines):
    if any(keyword in line for keyword in keywords):
        print(f"[{i}] {line}")

        # 周辺5行も表示
        for surrounding in lines[max(0, i - 2):min(len(lines), i + 3)]:
            if surrounding != line:
                print("    ", surrounding)

        print()
        count += 1

        # ログが巨大になりすぎないよう制限
        if count >= 100:
            print("===== 100件で表示を停止 =====")
            break

print()
print(f"関連テキスト検出数: {count}")
print()
print("katamichi.html を保存しました")