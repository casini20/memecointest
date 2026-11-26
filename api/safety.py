"""Token safety from RugCheck (free, no key). /api/safety?mint=<address>
Optional: set SOLANA_RPC_URL (for example a free Helius endpoint) in Vercel to turn on dev-wallet age."""
import json, os, re, time, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler

def f(x, d=0.0):
    try: return float(x)
    except (TypeError, ValueError): return d

def reply(h, code, obj, cache):
    b = json.dumps(obj).encode()
    h.send_response(code); h.send_header("Content-Type", "application/json")
    h.send_header("Cache-Control", cache if code == 200 else "no-store")
    h.send_header("Content-Length", str(len(b))); h.end_headers(); h.wfile.write(b)

def dev_age(creator):
    """Age in days of the creator wallet's oldest transaction in its last 1000 (a lower bound). None if no RPC set."""
    url = os.environ.get("SOLANA_RPC_URL")
    if not url or not creator: return None
    try:
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": [creator, {"limit": 1000}]}).encode()
        r = json.load(urllib.request.urlopen(urllib.request.Request(url, body, {"content-type": "application/json"}), timeout=5))
        t = [s["blockTime"] for s in r.get("result") or [] if s.get("blockTime")]
        return round((time.time() - min(t)) / 86400, 1) if t else None
    except Exception:
        return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        mint = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("mint", [""])[0]
        if not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", mint):
            return reply(self, 400, {"error": "bad mint"}, "")
        try:
            req = urllib.request.Request("https://api.rugcheck.xyz/v1/tokens/%s/report" % mint,
                                         headers={"accept": "application/json", "user-agent": "agent-desk"})
            rep = json.load(urllib.request.urlopen(req, timeout=8))
            vaults, locked = set(), []                    # pool vaults are not real holders
            for m in rep.get("markets") or []:
                vaults |= {m.get("pubkey"), m.get("liquidityA"), m.get("liquidityB")}
                if (m.get("lp") or {}).get("lpLockedPct") is not None: locked.append(f(m["lp"]["lpLockedPct"]))
            vaults.discard(None)
            hold = [h for h in rep.get("topHolders") or [] if h.get("address") not in vaults and h.get("owner") not in vaults]
            sup, risks = f((rep.get("token") or {}).get("supply")), rep.get("risks") or []
            reply(self, 200, {"mint": rep.get("mintAuthority") is None and rep.get("freezeAuthority") is None,
                "honey": bool(rep.get("rugged")),
                "devPct": round(f(rep.get("creatorBalance")) / sup * 100, 2) if sup else 0.0,
                "top10": round(sum(f(h.get("pct")) for h in hold[:10]), 1),
                "insPct": round(sum(f(h.get("pct")) for h in hold if h.get("insider")), 1),   # supply held by wallets RugCheck marks as insiders
                "ins": int(f(rep.get("graphInsidersDetected"))),
                "lp": max(locked) if locked else None,                                         # % of LP locked or burned (best market)
                "dng": [str(r.get("name"))[:50] for r in risks if str(r.get("level")).lower() == "danger"][:3],
                "devAge": dev_age(rep.get("creator")),
                "risks": [{"n": str(r.get("name"))[:60], "l": str(r.get("level"))[:12]} for r in risks[:6]]}, "s-maxage=300")
        except Exception as e:
            reply(self, 502, {"error": str(e)}, "")
