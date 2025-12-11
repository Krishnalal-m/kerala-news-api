# scraper.py
# Cleaned version for Cloud Run API
# Contains ONLY extraction + translation + date logic

import tldextract
import nltk
import re
import requests
from bs4 import BeautifulSoup
from newspaper import Article, Config
from htmldate import find_date
from datetime import datetime
from deep_translator import GoogleTranslator

# -------------------------------------------------------------
# SETUP
# -------------------------------------------------------------

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

MEDIA_MAP = {
    "manoramaonline": "Malayala Manorama",
    "onmanorama": "Onmanorama",
    "mathrubhumi": "Mathrubhumi News",
    "asianetnews": "Asianet News",
    "keralakaumudi": "Kerala Kaumudi",
    "janmabhumi": "Janmabhumi",
    "deshabhimani": "Deshabhimani",
    "news18": "News18 Malayalam",
    "thehindu": "The Hindu",
    "timesofindia": "Times of India",
    "indiatoday": "India Today"
}

MALAYALAM_MONTHS = {
    "ജനുവരി": "January", "ഫെബ്രുവരി": "February", "മാർച്ച്": "March",
    "ഏപ്രിൽ": "April", "മേയ്": "May", "ജൂൺ": "June",
    "ജൂലൈ": "July", "ആഗസ്റ്റ്": "August", "സെപ്റ്റംബർ": "September",
    "ഒക്ടോബർ": "October", "നവംബർ": "November", "ഡിസംബർ": "December",
    "ഡിസം": "December"
}

# -------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------

def translate_text_if_needed(text: str) -> str:
    if text and re.search(r"[\u0D00-\u0D7F]", text):
        try:
            return GoogleTranslator(source="auto", target="en").translate(text)
        except:
            return text
    return text


def extract_malayalam_date(text: str):
    """Convert Malayalam date like '7 ഡിസംബർ 2024' → YYYY-MM-DD"""
    for ml, eng in MALAYALAM_MONTHS.items():
        if ml in text:
            fixed = text.replace(ml, eng)
            for fmt in ("%d %B %Y", "%d-%B-%Y", "%d %B, %Y"):
                try:
                    return datetime.strptime(fixed, fmt).strftime("%Y-%m-%d")
                except:
                    pass
    return None


def extract_malayalam_text(soup: BeautifulSoup) -> str:
    """Extract ONLY Malayalam text from <p> tags"""
    mal = []
    for p in soup.find_all("p"):
        text = p.get_text(" ", strip=True)
        if re.search(r"[\u0D00-\u0D7F]", text):
            clean = re.sub(r"[^ \u0D00-\u0D7F]+", " ", text)
            mal.append(clean.strip())
    return " ".join(mal) if mal else ""


# -------------------------------------------------------------
# MAIN SCRAPER FUNCTION
# -------------------------------------------------------------

def analyze_news_article(url: str) -> dict:
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        html = requests.get(url, headers=headers, timeout=10).text
    except:
        html = ""

    soup = BeautifulSoup(html, "lxml")

    # Media source name
    extracted = tldextract.extract(url)
    domain = extracted.domain.lower()
    media_source = MEDIA_MAP.get(domain, domain.capitalize())

    # ---------------------------------------------------------
    # TITLE
    # ---------------------------------------------------------
    title = "No Title Found"
    article = None

    try:
        config = Config()
        config.browser_user_agent = headers["User-Agent"]
        config.request_timeout = 10

        article = Article(url, config=config)
        article.download()
        article.parse()

        if article.title:
            title = article.title.strip()
    except:
        if soup.title:
            title = soup.title.text.strip()

    title = translate_text_if_needed(title)

    # ---------------------------------------------------------
    # SUMMARY (Malayalam → English)
    # ---------------------------------------------------------
    mal_text = extract_malayalam_text(soup)
    summary = translate_text_if_needed(mal_text) if mal_text else "No readable Malayalam content found."

    # ---------------------------------------------------------
    # DATE EXTRACTION (Tiered system)
    # ---------------------------------------------------------
    pub_date_str = None

    # Method A: htmldate
    try:
        found = find_date(url)
        if found:
            pub_date_str = found
    except:
        pass

    # Method B: Malayalam inside HTML
    if not pub_date_str:
        parsed = extract_malayalam_date(soup.text)
        if parsed:
            pub_date_str = parsed

    # Method C: newspaper3k metadata
    try:
        if not pub_date_str and article and article.publish_date:
            pub_date_str = article.publish_date.strftime("%Y-%m-%d")
    except:
        pass

    # Method D: Regex inside URL
    match = re.search(r"/(\d{4})[/-](\d{2})[/-](\d{2})", url)
    if not pub_date_str and match:
        pub_date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    if not pub_date_str:
        pub_date_str = "Date Not Found"

    # ---------------------------------------------------------
    # RETURN CLEAN JSON
    # ---------------------------------------------------------
    return {
        "url": url,
        "media_source": media_source,
        "date": pub_date_str,
        "title": title,
        "summary": summary
    }


# for quick testing
if __name__ == "__main__":
    test = "https://www.keralakaumudi.com/news/..."
    print(analyze_news_article(test))
