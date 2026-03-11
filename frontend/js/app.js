/**
 * SmartPre — Main Application Controller
 * Orchestrates all modules and manages state
 */
(function () {
   'use strict';

    // ─── API Config ─────────────────────────────────
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    // Change this to your Render backend URL (e.g., 'https://your-app.onrender.com')
    const API_BASE_URL = isLocal ? '' : 'https://smart-pre-backend.onrender.com';

    // ─── State ──────────────────────────────────────
   const state = {
      activeSymbol: 'BTCUSDT',
      symbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'],
      prices: {},
      decisions: {},
      chartData: {},
      currentCandles: {}, // symbol -> {time, open, high, low, close, volume}
   };

   const SYMBOL_NAMES = {
      'BTCUSDT': 'BTC',
      'ETHUSDT': 'ETH',
      'SOLUSDT': 'SOL',
      'BNBUSDT': 'BNB',
      'XRPUSDT': 'XRP',
   };

   const SYMBOL_COLORS = {
      'BTC': '#f7931a',
      'ETH': '#627eea',
      'SOL': '#9945ff',
      'BNB': '#f0b90b',
      'XRP': '#00aae4',
   };

   // ─── Initialization ─────────────────────────────
   document.addEventListener('DOMContentLoaded', init);

   function init() {
      console.log('🚀 SmartPre Dashboard initializing...');

      // Build symbol tabs
      buildSymbolTabs();

      // Initialize chart
      window.chartManager = new ChartManager('chart-container');

      // Setup WebSocket listeners
      setupWebSocket();

      // Setup timeframe buttons
      setupTimeframeButtons();

      // Start clock
      startClock();

      // Initial data fetch via REST (fallback)
      fetchInitialData();
   }

   // ─── Symbol Tabs ────────────────────────────────
   function buildSymbolTabs() {
      const tabsEl = document.getElementById('symbol-tabs');
      if (!tabsEl) return;

      tabsEl.innerHTML = state.symbols.map(symbol => {
         const name = SYMBOL_NAMES[symbol] || symbol;
         const isActive = symbol === state.activeSymbol;
         return `<button class="sym-tab ${isActive ? 'active' : ''}" 
                            data-symbol="${symbol}" id="tab-${symbol}">
                        ${name}
                    </button>`;
      }).join('');

      tabsEl.addEventListener('click', (e) => {
         const btn = e.target.closest('.sym-tab');
         if (!btn) return;
         const symbol = btn.dataset.symbol;
         switchSymbol(symbol);
      });
   }

   function switchSymbol(symbol) {
      state.activeSymbol = symbol;

      // Update tab styles
      document.querySelectorAll('.sym-tab').forEach(tab => {
         tab.classList.toggle('active', tab.dataset.symbol === symbol);
      });

      // Update chart header
      const name = SYMBOL_NAMES[symbol] || symbol;
      document.getElementById('chart-symbol').textContent = `${name}/USDT`;

      // Update price
      updatePriceDisplay(symbol);

      // Update panels with cached data
      if (state.decisions[symbol]) {
         window.signalManager.updateDecision(state.decisions[symbol]);
      }

      // Update market table active row
      document.querySelectorAll('#market-tbody tr').forEach(row => {
         row.classList.toggle('active', row.dataset.symbol === symbol);
      });

      // Request fresh analysis
      if (window.smartWS && window.smartWS.isConnected) {
         window.smartWS.requestAnalysis(symbol);
      }

      // Load chart data
      loadChartData(symbol);
   }

   // ─── WebSocket Setup ────────────────────────────
   function setupWebSocket() {
      const ws = window.smartWS;

      ws.on('connected', () => {
         console.log('✅ Connected to SmartPre backend');
      });

      ws.on('initialData', (data) => {
         console.log('📦 Received initial data');

         if (data.prices) {
            state.prices = data.prices;
            updatePriceDisplay(state.activeSymbol);
         }

         if (data.symbols) {
            state.symbols = data.symbols;
         }

         if (data.decisions) {
            state.decisions = data.decisions;
            updateAllPanels();
         }
      });

      ws.on('analysisUpdate', (data) => {
         console.log('📊 Analysis update received');

         // Update all decisions
         for (const [symbol, decision] of Object.entries(data)) {
            state.decisions[symbol] = decision;
            if (decision.price) state.prices[symbol] = decision.price;
         }

         updateAllPanels();
      });

      ws.on('analysisResult', (data) => {
         for (const [symbol, decision] of Object.entries(data)) {
            state.decisions[symbol] = decision;
            if (decision.price) state.prices[symbol] = decision.price;
         }
         updateAllPanels();
      });

      ws.on('priceUpdate', (data) => {
         for (const [symbol, price] of Object.entries(data)) {
            const oldPrice = state.prices[symbol] || 0;
            if (price !== oldPrice) {
               state.prices[symbol] = price;
               if (symbol === state.activeSymbol) {
                  updatePriceDisplay(symbol, oldPrice);
                  updateActiveChartPrice(symbol, price);
               }
               updateMarketRowPrice(symbol, price, oldPrice);
            }
         }
      });

      // Connect
      ws.connect();
   }

   // ─── Data Fetching (REST fallback) ──────────────
   async function fetchInitialData() {
      try {
         // Fetch prices
         const priceResp = await fetch(`${API_BASE_URL}/api/prices`);
         if (priceResp.ok) {
            state.prices = await priceResp.json();
            updatePriceDisplay(state.activeSymbol);
         }
      } catch (e) {
         console.log('REST fallback: prices unavailable, waiting for WebSocket');
      }

      try {
         // Fetch all decisions
         const decResp = await fetch(`${API_BASE_URL}/api/decisions`);
         if (decResp.ok) {
            const decisions = await decResp.json();
            if (Object.keys(decisions).length > 0) {
               state.decisions = decisions;
               updateAllPanels();
            }
         }
      } catch (e) {
         console.log('REST fallback: decisions unavailable');
      }

      // Fetch chart data
      loadChartData(state.activeSymbol);
   }

   async function loadChartData(symbol) {
      try {
         const resp = await fetch(`${API_BASE_URL}/api/market/${symbol}`);
         if (!resp.ok) return;
         const data = await resp.json();
         if (data.price) {
            state.prices[symbol] = data.price;
            updatePriceDisplay(symbol);
         }
      } catch (e) {
         // Chart data will come via WebSocket
      }

      // Generate simulated candles for display if backend not available
      if (window.chartManager) {
         const price = state.prices[symbol] || 60000;
         const candles = generateSimulatedCandles(price, 200);
         state.chartData[symbol] = candles;
         state.currentCandles[symbol] = { ...candles[candles.length - 1] };
         window.chartManager.updateCandles(candles);
      }
   }

   function updateActiveChartPrice(symbol, price) {
      if (!window.chartManager || !state.currentCandles[symbol]) return;

      const candle = state.currentCandles[symbol];
      const now = Math.floor(Date.now() / 1000);
      const timeframeMinutes = getTimeframeMinutes(window.chartManager.currentTimeframe);
      const candleTime = Math.floor(now / (timeframeMinutes * 60)) * (timeframeMinutes * 60);

      // If it's a new candle
      if (candleTime > candle.time) {
         candle.time = candleTime;
         candle.open = price;
         candle.high = price;
         candle.low = price;
         candle.close = price;
         candle.volume = Math.random() * 10 + 2; // Simulated increment
      } else {
         // Update existing candle
         candle.close = price;
         candle.high = Math.max(candle.high, price);
         candle.low = Math.min(candle.low, price);
         candle.volume += Math.random() * 0.5; // Simulated increment
      }

      window.chartManager.addCandle(candle);
   }

   function getTimeframeMinutes(tf) {
      if (tf === '1m') return 1;
      if (tf === '5m') return 5;
      if (tf === '15m') return 15;
      if (tf === '1h') return 60;
      return 1;
   }

   function generateSimulatedCandles(basePrice, count) {
      const candles = [];
      let price = basePrice;
      const now = Math.floor(Date.now() / 1000);
      const startTime = Math.floor(now / 60) * 60;

      for (let i = 0; i <= count; i++) {
         const time = startTime - (i * 60);
         const change = (Math.random() - 0.5) * price * 0.002;
         const close = price;
         const open = price - change;
         const high = Math.max(open, close) + Math.random() * price * 0.001;
         const low = Math.min(open, close) - Math.random() * price * 0.001;
         const volume = Math.random() * 80 + 20;

         candles.unshift({ time, open, high, low, close, volume });
         price = open;
      }
      return candles;
   }

   // ─── UI Updates ─────────────────────────────────
   function updateAllPanels() {
      const symbol = state.activeSymbol;
      const decision = state.decisions[symbol];

      if (decision) {
         window.signalManager.updateDecision(decision);

         // Update sentiment
         if (decision.sentiment) {
            window.sentimentManager.updateSentiment(decision.sentiment);
         }
      }

      // Update price
      updatePriceDisplay(symbol);

      // Update market table
      updateMarketTable();
   }

   function updatePriceDisplay(symbol, oldPrice = null) {
      const price = state.prices[symbol] || 0;
      const priceEl = document.getElementById('chart-price');
      if (priceEl) {
         const newPriceText = formatPrice(price);
         if (priceEl.textContent !== newPriceText) {
            priceEl.textContent = newPriceText;

            // Visual flash
            if (oldPrice && price > oldPrice) {
               priceEl.classList.remove('flash-up', 'flash-down');
               void priceEl.offsetWidth; // trigger reflow
               priceEl.classList.add('flash-up');
            } else if (oldPrice && price < oldPrice) {
               priceEl.classList.remove('flash-up', 'flash-down');
               void priceEl.offsetWidth; // trigger reflow
               priceEl.classList.add('flash-down');
            }
         }
      }

      // Change percentage from decision
      const decision = state.decisions[symbol];
      const changeEl = document.getElementById('chart-change');
      if (changeEl && decision) {
         const vol = decision.technical?.volatility || 0;
         const trend = decision.technical?.market_structure?.trend || 'FLAT';
         const isUp = trend === 'UP';
         const changePct = isUp ? vol : -vol;
         changeEl.textContent = `${changePct > 0 ? '+' : ''}${changePct.toFixed(2)}%`;
         changeEl.className = 'price-change';
         changeEl.classList.add(changePct >= 0 ? 'up' : 'down');
      }
   }

   function updateMarketRowPrice(symbol, price, oldPrice) {
      const row = document.querySelector(`#market-tbody tr[data-symbol="${symbol}"]`);
      if (!row) return;

      const priceCell = row.querySelector('.price-cell');
      if (priceCell) {
         priceCell.textContent = formatPrice(price);

         // Visual flash for row
         if (price > oldPrice) {
            priceCell.classList.remove('flash-up', 'flash-down');
            void priceCell.offsetWidth;
            priceCell.classList.add('flash-up');
         } else {
            priceCell.classList.remove('flash-up', 'flash-down');
            void priceCell.offsetWidth;
            priceCell.classList.add('flash-down');
         }
      }
   }

   function updateMarketTable() {
      const tbody = document.getElementById('market-tbody');
      if (!tbody) return;

      tbody.innerHTML = state.symbols.map(symbol => {
         const name = SYMBOL_NAMES[symbol] || symbol;
         const color = SYMBOL_COLORS[name] || '#94a3b8';
         const price = state.prices[symbol] || 0;
         const decision = state.decisions[symbol] || {};
         const action = decision.action || 'HOLD';
         const confidence = decision.confidence_pct || 50;
         const trend = decision.technical?.market_structure?.trend || '--';
         const isActive = symbol === state.activeSymbol;

         let actionClass = 'hold';
         if (action.includes('BUY')) actionClass = 'buy';
         else if (action.includes('SELL')) actionClass = 'sell';

         return `<tr data-symbol="${symbol}" class="${isActive ? 'active' : ''}" 
                        onclick="document.dispatchEvent(new CustomEvent('switchSymbol', {detail:'${symbol}'}))">
                <td>
                    <div class="pair-cell">
                        <span class="pair-icon" style="color:${color};border-color:${color}40">${name.charAt(0)}</span>
                        ${name}/USDT
                    </div>
                </td>
                <td class="price-cell">${formatPrice(price)}</td>
                <td class="signal-cell ${actionClass}">${action}</td>
                <td class="conf-cell">${confidence.toFixed(0)}%</td>
                <td class="trend-cell" style="color:${trend === 'UP' ? 'var(--color-bullish)' : trend === 'DOWN' ? 'var(--color-bearish)' : 'var(--text-muted)'}">
                    ${trend === 'UP' ? '▲' : trend === 'DOWN' ? '▼' : '●'} ${trend}
                </td>
            </tr>`;
      }).join('');
   }

   // Listen for symbol switch from market table
   document.addEventListener('switchSymbol', (e) => {
      switchSymbol(e.detail);
   });

   // ─── Timeframe Buttons ──────────────────────────
   function setupTimeframeButtons() {
      document.querySelectorAll('.tf-btn').forEach(btn => {
         btn.addEventListener('click', () => {
            document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const tf = btn.dataset.tf;
            if (window.chartManager) {
               window.chartManager.setTimeframe(tf);
            }
            // Re-generate chart for new timeframe
            const price = state.prices[state.activeSymbol] || 60000;
            const multiplier = tf === '1m' ? 60 : tf === '5m' ? 300 : tf === '15m' ? 900 : 3600;
            const candles = generateSimulatedCandlesTF(price, 200, multiplier);

            // Critical fix: update state to track the new timeframe's last candle
            state.chartData[state.activeSymbol] = candles;
            state.currentCandles[state.activeSymbol] = { ...candles[candles.length - 1] };

            if (window.chartManager) {
               window.chartManager.updateCandles(candles);
            }
         });
      });
   }

   function generateSimulatedCandlesTF(basePrice, count, intervalSec) {
      const candles = [];
      let price = basePrice;
      const now = Math.floor(Date.now() / 1000);
      const startTime = Math.floor(now / intervalSec) * intervalSec;

      for (let i = 0; i <= count; i++) {
         const time = startTime - (i * intervalSec);
         const volatility = intervalSec > 600 ? 0.005 : 0.003;
         const change = (Math.random() - 0.5) * price * volatility;
         const close = price;
         const open = price - change;
         const high = Math.max(open, close) + Math.random() * price * (volatility * 0.5);
         const low = Math.min(open, close) - Math.random() * price * (volatility * 0.5);
         const volume = Math.random() * 100 * (intervalSec / 60) + 10;

         candles.unshift({ time, open, high, low, close, volume });
         price = open;
      }
      return candles;
   }

   // ─── Clock ──────────────────────────────────────
   function startClock() {
      const update = () => {
         const el = document.getElementById('header-time');
         if (el) {
            const now = new Date();
            el.textContent = now.toLocaleTimeString([], {
               hour: '2-digit', minute: '2-digit', second: '2-digit',
            });
         }
      };
      update();
      setInterval(update, 1000);
   }

   // ─── Utilities ──────────────────────────────────
   function formatPrice(price) {
      if (!price || price === 0) return '$0.00';
      if (price >= 1000) return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      if (price >= 1) return `$${price.toFixed(2)}`;
      return `$${price.toFixed(6)}`;
   }

})();
