/**
 * SmartPre — Main Application Controller
 * Orchestrates all modules and manages state
 */
(function () {
   'use strict';

   // ─── State ──────────────────────────────────────
   const state = {
      activeSymbol: 'BTCUSDT',
      symbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'PAXGUSDT'],
      prices: {},
      decisions: {},
      chartData: {},
      currentCandles: {},
      notificationsEnabled: false,
      previousDecisions: {},
   };

   const SYMBOL_NAMES = {
      'BTCUSDT': 'BTC',
      'ETHUSDT': 'ETH',
      'SOLUSDT': 'SOL',
      'BNBUSDT': 'BNB',
      'XRPUSDT': 'XRP',
      'PAXGUSDT': 'PAXG',
   };

   const SYMBOL_COLORS = {
      'BTC': '#f7931a',
      'ETH': '#627eea',
      'SOL': '#9945ff',
      'BNB': '#f0b90b',
      'XRP': '#00aae4',
      'PAXG': '#FFD700',
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

      // Setup notification toggle
      setupNotifications();

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

   // ─── Notifications ──────────────────────────────
   function setupNotifications() {
      // Load saved preference
      const saved = localStorage.getItem('smartpre_notifications');
      state.notificationsEnabled = saved === 'true';
      updateNotifUI();

      const toggleBtn = document.getElementById('notif-toggle');
      if (toggleBtn) {
         toggleBtn.addEventListener('click', toggleNotifications);
      }
   }

   function toggleNotifications() {
      console.log('🔔 Toggle notification clicked. Current state:', state.notificationsEnabled);
      
      if (!state.notificationsEnabled) {
         // User wants to turn ON
         if (!('Notification' in window)) {
            alert('Your browser does not support desktop notifications.');
            return;
         }

         console.log('🔔 Notification permission status:', Notification.permission);

         if (Notification.permission === 'granted') {
            enableNotifications();
         } else if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
               console.log('🔔 Permission request result:', permission);
               if (permission === 'granted') {
                  enableNotifications();
               } else {
                  alert('Notification permission was denied. Please allow notifications in your browser settings.');
               }
            });
         } else {
            alert('Notifications are blocked for this site. Please enable them in your browser/system settings.');
         }
      } else {
         // Turn OFF
         state.notificationsEnabled = false;
         localStorage.setItem('smartpre_notifications', 'false');
         updateNotifUI();
         console.log('🔔 Notifications disabled');
      }
   }

   function enableNotifications() {
      state.notificationsEnabled = true;
      localStorage.setItem('smartpre_notifications', 'true');
      updateNotifUI();
      console.log('🔔 Notifications enabled successfully');
      
      // Immediately notify about any current signals so the user knows it's working
      showTestNotification();
      
      // Delay a bit then check current decisions
      setTimeout(() => {
         console.log('🔔 Checking current signals for immediate notification...');
         // Clear previous decisions to force a notification for existing signals
         state.previousDecisions = {};
         checkAndNotify(state.decisions);
      }, 1000);
   }

   function updateNotifUI() {
      const iconEl = document.getElementById('notif-icon');
      const labelEl = document.getElementById('notif-label');
      const toggleBtn = document.getElementById('notif-toggle');

      if (state.notificationsEnabled) {
         if (iconEl) iconEl.setAttribute('data-lucide', 'bell-ring');
         if (labelEl) labelEl.textContent = 'ON';
         if (toggleBtn) toggleBtn.classList.add('active');
      } else {
         if (iconEl) iconEl.setAttribute('data-lucide', 'bell-off');
         if (labelEl) labelEl.textContent = 'OFF';
         if (toggleBtn) toggleBtn.classList.remove('active');
      }

      const lucide = window.lucide;
      if (lucide) lucide.createIcons();
   }

   function showTestNotification() {
      try {
         const n = new Notification('🟢 SmartPre Active', {
            body: 'Trading alerts are now active for BUY and SELL signals.',
            icon: '/static/static/assets/favicon.png', // Try both common paths
            tag: 'smartpre-welcome',
         });
         console.log('🔔 Test notification sent');
      } catch (e) {
         console.warn('🔔 Failed to send test notification:', e);
      }
   }

   function checkAndNotify(newDecisions) {
      if (!state.notificationsEnabled) return;
      if (!('Notification' in window) || Notification.permission !== 'granted') {
         console.warn('🔔 Cannot notify: Permission not granted or API unavailable');
         return;
      }

      console.log('🔔 checkAndNotify processing decisions for symbols:', Object.keys(newDecisions).length);

      for (const [symbol, decision] of Object.entries(newDecisions)) {
         const action = decision.action;
         const prevAction = state.previousDecisions[symbol]?.action;

         // Skip if action hasn't changed (prevents spam)
         if (action === prevAction) continue;
         
         // Only notify on actionable signals
         if (!['BUY', 'SELL', 'WEAK_BUY', 'WEAK_SELL'].includes(action)) {
            // Update previous action even if it's HOLD so we catch the next change
            state.previousDecisions[symbol] = { action: action };
            continue;
         }

         const name = SYMBOL_NAMES[symbol] || symbol;
         const confidence = decision.confidence_pct || 0;
         const price = decision.price ? formatPrice(decision.price) : '';
         const reason = decision.reason || '';

         console.log(`🔔 TRIGGERING NOTIFICATION: ${symbol} ${action}`);

         let emoji = '📊';
         if (action === 'BUY') emoji = '🟢';
         else if (action === 'SELL') emoji = '🔴';
         else if (action === 'WEAK_BUY') emoji = '📈';
         else if (action === 'WEAK_SELL') emoji = '📉';

         const title = `${emoji} ${action} Signal — ${name}/USDT`;
         const body = `Price: ${price} | Confidence: ${confidence.toFixed(0)}%\n${reason}`;

         try {
            const notif = new Notification(title, {
               body: body,
               icon: '/static/static/assets/favicon.png',
               tag: `smartpre-${symbol}`,
               requireInteraction: true,
               silent: false,
            });

            notif.onclick = () => {
               window.focus();
               switchSymbol(symbol);
               notif.close();
            };

            // Sound fallback: You can't play sound easily without user interaction, 
            // but the Notification API handles the system sound.
         } catch (e) {
            console.error('🔔 Notification API Error:', e);
            // Fallback: Show a regular alert so the user at least sees the signal
            console.log(`Fallback Alert: ${title}\n${body}`);
         }

         // Save current action
         state.previousDecisions[symbol] = { action: action };
      }
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
            // Save as previous first (don't notify on initial load)
            for (const [sym, dec] of Object.entries(data.decisions)) {
               state.previousDecisions[sym] = { action: dec.action };
            }
            state.decisions = data.decisions;
            updateAllPanels();
         }
      });

      ws.on('analysisUpdate', (data) => {
         console.log('📊 Analysis update received');

         // Check for notifications BEFORE updating state
         checkAndNotify(data);

         // Update all decisions
         for (const [symbol, decision] of Object.entries(data)) {
            state.decisions[symbol] = decision;
            if (decision.price) state.prices[symbol] = decision.price;
         }

         updateAllPanels();
      });

      ws.on('analysisResult', (data) => {
         checkAndNotify(data);
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
         const priceResp = await fetch('/api/prices');
         if (priceResp.ok) {
            state.prices = await priceResp.json();
            updatePriceDisplay(state.activeSymbol);
         }
      } catch (e) {
         console.log('REST fallback: prices unavailable, waiting for WebSocket');
      }

      try {
         const decResp = await fetch('/api/decisions');
         if (decResp.ok) {
            const decisions = await decResp.json();
            if (Object.keys(decisions).length > 0) {
               for (const [sym, dec] of Object.entries(decisions)) {
                  state.previousDecisions[sym] = { action: dec.action };
               }
               state.decisions = decisions;
               updateAllPanels();
            }
         }
      } catch (e) {
         console.log('REST fallback: decisions unavailable');
      }

      // Fetch chart data — DEFAULT 15m
      loadChartData(state.activeSymbol);
   }

   async function loadChartData(symbol) {
      const tf = window.chartManager ? window.chartManager.currentTimeframe : '15m';
      
      try {
         // Fetch REAL history from backend
         const histResp = await fetch(`/api/history/${symbol}?timeframe=${tf}`);
         if (histResp.ok) {
            const candles = await histResp.json();
            if (candles && candles.length > 0) {
               console.log(`📈 Loaded ${candles.length} historical candles for ${symbol}`);
               state.chartData[symbol] = candles;
               state.currentCandles[symbol] = { ...candles[candles.length - 1] };
               if (window.chartManager) {
                  window.chartManager.updateCandles(candles);
               }
               return; // Exit if success
            }
         }
      } catch (e) {
         console.warn('Failed to fetch real history, falling back to simulation:', e);
      }

      // FALLBACK: Generate simulated candles if API fails or returns empty
      if (window.chartManager) {
         const price = state.prices[symbol] || 60000;
         const intervalSec = tf === '1m' ? 60 : tf === '5m' ? 300 : tf === '15m' ? 900 : 3600;
         const candles = generateSimulatedCandlesTF(price, 200, intervalSec);
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

      if (candleTime > candle.time) {
         candle.time = candleTime;
         candle.open = price;
         candle.high = price;
         candle.low = price;
         candle.close = price;
         candle.volume = Math.random() * 10 + 2;
      } else {
         candle.close = price;
         candle.high = Math.max(candle.high, price);
         candle.low = Math.min(candle.low, price);
         candle.volume += Math.random() * 0.5;
      }

      window.chartManager.addCandle(candle);
   }

   function getTimeframeMinutes(tf) {
      if (tf === '1m') return 1;
      if (tf === '5m') return 5;
      if (tf === '15m') return 15;
      if (tf === '1h') return 60;
      return 15;
   }

   // ─── UI Updates ─────────────────────────────────
   function updateAllPanels() {
      const symbol = state.activeSymbol;
      const decision = state.decisions[symbol];

      if (decision) {
         window.signalManager.updateDecision(decision);

         if (decision.sentiment) {
            window.sentimentManager.updateSentiment(decision.sentiment);
         }
      }

      updatePriceDisplay(symbol);
      updateMarketTable();
   }

   function updatePriceDisplay(symbol, oldPrice = null) {
      const price = state.prices[symbol] || 0;
      const priceEl = document.getElementById('chart-price');
      if (priceEl) {
         const newPriceText = formatPrice(price);
         if (priceEl.textContent !== newPriceText) {
            priceEl.textContent = newPriceText;

            if (oldPrice && price > oldPrice) {
               priceEl.classList.remove('flash-up', 'flash-down');
               void priceEl.offsetWidth;
               priceEl.classList.add('flash-up');
            } else if (oldPrice && price < oldPrice) {
               priceEl.classList.remove('flash-up', 'flash-down');
               void priceEl.offsetWidth;
               priceEl.classList.add('flash-down');
            }
         }
      }

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
         const reason = decision.reason || '';
         const isActive = symbol === state.activeSymbol;

         let actionClass = 'hold';
         if (action.includes('BUY')) actionClass = 'buy';
         else if (action.includes('SELL')) actionClass = 'sell';

         let actionDisplay = action;
         if (action === 'WEAK_BUY') actionDisplay = 'W.BUY';
         else if (action === 'WEAK_SELL') actionDisplay = 'W.SELL';

         let confColor = 'var(--text-muted)';
         if (confidence >= 65) confColor = 'var(--color-bullish)';
         else if (confidence >= 45) confColor = 'var(--color-warning)';
         else confColor = 'var(--color-bearish)';

         const icon = name === 'PAXG' ? '🥇' : name.charAt(0);

         return `<tr data-symbol="${symbol}" class="${isActive ? 'active' : ''}" 
                        title="${reason}"
                        onclick="document.dispatchEvent(new CustomEvent('switchSymbol', {detail:'${symbol}'}))">
                <td>
                    <div class="pair-cell">
                        <span class="pair-icon" style="color:${color};border-color:${color}40">${icon}</span>
                        ${name}/USDT
                    </div>
                </td>
                <td class="price-cell">${formatPrice(price)}</td>
                <td class="signal-cell ${actionClass}">${actionDisplay}</td>
                <td class="conf-cell" style="color:${confColor}">${confidence.toFixed(0)}%</td>
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
         btn.addEventListener('click', async () => {
            document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const tf = btn.dataset.tf;
            if (window.chartManager) {
               window.chartManager.setTimeframe(tf);
            }
            
            // Fetch real history for the new timeframe
            await loadChartData(state.activeSymbol);
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
            el.textContent = now.toLocaleTimeString('en-US', {
               hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
            }).toLowerCase();
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
