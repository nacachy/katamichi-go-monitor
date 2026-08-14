import requests

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

with open("katamichi.html", "w", encoding="utf-8") as f:
    f.write(response.text)

print("ページ取得成功")
print(f"HTMLサイズ: {len(response.text):,} bytes")
print("katamichi.html を保存しました")