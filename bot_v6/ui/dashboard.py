"""Web-Dashboard (Flask-basiert)
Zeigt Live-Status des Bots auf http://localhost:5050
"""
import threading
import logging

try:
    from flask import Flask, jsonify, render_template_string
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    print("⚠️ Flask nicht installiert. Dashboard deaktiviert. Installiere mit: pip install flask")


DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Trading Imperium V6 - Dashboard</title>
<style>
  body{font-family:'Courier New',monospace;background:#0a0a0a;color:#00ff88;margin:0;padding:20px;min-height:100vh}
  h1{color:#ffcc00;border-bottom:2px solid #333;padding-bottom:12px;display:flex;align-items:center;gap:15px}
  .pulse{display:inline-block;width:12px;height:12px;background:#00ff88;border-radius:50%;animation:p 1.5s infinite}
  @keyframes p{0%{opacity:1}50%{opacity:.3}100%{opacity:1}}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px;margin:20px 0}
  .card{background:#111;border:1px solid #333;border-radius:8px;padding:18px;transition:border-color .2s}
  .card:hover{border-color:#ffcc00}
  .card h3{color:#ffcc00;margin:0 0 12px;font-size:14px;text-transform:uppercase;letter-spacing:1px}
  .big{font-size:28px;color:#00ff88;font-weight:bold}
  .pos{color:#00ff88}.neg{color:#ff4444}.neu{color:#aaa}.yellow{color:#ffcc00}
  table{width:100%;border-collapse:collapse;font-size:13px}
  td,th{padding:8px 10px;text-align:left;border-bottom:1px solid #222}
  th{color:#ffcc00;font-weight:normal;text-transform:uppercase;font-size:11px;letter-spacing:1px}
  tr:hover{background:#1a1a1a}
  .badge{display:inline-block;padding:3px 10px;border-radius:4px;font-size:11px;text-transform:uppercase;letter-spacing:1px}
  .live{background:#1a4a1a;color:#00ff88;border:1px solid #00ff88}
  .paper{background:#4a3a0a;color:#ffcc00;border:1px solid #ffcc00}
  .footer{text-align:center;color:#555;margin-top:30px;font-size:11px}
</style>
</head>
<body>
<h1>⚡ Trading Imperium V6 <span class="pulse"></span> <span id="mode-badge"></span></h1>

<div class="grid">
  <div class="card">
    <h3>💰 Balance</h3>
    <div id="balance" class="big">Lade...</div>
    <div id="balance-sub" style="color:#666;font-size:11px;margin-top:5px"></div>
  </div>
  <div class="card">
    <h3>📈 Gesamt P&L</h3>
    <div id="pnl" class="big">Lade...</div>
    <div id="pnl-sub" style="color:#666;font-size:11px;margin-top:5px"></div>
  </div>
  <div class="card">
    <h3>🎯 Win-Rate</h3>
    <div id="winrate" class="big">Lade...</div>
    <div id="trades-sub" style="color:#666;font-size:11px;margin-top:5px"></div>
  </div>
  <div class="card">
    <h3>🧠 Strategie</h3>
    <div id="strategy" style="font-size:16px;color:#ffcc00">Lade...</div>
    <div id="regime" style="color:#666;font-size:11px;margin-top:5px"></div>
  </div>
</div>

<div class="card">
  <h3>📊 Offene Positionen</h3>
  <table>
    <thead><tr><th>Coin</th><th>Menge</th><th>Entry</th><th>Aktuell</th><th>P&L %</th><th>Wert</th></tr></thead>
    <tbody id="positions"><tr><td colspan="6" class="neu">Lade...</td></tr></tbody>
  </table>
</div>

<div class="card" style="margin-top:15px">
  <h3>📋 Letzte Trades</h3>
  <table>
    <thead><tr><th>Zeit</th><th>Typ</th><th>Coin</th><th>Preis</th><th>Betrag</th><th>P&L</th><th>Strategie</th></tr></thead>
    <tbody id="trades"><tr><td colspan="7" class="neu">Lade...</td></tr></tbody>
  </table>
</div>

<div class="footer">
  Auto-Refresh alle 5 Sekunden | <span id="last-update">-</span>
</div>

<script>
async function update(){
  try{
    const r = await fetch('/api/status');
    const d = await r.json();

    // Mode Badge
    const mode = d.mode || 'paper';
    document.getElementById('mode-badge').innerHTML =
      `<span class="badge ${mode}">${mode.toUpperCase()}</span>`;

    // Balance
    const bal = (d.balance && d.balance.total) || {};
    const usdc = (bal.USDC || 0) + (bal.USDT || 0);
    document.getElementById('balance').textContent = usdc.toFixed(2) + ' USDC';

    // Coin-Werte zusammenrechnen
    let coinValue = 0;
    const prices = d.prices || {};
    for(const [sym, p] of Object.entries(prices)){
      const asset = sym.split('/')[0];
      const qty = bal[asset] || 0;
      if(qty > 0) coinValue += qty * p;
    }
    if(coinValue > 0){
      document.getElementById('balance-sub').textContent =
        `+ ${coinValue.toFixed(2)}$ in Coins = ${(usdc + coinValue).toFixed(2)}$ gesamt`;
    }

    // P&L
    const st = d.journal_stats || {};
    const pnl = st.total_pnl || 0;
    const pnlEl = document.getElementById('pnl');
    pnlEl.textContent = (pnl >= 0 ? '+' : '') + pnl.toFixed(2) + '$';
    pnlEl.className = 'big ' + (pnl >= 0 ? 'pos' : 'neg');
    document.getElementById('pnl-sub').textContent =
      `${st.total_trades || 0} Trades | ${(st.sells || 0)} Verkäufe`;

    // Win-Rate
    const wr = st.win_rate || 0;
    const wrEl = document.getElementById('winrate');
    wrEl.textContent = wr.toFixed(0) + '%';
    wrEl.className = 'big ' + (wr >= 50 ? 'pos' : wr >= 30 ? 'yellow' : 'neg');
    document.getElementById('trades-sub').textContent =
      `${st.wins || 0} Wins / ${st.losses || 0} Losses`;

    // Strategie
    document.getElementById('strategy').textContent = d.strategy || '-';
    document.getElementById('regime').textContent =
      `Regime: ${d.regime || '-'} | Zyklus: ${d.cycle || '-'} | F&G: ${d.fear_greed || '-'}`;

    // Positionen
    const risk = d.risk || {};
    const pos = risk.open_positions || {};
    let posHtml = '';
    for(const [sym, p] of Object.entries(pos)){
      if(p.active){
        const price = prices[sym] || 0;
        const entry = p.entry_price || 0;
        const qty = p.qty || 0;
        const pnlPct = entry > 0 && price > 0 ? ((price/entry)-1)*100 : 0;
        const value = qty * price;
        const cls = pnlPct >= 0 ? 'pos' : 'neg';
        const coinName = sym.split('/')[0];
        posHtml += `<tr><td><b>${coinName}</b></td><td>${qty.toFixed(6)}</td>` +
                   `<td>${entry.toFixed(2)}$</td><td>${price.toFixed(2)}$</td>` +
                   `<td class="${cls}">${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%</td>` +
                   `<td>${value.toFixed(2)}$</td></tr>`;
      }
    }
    document.getElementById('positions').innerHTML = posHtml ||
      '<tr><td colspan="6" class="neu">Keine offenen Positionen</td></tr>';

    // Trades
    const trades = (d.recent_trades || []).slice().reverse();
    let tradesHtml = '';
    trades.forEach(t => {
      const time = String(t.time || '').slice(11, 19);
      const type = t.type || '?';
      const coin = String(t.coin || '').split('/')[0];
      const price = (t.price || 0).toFixed(2);
      const amount = (t.amount || 0).toFixed(2);
      const pnl = t.pnl;
      const pnlStr = (pnl != null && pnl !== 0 && pnl !== '') ?
        `<span class="${pnl >= 0 ? 'pos' : 'neg'}">${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}$</span>` : '-';
      const strat = String(t.strategy || '').slice(0, 15);
      tradesHtml += `<tr><td>${time}</td><td class="${type === 'BUY' ? 'pos' : 'neg'}">${type}</td>` +
                    `<td><b>${coin}</b></td><td>${price}$</td><td>${amount}$</td>` +
                    `<td>${pnlStr}</td><td class="neu">${strat}</td></tr>`;
    });
    document.getElementById('trades').innerHTML = tradesHtml ||
      '<tr><td colspan="7" class="neu">Noch keine Trades</td></tr>';

    document.getElementById('last-update').textContent = 'Aktualisiert: ' + new Date().toLocaleTimeString();
  } catch(e) {
    console.error('Update error:', e);
    document.getElementById('last-update').textContent = 'Fehler: ' + e.message;
  }
}
update();
setInterval(update, 5000);
</script>
</body>
</html>'''


class WebDashboard:
    """Flask-basiertes Web-Dashboard."""

    def __init__(self, engine, port=5050):
        self.engine = engine
        self.app_ref = engine  # Alias
        self.port = port
        self.running = False

        if not HAS_FLASK:
            return

        self.flask = Flask(__name__)
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        self._setup_routes()

    def _setup_routes(self):
        @self.flask.route('/')
        def index():
            return render_template_string(DASHBOARD_HTML)

        @self.flask.route('/api/status')
        def status():
            try:
                data = self.engine.get_system_status()
                # Prices hinzufuegen fuer P&L-Berechnung
                try:
                    data['prices'] = dict(self.engine.data_agent.price_cache)
                except Exception:
                    data['prices'] = {}
                response = jsonify(data)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.flask.route('/api/trades')
        def trades():
            try:
                data = self.engine.journal.get_all() if hasattr(self.engine, 'journal') else []
                response = jsonify(data)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.flask.route('/api/health')
        def health():
            return jsonify({'status': 'running', 'port': self.port})

    def start(self):
        if not HAS_FLASK:
            print('⚠️ Dashboard nicht gestartet: Flask fehlt')
            return False

        def _run():
            try:
                self.flask.run(host='0.0.0.0', port=self.port,
                              debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                print(f'❌ Dashboard Error: {e}')

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        self.running = True
        print(f'✅ Dashboard: http://localhost:{self.port}')
        return True

    def stop(self):
        self.running = False

    def get_status(self):
        return {'port': self.port, 'running': self.running, 'flask_available': HAS_FLASK}
