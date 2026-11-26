"""Fast lane for new coins: DexScreener latest token profiles + latest boosts, then pair data.
Edge-cached for 5s, so every visitor shares the same upstream calls (about 12 per minute)."""
import json, re, time, urllib.request
from http.server import BaseHTTPRequestHandler

B = "https://api.dexscreener.com"
OK = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")
H = {"accept": "application/json", "user-agent": "agent-desk"}

def jget(path):
    return json.load(urllib.request.urlopen(urllib.request.Request(B + path, headers=H), timeout=6))

def f(x, d=0.0):
    try: return float(x)
    except (TypeError, ValueError): return d

def reply(h, code, obj, cache):
    b = json.dumps(obj).encode()
    h.send_response(code); h.send_header("Content-Type", "application/json")
    h.send_header("Cache-Control", cache if code == 200 else "no-store")
    h.send_header("Content-Length", str(len(b))); h.end_headers(); h.wfile.write(b)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            addrs = []
            for path in ("/token-profiles/latest/v1", "/token-boosts/latest/v1"):
                try:                                   # one feed failing must not break the other
                    for t in jget(path):
                        a = t.get("tokenAddress", "")
                        if t.get("chainId") == "solana" and OK.fullmatch(a) and a not in addrs: addrs.append(a)
                except Exception: pass
            best = {}
            if addrs:
                for p in jget("/latest/dex/tokens/" + ",".join(addrs[:30])).get("pairs") or []:
                    a = (p.get("baseToken") or {}).get("address")
                    liq = f((p.get("liquidity") or {}).get("usd"))
                    if p.get("chainId") == "solana" and a in addrs and (a not in best or liq > f((best[a].get("liquidity") or {}).get("usd"))):
                        best[a] = p
            out, now = [], time.time()
            for a, p in best.items():
                created = f(p.get("pairCreatedAt")) / 1000
                if not created or now - created > 7200: continue
                v = p.get("volume") or {}; tx = (p.get("txns") or {}).get("m5") or {}; v1 = f(v.get("h1"))
                name = re.sub(r"[^A-Za-z0-9_.-]", "", (p.get("baseToken") or {}).get("symbol", ""))[:10].upper() or "COIN"
                out.append({"id": "ds_" + a, "sym": "$" + name, "addr": a, "created": created,
                    "liq": f((p.get("liquidity") or {}).get("usd")),
                    "vol": round(f(v.get("m5")) / (v1 / 12), 2) if v1 > 0 else 0,
                    "buys": f(tx.get("buys")), "sells": f(tx.get("sells")),
                    "buyers": f(tx.get("buys"))})      # DexScreener has no unique-buyer count, so buy count stands in
            reply(self, 200, {"pools": out}, "s-maxage=5, stale-while-revalidate=10")
        except Exception as e:
            reply(self, 502, {"error": str(e)}, "")