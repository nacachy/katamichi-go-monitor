import os
import json
import re
import hashlib
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup


URL = "https://cp.toyota.jp/rentacar/"
STATE_FILE = "state.json"

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    )
}


def normalize(text):
    """文字列を比較しやすい形にする"""
    if not text:
        return ""

    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_value(lines, start_index, labels):
    """指定したラベルの直後にある値を取得"""
    for i in range(start_index + 1, min(start_index + 5, len(lines))):
        if lines[i] and lines[i] not in labels:
            return normalize(lines[i])
    return ""


def make_key(item):
    """車両情報から重複判定用のIDを作る"""
    raw = "|".join([
        item["departure"],
        item["return"],
        item["period"],
        item["vehicle"],
        item["condition"],
        item["phone"],
    ])

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def fetch_listings():
    """片道GOページから掲載車両を取得"""

    response = requests.get(
        URL,
        timeout=30,
        headers=HEADERS,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    text = soup.get_text("\n", strip=True)
    lines = [
        normalize(line)
        for line in text.splitlines()
        if normalize(line)
    ]

    labels = {
        "出発店舗",
        "返却店舗",
        "出発期間",
        "さらに詳細をみる",
        "詳細を閉じる",
        "車種",
        "車両条件",
        "予約電話番号",
        "出発",
        "到着",
        "店舗",
    }

    listings = []

    for i, line in enumerate(lines):

        if line != "出発店舗":
            continue

        # 次の「出発店舗」までを1件の候補として扱う
        end = len(lines)

        for j in range(i + 1, len(lines)):
            if lines[j] == "出発店舗":
                end = j
                break

        block = lines[i:end]

        departure = ""
        return_store = ""
        period = ""
        vehicle = ""
        condition = ""
        phone = ""

        # 出発店舗
        try:
            idx = block.index("出発店舗")
            departure = get_value(block, idx, labels)
        except ValueError:
            pass

        # 返却店舗
        try:
            idx = block.index("返却店舗")
            return_store = get_value(block, idx, labels)
        except ValueError:
            pass

        # 出発期間
        try:
            idx = block.index("出発期間")

            for k in range(idx + 1, min(idx + 5, len(block))):
                if re.search(r"\d{4}年\d+月\d+日", block[k]):
                    period = block[k]
                    break
        except ValueError:
            pass

        # 車種
        try:
            idx = block.index("車種")
            vehicle = get_value(block, idx, labels)
        except ValueError:
            pass

        # 車両条件
        try:
            idx = block.index("車両条件")
            condition = get_value(block, idx, labels)
        except ValueError:
            pass

        # 電話番号
        try:
            idx = block.index("予約電話番号")

            for k in range(idx + 1, min(idx + 6, len(block))):
                if re.search(r"\d{2,4}-\d{2,4}-\d{3,4}", block[k]):
                    phone = block[k]
                    break
        except ValueError:
            pass

        # 車両情報が取れていないものは除外
        if not departure or not vehicle or not period:
            continue

        item = {
            "departure": departure,
            "return": return_store,
            "period": period,
            "vehicle": vehicle,
            "condition": condition,
            "phone": phone,
        }

        item["key"] = make_key(item)

        listings.append(item)

    # 同じ車両情報がページ内に複数回存在する場合は1件にまとめる
    unique = {}

    for item in listings:
        unique[item["key"]] = item

    return list(unique.values())


def load_state():
    """過去の通知済み車両を読み込む"""

    if not os.path.exists(STATE_FILE):
        return {
            "notified_keys": []
        }

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "notified_keys": []
        }


def save_state(state):
    """通知済み車両を保存"""

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2,
        )


def send_discord(items):
    """新規掲載車両をDiscordへ通知"""

    if not WEBHOOK_URL:
        raise RuntimeError(
            "DISCORD_WEBHOOK_URL が設定されていません"
        )

    if not items:
        return

    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst).strftime("%Y/%m/%d %H:%M:%S")

    messages = []

    for item in items:
        message = (
            "🚗 **片道GO! 新規掲載を検知**\n"
            f"検知日時：{now}\n\n"
            f"📍 出発：{item['departure']}\n"
            f"📍 返却：{item['return'] or '記載なし'}\n"
            f"🚙 車種：{item['vehicle']}\n"
            f"📅 出発期間：{item['period']}\n"
            f"📝 車両条件：{item['condition'] or '記載なし'}\n"
            f"📞 予約電話：{item['phone'] or '記載なし'}\n\n"
            f"🔗 {URL}"
        )

        messages.append(message)

    # Discordの1メッセージ上限を考慮して分割
    current = ""

    for message in messages:

        if len(current) + len(message) + 2 > 1900:
            requests.post(
                WEBHOOK_URL,
                json={"content": current},
                timeout=20,
            ).raise_for_status()

            current = message

        else:
            if current:
                current += "\n\n"
            current += message

    if current:
        requests.post(
            WEBHOOK_URL,
            json={"content": current},
            timeout=20,
        ).raise_for_status()


def main():

    print("===== 片道GO Monitor =====")

    listings = fetch_listings()

    print(f"現在の掲載車両数：{len(listings)}件")

    state = load_state()

    notified_keys = set(
        state.get("notified_keys", [])
    )

    # 初回実行
    if not os.path.exists(STATE_FILE):

        print(
            f"初回実行：{len(listings)}件を基準として登録します。"
        )
        print("初回はDiscord通知を行いません。")

        state["notified_keys"] = [
            item["key"]
            for item in listings
        ]

        save_state(state)

        print("state.json を保存しました。")
        return

    # 新規掲載だけ抽出
    new_items = [
        item
        for item in listings
        if item["key"] not in notified_keys
    ]

    print(f"新規掲載：{len(new_items)}件")

    if new_items:

        for item in new_items:
            print(
                f"  NEW: {item['departure']} / "
                f"{item['vehicle']} / "
                f"{item['period']}"
            )

        send_discord(new_items)

        for item in new_items:
            notified_keys.add(item["key"])

        state["notified_keys"] = list(notified_keys)

        save_state(state)

        print("Discord通知完了。")

    else:
        print("新規掲載はありません。")

    print("===== 処理完了 =====")


if __name__ == "__main__":
    main()
