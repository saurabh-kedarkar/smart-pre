/**
 * SmartPre — Sentiment Display Manager
 * Updates the sentiment gauge, fear/greed index, and news feed
 */
class SentimentManager {
   constructor() {
      this.currentSentiment = null;
   }

   updateSentiment(data) {
      if (!data) return;
      this.currentSentiment = data;

      const sentiment = data.sentiment || data;

      // Gauge
      this._updateGauge(sentiment.score || sentiment.composite_score || 0);

      // Label
      const label = sentiment.label || sentiment.sentiment || 'NEUTRAL';
      const labelEl = document.getElementById('sentiment-label');
      if (labelEl) {
         labelEl.textContent = label.replace(/_/g, ' ');
      }

      // Fear & Greed
      const fg = sentiment.fear_greed || data.fear_greed || {};
      this._setText('fg-value', fg.value || 50);
      this._setText('fg-class', fg.classification || 'Neutral');

      const fgClassEl = document.getElementById('fg-class');
      if (fgClassEl) {
         fgClassEl.style.color = this._fgColor(fg.value || 50);
      }

      // News
      this._updateNews(sentiment.news || data.news || {});
   }

   _updateGauge(score) {
      // Score ranges from -1 to 1, normalize to 0-100
      const normalized = ((score + 1) / 2) * 100;

      const scoreEl = document.getElementById('sentiment-score');
      if (scoreEl) scoreEl.textContent = Math.round(normalized);

      // Update SVG arc
      const arc = document.getElementById('sentiment-arc');
      if (arc) {
         const circumference = 326.7;
         const offset = circumference - (circumference * (normalized / 100));
         arc.style.strokeDashoffset = offset;
      }
   }

   _updateNews(news) {
      const newsList = document.getElementById('news-list');
      if (!newsList) return;

      const headlines = news.headlines || [];
      if (headlines.length === 0) {
         newsList.innerHTML = '<div class="news-item neutral">No recent headlines</div>';
         return;
      }

      newsList.innerHTML = headlines.map(h => {
         const sentiment = h.sentiment || 'neutral';
         const score = h.score || 0;
         const scoreColor = score > 0.1 ? 'var(--color-bullish)' :
            score < -0.1 ? 'var(--color-bearish)' : 'var(--text-muted)';

         return `<div class="news-item ${sentiment}">
                ${h.text}
                <span class="news-score" style="color: ${scoreColor}">${score > 0 ? '+' : ''}${score.toFixed(2)}</span>
            </div>`;
      }).join('');
   }

   _fgColor(value) {
      if (value <= 25) return 'var(--color-bearish)';
      if (value <= 45) return 'var(--color-warning)';
      if (value <= 55) return 'var(--text-muted)';
      if (value <= 75) return 'var(--color-bullish)';
      return '#22c55e';
   }

   _setText(id, text) {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
   }
}

window.sentimentManager = new SentimentManager();
