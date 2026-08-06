"""
반도체 업황 참고지표 클라이언트 (인증키 불필요)
- 필라델피아 반도체지수(SOX): 업황 심리를 보여주는 대표 지수
- 마이크론(Micron) 분기 매출: 한국 업체보다 실적 발표가 앞서는 메모리 업황 선행지표
"""

from datetime import date

import requests

SOX_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5ESOX"
SEC_BASE = "https://data.sec.gov/api/xbrl/companyconcept"
MICRON_CIK = "CIK0000723125"

# SEC는 요청자를 식별할 수 있는 User-Agent를 요구한다 (미기재 시 차단될 수 있음)
SEC_HEADERS = {"User-Agent": "SemiTrack-Personal-Project contact@example.com"}


def get_sox_index() -> dict:
    """필라델피아 반도체지수(SOX) 최근 종가 및 전일 대비 변동률"""
    resp = requests.get(
        SOX_URL, params={"range": "10d", "interval": "1d"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=10
    )
    resp.raise_for_status()
    result = resp.json()["chart"]["result"][0]
    closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
    if len(closes) < 2:
        raise ValueError("SOX 종가 데이터가 충분하지 않습니다.")

    latest, prev = closes[-1], closes[-2]
    return {
        "latest_close": round(latest, 2),
        "prev_close": round(prev, 2),
        "change_pct": round((latest - prev) / prev * 100, 2),
    }


def get_micron_revenue_trend(quarters: int = 4) -> list:
    """마이크론 최근 N개 분기 매출 (SEC EDGAR 공시 기준, 회계연도는 9월 결산이라 달력분기와 다름에 유의)"""
    url = f"{SEC_BASE}/{MICRON_CIK}/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax.json"
    resp = requests.get(url, headers=SEC_HEADERS, timeout=10)
    resp.raise_for_status()
    entries = resp.json().get("units", {}).get("USD", [])

    quarterly = []
    for e in entries:
        if e.get("form") not in ("10-Q", "10-K"):
            continue
        start = date.fromisoformat(e["start"])
        end = date.fromisoformat(e["end"])
        if 80 <= (end - start).days <= 100:
            quarterly.append({"period_end": e["end"], "revenue_usd": e["val"]})

    # 같은 분기가 여러 번 수정 공시될 수 있어 마지막(최신 filed) 값으로 중복 제거
    dedup = {q["period_end"]: q for q in quarterly}
    ordered = sorted(dedup.values(), key=lambda q: q["period_end"])
    return ordered[-quarters:]


if __name__ == "__main__":
    print("SOX:", get_sox_index())
    print("Micron 분기 매출:", get_micron_revenue_trend())
