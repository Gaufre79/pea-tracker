#!/usr/bin/env python3
"""Suivi PEA : serveur local. Lancer avec `python3 server.py` (aucune dépendance)."""
import json, os, re, ssl, uuid, threading, webbrowser, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HOST, PORT = "127.0.0.1", 8765
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "data.json")
LOCK = threading.Lock()
try:  # certificats de certifi si disponible (corrige l'erreur SSL fréquente sur Mac)
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    CTX = None


def load():
    try:
        with open(DB, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"positions": [], "prices": {}, "updated": None, "errors": []}


def save(d):
    tmp = DB + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DB)


def fetch_price(ticker, since=None):
    now = datetime.now(timezone.utc)
    if since:
        start = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc) - timedelta(days=7)
    else:
        start = now - timedelta(days=365)
    q = urllib.parse.quote(ticker)
    period = "?period1=%d&period2=%d&interval=1d" % (start.timestamp(), now.timestamp() + 86400)
    urls = [f"https://query1.finance.yahoo.com/v8/finance/chart/{q}{period}",
            f"https://query2.finance.yahoo.com/v8/finance/chart/{q}{period}",
            f"https://query1.finance.yahoo.com/v8/finance/chart/{q}?range=max&interval=1d"]
    last = None
    for url in urls:  # plusieurs tentatives : Yahoo refuse parfois une requête
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
                res = json.load(r)["chart"]["result"][0]
            meta = res["meta"]
            closes = res["indicators"]["quote"][0]["close"]
            hist = [[datetime.fromtimestamp(t, timezone.utc).date().isoformat(), round(c, 4)]
                    for t, c in zip(res.get("timestamp") or [], closes) if c is not None]
            price = meta.get("regularMarketPrice") or (hist[-1][1] if hist else None)
            return {"price": float(price), "currency": meta.get("currency", "EUR")}, hist
        except Exception as e:
            last = e
    raise last


def refresh(d, only=None):
    tickers = {p["ticker"] for p in d["positions"]} if only is None else {only}
    errors = [e for e in d.get("errors", []) if e not in tickers]
    details = {}
    for t in tickers:
        try:
            dates = [p["date"] for p in d["positions"] if p["ticker"] == t and p.get("date")]
            d["prices"][t], hist = fetch_price(t, min(dates) if dates else None)
            d.setdefault("history", {})[t] = hist
        except Exception as e:
            errors.append(t)
            details[t] = f"{type(e).__name__}: {e}"
            print(f"[cours] {t} : {details[t]}")
    d["errors"] = errors
    d["error_details"] = {**{k: v for k, v in d.get("error_details", {}).items() if k in errors and k not in tickers}, **details}
    if only is None:
        d["updated"] = datetime.now().isoformat(timespec="minutes")
    save(d)


def current():
    """Données à jour : actualise les cours au premier accès de la journée."""
    d = load()
    today = datetime.now().date().isoformat()
    missing = any(p["ticker"] not in d.get("history", {}) for p in d["positions"])
    if d["positions"] and ((d["updated"] or "")[:10] != today or missing):
        refresh(d)
    return d


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/data":
            with LOCK:
                return self.send_json(current())
        if self.path in ("/", "/index.html"):
            with open(os.path.join(BASE, "index.html"), "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        self.send_json({"error": "introuvable"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self.send_json({"error": "JSON invalide"}, 400)
        with LOCK:
            d = load()
            if self.path == "/api/refresh":
                refresh(d)
                return self.send_json(d)
            if self.path == "/api/positions":
                try:
                    p = {
                        "id": uuid.uuid4().hex[:10],
                        "name": str(data["name"]).strip()[:80],
                        "ticker": str(data["ticker"]).strip().upper(),
                        "qty": float(data["qty"]),
                        "buy": float(data["buy"]),
                        "fees": float(data.get("fees") or 0),
                        "date": str(data.get("date") or ""),
                    }
                    assert p["name"] and re.fullmatch(r"[A-Z0-9.\-^=]{1,20}", p["ticker"])
                    assert p["qty"] > 0 and p["buy"] > 0 and p["fees"] >= 0
                except Exception:
                    return self.send_json({"error": "Champs invalides"}, 400)
                d["positions"].append(p)
                refresh(d, only=p["ticker"])
                return self.send_json(d)
        self.send_json({"error": "introuvable"}, 404)

    def do_DELETE(self):
        m = re.fullmatch(r"/api/positions/([0-9a-f]+)", self.path)
        if not m:
            return self.send_json({"error": "introuvable"}, 404)
        with LOCK:
            d = load()
            d["positions"] = [p for p in d["positions"] if p["id"] != m.group(1)]
            used = {p["ticker"] for p in d["positions"]}
            d["prices"] = {t: v for t, v in d["prices"].items() if t in used}
            d["history"] = {t: v for t, v in d.get("history", {}).items() if t in used}
            save(d)
            self.send_json(d)


if __name__ == "__main__":
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"Suivi PEA disponible sur {url}  (Ctrl+C pour arrêter)")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
