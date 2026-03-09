import os
import smtplib
import json
import requests
from email.mime.text import MIMEText

# --- GitHub Secrets から設定を取得 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

def test_gemini_api():
    print("--- 1. Gemini API 検証開始 ---")
    if not GEMINI_API_KEY:
        print("FAIL: GEMINI_API_KEY が設定されていません。")
        return False
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": "Hello, this is a connection test. Please reply with 'OK'."}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            reply = result['candidates'][0]['content']['parts'][0]['text']
            print(f"SUCCESS: Gemini API 接続成功。応答: {reply.strip()}")
            return True
        else:
            print(f"FAIL: Gemini API エラー (Status: {response.status_code})")
            print(f"詳細: {response.text}")
            return False
    except Exception as e:
        print(f"FAIL: Gemini API 通信エラー: {e}")
        return False

def test_smtp_login():
    print("\n--- 2. SMTP (メール送信) 検証開始 ---")
    if not SMTP_USER or not SMTP_PASS:
        print("FAIL: SMTP_USER または SMTP_PASS が設定されていません。")
        return False
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            print(f"SUCCESS: SMTPサーバー ({SMTP_HOST}) へのログインに成功しました。")
            
            # 自分のアドレス宛にテストメールを送信
            print("テストメールを送信中...")
            msg = MIMEText("これは自動投稿システムの設定検証メールです。このメールが届いていれば、SMTP設定は完璧です！")
            msg['Subject'] = "【テスト】自動投稿システム設定確認"
            msg['From'] = SMTP_USER
            msg['To'] = SMTP_USER
            
            server.send_message(msg)
            print(f"SUCCESS: {SMTP_USER} 宛にテストメールを送信しました。受信トレイを確認してください。")
            return True
    except smtplib.SMTPAuthenticationError:
        print("FAIL: 認証失敗。メールアドレスまたはアプリパスワードが間違っています。")
    except Exception as e:
        print(f"FAIL: SMTPエラー: {e}")
    return False

def main():
    print("=== システム設定検証ツール ===\n")
    
    gemini_ok = test_gemini_api()
    smtp_ok = test_smtp_login()
    
    print("\n=== 検証結果まとめ ===")
    print(f"Gemini API: {'[OK]' if gemini_ok else '[NG]'}")
    print(f"SMTP送信  : {'[OK]' if smtp_ok else '[NG]'}")
    
    if gemini_ok and smtp_ok:
        print("\nおめでとうございます！すべての設定が正しいです。本番の自動投稿を開始できます。")
    else:
        print("\nエラー箇所を確認し、GitHub Secrets の設定を見直してください。")

if __name__ == "__main__":
    main()
