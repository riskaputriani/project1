import sys
import asyncio
import platform
import os
import subprocess
import socket
import stat
import shutil
import urllib.request
from pathlib import Path
from typing import Optional

import streamlit as st
from playwright.sync_api import Error as PlaywrightError, sync_playwright


if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except RuntimeError:
        pass


LIGHTPANDA_RELEASE_URL = (
    "https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-x86_64-linux"
)
LIGHTPANDA_PORT = 9222
LIGHTPANDA_CDP_ENDPOINT = f"ws://127.0.0.1:{LIGHTPANDA_PORT}"
LIGHTPANDA_BINARY_PATH = Path("lightpanda")


def _download_lightpanda(target: Path) -> None:
    """Download the LightPanda binary and make sure it is executable."""
    temp_path = target.with_suffix(".download")
    try:
        with urllib.request.urlopen(LIGHTPANDA_RELEASE_URL, timeout=30) as response, temp_path.open(
            "wb"
        ) as temp_file:
            shutil.copyfileobj(response, temp_file)
        temp_path.replace(target)
        try:
            target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except PermissionError:
            pass
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Gagal mengunduh LightPanda: {exc}") from exc


def _ensure_lightpanda_binary() -> Path:
    if LIGHTPANDA_BINARY_PATH.exists():
        return LIGHTPANDA_BINARY_PATH
    _download_lightpanda(LIGHTPANDA_BINARY_PATH)
    if not LIGHTPANDA_BINARY_PATH.exists():
        raise RuntimeError("LightPanda tidak ditemukan setelah unduhan.")
    return LIGHTPANDA_BINARY_PATH


def _is_lightpanda_listening() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", LIGHTPANDA_PORT), timeout=1):
            return True
    except OSError:
        return False


@st.experimental_singleton
def _start_lightpanda_instance() -> Optional[subprocess.Popen]:
    """Download and launch LightPanda once per Streamlit session."""
    if _is_lightpanda_listening():
        return None
    binary = _ensure_lightpanda_binary()
    try:
        return subprocess.Popen(
            [str(binary), "serve", "--host", "127.0.0.1", "--port", str(LIGHTPANDA_PORT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise RuntimeError(
            "LightPanda gagal dijalankan. Pastikan binari dapat dieksekusi di sistem Anda."
        ) from exc


def _ensure_scheme(value: str) -> str:
    """Add a default scheme when the provided URL is missing one."""
    trimmed = value.strip()
    if trimmed and not trimmed.startswith(("http://", "https://")):
        return f"https://{trimmed}"
    return trimmed


def fetch_title_from_url(url: str, timeout: int = 30_000) -> str:
    """Use Playwright over CDP to open the page and return the fully loaded title."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(LIGHTPANDA_CDP_ENDPOINT)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            page.wait_for_selector("title", timeout=timeout)
            return page.title()
        finally:
            browser.close()


def _system_info_text() -> str:
    """Return a text summary similar to the provided console script."""
    parts = [
        "\n=== SYSTEM INFO ===",
        f"OS          : {platform.system()} {platform.release()}",
        f"Kernel      : {platform.version()}",
        f"Machine     : {platform.machine()}",
        f"Platform    : {platform.platform()}",
        "",
        "=== PYTHON INFO ===",
        f"Python      : {sys.version.replace('\\n', ' ')}",
        f"Build       : {platform.python_build()}",
        f"Compiler    : {platform.python_compiler()}",
        "",
        "=== ENVIRONMENT ===",
        f"os.name     : {os.name}",
        f"USER        : {os.environ.get('USER')}",
        f"HOME        : {os.environ.get('HOME')}",
        "",
        "=== SPECIAL CHECKS ===",
        f"Docker?     : {os.path.exists('/.dockerenv')}",
        f"WSL?        : {'microsoft' in platform.release().lower()}",
        f"Alpine?     : {'alpine' in platform.platform().lower()}",
    ]
    return "\n".join(parts)


st.set_page_config(page_title="Playwright Title Reader", layout="centered")
st.title("Ambil Title dari URL dengan Playwright")
st.caption("Tekan tombol agar Playwright membuka URL lewat LightPanda dan membaca judul.")

st.subheader("Info Sistem")
st.code(_system_info_text(), language="text")
st.markdown("---")

lightpanda_error: Optional[str] = None
try:
    _start_lightpanda_instance()
except RuntimeError as exc:
    lightpanda_error = str(exc)

lightpanda_ready = _is_lightpanda_listening()

st.subheader("LightPanda Browser")
if lightpanda_error:
    st.error(f"LightPanda gagal diinisialisasi: {lightpanda_error}")
elif lightpanda_ready:
    st.success(f"LightPanda siap di {LIGHTPANDA_CDP_ENDPOINT}")
else:
    st.info("LightPanda sedang dijalankan. Tunggu beberapa saat dan klik tombol lagi.")
st.caption(f"CDP endpoint: {LIGHTPANDA_CDP_ENDPOINT}")
st.markdown("---")

url_input = st.text_input("Masukkan URL yang ingin diambil judulnya", value="")

if st.button("Dapatkan Title"):
    normalized_url = _ensure_scheme(url_input)
    if not normalized_url:
        st.error("Silakan masukkan URL terlebih dahulu.")
    elif not _is_lightpanda_listening():
        st.error("LightPanda belum siap, silakan tunggu beberapa detik dan coba lagi.")
    else:
        with st.spinner("Memuat dan membaca title..."):
            try:
                title = fetch_title_from_url(normalized_url)
                st.success("Title ditemukan:")
                st.code(title)
            except PlaywrightError as exc:
                st.error(f"Gagal mengambil title: {exc}")
