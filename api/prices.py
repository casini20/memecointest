"""Live prices from DexScreener (free, no key). /api/prices?a=<mint>,<mint>  (max 30)"""
import json, re, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler

def reply(h, code, obj, cache):
    b = json.dumps(obj).encode()
    h.send_response(code); h.send_header("Content-Type", "application/json")
    h.send_header("Cache-Control", cache if code == 200 else "no-store")
    h.send_header("Content-Length", str(len(b))); h.end_headers(); h.wfile.write(b)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("a", [""])[0]
        addrs = [a for a in q.split(",") if re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", a)][:30]
        if not addrs: return reply(self, 200, {}, "s-maxage=2")
        try:
            req = urllib.request.Request("https://api.dexscreener.com/latest/dex/tokens/" + ",".join(addrs),
                                         headers={"accept": "application/json", "user-agent": "agent-desk"})
            best = {}
            for p in json.load(urllib.request.urlopen(req, timeout=8)).get("pairs") or []:
                if p.get("chainId") != "solana": continue
                a = p["baseToken"]["address"]
                liq = float((p.get("liquidity") or {}).get("usd") or 0); px = float(p.get("priceUsd") or 0)
                if px > 0 and (a not in best or liq > best[a][1]): best[a] = (px, liq)
            reply(self, 200, {a: v[0] for a, v in best.items()}, "s-maxage=2")
        except Exception as e:
            reply(self, 502, {"error": str(e)}, "")