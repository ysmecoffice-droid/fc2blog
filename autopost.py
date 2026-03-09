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
        
        # 無料版の場合、画像生成（IMAGE出力）は制限されることが多いため、
        # 失敗してもプログラムが止まらないようにしています
        response = model.generate_content(
            contents=[{'parts': [{'text': prompt}]}]
        )
        
        image_part = next((p for p in response.candidates[0].content.parts if p.inline_data), None)
        if image_part:
            return image_part.inline_data.data
    except Exception as e:
        print(f"画像生成はスキップされました（無料版制限など）: {e}")
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

    target_idx = next((i for i, l in enumerate(lines) if not l.startswith("[済]")), -1)
    if target_idx == -1:
        print("投稿できるネタがありません。")
        return
    
    target_topic = lines.pop(target_idx)

    print(f"実行中（モデル: gemini-1.5-flash）: {target_topic}")
    try:
        # モデル名を 'models/gemini-1.5-flash' とフルパスで指定（404対策）
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        # system_instruction を引数に使わず、プロンプトに統合して送信（404対策）
        prompt = f"あなたはプロのブロガーです。以下の【執筆ルール】に従い、【テーマ】について記事を書いてください。\n\n【執筆ルール】\n{writing_rule}\n\n【テーマ】\n{target_topic}"
        
        article_res = model.generate_content(prompt)
        
        # 画像生成を試行
        img_b64 = generate_infographic(article_res.text)
        
        # 送信
        success = send_blog_email(target_topic, article_res.text, img_b64)
        
        if success:
            now = datetime.datetime.now().strftime("%Y-%m-%d")
            lines.append(f"[済] {now} : {target_topic}")
            with open("neta.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            print("ブログ投稿に成功しました。")
        else:
            print("ブログ投稿（メール送信）に失敗しました。")
            
    except Exception as e:
        print(f"Gemini API エラー: {e}")

if __name__ == "__main__":
    main()
