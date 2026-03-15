/**
 * SmartPre — Main Application Controller
 * Orchestrates all modules and manages state
 */
(function () {
   'use strict';

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
      console.log('🔄 Fetching initial data via REST...');
      
      try {
         // Fetch prices
         const priceResp = await fetch('/api/prices');
         if (priceResp.ok) {
            state.prices = await priceResp.json();
            console.log('💰 Prices loaded:', Object.keys(state.prices).length, 'symbols');
            updatePriceDisplay(state.activeSymbol);
         }
      } catch (e) {
         console.log('REST fallback: prices unavailable, waiting for WebSocket');
      }

      try {
         // Fetch all decisions
         const decResp = await fetch('/api/decisions');
         if (decResp.ok) {
            const decisions = await decResp.json();
            if (Object.keys(decisions).length > 0) {
               state.decisions = decisions;
               console.log('📊 Decisions loaded:', Object.keys(decisions).length, 'symbols');
               updateAllPanels();
            } else {
               console.log('No cached decisions yet, triggering analysis...');
               // Trigger a fresh analysis for active symbol
               try {
                  const analysisResp = await fetch(`/api/analysis/${state.activeSymbol}`);
                  if (analysisResp.ok) {
                     const analysis = await analysisResp.json();
                     if (analysis && analysis.action) {
                        state.decisions[state.activeSymbol] = analysis;
                        if (analysis.price) state.prices[state.activeSymbol] = analysis.price;
                        console.log('✅ Fresh analysis loaded for', state.activeSymbol);
                        updateAllPanels();
                     }
                  }
               } catch (e) {
                  console.log('Fresh analysis fetch failed:', e);
               }
            }
         }
      } catch (e) {
         console.log('REST fallback: decisions unavailable');
      }

      // Fetch chart data
      loadChartData(state.activeSymbol);
   }

   async function loadChartData(symbol) {
      const tf = window.chartManager ? window.chartManager.currentTimeframe : '1m';
      try {
         const resp = await fetch(`/api/klines/${symbol}?timeframe=${tf}`);
         if (resp.ok) {
            const candles = await resp.json();
            if (candles && candles.length > 0) {
               console.log(`📊 Loaded ${candles.length} candles for ${symbol}/${tf}`);
               state.chartData[symbol] = candles;
               state.currentCandles[symbol] = { ...candles[candles.length - 1] };
               if (window.chartManager) {
                  window.chartManager.updateCandles(candles);
               }
               // Also update price from latest candle
               const latest = candles[candles.length - 1];
               if (latest.close > 0) {
                  state.prices[symbol] = latest.close;
                  updatePriceDisplay(symbol);
               }
               return;
            } else {
               console.warn(`No candles returned for ${symbol}/${tf}`);
            }
         }
      } catch (e) {
         console.warn('Failed to fetch klines:', e);
      }
      
      // Fallback: try 1m if we requested a different timeframe
      if (tf !== '1m') {
         try {
            const fallbackResp = await fetch(`/api/klines/${symbol}?timeframe=1m`);
            if (fallbackResp.ok) {
               const candles = await fallbackResp.json();
               if (candles && candles.length > 0) {
                  console.log(`📊 Fallback: Loaded ${candles.length} 1m candles for ${symbol}`);
                  state.chartData[symbol] = candles;
                  state.currentCandles[symbol] = { ...candles[candles.length - 1] };
                  if (window.chartManager) {
                     window.chartManager.updateCandles(candles);
                  }
                  const latest = candles[candles.length - 1];
                  if (latest.close > 0) {
                     state.prices[symbol] = latest.close;
                     updatePriceDisplay(symbol);
                  }
                  return;
               }
            }
         } catch (e) {
            console.warn('Fallback 1m klines also failed:', e);
         }
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
         candle.volume = candle.volume; // No fake volume increment
      } else {
         // Update existing candle
         candle.close = price;
         candle.high = Math.max(candle.high, price);
         candle.low = Math.min(candle.low, price);
         candle.volume = candle.volume; // No fake volume increment
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
            // Fetch real data for new timeframe
            if (state.activeSymbol) {
               loadChartData(state.activeSymbol);
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
