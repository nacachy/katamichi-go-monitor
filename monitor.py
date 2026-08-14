import re
import requests
from bs4 import BeautifulSoup

URL = "https://cp.toyota.jp/rentacar/"

TARGET_PREFECTURES = ("岩手県", "宮城県", "福島県")


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def main():
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

    soup = BeautifulSoup(response.text, "html.parser")

    # まずページ全体のテキストから、
    # 「出発店舗」「返却店舗」「出発期間」などを含む
    # 車両情報を取得できるか確認する。
    text = soup.get_text("\n", strip=True)

    print("ページ取得成功")
    print(f"HTMLサイズ: {len(response.text):,} bytes")
    print()

    # 対象3県の出発店舗を含む箇所を抽出
    lines = [normalize(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    found = 0

    for i, line in enumerate(lines):
        if "出発" not in line or "店舗" not in line:
            continue

        # この周辺に都道府県名があるか確認
        block = " ".join(lines[i:i + 20])

        if not any(pref in block for pref in TARGET_PREFECTURES):
            continue

        # 東京への返却を示す可能性のあるブロックだけ表示
        if "東京" not in block and "西東京" not in block:
            continue

        print("=" * 70)
        print(block)
        print("=" * 70)

        found += 1

    print()
    print(f"候補ブロック数: {found}")


if __name__ == "__main__":
    main()