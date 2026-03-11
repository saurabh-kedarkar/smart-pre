/**
 * SmartPre — Signal Display Manager
 * Updates the signal, decision, prediction, and risk panels
 */
class SignalManager {
   constructor() {
      this.currentDecision = null;
   }

   updateDecision(data) {
      if (!data) return;
      this.currentDecision = data;

      // Decision card
      const action = data.action || 'HOLD';
      const confidence = data.confidence_pct || 50;

      const actionEl = document.getElementById('decision-action');
      if (actionEl) {
         actionEl.textContent = action;
         actionEl.className = 'decision-action';
         if (action === 'BUY' || action === 'WEAK_BUY') actionEl.classList.add('buy');
         else if (action === 'SELL' || action === 'WEAK_SELL') actionEl.classList.add('sell');
         else actionEl.classList.add('hold');
      }

      // Confidence meter
      const confFill = document.getElementById('confidence-fill');
      const confValue = document.getElementById('confidence-value');
      if (confFill) confFill.style.width = `${confidence}%`;
      if (confValue) confValue.textContent = `${confidence.toFixed(1)}%`;

      // Decision time
      const timeEl = document.getElementById('decision-time');
      if (timeEl && data.timestamp) {
         const d = new Date(data.timestamp);
         timeEl.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }

      // Signal card
      this._updateSignalCard(data.signal || {});

      // Risk card
      this._updateRiskCard(data.risk || {});

      // Prediction
      this._updatePrediction(data.prediction || {});

      // Technical
      this._updateTechnical(data.technical || {}, data);

      // Agreement
      this._updateAgreement(data);
   }

   _updateSignalCard(signal) {
      const type = signal.type || 'HOLD';

      const badge = document.getElementById('signal-badge');
      if (badge) {
         badge.textContent = type;
         badge.className = 'signal-badge';
         if (type.includes('BUY')) badge.classList.add('buy');
         else if (type.includes('SELL')) badge.classList.add('sell');
         else badge.classList.add('hold');
      }

      this._setText('sig-entry', this._formatPrice(signal.entry));
      this._setText('sig-target1', this._formatPrice(signal.target_1));
      this._setText('sig-target2', this._formatPrice(signal.target_2));
      this._setText('sig-target3', this._formatPrice(signal.target_3));
      this._setText('sig-stoploss', this._formatPrice(signal.stop_loss));
      this._setText('sig-rr', signal.risk_reward ? `${signal.risk_reward.toFixed(1)}:1` : '--');
   }

   _updateRiskCard(risk) {
      const badge = document.getElementById('risk-badge');
      if (badge) {
         const level = (risk.level || 'UNKNOWN').toLowerCase();
         badge.textContent = risk.level || '--';
         badge.className = 'risk-badge';
         if (level === 'low') badge.classList.add('low');
         else if (level === 'medium') badge.classList.add('medium');
         else badge.classList.add('high');
      }

      this._setText('sig-risk', risk.level || '--');
      this._setText('risk-position', `$${(risk.position_value || 0).toFixed(2)}`);
      this._setText('risk-maxloss', `$${(risk.max_loss || 0).toFixed(2)}`);
      this._setText('risk-gain', `$${(risk.potential_gain || 0).toFixed(2)}`);
      this._setText('risk-pct', `${(risk.risk_pct || 0).toFixed(2)}%`);

      // Warnings
      const warningsEl = document.getElementById('risk-warnings');
      if (warningsEl && risk.warnings) {
         warningsEl.innerHTML = risk.warnings.map(w =>
            `<div class="risk-warning">${w}</div>`
         ).join('');
      }

      // Recommendation
      const recEl = document.getElementById('risk-recommendation');
      if (recEl) {
         const shouldTrade = risk.should_trade;
         recEl.innerHTML = `<span style="color: ${shouldTrade ? 'var(--color-bullish)' : 'var(--color-warning)'}">
                ${shouldTrade ? '✅' : '⏸️'} ${risk.recommendation || 'No recommendation'}
            </span>`;
      }
   }

   _updatePrediction(pred) {
      const direction = pred.direction || 'NEUTRAL';
      const confidence = pred.confidence ? (pred.confidence * 100).toFixed(1) : '50.0';

      // Main prediction
      const arrow = document.getElementById('pred-arrow');
      const label = document.getElementById('pred-label');
      const conf = document.getElementById('pred-conf');

      if (arrow) {
         arrow.textContent = direction === 'BULLISH' ? '↑' : direction === 'BEARISH' ? '↓' : '→';
         arrow.className = 'pred-arrow';
         if (direction === 'BULLISH') arrow.classList.add('up');
         else if (direction === 'BEARISH') arrow.classList.add('down');
      }

      if (label) {
         label.textContent = direction;
         label.className = 'pred-label';
         label.classList.add(direction.toLowerCase());
      }

      if (conf) conf.textContent = `${confidence}%`;

      // Timeframes
      const pred5m = pred.next_5m || {};
      const pred15m = pred.next_15m || {};

      this._setText('pred-5m', pred5m.direction || '--');
      this._setText('pred-5m-prob', `${(pred5m.probability || 50).toFixed(0)}%`);
      this._setText('pred-15m', pred15m.direction || '--');
      this._setText('pred-15m-prob', `${(pred15m.probability || 50).toFixed(0)}%`);
      this._setText('pred-breakout', pred.breakout_probability ?
         (pred.breakout_probability > 0.5 ? 'Likely' : 'Unlikely') : '--');
      this._setText('pred-breakout-prob',
         `${((pred.breakout_probability || 0.1) * 100).toFixed(0)}%`);

      // Model tags
      const models = pred.models || {};
      if (models.lstm) {
         this._setText('model-lstm',
            `LSTM: ${models.lstm.direction} ${((models.lstm.confidence || 0.5) * 100).toFixed(0)}%`);
      }
      if (models.transformer) {
         this._setText('model-transformer',
            `Transformer: ${models.transformer.direction} ${((models.transformer.confidence || 0.5) * 100).toFixed(0)}%`);
      }
   }

   _updateTechnical(tech, fullData) {
      const signal = tech.signal || 'NEUTRAL';

      const taSignal = document.getElementById('ta-signal');
      if (taSignal) {
         taSignal.textContent = signal;
         taSignal.className = 'ta-signal';
         if (signal.includes('BULL')) taSignal.classList.add('bullish');
         else if (signal.includes('BEAR')) taSignal.classList.add('bearish');
         else taSignal.classList.add('neutral');
      }

      // Market structure
      const ms = tech.market_structure || {};
      this._setText('ms-type', ms.type || '--');
      this._setText('ms-trend', ms.trend || '--');

      // Indicators (from the full analysis)
      this._updateIndicators(fullData);
   }

   _updateIndicators(data) {
      // Get indicator data from breakdown if available
      const breakdown = data?.signal?.breakdown || {};
      const techStrength = data?.technical?.strength || 0;

      // RSI
      const rsi = data?._indicators?.rsi;
      if (rsi) {
         this._setText('rsi-value', rsi.value?.toFixed(1) || '50');
         this._setBar('rsi-bar', rsi.value || 50, 100);
         this._setIndSignal('rsi-signal', rsi.signal);
      }

      // MACD
      const macd = data?._indicators?.macd;
      if (macd) {
         this._setText('macd-value', macd.histogram?.toFixed(4) || '0.00');
         this._setBar('macd-bar', 50 + (macd.strength || 0) * 50, 100);
         this._setIndSignal('macd-signal', macd.signal);
      }

      // If no detailed indicators, use composite
      if (!data?._indicators) {
         const str = techStrength || 0;
         const pct = 50 + str * 50;
         ['rsi-bar', 'macd-bar', 'bb-bar', 'ma-bar', 'vwap-bar', 'vol-bar'].forEach(id => {
            this._setBar(id, Math.max(10, Math.min(90, pct + (Math.random() - 0.5) * 20)), 100);
         });
      }
   }

   _updateAgreement(data) {
      const agreement = data.agreement || {};
      const bullish = agreement.bullish_count || 0;
      const bearish = agreement.bearish_count || 0;
      const pct = agreement.agreement_pct || 0;

      const isBullish = bullish >= bearish;
      const direction = isBullish ? 'bullish' : 'bearish';

      // Individual bars
      const techSig = data.technical?.signal || 'NEUTRAL';
      const predDir = data.prediction?.direction || 'NEUTRAL';
      const sentLabel = data.sentiment?.label || 'NEUTRAL';
      const sigType = data.signal?.type || 'HOLD';

      this._setAgreementBar('agree-tech', 'agree-tech-val', techSig);
      this._setAgreementBar('agree-ml', 'agree-ml-val', predDir);
      this._setAgreementBar('agree-sent', 'agree-sent-val', sentLabel);
      this._setAgreementBar('agree-sig', 'agree-sig-val', sigType);

      // Summary
      this._setText('agreement-pct', `${pct.toFixed(0)}%`);
   }

   _setAgreementBar(barId, valId, signal) {
      const bar = document.getElementById(barId);
      const val = document.getElementById(valId);

      let width = 50;
      let className = '';
      let label = signal;

      if (signal.includes('BULL') || signal.includes('BUY') || signal.includes('POSITIVE')) {
         width = 75;
         className = 'bullish';
      } else if (signal.includes('BEAR') || signal.includes('SELL') || signal.includes('NEGATIVE')) {
         width = 25;
         className = 'bearish';
      }

      if (bar) {
         bar.style.width = `${width}%`;
         bar.className = 'agree-fill';
         if (className) bar.classList.add(className);
      }
      if (val) val.textContent = label;
   }

   _setBar(id, value, max) {
      const el = document.getElementById(id);
      if (el) {
         const pct = Math.max(0, Math.min(100, (value / max) * 100));
         el.style.width = `${pct}%`;
         el.className = 'ind-bar-fill';
         if (pct > 60) el.classList.add('bullish');
         else if (pct < 40) el.classList.add('bearish');
         else el.classList.add('neutral');
      }
   }

   _setIndSignal(id, signal) {
      const el = document.getElementById(id);
      if (el && signal) {
         el.textContent = signal;
         el.className = 'ind-signal';
         if (signal.includes('BUY') || signal.includes('BULL')) el.classList.add('bullish');
         else if (signal.includes('SELL') || signal.includes('BEAR')) el.classList.add('bearish');
         else el.classList.add('neutral');
      }
   }

   _setText(id, text) {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
   }

   _formatPrice(price) {
      if (!price) return '$0.00';
      if (price >= 1000) return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      if (price >= 1) return `$${price.toFixed(2)}`;
      return `$${price.toFixed(6)}`;
   }
}

window.signalManager = new SignalManager();
