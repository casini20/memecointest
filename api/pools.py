"""New Solana pools from GeckoTerminal (free, no key). Edge-cached for 60s so every visitor shares one upstream call."""
import json, re, urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler

GT = "https://api.geckoterminal.com/api/v2/networks/solana/new_pools?page=1"

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
            req = urllib.request.Request(GT, headers={"accept": "application/json", "user-agent": "agent-desk"})
            out = []
            for p in json.load(urllib.request.urlopen(req, timeout=8)).get("data", []):
                at = p["attributes"]; v = at.get("volume_usd") or {}; tx = (at.get("transactions") or {}).get("m5") or {}
                v1 = f(v.get("h1"))
                out.append({"id": p["id"], "sym": "$" + (re.sub(r"[^A-Za-z0-9_.-]", "", at["name"].split(" / ")[0])[:10].upper() or "COIN"),
                    "addr": p["relationships"]["base_token"]["data"]["id"].split("_", 1)[1],
                    "created": datetime.fromisoformat(at["pool_created_at"].replace("Z", "+00:00")).timestamp(),
                    "liq": f(at.get("reserve_in_usd")), "vol": round(f(v.get("m5")) / (v1 / 12), 2) if v1 > 0 else 0,
                    "buys": f(tx.get("buys")), "sells": f(tx.get("sells")), "buyers": f(tx.get("buyers"))})
            reply(self, 200, {"pools": out}, "s-maxage=60, stale-while-revalidate=120")
        except Exception as e:
            reply(self, 502, {"error": str(e)}, "")