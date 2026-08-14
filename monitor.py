import requests
from bs4 import BeautifulSoup
import re

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

print("ページ取得成功")
print(f"HTMLサイズ: {len(html):,} bytes")
print()

soup = BeautifulSoup(html, "html.parser")

# ページ内のテキストを取得
text = soup.get_text("\n", strip=True)
lines = [line.strip() for line in text.splitlines() if line.strip()]

print("===== 片道GO 車両情報 =====")
print()

results = []

# 「（○○県 ○○市）」から始まるブロックを探す
for i, line in enumerate(lines):

    # 都道府県＋市区町村の行を発見
    if not re.match(r"^（.+県 .+市）$", line):
        continue

    location = line

    # この地点から次の地点までを見る
    end = len(lines)
    for j in range(i + 1, len(lines)):
        if re.match(r"^（.+県 .+市）$", lines[j]):
            end = j
            break

    block = lines[i:end]

    departure_store = None
    return_company = None
    departure_period = None
    car_model = None

    # 出発店舗
    for j in range(len(block) - 1):
        if block[j] == "店舗":
            candidate = block[j + 1]
            if "トヨタ" in candidate:
                departure_store = candidate
                break

    # 返却可能会社
    for j in range(len(block) - 1):
        if "返却可能店舗" in block[j]:
            candidate = block[j - 1] if j > 0 else ""
            if candidate:
                return_company = candidate
            break

    # 出発期間
    for j in range(len(block) - 1):
        if block[j] == "出発期間":
            candidate = block[j + 1]
            if re.search(r"\d{4}年\d{1,2}月\d{1,2}日", candidate):
                departure_period = candidate
            break

    # 車種
    for j in range(len(block) - 1):
        if block[j] == "車種":
            # 「さらに詳細をみる」などを飛ばして車種名を探す
            for k in range(j + 1, min(j + 10, len(block))):
                candidate = block[k]

                if candidate in ["さらに詳細をみる", "詳細を閉じる", "車両条件"]:
                    continue

                # 車種らしい文字列
                if any(
                    name in candidate
                    for name in [
                        "ヤリス",
                        "プリウス",
                        "カローラ",
                        "シエンタ",
                        "ライズ",
                        "ノア",
                        "アルファード",
                        "ハイエース",
                        "プロボックス",
                        "ツーリング",
                    ]
                ):
                    car_model = candidate
                    break

            if car_model:
                break

    # 情報が取れたものだけ登録
    if departure_store and departure_period and car_model:
        results.append({
            "location": location,
            "departure_store": departure_store,
            "return_company": return_company,
            "departure_period": departure_period,
            "car_model": car_model,
        })


# 結果を表示
print(f"検出した車両情報: {len(results)}件")
print()

for n, result in enumerate(results, 1):
    print(f"===== {n}件目 =====")
    print(f"出発地: {result['location']}")
    print(f"出発店舗: {result['departure_store']}")
    print(f"返却可能: {result['return_company']}")
    print(f"出発期間: {result['departure_period']}")
    print(f"車種: {result['car_model']}")
    print()

print("===== 処理完了 =====")