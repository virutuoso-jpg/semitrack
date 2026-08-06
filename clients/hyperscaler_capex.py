"""
하이퍼스케일러(MS/구글/AWS/메타) capex, 클라우드·AI 매출 추적
- 정형 API가 없어 분기 실적 발표(10-Q, 어닝콜 자료) 내용을 확인한 뒤 수동으로 한 줄씩 입력한다.
- 입력된 값은 data/hyperscaler_capex.json 에 누적 저장된다 (연-분기 중복 시 최신 값으로 덮어씀).

사용법 (실적 발표 확인 후, 파이썬 인터프리터나 스크립트에서):
    from clients.hyperscaler_capex import add_quarter
    add_quarter(
        "Microsoft", 2026, 2,
        capex_usd_million=19200,
        cloud_revenue_usd_million=42400,
        ai_note="Azure AI 매출 3자릿수 % 성장 언급",
        source_url="https://www.microsoft.com/en-us/investor/earnings/...",
    )
"""

import json
import os
from datetime import datetime

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "hyperscaler_capex.json")

COMPANIES = ["Microsoft", "Google", "Amazon", "Meta"]


def _load() -> list:
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(records: list) -> None:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def add_quarter(
    company: str,
    year: int,
    quarter: int,
    capex_usd_million: float,
    cloud_revenue_usd_million: float = None,
    ai_note: str = "",
    source_url: str = "",
) -> None:
    """분기 실적 발표 내용을 확인한 뒤 직접 호출해서 한 줄 추가/갱신한다."""
    if company not in COMPANIES:
        raise ValueError(f"등록되지 않은 회사: {company} (허용: {COMPANIES})")

    records = _load()
    key = (company, year, quarter)
    records = [r for r in records if (r["company"], r["year"], r["quarter"]) != key]
    records.append(
        {
            "company": company,
            "year": year,
            "quarter": quarter,
            "capex_usd_million": capex_usd_million,
            "cloud_revenue_usd_million": cloud_revenue_usd_million,
            "ai_note": ai_note,
            "source_url": source_url,
            "recorded_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    records.sort(key=lambda r: (r["company"], r["year"], r["quarter"]))
    _save(records)


def get_history(company: str = None) -> list:
    """저장된 전체(또는 특정 회사) 분기별 capex/매출 이력 조회"""
    records = _load()
    if company:
        return [r for r in records if r["company"] == company]
    return records


if __name__ == "__main__":
    history = get_history()
    if not history:
        print("아직 입력된 데이터가 없습니다.")
        print("사용법: from clients.hyperscaler_capex import add_quarter; add_quarter(...)")
    else:
        for r in history:
            print(r)
