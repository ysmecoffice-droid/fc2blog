import os
import datetime
import smtplib
import base64
import json
import requests
import markdown
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# --- GitHub Secrets から設定を取得 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FC2_POST_EMAIL = os.getenv("FC2_POST_EMAIL")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

def call_gemini_api(prompt):
    """
    Google AI Studio の REST API (v1 安定版) を直接呼び出す。
    ライブラリの 404 エラーを回避するための最も確実な方法です。
    """
    # 安定版 v1 エンドポイントを使用
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Gemini API 直接呼び出しエラー: {e}")
        if response.text:
            print(f"エラー詳細: {response.text}")
        return None

def send_blog_email(title, md_content):
    """メールを介してFC2ブログへ投稿（今回は確実に記事を送るため画像なしのシンプル版）"""
    msg = MIMEMultipart()
    msg['Subject'] = title
    msg['From'] = SMTP_USER
    msg['To'] = FC2_POST_EMAIL

    # MarkdownをHTMLに変換
    html_main = markdown.markdown(md_content)
    msg.attach(MIMEText(html_main, 'html'))

    # SMTP送信
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"SMTP送信エラー: {e}")
        return False

def load_file(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def main():
    writing_rule = load_file("rules_writing.txt")
    if not os.path.exists("neta.txt"):
        print("Error: neta.txt が見つかりません。")
        return
        
    with open("neta.txt", "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    target_idx = next((i for i, l in enumerate(lines) if not l.startswith("[済]")), -1)
    if target_idx == -1:
        print("通知: すべてのネタが投稿済みです。")
        return
    
    target_topic = lines[target_idx]
    print(f"開始（REST API v1 使用）: {target_topic}")

    # プロンプト作成
    full_prompt = (
        f"あなたはプロのブロガーです。以下の【執筆ルール】を厳守し、【テーマ】についてMarkdown形式で執筆してください。\n\n"
        f"【執筆ルール】\n{writing_rule}\n\n"
        f"【テーマ】\n{target_topic}"
    )

    # 記事生成
    article_text = call_gemini_api(full_prompt)
    
    if article_text:
        # 送信処理
        if send_blog_email(target_topic, article_text):
            now = datetime.datetime.now().strftime("%Y-%m-%d")
            lines[target_idx] = f"[済] {now} : {target_topic}"
            with open("neta.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            print(f"完了: '{target_topic}' の投稿に成功しました。")
        else:
            print("エラー: 送信に失敗しました。")
    else:
        print("エラー: 記事の生成に失敗しました。")

if __name__ == "__main__":
    main()
