"""Waraqah agent swarm — 4 personas chat live with the AI agent at :8123.
Each persona sends its natural questions via POST /agent/chat (SSE), collects
tool events + answer, and evaluates grounding, language, and usefulness.
"""
import json, re, sys, urllib.request

BASE = "http://127.0.0.1:8123"

PERSONAS = [
    {
        "name": "أبو فيصل — مستثمر تقليدي",
        "qs": [
            ("احلل لي سهم أرامكو 2222 — هل يشتري الآن؟", "2222.SR"),
            ("وش توزيعات الراجحي 1120؟", "1120.SR"),
        ],
        "checks": ["arabic_answer", "grounded_numbers", "no_english_jargon"],
    },
    {
        "name": "QuantKhaled — متداول كمي",
        "qs": [
            ("Compare AAPL and MSFT on valuation and give me the numbers.", "AAPL"),
            ("What is the RSI and SMA200 trend for 2222 right now?", "2222.SR"),
        ],
        "checks": ["exact_numbers", "tool_citation"],
    },
    {
        "name": "Nadia — مستخدمة جديدة تعلم الاستثمار",
        "qs": [
            ("What does P/E ratio mean for Apple stock?", "AAPL"),
            ("Is Toyota 7203 a good company? Explain simply.", "7203.T"),
        ],
        "checks": ["educational_tone", "grounded_numbers", "no_false_advice"],
    },
    {
        "name": "Portfolio-Pete — مستثمر محفظة",
        "qs": [
            ("Analyze my portfolio: 100 shares Aramco at 30, 50 shares Jarir at 140. Is it risky?", None),
        ],
        "checks": ["portfolio_math", "concentration_warning", "grounded"],
    },
]

def chat(message, symbol):
    body = {"message": message}
    if symbol: body["symbol"] = symbol
    req = urllib.request.Request(BASE + "/agent/chat",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    events = {}
    answer_text = ""
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            cur_ev, buf = None, []
            for raw in r.read().decode("utf-8", "replace").split("\n"):
                if raw.startswith("event: "):
                    cur_ev = raw[7:].strip()
                elif raw.startswith("data: ") and cur_ev:
                    buf.append(raw[6:])
                elif raw.strip() == "" and cur_ev:
                    try: payload = json.loads("\n".join(buf))
                    except Exception: payload = {"_raw": "\n".join(buf)}
                    if cur_ev == "answer" and isinstance(payload.get("text") or payload.get("content") or "", str):
                        answer_text += payload.get("text") or payload.get("content") or ""
                    events.setdefault(cur_ev, []).append(payload)
                    cur_ev, buf = None, []
    except Exception as e:
        return {"error": str(e)[:200], "events": events, "answer": ""}
    return {"events": events, "answer": answer_text}

def flatten_numbers(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (int, float)) and k in {"price","pe","roe","div_yield","payout","rsi14","market_cap","maxdd_2y"}:
                out.append((k, float(v)))
            else: flatten_numbers(v, out)
    elif isinstance(obj, list):
        for i in obj: flatten_numbers(i, out)

results = []
for persona in PERSONAS:
    print("=" * 55)
    print("PERSONA:", persona["name"])
    for q, sym in persona["qs"]:
        print(f"  Q: {q[:60]}...")
        r = chat(q, sym)
        if r.get("error"):
            print("    ERROR:", r["error"])
            results.append({"persona": persona["name"], "q": q, "verdict": "ERROR", "err": r["error"]})
            continue
        ev = r["events"]
        tool_results = ev.get("tool_result", [])
        nums = []
        for tr in tool_results:
            flatten_numbers(tr, nums)
        answer = r["answer"] or str(ev.get("answer", ""))[:400]
        # grounding: numbers in answer trace to tool payload
        grounded_hits = 0
        for k, v in nums:
            if v != 0 and (f"{v:.2f}" in answer or f"{v:.1f}" in answer or f"{v:.4f}" in answer or f"{int(v)}" in answer):
                grounded_hits += 1
        tools_used = [tc.get("tool") or tc.get("name") for tc in ev.get("tool_call", []) if isinstance(tc, dict)]
        has_conf = any("confidence" in json.dumps(tr) for tr in tool_results) or "confidence" in answer
        is_ar = bool(re.search(r"[\u0600-\u06FF]", answer))
        verdict = {
            "q": q[:50], "tools": tools_used, "tool_results": len(tool_results),
            "grounded_hits": grounded_hits, "arabic": is_ar,
            "answer_head": answer[:160].replace("\n", " "),
        }
        print(f"    tools={tools_used} results={len(tool_results)} grounded_hits={grounded_hits} arabic={is_ar}")
        print(f"    answer: {verdict['answer_head'][:120]}")
        results.append({"persona": persona["name"], **verdict})

print()
print("=" * 55)
print("SUMMARY")
ok = sum(1 for r in results if r.get("verdict") != "ERROR" and r.get("tool_results", 0) > 0)
print(f"queries: {len(results)} | with tool grounding: {ok}")
for r in results:
    print(f"- [{r.get('verdict','OK') if r.get('verdict') else 'OK'}] {r['persona'][:18]} | {r['q'][:38]} | tools={r.get('tools')} grounded={r.get('grounded_hits')}")
json.dump(results, open(r"C:/Users/Hamad/waraqah-build/agent_swarm_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved: agent_swarm_results.json")
