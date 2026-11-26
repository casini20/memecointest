"""Market details for one token from DexScreener (free, no key). /api/coin?mint=<address>"""
import json, re, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler

def reply(h, code, obj, cache):
    b = json.dumps(obj).encode()
    h.send_response(code); h.send_header("Content-Type", "application/json")
    h.send_header("Cache-Control", cache if code == 200 else "no-store")
    h.send_header("Content-Length", str(len(b))); h.end_headers(); h.wfile.write(b)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        mint = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("mint", [""])[0]
        if not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", mint):
            return reply(self, 400, {"error": "bad mint"}, "")
        try:
            req = urllib.request.Request("https://api.dexscreener.com/latest/dex/tokens/" + mint,
                                         headers={"accept": "application/json", "user-agent": "agent-desk"})
            pairs = [p for p in json.load(urllib.request.urlopen(req, timeout=8)).get("pairs") or [] if p.get("chainId") == "solana"]
            if not pairs: return reply(self, 200, {}, "s-maxage=2")
            p = max(pairs, key=lambda x: float((x.get("liquidity") or {}).get("usd") or 0))
            reply(self, 200, {"px": float(p.get("priceUsd") or 0), "mc": p.get("marketCap"), "fdv": p.get("fdv"),
                "liq": (p.get("liquidity") or {}).get("usd"), "vol": p.get("volume"), "chg": p.get("priceChange"),
                "tx": p.get("txns"), "created": p.get("pairCreatedAt"), "dex": p.get("dexId"),
                "url": p.get("url") if str(p.get("url", "")).startswith("https://dexscreener.com/") else None}, "s-maxage=2")
        except Exception as e:
            reply(self, 502, {"error": str(e)}, "")