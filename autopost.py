import os
import datetime
import smtplib
import base64
import random
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
    """画像生成モデルでインフォグラフィック生成"""
    # 確実に存在するモデル名に変更
    model_image = genai.GenerativeModel('gemini-1.5-flash')
    try:
        prompt = f"Create a simple, professional infographic summarizing the following content. Use clear icons and layout, no complex text: {text_content}"
        
        # モデルが画像生成（response_modalities）に対応しているか、
        # またはテキストから画像生成を試みる設定。非対応環境を考慮しtry-exceptで保護
        response = model_image.generate_content(
            contents=[{'parts': [{'text': prompt}]}]
        )
        
        # インラインデータの抽出
        image_part = next((p for p in response.candidates[0].content.parts if p.inline_data), None)
        if image_part:
            return image_part.inline_data.data
    except Exception as e:
        print(f"画像生成スキップ（非対応またはエラー）: {e}")
    return None

def send_blog_email(title, md_content, img_base64):
    """メール投稿機能を利用して投稿"""
    msg = MIMEMultipart()
    msg['Subject'] = title
    msg['From'] = SMTP_USER
    msg['To'] = FC2_POST_EMAIL

    html_main = markdown.markdown(md_content)
    
    if img_base64:
        html_body = f'<div style="text-align:center;"><img src="cid:info_img" style="max-width:100%; border-radius:8px;"></div><br>{html_main}'
    else:
        html_body = html_main

    msg.attach(MIMEText(html_body, 'html'))

    if img_base64:
        img_data = base64.b64decode(img_base64)
        img = MIMEImage(img_data)
        img.add_header('Content-ID', '<info_img>')
        msg.attach(img)

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
    neta_rule = load_file("rules_neta.txt")
    
    if not os.path.exists("neta.txt"):
        print("neta.txt が見つかりません。")
        return
        
    with open("neta.txt", "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    unused_neta = [l for l in lines if not l.startswith("[済]")]
    if len(unused_neta) < 20:
        print("ネタを補充中...")
        # 安定版モデル名を使用
        model_neta = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Create 20 blog post ideas in 1 line each based on:\n{neta_rule}"
        res_neta = model_neta.generate_content(prompt)
        new_items = [l.strip() for l in res_neta.text.split('\n') if l.strip() and not l.startswith(('[', '1', '2'))]
        
        insert_pos = len(unused_neta)
        for item in new_items:
            lines.insert(insert_pos, item)
            insert_pos += 1

    target_idx = next((i for i, l in enumerate(lines) if not l.startswith("[済]")), -1)
    if target_idx == -1:
        print("投稿できるネタがありません。")
        return
    target_topic = lines.pop(target_idx)

    # 記事執筆
    print(f"執筆中: {target_topic}")
    model_write = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        system_instruction=writing_rule
    )
    article_res = model_write.generate_content(f"テーマ: {target_topic}")
    
    # 画像生成
    print("画像生成を試行中...")
    img_b64 = generate_infographic(article_res.text)
    
    # 送信
    success = send_blog_email(target_topic, article_res.text, img_b64)
    
    if success:
        now = datetime.datetime.now().strftime("%Y-%m-%d")
        lines.append(f"[済] {now} : {target_topic}")
        with open("neta.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("完了しました。")
    else:
        print("投稿に失敗しました。")

if __name__ == "__main__":
    main()
