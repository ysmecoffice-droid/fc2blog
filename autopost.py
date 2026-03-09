import os
import datetime
import smtplib
import base64
import google.generativeai as genai
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

# Gemini API の初期化
genai.configure(api_key=GEMINI_API_KEY)

def generate_infographic(text_content):
    """画像生成を試みる（無料版では失敗してもエラーにせずスキップする）"""
    try:
        # 確実に存在する名称を指定
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Create a simple infographic about: {text_content}"
        
        # 無料版の場合、IMAGE出力は制限されることが多いためtry-exceptで保護
        response = model.generate_content(prompt)
        
        image_part = next((p for p in response.candidates[0].content.parts if p.inline_data), None)
        if image_part:
            return image_part.inline_data.data
    except Exception as e:
        print(f"画像生成はスキップされました: {e}")
    return None

def send_blog_email(title, md_content, img_base64):
    """メール投稿機能を利用して投稿"""
    msg = MIMEMultipart()
    msg['Subject'] = title
    msg['From'] = SMTP_USER
    msg['To'] = FC2_POST_EMAIL

    html_main = markdown.markdown(md_content)
    
    if img_base64:
        html_body = f'<div style="text-align:center;"><img src="cid:info_img" style="max-width:100%;"></div><br>{html_main}'
    else:
        html_body = html_main

    msg.attach(MIMEText(html_body, 'html'))

    if img_base64:
        try:
            img_data = base64.b64decode(img_base64)
            img = MIMEImage(img_data)
            img.add_header('Content-ID', '<info_img>')
            msg.attach(img)
        except:
            pass

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"メール送信エラー: {e}")
        return False

def load_file(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def main():
    writing_rule = load_file("rules_writing.txt")
    
    if not os.path.exists("neta.txt"):
        print("neta.txt がありません。")
        return
        
    with open("neta.txt", "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    # ネタ切れチェック
    target_idx = next((i for i, l in enumerate(lines) if not l.startswith("[済]")), -1)
    if target_idx == -1:
        print("投稿できるネタがありません。")
        return
    
    target_topic = lines.pop(target_idx)

    print(f"モデル models/gemini-1.5-flash で実行中: {target_topic}")
    try:
        # モデル名をフルパス 'models/gemini-1.5-flash' で指定して404を回避
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        # エラーの原因になりやすい引数を避け、プロンプトに全てを詰め込む
        prompt = (
            f"あなたはプロのブロガーです。以下の【ルール】を守って、【テーマ】について読者が喜ぶ記事を書いてください。\n\n"
            f"【ルール】\n{writing_rule}\n\n"
            f"【テーマ】\n{target_topic}"
        )
        
        # 記事生成
        response = model.generate_content(prompt)
        article_text = response.text
        
        # 画像生成（オプション）
        img_b64 = generate_infographic(article_text)
        
        # 送信
        success = send_blog_email(target_topic, article_text, img_b64)
        
        if success:
            now = datetime.datetime.now().strftime("%Y-%m-%d")
            lines.append(f"[済] {now} : {target_topic}")
            with open("neta.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            print("--- 投稿成功 ---")
        else:
            print("--- 送信失敗 ---")
            
    except Exception as e:
        print(f"重大なエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
