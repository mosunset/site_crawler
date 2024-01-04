from pathlib import Path
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.parse import unquote
from PIL import Image

# from anti_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# ------ download_dir の変数 ------
# パスにOneDriveが含まれているときの対策
f_lst = list(Path.home().glob("*/Downloads"))
if len(f_lst) == 0:
    f_lst = list(Path.home().glob("Downloads"))
download_dir = str(f_lst[0])

# ------ ChromeDriver のオプション ------
options = Options()
# options.add_argument("--blink-settings=imagesEnabled=false")                                 # 画像を非表示にする。
options.add_argument("--disable-background-networking")                                      # 拡張機能の更新、セーフブラウジングサービス、アップグレード検出、翻訳、UMAを含む様々なバックグラウンドネットワークサービスを無効にする。
options.add_argument("--disable-blink-features=AutomationControlled")                        # navigator.webdriver=false となる設定。確認⇒ driver.execute_script("return navigator.webdriver")
options.add_argument("--disable-default-apps")                                               # デフォルトアプリのインストールを無効にする。
options.add_argument("--disable-dev-shm-usage")                                              # ディスクのメモリスペースを使う。DockerやGcloudのメモリ対策でよく使われる。
options.add_argument("--disable-extensions")                                                 # 拡張機能をすべて無効にする。
# options.add_argument("--disable-features=DownloadBubble")                                    # ダウンロードが完了したときの通知を吹き出しから下部表示(従来の挙動)にする。
options.add_argument('--disable-features=DownloadBubbleV2')                                  # `--incognito`を使うとき、ダイアログ(名前を付けて保存)を非表示にする。
options.add_argument("--disable-features=Translate")                                         # Chromeの翻訳を無効にする。右クリック・アドレスバーから翻訳の項目が消える。
# options.add_argument("--disable-popup-blocking")                                             # ポップアップブロックを無効にする。
# options.add_argument("--headless=new")                                                       # ヘッドレスモードで起動する。
options.add_argument("--hide-scrollbars")                                                    # スクロールバーを隠す。
options.add_argument("--ignore-certificate-errors")                                          # SSL認証(この接続ではプライバシーが保護されません)を無効
options.add_argument("--incognito")                                                          # シークレットモードで起動する。
options.add_argument("--mute-audio")                                                         # すべてのオーディオをミュートする。
options.add_argument("--no-default-browser-check")                                           # アドレスバー下に表示される「既定のブラウザとして設定」を無効にする。
options.add_argument("--propagate-iph-for-testing")                                          # Chromeに表示される青いヒント(？)を非表示にする。
options.add_argument("--start-maximized")                                                    # ウィンドウの初期サイズを最大化。--window-position, --window-sizeの2つとは併用不可
# options.add_argument("--test-type=gpu")                                                      # アドレスバー下に表示される「Chrome for Testing~~」を非表示にする。
# options.add_argument("--user-agent=" + UserAgent("windows").chrome)                          # ユーザーエージェントの指定。
# options.add_argument("--window-position=100,100")                                            # ウィンドウの初期位置を指定する。--start-maximizedとは併用不可
# options.add_argument("--window-size=1600,1024")                                              # ウィンドウの初期サイズを設定する。--start-maximizedとは併用不可
options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])  # Chromeは自動テスト ソフトウェア~~ ｜ コンソールに表示されるエラー を非表示
# options.set_capability("browserVersion", "117")                                              # `--headless=new`を使うとき、コンソールに表示されるエラーを非表示にするための必須オプション
prefs = {
    "credentials_enable_service": False,                                                     # パスワード保存のポップアップを無効
    "savefile.default_directory": download_dir,                                              # ダイアログ(名前を付けて保存)の初期ディレクトリを指定
    "download.default_directory": download_dir,                                              # ダウンロード先を指定
    "download_bubble.partial_view_enabled": False,                                           # ダウンロードが完了したときの通知(吹き出し/下部表示)を無効にする。
    "plugins.always_open_pdf_externally": True,                                              # Chromeの内部PDFビューアを使わない(＝URLにアクセスすると直接ダウンロードされる)
}
options.add_experimental_option("prefs", prefs)

# アクセスしたいページの最上層のURLを指定
def top_url():
    return "https://wikiwiki.jp/nijisanji/%E6%9C%88%E3%83%8E%E7%BE%8E%E5%85%8E/%E7%94%BB%E5%83%8F#isyou2D"

def no_url():
    return "wikiwiki.jp/nijisanji"

def top_url_filename():
    return sanitize_filename(top_url())

def init():
    print(unquote(top_url()))

def main():
    # ------ ChromeDriver の起動 ------
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(10)

    # ページにアクセス
    driver.get(top_url())

    # スクロールしてページ内の全ての画像を読み込む
    body = driver.find_element(By.TAG_NAME, 'body')
    body.send_keys(Keys.END)

    # ページのタイトルを表示
    print(top_url())
    print(driver.title)

    #download_img(driver,top_url())
    urls = all_url(driver,top_url())

    for url in urls:
        if no_url() in url:
            print(url)

    # ブラウザを閉じる
    driver.quit()

def all_url(driver,url):
    # URLを格納するリスト
    urls = set()

    # すべてのタグからリンクを含む要素を取得
    link_elements = driver.find_elements(By.XPATH, '//*[@href]')

    # 各要素からhref属性を取得し、セットに追加
    for link_element in link_elements:
        href = link_element.get_attribute('href')
        if not (".css" in href or ".js" in href):
            urls.add(href)

    # すべてのタグからリンクを含む要素を取得
    link_elements = driver.find_elements(By.XPATH, '//*[@src]')

    # 各要素からsrc属性を取得し、セットに追加
    for link_element in link_elements:
        src = link_element.get_attribute('src')
        if not (".css" in src or ".js" in src):
            urls.add(src)

    urls.discard(None)
    return urls


def download_img(driver,url):

    # 画像を格納するディレクトリを作成
    image_dir = os.path.join(top_url_filename(), sanitize_filename(url))
    os.makedirs(image_dir, exist_ok=True)

    # 画像の要素を取得
    img_elements = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.TAG_NAME, 'img'))
    )

    for index, img_element in enumerate(img_elements):
        img_url = img_element.get_attribute('src')
        img_url = urljoin(url, img_url)  # 相対URLを絶対URLに変換
        print(img_url)

        # 画像のダウンロード
        response = requests.get(img_url, stream=True)
        img_name = os.path.join(image_dir, f"image_{index+1}.png")

        try:
            with open(img_name, 'wb') as img_file:
                for chunk in response.iter_content(chunk_size=128):
                    img_file.write(chunk)

            # PILを使用して画像を開き、必要に応じて処理を行う
            with Image.open(img_name) as img:
                # 画像のリサイズ、回転、フィルタリングなどが可能
                # 例: img = img.resize((new_width, new_height), Image.ANTIALIAS)
                # 例: img = img.rotate(90)
                # 必要な処理を追加
                #img = img.convert("RGB")

                # 画像を保存（元の画像を上書き or 別の名前で保存）
                img.save(img_name)

        except Exception as e:
            print(f"Error downloading or processing image: {e}")
            continue

    return

def sanitize_filename(filename):
    filename_ja = unquote(filename)
    # 使用できない文字を正規表現で検索して削除
    invalid_chars = re.compile(r'[\\/:"*?<>|]')  # Windowsで使用できない文字
    sanitized_filename = re.sub(invalid_chars, '', filename_ja)

    return sanitized_filename if sanitized_filename else "unknown"



if __name__ == "__main__":
    init()
    main()
