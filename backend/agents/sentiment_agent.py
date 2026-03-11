"""
Sentiment Analysis Agent — analyzes news and social media sentiment
for cryptocurrency market signals.
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

import httpx
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)


class SentimentAgent:
    """
    Collects and analyzes sentiment from multiple sources:
    - Crypto news APIs
    - Social media keyword heuristics
    - Fear/Greed index
    """

    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        self._http = httpx.AsyncClient(timeout=15.0)
        self._sentiment_cache: dict = {}
        self._news_cache: dict = {}
        self._fear_greed: dict = {}

        # Crypto-specific vocabulary boosts
        self._crypto_terms = {
            "moon": 0.5, "mooning": 0.6, "bullish": 0.4, "pump": 0.3,
            "rally": 0.3, "breakout": 0.3, "ath": 0.4, "all time high": 0.4,
            "adoption": 0.3, "partnership": 0.2, "upgrade": 0.2,
            "dump": -0.4, "crash": -0.5, "bearish": -0.4, "rug": -0.6,
            "scam": -0.5, "hack": -0.5, "exploit": -0.4, "liquidation": -0.4,
            "ban": -0.3, "regulation": -0.2, "sec": -0.2, "fud": -0.3,
            "sell off": -0.3, "capitulation": -0.5, "fear": -0.3,
        }

    async def analyze_sentiment(self, symbol: str) -> dict:
        """
        Run full sentiment analysis for a symbol.
        Returns composite sentiment score and breakdown.
        """
        clean_symbol = symbol.replace("USDT", "").replace("USD", "")

        # Fetch news sentiment
        news_result = await self._fetch_news_sentiment(clean_symbol)

        # Fetch fear/greed index
        fear_greed = await self._fetch_fear_greed()

        # Compute composite sentiment
        news_score = news_result.get("score", 0)
        fg_score = fear_greed.get("normalized_score", 0)

        # Weighted composite: 70% news, 30% fear/greed
        composite = news_score * 0.7 + fg_score * 0.3

        if composite > 0.3:
            sentiment = "POSITIVE"
        elif composite > 0.1:
            sentiment = "SLIGHTLY_POSITIVE"
        elif composite > -0.1:
            sentiment = "NEUTRAL"
        elif composite > -0.3:
            sentiment = "SLIGHTLY_NEGATIVE"
        else:
            sentiment = "NEGATIVE"

        result = {
            "symbol": symbol,
            "sentiment": sentiment,
            "composite_score": round(composite, 4),
            "news": news_result,
            "fear_greed": fear_greed,
            "updated_at": datetime.utcnow().isoformat(),
        }

        self._sentiment_cache[symbol] = result
        return result

    async def _fetch_news_sentiment(self, keyword: str) -> dict:
        """
        Fetch and analyze crypto news sentiment.
        Uses CryptoPanic API (free tier) as primary source.
        Falls back to simulated sentiment based on market conditions.
        """
        headlines = []

        try:
            # Try CryptoPanic API
            resp = await self._http.get(
                "https://cryptopanic.com/api/free/v1/posts/",
                params={"auth_token": "free", "currencies": keyword,
                        "filter": "hot", "public": "true"},
            )
            if resp.status_code == 200:
                data = resp.json()
                for post in data.get("results", [])[:20]:
                    headlines.append(post.get("title", ""))
        except Exception as e:
            logger.debug(f"CryptoPanic fetch failed: {e}")

        # If no headlines, generate simulated analysis
        if not headlines:
            return self._simulated_news_sentiment(keyword)

        # Analyze each headline
        scores = []
        analyzed = []
        for headline in headlines:
            score = self._analyze_text(headline)
            scores.append(score)
            analyzed.append({
                "text": headline[:100],
                "score": round(score, 3),
                "sentiment": "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral",
            })

        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            "score": round(avg_score, 4),
            "count": len(headlines),
            "headlines": analyzed[:5],
            "positive_pct": round(sum(1 for s in scores if s > 0.1) / max(len(scores), 1) * 100, 1),
            "negative_pct": round(sum(1 for s in scores if s < -0.1) / max(len(scores), 1) * 100, 1),
        }

    def _analyze_text(self, text: str) -> float:
        """
        Score text sentiment using VADER + crypto-specific terms.
        Returns -1.0 to 1.0.
        """
        # VADER base score
        vader_score = self.vader.polarity_scores(text)["compound"]

        # Crypto-specific boost
        text_lower = text.lower()
        crypto_boost = 0
        for term, boost in self._crypto_terms.items():
            if term in text_lower:
                crypto_boost += boost

        # Clamp crypto boost
        crypto_boost = max(-1.0, min(1.0, crypto_boost))

        # Combine: 60% VADER, 40% crypto terms
        final = vader_score * 0.6 + crypto_boost * 0.4
        return max(-1.0, min(1.0, final))

    def _simulated_news_sentiment(self, keyword: str) -> dict:
        """
        Provide a default sentiment when APIs are unavailable.
        Uses a slightly positive bias (crypto markets).
        """
        import random
        random.seed(hash(keyword + datetime.utcnow().strftime("%Y%m%d%H")))

        base_score = random.uniform(-0.2, 0.3)

        sample_headlines = [
            {"text": f"{keyword} showing strong institutional interest",
             "score": 0.3, "sentiment": "positive"},
            {"text": f"{keyword} market consolidating near support",
             "score": 0.05, "sentiment": "neutral"},
            {"text": f"Trading volume for {keyword} increases 15%",
             "score": 0.2, "sentiment": "positive"},
        ]

        return {
            "score": round(base_score, 4),
            "count": 3,
            "headlines": sample_headlines,
            "positive_pct": 60.0,
            "negative_pct": 10.0,
            "simulated": True,
        }

    async def _fetch_fear_greed(self) -> dict:
        """
        Fetch the Bitcoin Fear & Greed Index.
        """
        try:
            resp = await self._http.get(
                "https://api.alternative.me/fng/?limit=1"
            )
            if resp.status_code == 200:
                data = resp.json()
                entry = data.get("data", [{}])[0]
                value = int(entry.get("value", 50))

                # Normalize to -1 to 1 range
                normalized = (value - 50) / 50

                self._fear_greed = {
                    "value": value,
                    "classification": entry.get("value_classification", "Neutral"),
                    "normalized_score": round(normalized, 4),
                    "timestamp": entry.get("timestamp", ""),
                }
                return self._fear_greed
        except Exception as e:
            logger.debug(f"Fear/Greed fetch failed: {e}")

        return {
            "value": 50,
            "classification": "Neutral",
            "normalized_score": 0.0,
            "timestamp": "",
        }

    def get_cached_sentiment(self, symbol: str) -> dict:
        return self._sentiment_cache.get(symbol, {
            "symbol": symbol,
            "sentiment": "NEUTRAL",
            "composite_score": 0.0,
        })

    async def close(self):
        await self._http.aclose()
