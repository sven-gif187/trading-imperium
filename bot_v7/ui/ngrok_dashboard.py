"""
Trading Imperium V7 - ngrok Public Dashboard
Erstellt einen oeffentlichen Tunnel zum lokalen Dashboard.
Liest Auth-Token aus config.json oder .env Datei.

GRACEFUL FAILURE: Bot laeuft auch ohne ngrok problemlos.
- Ohne pyngrok: Warnung, kein Crash
- Ohne Token: Warnung, kein Crash
- Bei Fehler: Komplette Fehlermeldung, kein Crash
"""
import os
import threading
from core.logger import log

try:
    from pyngrok import ngrok, conf
    HAS_NGROK = True
except ImportError:
    HAS_NGROK = False
    ngrok = None
    conf = None


def _load_token_from_env():
    """Liest NGROK_AUTHTOKEN aus .env-Datei oder Umgebungsvariable."""
    # 1. Umgebungsvariable
    token = os.environ.get("NGROK_AUTHTOKEN", "").strip()
    if token:
        return token

    # 2. .env-Datei
    env_paths = [".env", "config/.env", os.path.expanduser("~/.ngrok2/ngrok.env")]
    for path in env_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("NGROK_AUTHTOKEN="):
                            return line.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception:
                pass

    return ""


class NgrokDashboard:
    """Startet ngrok-Tunnel zum lokalen Dashboard.
    Graceful Failure: Bot laeuft IMMER, auch wenn ngrok fehlschlaegt.
    """

    # [25.09.2026, Befund 111] Vorgabe 5050 -> 5070, siehe ui/dashboard.py.
    def __init__(self, local_port=5070, auth_token=None, config=None):
        self.local_port = local_port
        self.public_url = None
        self.tunnel = None
        self.last_error = ""
        self.auth_token = auth_token or ""
        self.config = config

        # Token aus mehreren Quellen versuchen zu finden
        if not self.auth_token and config is not None:
            # Aus AppConfig (falls hinterlegt)
            self.auth_token = getattr(getattr(config, "dashboard", None), "ngrok_token", "") or ""

        if not self.auth_token:
            self.auth_token = _load_token_from_env()

    def start(self) -> str:
        """Startet ngrok-Tunnel. Gibt oeffentliche URL zurueck oder leeren String.
        Crasht NIE - failed gracefully.
        """
        # 1. pyngrok Library check
        if not HAS_NGROK:
            log.info("NGROK", "Deaktiviert - pyngrok nicht installiert (pip install pyngrok)")
            # [25.09.2026] Hier stand die 5050 fest im Text. Eine Logzeile,
            # die einen falschen Anschluss nennt, schickt einen auf den
            # Bot des anderen Ordners - siehe Befund 111.
            log.info("NGROK", "  -> Bot laeuft normal weiter, nur lokaler "
                              "Zugriff (localhost:%d)" % self.local_port)
            self.last_error = "pyngrok not installed"
            return ""

        # 2. Auth-Token check
        if not self.auth_token:
            log.warn("NGROK", "Deaktiviert - Kein Auth-Token gefunden")
            log.info("NGROK", "  -> Token holen: https://dashboard.ngrok.com/get-started/your-authtoken")
            log.info("NGROK", "  -> In .env Datei eintragen: NGROK_AUTHTOKEN=dein_token")
            log.info("NGROK", "  -> Bot laeuft normal weiter, nur lokaler Zugriff")
            self.last_error = "No auth token"
            return ""

        # 3. Token setzen + Tunnel starten
        try:
            ngrok.set_auth_token(self.auth_token)
            self.tunnel = ngrok.connect(self.local_port, "http")
            self.public_url = self.tunnel.public_url
            log.info("NGROK", f"✅ Dashboard oeffentlich: {self.public_url}")
            self.last_error = ""
            return self.public_url
        except Exception as e:
            # Vollstaendige Fehlermeldung loggen, NICHT abschneiden
            error_msg = str(e)
            self.last_error = error_msg

            if "ERR_NGROK_4018" in error_msg or "authentication" in error_msg.lower():
                log.warn("NGROK", "Auth-Token ungueltig oder abgelaufen!")
                log.info("NGROK", "  -> Token erneuern: https://dashboard.ngrok.com/get-started/your-authtoken")
            elif "ERR_NGROK_3200" in error_msg or "tunnel limit" in error_msg.lower():
                log.warn("NGROK", "ngrok Limit erreicht (kostenlose Version: max 1 Tunnel)")
            elif "ERR_NGROK_8012" in error_msg:
                log.warn("NGROK", "Region-Fehler - probiere andere Region (eu/us)")
            else:
                log.warn("NGROK", f"Fehler: {error_msg[:300]}")

            log.info("NGROK", "  -> Bot laeuft normal weiter (lokaler Zugriff funktioniert)")
            return ""

    def stop(self):
        """Stoppt den Tunnel sicher."""
        if self.tunnel and HAS_NGROK:
            try:
                ngrok.disconnect(self.tunnel.public_url)
                ngrok.kill()  # Komplett aufraeumen
            except Exception as e:
                log.warn("NGROK", f"Stop-Fehler: {str(e)[:100]}")
        self.public_url = None
        self.tunnel = None

    def get_status(self):
        return {
            "active": self.public_url is not None,
            "url": self.public_url or "",
            "available": HAS_NGROK,
            "has_token": bool(self.auth_token),
            "last_error": self.last_error,
        }

    def set_token(self, token: str):
        """Setzt das Auth-Token zur Laufzeit (z.B. aus UI)."""
        self.auth_token = token.strip()
        if self.auth_token:
            log.info("NGROK", "Token gesetzt - Restart noetig fuer neuen Tunnel")
