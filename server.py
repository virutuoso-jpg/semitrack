"""
SEMI.TRACK 대시보드 로컬 서버
- clients/의 각 API 클라이언트를 호출하거나 data/의 최신 스냅샷을 읽어
  frontend/index.html에서 fetch로 가져다 쓸 수 있게 JSON으로 내려준다.

실행: python server.py  →  http://localhost:5000
"""

import glob
import json
import os

from flask import Flask, jsonify, request, send_from_directory

from clients import dart_client, export_stats_client, hyperscaler_capex, krx_investor, market_reference
from scheduler import jobs as scheduler_jobs

app = Flask(__name__, static_folder="frontend", static_url_path="")

# 무료 호스팅은 재배포/재시작마다 저장 파일이 초기화되므로,
# 서버가 뜰 때 한 번 즉시 수집하고 이후 주기적으로 백그라운드에서 갱신한다.
scheduler_jobs.start_background()

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

TICKERS = {"삼성전자": "005930", "SK하이닉스": "000660"}


def _latest_snapshot(prefix: str) -> dict | None:
    files = sorted(glob.glob(os.path.join(DATA_DIR, f"{prefix}_*.json")))
    if not files:
        return None
    with open(files[-1], "r", encoding="utf-8") as f:
        return json.load(f)


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/foreign-investor")
def foreign_investor():
    stock = request.args.get("stock", "삼성전자")
    snapshot = _latest_snapshot("foreign_investor")
    if not snapshot or stock not in snapshot:
        return jsonify({"error": "저장된 스냅샷이 없습니다. scheduler/jobs.py의 update_foreign_investor()를 먼저 실행하세요."}), 404

    data = snapshot[stock]
    dates = sorted(data.get("close", {}).keys())
    parsed = [
        {
            "date": d,
            "close": _to_float(data["close"].get(d)),
            "foreign_net_qty": _to_float(data["foreign_net_value"].get(d)),
            "institution_net_qty": _to_float(data["institution_net_value"].get(d)),
        }
        for d in dates
    ]
    return jsonify(parsed)


@app.route("/api/institution-flow")
def institution_flow():
    stock = request.args.get("stock", "삼성전자")
    snapshot = _latest_snapshot("institution_flow")
    if not snapshot or stock not in snapshot:
        return jsonify({"error": "저장된 스냅샷이 없습니다. scheduler/jobs.py의 update_institution_flow()를 먼저 실행하세요."}), 404
    return jsonify(snapshot[stock])


@app.route("/api/quarterly-financials")
def quarterly_financials():
    stock = request.args.get("stock", "삼성전자")
    year = int(request.args.get("year", 2026))
    quarter = int(request.args.get("quarter", 1))
    try:
        result = dart_client.get_quarterly_financials(stock, year, quarter)
    except Exception as e:
        app.logger.error(f"DART 조회 실패: {e}")
        return jsonify({"error": "DART 조회 실패"}), 502

    items = result.get("list") or []
    picked = {}
    for item in items:
        if item.get("sj_div") in ("IS", "CIS") and item.get("account_nm") in ("매출액", "영업이익"):
            picked[item["account_nm"]] = _to_float(item.get("thstrm_amount"))

    if not picked:
        return jsonify({"error": result.get("message", "해당 분기 재무 데이터를 찾지 못했습니다.")}), 404

    return jsonify(
        {
            "stock": stock,
            "year": year,
            "quarter": quarter,
            "revenue": picked.get("매출액", 0),
            "operating_profit": picked.get("영업이익", 0),
        }
    )


@app.route("/api/export-stats")
def export_stats():
    hs_code = request.args.get("hs_code", export_stats_client.HS_CODES["메모리반도체"])
    cnty_cd = request.args.get("cnty_cd", "US")
    strt = request.args.get("strt_yymm", "202605")
    end = request.args.get("end_yymm", "202607")
    try:
        result = export_stats_client.get_trade_stats(hs_code, strt, end, cnty_cd)
    except Exception as e:
        app.logger.error(f"관세청 API 조회 실패: {e}")
        return jsonify({"error": "관세청 API 조회 실패"}), 502

    header = result.get("header", {})
    if header.get("resultCode") != "00":
        return jsonify({"error": header.get("resultMsg", "조회 실패")}), 502

    items = result.get("body", {}).get("items", {}).get("item", [])
    parsed = [
        {
            "period": i["year"],
            "item": i.get("statKor", "-"),
            "export_usd": _to_float(i.get("expDlr")),
            "import_usd": _to_float(i.get("impDlr")),
        }
        for i in items
        if i.get("year") != "총계"
    ]
    return jsonify(parsed)


@app.route("/api/hyperscaler-capex")
def hyperscaler_capex_route():
    return jsonify(hyperscaler_capex.get_history())


@app.route("/api/valuation")
def valuation():
    stock = request.args.get("stock", "삼성전자")
    ticker = TICKERS.get(stock)
    if not ticker:
        return jsonify({"error": f"등록되지 않은 종목: {stock}"}), 400
    try:
        data = krx_investor.get_valuation(ticker)
    except Exception as e:
        app.logger.error(f"밸류에이션 조회 실패: {e}")
        return jsonify({"error": "밸류에이션 조회 실패"}), 502

    return jsonify({"stock": stock, **data})


@app.route("/api/daily-digest")
def daily_digest():
    stock = request.args.get("stock", "삼성전자")
    ticker = TICKERS.get(stock)

    try:
        disclosures = dart_client.get_recent_disclosures(stock, days=2)
    except Exception as e:
        app.logger.error(f"공시 조회 실패: {e}")
        disclosures = []

    foreign_briefing = None
    if ticker:
        try:
            foreign_briefing = krx_investor.get_foreign_investor_briefing(ticker)
        except Exception as e:
            app.logger.error(f"외국인 브리핑 조회 실패: {e}")

    return jsonify({"stock": stock, "disclosures": disclosures, "foreign_briefing": foreign_briefing})


@app.route("/api/sox-index")
def sox_index():
    try:
        return jsonify(market_reference.get_sox_index())
    except Exception as e:
        app.logger.error(f"SOX 지수 조회 실패: {e}")
        return jsonify({"error": "SOX 지수 조회 실패"}), 502


@app.route("/api/overnight-futures")
def overnight_futures():
    try:
        return jsonify(market_reference.get_overnight_futures())
    except Exception as e:
        app.logger.error(f"야간 시세 조회 실패: {e}")
        return jsonify({"error": "야간 시세 조회 실패"}), 502


@app.route("/api/micron-trend")
def micron_trend():
    try:
        return jsonify(market_reference.get_micron_revenue_trend())
    except Exception as e:
        app.logger.error(f"마이크론 매출 조회 실패: {e}")
        return jsonify({"error": "마이크론 매출 조회 실패"}), 502


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
