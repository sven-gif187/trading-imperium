"""TradingView Webhook Server (Flask-basiert) - STILLGELEGT seit 13.08.2026.

=======================================================================
DIESES MODUL WIRD NICHT MEHR GESTARTET.
=======================================================================

Es ist in app.py nicht mehr importiert und nicht mehr verdrahtet
(dort steht self.webhook = None). Die Datei bleibt liegen, damit der
Code nicht verloren geht - sie tut aber nichts mehr.

WARUM STILLGELEGT (GEFUNDENE-PROBLEME #14, 13.08.2026)
------------------------------------------------------
1. start() band den Server auf host='0.0.0.0' - also auf ALLE
   Netzwerkschnittstellen. Port 5051 war damit von jedem Geraet im
   Heimnetz erreichbar, nicht nur vom eigenen Rechner. Dafuer brauchte
   es keine Router-Freigabe; die reichte nur noch weiter ins Internet.
2. Es gab KEINE Authentifizierung: kein Token, kein Passwort, keine
   IP-Beschraenkung. Ein einziger POST auf /webhook erzeugte einen
   echten Kaufwunsch.
3. Die Signalguete war frei erfunden - confidence=0.85 und score=7
   standen fest im Code, unabhaengig davon, was tatsaechlich geschickt
   wurde.
4. Sven benutzt TradingView nicht. Ein Kaufweg, den niemand braucht,
   ist reine Angriffsflaeche.
5. Waehrend des Messfensters haette jedes Signal von hier als
   strategy_id='TRADINGVIEW' in die Auswertung gezaehlt und die
   Messung verunreinigt.

Immerhin korrekt: der Weg lief ueber bus.publish(EVENT_SIGNAL) und
damit DURCH die Risikopruefung - anders als der manuelle Kauf im
Cockpit, der direkt execution.execute() aufrief.

WIEDER EINSCHALTEN - was vorher repariert werden MUSS
-----------------------------------------------------
a) host='0.0.0.0' -> host='127.0.0.1' in start().
b) Ein Token aus der .env pruefen; ohne gueltiges Token 401 antworten.
c) confidence/score nicht mehr fest verdrahten, sondern aus dem
   Signal ableiten oder bewusst neutral setzen.
d) self._received waechst unbegrenzt (Speicherleck) - begrenzen.
e) Danach in app.py wieder importieren, instanziieren und starten.

Empfaengt Signale von TradingView Alerts und leitet sie an den Bot weiter.
"""
import threading
import json
import logging

try:
    from flask import Flask, request, jsonify
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    print("⚠️ Flask nicht installiert. Webhook deaktiviert. Installiere mit: pip install flask")


class WebhookServer:
    """Flask-basierter Webhook Server fuer TradingView Alerts.

    TradingView Alert Message (JSON Format):
        {"action": "BUY", "ticker": "{{ticker}}", "price": {{close}}}
    """

    def __init__(self, app, port=5051):
        self.app_ref = app
        self.port = port
        self._received = []
        self.running = False

        if not HAS_FLASK:
            return

        self.flask = Flask(__name__)
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        self._setup_routes()

    def _setup_routes(self):
        @self.flask.route('/webhook', methods=['POST'])
        def webhook():
            try:
                data = request.get_json(force=True, silent=True)
                if not data:
                    try:
                        data = json.loads(request.data.decode('utf-8'))
                    except Exception:
                        data = {}

                self._received.append(data)
                action = str(data.get('action', data.get('signal', ''))).upper()
                symbol = str(data.get('ticker', data.get('symbol', 'BTCUSDC')))
                price = float(data.get('price', 0) or 0)

                if '/' not in symbol:
                    if symbol.endswith('USDC'):
                        symbol = symbol[:-4] + '/USDC'
                    elif symbol.endswith('USDT'):
                        symbol = symbol[:-4] + '/USDT'

                ok = self._process_signal(action, symbol, price, data)
                return jsonify({'status': 'ok' if ok else 'ignored',
                                'action': action, 'symbol': symbol, 'price': price}), 200
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 400

        @self.flask.route('/health', methods=['GET'])
        def health():
            return jsonify({'status': 'running', 'port': self.port,
                            'received': len(self._received)}), 200

        @self.flask.route('/', methods=['GET'])
        def index():
            html = ('<html><head><title>Trading Imperium V6 - Webhook</title>'
                    '<style>body{background:#0a0a0a;color:#00ff88;font-family:monospace;padding:40px;text-align:center}'
                    'h1{color:#ffcc00}code{background:#111;padding:15px;display:block;max-width:500px;margin:20px auto;text-align:left;border-radius:8px;border:1px solid #333}'
                    '.pulse{display:inline-block;width:12px;height:12px;background:#00ff88;border-radius:50%;animation:p 1.5s infinite}'
                    '@keyframes p{0%{opacity:1}50%{opacity:.3}100%{opacity:1}}</style></head>'
                    '<body><h1>⚡ TradingView Webhook <span class="pulse"></span> LIVE</h1>'
                    '<p>Empfange Signale an: <b>POST /webhook</b></p>'
                    '<code>TradingView Alert Message:<br><br>'
                    '{"action": "BUY", "ticker": "{{ticker}}", "price": {{close}}}<br><br>'
                    '{"action": "SELL", "ticker": "{{ticker}}", "price": {{close}}}</code>'
                    f'<p>Empfangen: {len(self._received)} Signale</p>'
                    f'<p style="color:#888;font-size:12px">Webhook URL (TradingView Alert):<br>'
                    f'http://DEINE-IP:{self.port}/webhook</p></body></html>')
            return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

    def _process_signal(self, action, symbol, price, raw_data):
        try:
            from core.events import DecisionIntent, Side, EVENT_SIGNAL

            if price <= 0:
                price = self.app_ref.data_agent.price_cache.get(symbol, 0)
            if price <= 0:
                print(f'[WEBHOOK] Kein Preis fuer {symbol}')
                return False

            if action in ('BUY', 'LONG'):
                balance = self.app_ref.execution.get_balance()
                usdc = balance['total'].get('USDC', 0) + balance['total'].get('USDT', 0)
                pos_pct = self.app_ref.config.trading.position_size_pct or 10
                amount = usdc * pos_pct / 100

                if amount < 5:
                    print(f'[WEBHOOK] BUY abgelehnt: Balance zu klein ({amount:.2f}$)')
                    return False

                intent = DecisionIntent(
                    symbol=symbol, side=Side.BUY, confidence=0.85,
                    entry_price=price, amount_usd=amount,
                    stop_loss=price * (1 - self.app_ref.config.risk.stop_loss_pct / 100),
                    trailing_stop_pct=self.app_ref.config.risk.trailing_stop_pct,
                    strategy_id='TRADINGVIEW', strategy_name='TradingView Webhook',
                    entry_reason=f'TradingView Signal: {action}', score=7,
                    agent_id='webhook')
                self.app_ref.bus.publish(EVENT_SIGNAL, intent, source='webhook')
                print(f'[WEBHOOK] BUY {symbol} @ {price:.2f}$ ({amount:.2f}$)')
                return True

            elif action in ('SELL', 'SHORT', 'CLOSE'):
                if symbol in self.app_ref.risk_engine.open_positions:
                    pos = self.app_ref.risk_engine.open_positions[symbol]
                    if pos.get('active'):
                        intent = DecisionIntent(
                            symbol=symbol, side=Side.SELL, confidence=0.9,
                            entry_price=price, quantity=pos.get('qty', 0),
                            strategy_id='TRADINGVIEW', strategy_name='TradingView Webhook',
                            entry_reason=f'TradingView Signal: {action}', score=7,
                            agent_id='webhook')
                        self.app_ref.bus.publish(EVENT_SIGNAL, intent, source='webhook')
                        print(f'[WEBHOOK] SELL {symbol} @ {price:.2f}$')
                        return True
                print(f'[WEBHOOK] SELL abgelehnt: Keine offene Position in {symbol}')
                return False

            print(f'[WEBHOOK] Unbekannte Action: {action}')
            return False

        except Exception as e:
            print(f'[WEBHOOK] Signal Error: {e}')
            return False

    def start(self):
        if not HAS_FLASK:
            print('⚠️ Webhook nicht gestartet: Flask fehlt')
            return False

        def _run():
            try:
                self.flask.run(host='0.0.0.0', port=self.port,
                              debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                print(f'❌ Webhook Error: {e}')

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        self.running = True
        print(f'✅ Webhook: http://localhost:{self.port}/webhook')
        return True

    def stop(self):
        self.running = False

    def get_status(self):
        return {'port': self.port, 'received': len(self._received),
                'running': self.running, 'flask_available': HAS_FLASK}
