/**
 * SmartPre — Chart Manager
 * Uses TradingView Lightweight Charts for candlestick display
 */
class ChartManager {
   constructor(containerId) {
      this.container = document.getElementById(containerId);
      this.chart = null;
      this.candleSeries = null;
      this.volumeSeries = null;
      this.currentSymbol = 'BTCUSDT';
      this.currentTimeframe = '15m';
      this._init();
   }

   _init() {
      if (!this.container || typeof LightweightCharts === 'undefined') {
         console.warn('Chart container or LightweightCharts not available');
         return;
      }

      this.chart = LightweightCharts.createChart(this.container, {
         width: this.container.clientWidth,
         height: this.container.clientHeight || 400,
         layout: {
            background: { type: 'solid', color: 'transparent' },
            textColor: '#94a3b8',
            fontFamily: "'Inter', sans-serif",
            fontSize: 11,
         },
         grid: {
            vertLines: { color: 'rgba(255,255,255,0.03)' },
            horzLines: { color: 'rgba(255,255,255,0.03)' },
         },
         crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {
               color: 'rgba(99, 102, 241, 0.4)',
               width: 1,
               style: LightweightCharts.LineStyle.Dashed,
               labelBackgroundColor: '#6366f1',
            },
            horzLine: {
               color: 'rgba(99, 102, 241, 0.4)',
               width: 1,
               style: LightweightCharts.LineStyle.Dashed,
               labelBackgroundColor: '#6366f1',
            },
         },
         rightPriceScale: {
            borderColor: 'rgba(255,255,255,0.06)',
            scaleMargins: { top: 0.1, bottom: 0.25 },
         },
         timeScale: {
            borderColor: 'rgba(255,255,255,0.06)',
            timeVisible: true,
            secondsVisible: false,
         },
         handleScroll: { vertTouchDrag: false },
      });

      // Candle series
      this.candleSeries = this.chart.addCandlestickSeries({
         upColor: '#22c55e',
         downColor: '#ef4444',
         borderUpColor: '#22c55e',
         borderDownColor: '#ef4444',
         wickUpColor: 'rgba(34,197,94,0.6)',
         wickDownColor: 'rgba(239,68,68,0.6)',
         lastValueVisible: true,
         priceLineVisible: true,
         priceLineWidth: 1,
         priceLineColor: '#6366f1',
      });

      // Volume series
      this.volumeSeries = this.chart.addHistogramSeries({
         priceFormat: { type: 'volume' },
         priceScaleId: '', // Overlay
         lastValueVisible: false,
         priceLineVisible: false,
      });
      this.volumeSeries.priceScale().applyOptions({
         scaleMargins: { top: 0.8, bottom: 0 },
      });

      // Resize observer
      this._resizeObserver = new ResizeObserver(() => {
         if (this.chart) {
            this.chart.applyOptions({
               width: this.container.clientWidth,
               height: this.container.clientHeight,
            });
         }
      });
      this._resizeObserver.observe(this.container);
   }

   updateCandles(candles) {
      if (!this.candleSeries || !candles || candles.length === 0) return;

      const candleData = candles.map(c => ({
         time: c.time,
         open: c.open,
         high: c.high,
         low: c.low,
         close: c.close,
      }));

      const volumeData = candles.map(c => ({
         time: c.time,
         value: c.volume,
         color: c.close >= c.open
            ? 'rgba(34, 197, 94, 0.25)'
            : 'rgba(239, 68, 68, 0.25)',
      }));

      this.candleSeries.setData(candleData);
      this.volumeSeries.setData(volumeData);
      this.chart.timeScale().fitContent();
   }

   addCandle(candle) {
      if (!this.candleSeries || !candle) return;

      this.candleSeries.update({
         time: candle.time,
         open: candle.open,
         high: candle.high,
         low: candle.low,
         close: candle.close,
      });

      this.volumeSeries.update({
         time: candle.time,
         value: candle.volume,
         color: candle.close >= candle.open
            ? 'rgba(34, 197, 94, 0.25)'
            : 'rgba(239, 68, 68, 0.25)',
      });
   }

   setSymbol(symbol) {
      this.currentSymbol = symbol;
   }

   setTimeframe(tf) {
      this.currentTimeframe = tf;
   }

   destroy() {
      if (this._resizeObserver) this._resizeObserver.disconnect();
      if (this.chart) this.chart.remove();
   }
}

// Global instance
window.chartManager = null;
