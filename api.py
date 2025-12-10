# api.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from scraper import analyze_news_article  # <-- your real logic is imported from scraper.py

app = FastAPI()

@app.get("/scrape")
def scrape(url: str):
    """
    Usage:
    GET /scrape?url=https://www.manoramaonline.com/...
    """
    try:
        data = analyze_news_article(url)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
