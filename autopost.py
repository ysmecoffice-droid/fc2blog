import os
import datetime
import smtplib
import base64
import json
import requests
import markdown
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- GitHub Secrets から設定を取得 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FC2_POST_EMAIL = os.getenv("FC2_POST_EMAIL")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

def call_gemini_api(prompt):
    """
    モデル名やAPIバージョンの違いによる 404 エラーを回避するため
    複数の組み合わせで試行する頑健な呼び出し関数です。
    """
    # 試行するモデル名の候補
    models = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]
    # 試行するAPIバージョンの候補
    api_versions = ["v1", "v1beta"]
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for version in api_versions:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={GEMINI_API_KEY}"
            print(f"試行中: {version}/{model}...")
            
            try:
                response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    print(f"成功: {version}/{model} で記事を生成しました。")
                    return content
                else:
                    print(f"失敗: {version}/{model} (Status: {response.status_code})")
                    continue
            except Exception as e:
                print(f"通信エラー: {e}")
                continue
                
    return None

def send_blog_email(title, md_content):
    """メールを介してFC2ブログへ投稿"""
    msg = MIMEMultipart()
    msg['Subject'] = title
    msg['From'] = SMTP_USER
    msg['To'] = FC2_POST_EMAIL

    # MarkdownをHTMLに変換
    html_main = markdown.markdown(md_content)
    
    # 簡単な装飾を追加
    html_body = f"""
    <html>
    <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; line-height: 1.6;">
        {html_main}
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

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
    print(f"処理開始: {target_topic}")

    # プロンプト作成
    full_prompt = (
        f"以下の【執筆ルール】に従い、【テーマ】について読者に役立つブログ記事をMarkdown形式で書いてください。\n\n"
        f"【執筆ルール】\n{writing_rule}\n\n"
        f"【テーマ】\n{target_topic}"
    )

    # 記事生成（404回避ロジック付き）
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
            print("エラー: メール送信に失敗しました。")
    else:
        print("エラー: 記事生成に失敗しました（すべてのモデル/バージョンで404または拒否）。")

if __name__ == "__main__":
    main()
