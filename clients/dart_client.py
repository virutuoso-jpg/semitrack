"""
DART(전자공시) Open API 클라이언트 - 분기 매출/영업이익 조회
발급: https://opendart.fss.or.kr (무료)
"""

import os
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

DART_API_KEY = os.getenv("DART_API_KEY")
BASE_URL = "https://opendart.fss.or.kr/api"

# 고유번호(corp_code)는 DART에서 종목코드와 별개로 관리되는 값.
# 최초 1회 https://opendart.fss.or.kr/api/corpCode.xml 을 받아 매핑 테이블을 만들어둬야 함.
CORP_CODES = {
    "삼성전자": "00126380",
    "SK하이닉스": "00164779",
}


def get_quarterly_financials(corp_name: str, year: int, quarter: int) -> dict:
    """
    분기보고서 기준 매출액/영업이익 조회

    Args:
        corp_name: '삼성전자' 또는 'SK하이닉스'
        year: 조회 연도 (예: 2026)
        quarter: 1~4 분기
    """
    corp_code = CORP_CODES.get(corp_name)
    if not corp_code:
        raise ValueError(f"등록되지 않은 회사명: {corp_name}")

    reprt_map = {1: "11013", 2: "11012", 3: "11014", 4: "11011"}  # 1분기/반기/3분기/사업보고서
    url = f"{BASE_URL}/fnlttSinglAcntAll.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": reprt_map[quarter],
        "fs_div": "CFS",  # 연결재무제표
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


# 공시 제목에 이 키워드가 있으면 "주주환원" 관련으로 분류 (배당/자사주 등)
SHAREHOLDER_RETURN_KEYWORDS = ["배당", "자기주식", "자사주"]


def get_recent_disclosures(corp_name: str, days: int = 2) -> list:
    """최근 N일간 공시 목록 (제목 + 원문 링크). 매일 아침 브리핑용.

    Args:
        corp_name: '삼성전자' 또는 'SK하이닉스'
        days: 오늘 포함 조회 기간 (전날 9시~당일 9시 브리핑이면 2일이면 충분)
    """
    corp_code = CORP_CODES.get(corp_name)
    if not corp_code:
        raise ValueError(f"등록되지 않은 회사명: {corp_name}")

    end = datetime.today()
    start = end - timedelta(days=days)
    url = f"{BASE_URL}/list.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bgn_de": start.strftime("%Y%m%d"),
        "end_de": end.strftime("%Y%m%d"),
        "page_no": 1,
        "page_count": 30,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") == "013":  # 조회된 데이터 없음 (정상)
        return []
    if data.get("status") != "000":
        raise RuntimeError(data.get("message", "DART 공시 목록 조회 실패"))

    items = data.get("list", [])
    return [
        {
            "title": item["report_nm"],
            "date": item["rcept_dt"],
            "filer": item.get("flr_nm", ""),
            "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item['rcept_no']}",
            "is_shareholder_return": any(k in item["report_nm"] for k in SHAREHOLDER_RETURN_KEYWORDS),
        }
        for item in items
    ]


if __name__ == "__main__":
    # 동작 확인용 (.env에 DART_API_KEY 설정 후 로컬에서 실행)
    result = get_quarterly_financials("삼성전자", 2026, 1)
    print(result)
    print(get_recent_disclosures("삼성전자", days=7))
