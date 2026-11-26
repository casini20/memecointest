"""Token safety from RugCheck (free, no key). /api/safety?mint=<address>"""
import json, re, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler

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
        mint = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("mint", [""])[0]
        if not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", mint):
            return reply(self, 400, {"error": "bad mint"}, "")
        try:
            req = urllib.request.Request("https://api.rugcheck.xyz/v1/tokens/%s/report" % mint,
                                         headers={"accept": "application/json", "user-agent": "agent-desk"})
            rep = json.load(urllib.request.urlopen(req, timeout=8))
            lp = set()                                    # exclude pool vaults from holder concentration
            for m in rep.get("markets") or []:
                lp |= {m.get("pubkey"), m.get("liquidityA"), m.get("liquidityB")}
            lp.discard(None)
            hold = [h for h in rep.get("topHolders") or [] if h.get("address") not in lp and h.get("owner") not in lp]
            sup = f((rep.get("token") or {}).get("supply"))
            reply(self, 200, {"mint": rep.get("mintAuthority") is None and rep.get("freezeAuthority") is None,
                "honey": bool(rep.get("rugged")),
                "devPct": round(f(rep.get("creatorBalance")) / sup * 100, 2) if sup else 0.0,
                "top10": round(sum(f(h.get("pct")) for h in hold[:10]), 1),
                "risks": [{"n": str(r.get("name"))[:60], "l": str(r.get("level"))[:12]} for r in (rep.get("risks") or [])[:6]]}, "s-maxage=300")
        except Exception as e:
            reply(self, 502, {"error": str(e)}, "")