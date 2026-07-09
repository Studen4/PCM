import uvicorn
from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright
import asyncio
import os
import sys
from contextlib import asynccontextmanager

app = FastAPI(title="E-Katalog Session Daemon")

# Глобальні змінні
_playwright = None
_browser = None
_page = None
_browser_lock = asyncio.Lock()  # Замок для запобігання Race Condition

SESSION_FILE = "../test_data/ekatalog_session.json"


async def init_browser():
    global _playwright, _browser, _page
    print("[DAEMON] Запуск фонового асинхронного браузера Playwright...")
    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(headless=False, channel="chrome")

    context_args = {
        "user_agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        "locale": 'uk-UA',
        "viewport": {'width': 1280, 'height': 800}
    }
    if os.path.exists(SESSION_FILE):
        context_args["storage_state"] = SESSION_FILE

    context = await _browser.new_context(**context_args)
    _page = await context.new_page()

    print("[DAEMON] Переходжу на ek.ua...")
    await _page.goto("https://ek.ua/ua/", wait_until="domcontentloaded")
    print("[DAEMON] Браузер готовий. Очікую запитів від Streamlit...")


async def close_browser():
    global _playwright, _browser, _page
    print("[DAEMON] Збереження сесії та закриття ресурси...")
    try:
        if _page:
            await _page.context.storage_state(path=SESSION_FILE)
        if _browser:
            await _browser.close()
        if _playwright:
            await _playwright.stop()
        print("[DAEMON] Ресурси Playwright успішно очищено.")
    except Exception as e:
        print(f"[DAEMON ERROR] Помилка при закритті браузера: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_browser()
    yield
    await close_browser()


app = FastAPI(title="E-Katalog Session Daemon", lifespan=lifespan)


@app.get("/")
async def root_check():
    return {"status": "alive"}


@app.get("/get")
async def get_page_content(url: str):
    global _page
    if not _page:
        raise HTTPException(status_code=500, detail="Браузер не ініціалізовано")

    # Вишиковуємо паралельні потоки Streamlit в чергу
    async with _browser_lock:
        try:
            await _page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(0.4)  # Пауза для відпрацювання JS-скриптів ціни

            # Зберігаємо куки
            await _page.context.storage_state(path=SESSION_FILE)
            html_content = await _page.content()
            return {"status": "ok", "html": html_content}
        except Exception as e:
            print(f"[DAEMON ERROR] Не вдалося завантажити {url}: {e}")
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print("==================================================")
    print(" Запуск E-Katalog Session Daemon (Safe Lock Mode)")
    print("==================================================")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
