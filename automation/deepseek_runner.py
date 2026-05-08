from pathlib import Path


DEEPSEEK_CHAT_URL = "https://chat.deepseek.com/"
AUTOMATION_DIR = Path(__file__).resolve().parent
DEEPSEEK_BROWSER_DATA_DIR = AUTOMATION_DIR / "browser_data" / "deepseek"


def ensure_deepseek_browser_data_dir():
    DEEPSEEK_BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DEEPSEEK_BROWSER_DATA_DIR


def open_deepseek_with_persistent_context():
    user_data_dir = ensure_deepseek_browser_data_dir()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(DEEPSEEK_CHAT_URL, wait_until="domcontentloaded")

        print("DeepSeek 页面已打开。首次使用请在浏览器中手动登录。")
        print(f"登录态目录：{user_data_dir}")
        input("完成登录或查看后，按 Enter 关闭浏览器...")
        context.close()


if __name__ == "__main__":
    open_deepseek_with_persistent_context()
