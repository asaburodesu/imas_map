# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import json
import time

# シングルクォートをダブルクォートに変換し、JSONを修正する関数
def fix_json_string(json_str):
    try:
        # 1. プロパティ名の前にダブルクォートを追加（例：name: → "name":）
        json_str = re.sub(r'\b(\w+):(?=\s*["[\d{])', r'"\1":', json_str)
        
        # 2. 文字列値のシングルクォートをダブルクォートに変換し、特殊文字をエスケープ
        def escape_special_chars(match):
            value = match.group(1)
            # JSONで必要なエスケープ（例: " → \", & → \&）
            value = (value.replace('"', '\\"')
                         .replace('&', '\\&')
                         .replace('\n', '\\n')
                         .replace('\r', '\\r')
                         .replace('\t', '\\t'))
            return f'"{value}"'
        
        json_str = re.sub(r":\s*'([^']*)'", escape_special_chars, json_str)
        
        # 3. 配列内のシングルクォートをダブルクォートに変換
        json_str = re.sub(r"\[\s*'([^']*)'\s*]", r'["\1"]', json_str)
        
        # 4. 不正な制御文字を削除
        json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
        
        # 5. 余分なカンマを削除
        json_str = re.sub(r',\s*]', ']', json_str)
        json_str = re.sub(r',\s*}', '}', json_str)
        
        return json_str
    except Exception as e:
        print(f"JSON文字列修正エラー: {e}")
        return json_str

# 出力ファイルを開く
with open('data.json', 'w', encoding='utf-8', errors='ignore') as f:
    # ベースJSON構造
    base_json_dict = {
        "range": "スポットデータ",
        "majorDimension": "ROWS",
        "values": [
            ["タイムスタンプ", "カテゴリ", "画像", "緯度", "経度", "スポット名", "紹介文", "Instagram", "Twitter", "公式サイト", "Facebook"]
        ]
    }

    # 全都道府県（JP-01 から JP-47）をループ
    for area_code in range(1, 48):
        url = f'https://bandainamco-am.co.jp/am/vg/idolmaster-tours/location/list?area=JP-{str(area_code).zfill(2)}'
        print(f"スクレイピング中: {url}")
        
        try:
            # ページを取得
            res = requests.get(url)
            res.raise_for_status()  # エラーチェック
            soup = BeautifulSoup(res.text, "html.parser")

            # 都道府県名を取得（<h1>タグから）
            prefecture = soup.find("h1").text.strip() if soup.find("h1") else "不明"

            # <dl>タグからスポット情報を取得
            dl_elements = soup.find_all("dl")
            spot_dict = {}  # スポット名をキーにして情報を一時保存
            for dl in dl_elements:
                dt_elements = dl.find_all("dt")
                dd_elements = dl.find_all("dd")
                i = 0
                while i < len(dd_elements):
                    if dd_elements[i].get("class") == ["address"]:
                        name = dt_elements[i // 2].text.strip()
                        address = dd_elements[i].text.strip()
                        count = dd_elements[i + 1].text.strip() if i + 1 < len(dd_elements) and dd_elements[i + 1].get("class") == ["count"] else ""
                        detail_url = dt_elements[i // 2].find("a")["href"] if dt_elements[i // 2].find("a") else ""
                        if detail_url.startswith("./detail"):
                            detail_url = f"https://bandainamco-am.co.jp/am/vg/idolmaster-tours{detail_url[1:]}"
                        spot_dict[name] = {
                            "address": address,
                            "count": count,
                            "detail_url": detail_url,
                            "latitude": "",
                            "longitude": ""
                        }
                        i += 2
                    else:
                        i += 1

            # JavaScript内のlocations配列から緯度・経度を取得
            script_tags = soup.find_all("script")
            locations_found = False
            for script in script_tags:
                if "var locations =" in script.text:
                    # locations配列を抽出
                    locations_text = re.search(r'var locations = (\[.*?\]);', script.text, re.DOTALL)
                    if locations_text:
                        locations_found = True
                        try:
                            # デバッグ用：抽出された文字列を出力
                            raw_json = locations_text.group(1)
                            print(f"抽出されたlocations: {raw_json[:100]}...")
                            # JSONを修正
                            fixed_json = fix_json_string(raw_json)
                            print(f"修正後のJSON: {fixed_json[:100]}...")
                            # JSONパース
                            locations_data = json.loads(fixed_json)
                            for location in locations_data:
                                name = location.get("name", "")
                                if name in spot_dict:
                                    spot_dict[name]["latitude"] = str(location.get("latitude", ""))
                                    spot_dict[name]["longitude"] = str(location.get("longitude", ""))
                                    print(f"スポット: {name}, 緯度: {spot_dict[name]['latitude']}, 経度: {spot_dict[name]['longitude']}")
                        except json.JSONDecodeError as e:
                            print(f"JSONパースエラー ({url}): {e}")
                            print(f"問題のJSON文字列: {fixed_json}...")
                            continue
                        except Exception as e:
                            print(f"その他のエラー ({url}): {e}")
                            continue

            if not locations_found:
                print(f"警告: locations配列が見つかりませんでした ({url})")

            # JSONデータに追加
            for name, info in spot_dict.items():
                twitter_url = f"twitter://post?message={urllib.parse.quote(info['address'] + name)}"
                value = [
                    "",  # タイムスタンプ
                    prefecture,  # カテゴリ（都道府県）
                    "",  # 画像
                    info["latitude"],  # 緯度
                    info["longitude"],  # 経度
                    name,  # スポット名
                    f"{info['address']}\n{info['count']}",  # 紹介文（住所＋台数）
                    "",  # Instagram
                    twitter_url,  # Twitter
                    info["detail_url"],  # 公式サイト
                    ""   # Facebook
                ]
                base_json_dict["values"].append(value)

        except requests.RequestException as e:
            print(f"ページ取得エラー ({url}): {e}")
            continue

        # リクエスト間隔を調整（サーバー負荷軽減）
        time.sleep(1)

    # JSONを出力
    final_json_string = json.dumps(base_json_dict, indent=4, ensure_ascii=False)
    print(final_json_string)
    f.write(final_json_string)