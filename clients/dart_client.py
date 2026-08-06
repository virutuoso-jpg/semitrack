"""
DART(전자공시) Open API 클라이언트 - 분기 매출/영업이익 조회
발급: https://opendart.fss.or.kr (무료)
"""

import os
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


if __name__ == "__main__":
    # 동작 확인용 (.env에 DART_API_KEY 설정 후 로컬에서 실행)
    result = get_quarterly_financials("삼성전자", 2026, 1)
    print(result)
