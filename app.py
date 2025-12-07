import sys
import asyncio

import streamlit as st
from playwright.sync_api import Error as PlaywrightError, sync_playwright


if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except RuntimeError:
        pass


def _ensure_scheme(value: str) -> str:
    """Add a default scheme when the provided URL is missing one."""
    trimmed = value.strip()
    if trimmed and not trimmed.startswith(("http://", "https://")):
        return f"https://{trimmed}"
    return trimmed


def fetch_title_from_url(url: str, timeout: int = 30_000) -> str:
    """Use Playwright to open the page and return the fully loaded title."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            page.wait_for_selector("title", timeout=timeout)
            return page.title()
        finally:
            browser.close()


st.set_page_config(page_title="Playwright Title Reader", layout="centered")
st.title("Ambil Title dari URL dengan Playwright")

url_input = st.text_input("Masukkan URL yang ingin diambil judulnya", value="")

if st.button("Dapatkan Title"):
    normalized_url = _ensure_scheme(url_input)
    if not normalized_url:
        st.error("Silakan masukkan URL terlebih dahulu.")
    else:
        with st.spinner("Memuat dan membaca title..."):
            try:
                title = fetch_title_from_url(normalized_url)
                st.success("Title ditemukan:")
                st.code(title)
            except PlaywrightError as exc:
                st.error(f"Gagal mengambil title: {exc}")
