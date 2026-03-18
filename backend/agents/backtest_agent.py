"""
Backtest Agent — simulates historical trading strategies and verifies performance.
"""
import logging
import pandas as pd
import numpy as np
from typing import List, Tuple

from agents.technical_agent import TechnicalAgent
from agents.prediction_agent import PredictionAgent
from agents.signal_agent import SignalAgent
from agents.risk_agent import RiskAgent

logger = logging.getLogger(__name__)

class BacktestAgent:
    """
    Simulates trades over historical data using the agent pipeline.
    Useful for strategy optimization and performance verification.
    """

    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades = []
        self.equity_curve = []
        
    def run_backtest(self, df: pd.DataFrame, symbol: str) -> dict:
        """
        Simulate the agent's strategy on historical OHLCV data.
        
        Args:
            df: Historical candlestick data
            symbol: Trading pair
        
        Returns:
            Backtest report with metrics and equity curve
        """
        if len(df) < 100:
            return {"error": "Not enough historical data for backtest"}

        # Initialize agents
        ta_agent = TechnicalAgent()
        pred_agent = PredictionAgent()
        sig_agent = SignalAgent()
        risk_agent = RiskAgent()

        self.balance = self.initial_balance
        self.trades = []
        self.equity_curve = [self.initial_balance]
        
        active_trade = None
        
        # We start from index 60 so we have enough lookback for indicators/ML
        for i in range(60, len(df)):
            current_df = df.iloc[:i+1] # Look back window up to now
            current_candle = df.iloc[i]
            current_price = current_candle["close"]
            
            # 1. Pipeline (Mocking ML as heuristic for speed in backtest)
            ta = ta_agent.analyze(current_df, symbol)
            indicator_data = ta_agent.get_indicator_data_for_ml(current_df)
            # Use heuristic for backtest as real ML inference on each step is slow
            pred = pred_agent._heuristic_predict(indicator_data, symbol)
            
            sa = {"composite_score": 0, "sentiment": "NEUTRAL"} # Mock sentiment in backtest
            
            sig = sig_agent.generate_signal(symbol, current_price, ta, pred, sa)
            risk = risk_agent.evaluate_risk(sig, ta, self.balance)
            
            # 2. Check Active Trade Exit
            if active_trade:
                side = active_trade["side"]
                entry = active_trade["entry_price"]
                sl = active_trade["stop_loss"]
                tp = active_trade["target_1"]
                size = active_trade["size"]
                
                exit_price = None
                pnl = 0
                
                if side == "BUY":
                    if current_candle["low"] <= sl:
                        exit_price = sl
                        pnl = (exit_price - entry) * size
                    elif current_candle["high"] >= tp:
                        exit_price = tp
                        pnl = (exit_price - entry) * size
                elif side == "SELL":
                    if current_candle["high"] >= sl:
                        exit_price = sl
                        pnl = (entry - exit_price) * size
                    elif current_candle["low"] <= tp:
                        exit_price = tp
                        pnl = (entry - exit_price) * size
                
                if exit_price:
                    active_trade["exit_price"] = exit_price
                    active_trade["pnl"] = pnl
                    active_trade["exit_time"] = current_candle.name
                    active_trade["status"] = "CLOSED"
                    self.balance += pnl
                    self.trades.append(active_trade)
                    active_trade = None

            # 3. Check Signal for New Trade
            if not active_trade and risk["should_trade"]:
                action = sig["signal"]
                if action in ("BUY", "WEAK_BUY", "SELL", "WEAK_SELL"):
                    active_trade = {
                        "side": "BUY" if "BUY" in action else "SELL",
                        "entry_price": current_price,
                        "entry_time": current_candle.name,
                        "stop_loss": sig["stop_loss"],
                        "target_1": sig["target_1"],
                        "size": risk["position_size"],
                        "status": "OPEN",
                    }
                    
            self.equity_curve.append(self.balance)

        # Final Report
        return self._generate_report(symbol)

    def _generate_report(self, symbol: str) -> dict:
        if not self.trades:
            return {"symbol": symbol, "status": "no_trades_executed"}
            
        pnls = [t["pnl"] for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        total_pnl = sum(pnls)
        roi = (total_pnl / self.initial_balance) * 100
        win_rate = (len(wins) / len(self.trades)) * 100 if self.trades else 0
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0

        # Drawdown calculation
        eq = np.array(self.equity_curve)
        peak = np.maximum.accumulate(eq)
        drawdown = (eq - peak) / peak
        max_drawdown = np.min(drawdown) * 100

        return {
            "symbol": symbol,
            "initial_balance": self.initial_balance,
            "final_balance": round(self.balance, 2),
            "total_pnl": round(total_pnl, 2),
            "roi_pct": round(roi, 2),
            "total_trades": len(self.trades),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown": round(max_drawdown, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "equity_curve": eq.tolist()[-200:], # Last 200 points for charting
        }
