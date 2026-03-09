import os
import datetime
import smtplib
import base64
import google.generativeai as genai
from google.generativeai.types import RequestOptions
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

# Gemini API の初期化（REST通信を使用して安定性を向上）
genai.configure(api_key=GEMINI_API_KEY, transport='rest')

def generate_infographic(model_name, text_content):
    """インフォグラフィック（図解画像）の生成を試みる"""
    try:
        model = genai.GenerativeModel(model_name)
        # 画像生成用のプロンプト
        prompt = f"Create a simple, modern infographic summary for: {text_content}"
        
        # 404エラーを回避するため、明示的に安定版 v1 を使用
        options = RequestOptions(api_version='v1')
        response = model.generate_content(prompt, request_options=options)
        
        # 応答から画像データを抽出（インラインデータを探す）
        image_part = next((p for p in response.candidates[0].content.parts if p.inline_data), None)
        if image_part:
            return image_part.inline_data.data
    except Exception as e:
        print(f"画像生成スキップ（無料版制限など）: {e}")
    return None

def send_blog_email(title, md_content, img_base64):
    """メールを介してFC2ブログへ投稿"""
    msg = MIMEMultipart()
    msg['Subject'] = title
    msg['From'] = SMTP_USER
    msg['To'] = FC2_POST_EMAIL

    # MarkdownをHTMLに変換
    html_main = markdown.markdown(md_content)
    
    if img_base64:
        # 画像を記事の最上部に挿入し、枠線を付ける
        html_body = f'''
        <div style="text-align:center; margin-bottom:20px;">
            <img src="cid:info_img" style="max-width:100%; border:1px solid #ddd; border-radius:8px;">
        </div>
        <div class="article-body">
            {html_main}
        </div>
        '''
    else:
        html_body = html_main

    msg.attach(MIMEText(html_body, 'html'))

    # 画像の添付（HTML内から参照できるようにContent-IDを設定）
    if img_base64:
        try:
            img_data = base64.b64decode(img_base64)
            img = MIMEImage(img_data)
            img.add_header('Content-ID', '<info_img>')
            msg.attach(img)
        except Exception as e:
            print(f"画像デコード/添付エラー: {e}")

    # SMTP送信実行
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
    """外部ファイルを読み込む"""
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def main():
    # 各種設定・ルールの読み込み
    writing_rule = load_file("rules_writing.txt")
    if not os.path.exists("neta.txt"):
        print("Error: neta.txt がリポジトリに見つかりません。")
        return
        
    with open("neta.txt", "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    # 未投稿のネタ（[済]がつ言っていない最初の行）を特定
    target_idx = next((i for i, l in enumerate(lines) if not l.startswith("[済]")), -1)
    if target_idx == -1:
        print("通知: すべてのネタが投稿済みです。neta.txtを更新してください。")
        return
    
    target_topic = lines[target_idx]

    # 無料プランで最も安定動作するモデルを指定
    model_name = 'models/gemini-1.5-flash'
    print(f"開始: {target_topic} (使用モデル: {model_name})")

    try:
        # 安定版エンドポイント(v1)を指定してモデルを初期化
        options = RequestOptions(api_version='v1')
        model = genai.GenerativeModel(model_name)
        
        # 404エラーの原因になりやすい system_instruction 引数を避け、プロンプトに統合
        full_prompt = (
            f"あなたはプロのブロガーです。以下の【執筆ルール】を厳守し、【テーマ】について読者が読みやすい記事をMarkdown形式で執筆してください。\n\n"
            f"【執筆ルール】\n{writing_rule}\n\n"
            f"【テーマ】\n{target_topic}"
        )
        
        # 記事テキスト生成
        response = model.generate_content(full_prompt, request_options=options)
        article_text = response.text
        
        # インフォグラフィック画像を生成
        img_b64 = generate_infographic(model_name, article_text)
        
        # 送信処理
        if send_blog_email(target_topic, article_text, img_b64):
            # 成功時にneta.txtを更新（日付と[済]マークを付与）
            now = datetime.datetime.now().strftime("%Y-%m-%d")
            lines[target_idx] = f"[済] {now} : {target_topic}"
            with open("neta.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            print(f"完了: '{target_topic}' の投稿に成功しました。")
        else:
            print("エラー: メールの送信に失敗しました。SMTP設定を確認してください。")
            
    except Exception as e:
        print(f"実行中に重大なエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
