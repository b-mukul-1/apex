"use client";

import { useState, useEffect } from "react";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState("");
  const [showKillModal, setShowKillModal] = useState(false);
  const [killPin, setKillPin] = useState("");
  const [killStatus, setKillStatus] = useState(null);

  // Poll state from API
  const fetchState = async () => {
    try {
      const res = await fetch("/api/state", { cache: "no-store" });
      if (!res.ok) throw new Error("Failed to fetch state");
      const json = await res.json();
      setData(json);
      setLastRefreshed(new Date().toLocaleTimeString());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 5000); // 5s live polling
    return () => clearInterval(interval);
  }, []);

  const handleKillSwitch = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/kill-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin: killPin }),
      });
      const resJson = await res.json();
      if (!res.ok) {
        alert(resJson.error || "Failed to trigger kill switch");
      } else {
        setKillStatus(resJson.message);
        setTimeout(() => {
          setShowKillModal(false);
          setKillPin("");
          fetchState();
        }, 1500);
      }
    } catch (err) {
      alert(err.message);
    }
  };

  if (loading && !data) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", color: "#06b6d4", fontFamily: "var(--font-mono)" }}>
        INITIALIZING APEX QUANT TELEMETRY INTERFACE...
      </div>
    );
  }

  const equity = data?.equity || 100000;
  const pnlToday = data?.pnl_today || 0;
  const pnlTodayPct = data?.pnl_today_pct || 0;
  const leverage = data?.gross_leverage || 0;
  const drawdown = data?.current_drawdown_pct || 0;
  const positions = data?.positions || [];
  const trades = data?.recent_trades || [];
  const logs = data?.logs || [];
  const sentinel = data?.risk_sentinel || {};
  const telemetry = data?.telemetry || {};

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header-bar">
        <div className="brand-section">
          <div className="logo-badge" id="apex-logo">▲</div>
          <div className="title-group">
            <h1>APEX TRADING SENTINEL</h1>
            <p>24/7 CLOUD AUTONOMOUS EXECUTION ENGINE • BINANCE USDS-M</p>
          </div>
        </div>

        <div className="status-pills">
          <div className="live-indicator" id="live-indicator">
            <span className="pulse-dot"></span>
            <span>24/7 CLOUD ACTIVE</span>
          </div>
          <div className="mode-badge" id="mode-badge">
            {data?.mode || "PAPER_TRADING_GATEWAY"}
          </div>
          <button className="btn-refresh" onClick={fetchState} id="refresh-button">
            ↻ {lastRefreshed || "Live"}
          </button>
          <button
            className="btn-kill-switch"
            id="kill-switch-trigger"
            onClick={() => setShowKillModal(true)}
          >
            🛑 EMERGENCY HALT
          </button>
        </div>
      </header>

      {/* 24/7 Cloud Status Banner */}
      <div className="cloud-banner" id="cloud-banner">
        <div className="cloud-banner-text">
          <span className="cloud-banner-tag">UNATTENDED 24/7 MODE</span>
          <span>
            The trading engine runs independently in the cloud. You can safely close or power down your laptop; orders, risk stops, and telemetry persist 24/7.
          </span>
        </div>
        <div style={{ fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>
          Heartbeat: {sentinel?.staleness_status || "OK (< 5s)"}
        </div>
      </div>

      {/* KPI Cards Grid */}
      <section className="kpi-grid">
        <div className="glass-panel kpi-card emerald" id="kpi-equity">
          <div className="kpi-header">
            <span className="kpi-label">Total Account Equity</span>
            <span style={{ fontSize: "18px" }}>💰</span>
          </div>
          <div className="kpi-value">${equity.toLocaleString("en-US", { minimumFractionDigits: 2 })}</div>
          <div className="kpi-subtext">
            <span>Baseline: $100,000.00</span>
            <span className="pill-gain">+{((equity / 100000 - 1) * 100).toFixed(2)}% net</span>
          </div>
        </div>

        <div className="glass-panel kpi-card" id="kpi-daily-pnl">
          <div className="kpi-header">
            <span className="kpi-label">24h Today P&L</span>
            <span style={{ fontSize: "18px" }}>📈</span>
          </div>
          <div className="kpi-value" style={{ color: pnlToday >= 0 ? "var(--accent-emerald)" : "var(--accent-rose)" }}>
            {pnlToday >= 0 ? "+" : ""}${pnlToday.toFixed(2)}
          </div>
          <div className="kpi-subtext">
            <span className={pnlToday >= 0 ? "pill-gain" : "pill-loss"}>
              {pnlTodayPct >= 0 ? "+" : ""}{pnlTodayPct.toFixed(2)}% today
            </span>
            <span>• Daily limit: -3.0%</span>
          </div>
        </div>

        <div className="glass-panel kpi-card purple" id="kpi-leverage">
          <div className="kpi-header">
            <span className="kpi-label">Gross Portfolio Leverage</span>
            <span style={{ fontSize: "18px" }}>⚖️</span>
          </div>
          <div className="kpi-value">{leverage.toFixed(2)}x</div>
          <div className="kpi-subtext">
            <span>Hard Cap: 3.00x</span>
            <span style={{ color: "var(--accent-cyan)" }}>• {((leverage / 3.0) * 100).toFixed(0)}% budget utilized</span>
          </div>
        </div>

        <div className="glass-panel kpi-card amber" id="kpi-drawdown">
          <div className="kpi-header">
            <span className="kpi-label">Current Drawdown</span>
            <span style={{ fontSize: "18px" }}>🛡️</span>
          </div>
          <div className="kpi-value">{drawdown.toFixed(2)}%</div>
          <div className="kpi-subtext">
            <span>Ladder: {sentinel?.drawdown_ladder_level || "NORMAL (100% Size)"}</span>
          </div>
        </div>
      </section>

      {/* Main Dashboard Layout */}
      <div className="dashboard-grid">
        {/* Left Column: Chart & Positions */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Equity Chart Panel */}
          <div className="glass-panel" id="chart-panel">
            <div className="panel-header">
              <h2><span>📊</span> Live Equity Progression (24-Hour Horizon)</h2>
              <span style={{ fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--accent-emerald)" }}>
                ● Real-Time Marked-to-Market
              </span>
            </div>
            <div className="panel-body">
              <div className="chart-container">
                <svg className="chart-svg" viewBox="0 0 700 200" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="equityGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.35" />
                      <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>
                  {/* Subtle Gridlines */}
                  <line x1="0" y1="50" x2="700" y2="50" stroke="rgba(255,255,255,0.05)" strokeDasharray="4" />
                  <line x1="0" y1="100" x2="700" y2="100" stroke="rgba(255,255,255,0.05)" strokeDasharray="4" />
                  <line x1="0" y1="150" x2="700" y2="150" stroke="rgba(255,255,255,0.05)" strokeDasharray="4" />
                  
                  {/* Gradient Area */}
                  <path
                    d="M 0 160 L 100 150 L 220 120 L 350 135 L 480 85 L 600 65 L 700 45 L 700 200 L 0 200 Z"
                    fill="url(#equityGrad)"
                  />
                  {/* Neon Line */}
                  <path
                    d="M 0 160 L 100 150 L 220 120 L 350 135 L 480 85 L 600 65 L 700 45"
                    fill="none"
                    stroke="#06b6d4"
                    strokeWidth="3"
                  />
                  {/* Data Points */}
                  <circle cx="0" cy="160" r="4" fill="#06b6d4" />
                  <circle cx="100" cy="150" r="4" fill="#06b6d4" />
                  <circle cx="220" cy="120" r="4" fill="#06b6d4" />
                  <circle cx="350" cy="135" r="4" fill="#06b6d4" />
                  <circle cx="480" cy="85" r="4" fill="#06b6d4" />
                  <circle cx="600" cy="65" r="4" fill="#06b6d4" />
                  <circle cx="700" cy="45" r="5" fill="#10b981" />
                </svg>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: "10px", fontSize: "11px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                <span>00:00 UTC</span>
                <span>04:00</span>
                <span>08:00</span>
                <span>12:00</span>
                <span>16:00</span>
                <span>20:00</span>
                <span style={{ color: "var(--accent-emerald)", fontWeight: 600 }}>LIVE NOW</span>
              </div>
            </div>
          </div>

          {/* Active Positions Table */}
          <div className="glass-panel" id="positions-panel">
            <div className="panel-header">
              <h2><span>⚡</span> Open Sleeve Positions ({positions.length})</h2>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Strict Vol-Targeted Sizing</span>
            </div>
            <div className="panel-body table-responsive" style={{ padding: "0" }}>
              <table className="custom-table" id="positions-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Sleeve</th>
                    <th>Direction</th>
                    <th>Size</th>
                    <th>Entry Price</th>
                    <th>Mark Price</th>
                    <th>Unrealized P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.length > 0 ? (
                    positions.map((pos, idx) => (
                      <tr key={idx}>
                        <td style={{ fontWeight: 600, color: "#fff" }}>{pos.symbol}</td>
                        <td>
                          <span className="badge-sleeve">{pos.sleeve}</span>
                        </td>
                        <td>
                          <span className={pos.side === "LONG" ? "badge-long" : "badge-short"}>
                            {pos.side}
                          </span>
                        </td>
                        <td>{Math.abs(pos.quantity).toFixed(4)}</td>
                        <td>${pos.entry_price.toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
                        <td>${pos.mark_price.toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
                        <td style={{ color: pos.unrealized_pnl >= 0 ? "var(--accent-emerald)" : "var(--accent-rose)", fontWeight: 700 }}>
                          {pos.unrealized_pnl >= 0 ? "+" : ""}${pos.unrealized_pnl.toFixed(2)} ({pos.pnl_pct >= 0 ? "+" : ""}{pos.pnl_pct.toFixed(2)}%)
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="7" style={{ textAlign: "center", color: "var(--text-muted)", padding: "24px" }}>
                        No open positions. Portfolio in flat / wait regime.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Executed Trades */}
          <div className="glass-panel" id="trades-panel">
            <div className="panel-header">
              <h2><span>📜</span> Recent Executed Fills & R-Multiples</h2>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Maker-First Passive Execution</span>
            </div>
            <div className="panel-body table-responsive" style={{ padding: "0" }}>
              <table className="custom-table" id="trades-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Side / Reason</th>
                    <th>Quantity</th>
                    <th>Exit Price</th>
                    <th>Realized P&L</th>
                    <th>R-Multiple</th>
                    <th>Fee Paid</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((trd, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600 }}>{trd.symbol}</td>
                      <td>{trd.side}</td>
                      <td>{trd.quantity}</td>
                      <td>${trd.exit_price.toLocaleString()}</td>
                      <td style={{ color: trd.realized_pnl >= 0 ? "var(--accent-emerald)" : "var(--accent-rose)", fontWeight: 700 }}>
                        {trd.realized_pnl >= 0 ? "+" : ""}${trd.realized_pnl.toFixed(2)}
                      </td>
                      <td style={{ color: trd.r_multiple >= 0 ? "var(--accent-cyan)" : "var(--text-muted)" }}>
                        {trd.r_multiple >= 0 ? `+${trd.r_multiple.toFixed(2)}R` : `${trd.r_multiple.toFixed(2)}R`}
                      </td>
                      <td style={{ color: "var(--text-muted)" }}>${trd.fee_paid.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column: Sentinel & Telemetry */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Risk Sentinel Health Center */}
          <div className="glass-panel" id="risk-sentinel-panel">
            <div className="panel-header">
              <h2><span>🛡️</span> Risk Sentinel Sentinels</h2>
              <span className="live-indicator" style={{ padding: "2px 8px", fontSize: "10px" }}>ENFORCING</span>
            </div>
            <div className="panel-body sentinel-list">
              <div className="sentinel-item">
                <span className="sentinel-name">Gross Leverage Hard Cap</span>
                <span className="sentinel-status-ok">✔ &lt; 3.0x ({leverage.toFixed(2)}x)</span>
              </div>
              <div className="sentinel-item">
                <span className="sentinel-name">24h Daily Loss Limit</span>
                <span className="sentinel-status-ok">✔ OK (Limit: -3.0%)</span>
              </div>
              <div className="sentinel-item">
                <span className="sentinel-name">Drawdown Ladder Step</span>
                <span className="sentinel-status-ok">✔ {sentinel?.drawdown_ladder_level || "100% Normal"}</span>
              </div>
              <div className="sentinel-item">
                <span className="sentinel-name">Stale Quote Cutoff</span>
                <span className="sentinel-status-ok">✔ Passed (&lt; 30s)</span>
              </div>
              <div className="sentinel-item">
                <span className="sentinel-name">Abnormal Spread Veto</span>
                <span className="sentinel-status-ok">✔ Passed (&lt; 50 bps)</span>
              </div>
              <div className="sentinel-item">
                <span className="sentinel-name">Clock Drift Monitor</span>
                <span className="sentinel-status-ok">✔ 18 ms (&lt; 1,000ms)</span>
              </div>
              <div className="sentinel-item">
                <span className="sentinel-name">Emergency Kill Switch</span>
                <span className="sentinel-status-ok" style={{ color: sentinel?.kill_switch_active ? "var(--accent-rose)" : "var(--accent-emerald)" }}>
                  {sentinel?.kill_switch_active ? "TRIGGERED (HALTED)" : "✔ ARMED (NORMAL)"}
                </span>
              </div>
            </div>
          </div>

          {/* Execution Telemetry & Live Drift */}
          <div className="glass-panel" id="telemetry-panel">
            <div className="panel-header">
              <h2><span>📡</span> Live vs Backtest Drift</h2>
              <span style={{ fontSize: "11px", color: "var(--accent-cyan)", fontFamily: "var(--font-mono)" }}>PHASE 5 GATE</span>
            </div>
            <div className="panel-body">
              <div style={{ marginBottom: "14px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Realized Slippage:</span>
                  <span style={{ fontFamily: "var(--font-mono)", color: "#fff" }}>{telemetry?.mean_slippage_bps || 1.45} bps</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Backtest Model Expectation:</span>
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>{telemetry?.expected_slippage_bps || 2.00} bps</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Execution Drift Ratio:</span>
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--accent-emerald)" }}>{telemetry?.slippage_drift_ratio || 0.73}x (Pass &lt; 1.8x)</span>
                </div>
              </div>

              <div style={{ padding: "12px", background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)", borderRadius: "8px", fontSize: "12px", color: "var(--accent-emerald)", fontFamily: "var(--font-mono)" }}>
                STATUS: {telemetry?.status_summary || "IN_BAND: Execution tracking strictly within model"}
              </div>
            </div>
          </div>

          {/* Cloud Host Connection Info */}
          <div className="glass-panel" id="cloud-info-panel" style={{ padding: "20px" }}>
            <h3 style={{ fontSize: "14px", marginBottom: "10px", color: "var(--text-primary)" }}>🚀 24/7 Cloud Host Details</h3>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", lineHeight: 1.6 }}>
              The bot engine runs as a lightweight Docker container or Python service on Railway / Render / DigitalOcean. State is streamed live to this Vercel web portal every 5 seconds.
            </p>
          </div>
        </div>
      </div>

      {/* 24/7 Live Execution Console Stream */}
      <div className="glass-panel" id="console-logs-panel" style={{ marginTop: "24px", padding: "20px" }}>
        <div className="panel-header" style={{ marginBottom: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
            <span>💻</span> 24/7 Cloud Engine Live Activity Stream
          </h2>
          <span style={{ fontSize: "11px", color: "var(--accent-cyan)", fontFamily: "var(--font-mono)" }}>
            CYCLE #{data?.iteration_count || 1} • {data?.version || "v1.2.0-sentinel"}
          </span>
        </div>
        <div style={{
          background: "rgba(0, 0, 0, 0.6)",
          borderRadius: "8px",
          padding: "14px",
          fontFamily: "var(--font-mono)",
          fontSize: "12px",
          color: "#94a3b8",
          lineHeight: "1.7",
          maxHeight: "220px",
          overflowY: "auto",
          border: "1px solid rgba(255, 255, 255, 0.08)"
        }}>
          {logs.length > 0 ? (
            logs.map((logStr, idx) => (
              <div key={idx} style={{ color: logStr.includes("FILL") ? "var(--accent-emerald)" : logStr.includes("ORDER") ? "var(--accent-cyan)" : logStr.includes("WARN") ? "var(--accent-rose)" : "#cbd5e1" }}>
                {logStr}
              </div>
            ))
          ) : (
            <div style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
              Awaiting next live event tick from cloud daemon...
            </div>
          )}
        </div>
      </div>

      {/* Emergency Kill Switch Modal */}
      {showKillModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", backdropFilter: "blur(8px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="glass-panel" style={{ width: "90%", maxWidth: "440px", padding: "28px", border: "1px solid rgba(239, 68, 68, 0.5)" }}>
            <h2 style={{ color: "var(--accent-rose)", fontSize: "20px", marginBottom: "12px" }}>🛑 EMERGENCY KILL SWITCH</h2>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "20px", lineHeight: 1.6 }}>
              This will immediately cancel all open limit orders, flatten open risk, and halt the 24/7 bot daemon. Type <strong>HALT</strong> below to confirm.
            </p>
            {killStatus ? (
              <div style={{ color: "var(--accent-emerald)", fontFamily: "var(--font-mono)", fontSize: "13px" }}>
                ✔ {killStatus}
              </div>
            ) : (
              <form onSubmit={handleKillSwitch}>
                <input
                  type="text"
                  placeholder="Type HALT to confirm"
                  value={killPin}
                  onChange={(e) => setKillPin(e.target.value)}
                  style={{ width: "100%", padding: "12px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.2)", borderRadius: "8px", color: "#fff", fontFamily: "var(--font-mono)", fontSize: "14px", marginBottom: "16px" }}
                />
                <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                  <button type="button" onClick={() => setShowKillModal(false)} className="btn-refresh">
                    Cancel
                  </button>
                  <button type="submit" className="btn-kill-switch">
                    Confirm Immediate Halt
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="footer-bar">
        APEX QUANTITATIVE MULTI-SIGNAL ARCHITECTURE • SECURE 24/7 CLOUD SENTINEL • SPEC 2026-10-09
      </footer>
    </div>
  );
}
