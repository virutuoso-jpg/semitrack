"""
관세청 오픈API(공공데이터포털) 클라이언트 - 반도체 품목 수출입 실적
발급: https://www.data.go.kr ("관세청_품목별 국가별 수출입실적(GW)" 활용신청)

주의: 이 API는 국가코드(cntyCd) 지정이 필요하다 (전체 국가 합계 엔드포인트 아님).
      국가별로 나눠 조회한 뒤 합산해야 "전체 수출입" 수치가 나온다.
"""

import os
import xml.etree.ElementTree as ET
from urllib.parse import unquote

import requests
from dotenv import load_dotenv

load_dotenv()

# 공공데이터포털은 "Encoding"(URL 인코딩됨)/"Decoding"(원본) 두 종류 키를 발급하는데,
# requests가 params 전달 시 자체적으로 인코딩하므로 Encoding 키를 그대로 쓰면 이중 인코딩되어 인증 실패함.
# unquote로 먼저 원복시켜 어느 쪽 키를 넣어도 정상 동작하도록 처리.
CUSTOMS_API_KEY = unquote(os.getenv("CUSTOMS_API_KEY", ""))
BASE_URL = "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"

# HS코드(6단위) - 반도체 관련 주요 품목
# 8542: 전자집적회로 / 854232: 메모리(D램·낸드 등) / 854231: 프로세서·컨트롤러
HS_CODES = {
    "반도체_전체_HS4": "8542",
    "메모리반도체": "854232",
    "프로세서_컨트롤러": "854231",
}


def _parse_xml_response(text: str) -> dict:
    """공공데이터포털은 type=json을 줘도 가끔 XML로 응답하는 경우가 있어 대비용으로 파싱한다."""
    root = ET.fromstring(text)
    header = root.find("header")
    items = [
        {child.tag: child.text for child in item_el}
        for item_el in root.findall("body/items/item")
    ]
    return {
        "header": {
            "resultCode": header.findtext("resultCode", "") if header is not None else "",
            "resultMsg": header.findtext("resultMsg", "") if header is not None else "",
        },
        "body": {"items": {"item": items}},
    }


def get_trade_stats(hs_code: str, strt_yymm: str, end_yymm: str, cnty_cd: str) -> dict:
    """
    품목별(HS코드) 국가별 수출입실적 조회 (수량·금액 → 단가 계산용)

    Args:
        hs_code: HS코드 (HS_CODES 참고, 예: '854232' 메모리반도체)
        strt_yymm: 조회 시작 년월 (YYYYMM)
        end_yymm: 조회 종료 년월 (YYYYMM), strt_yymm 기준 최대 1년 이내
        cnty_cd: 국가코드 (예: 'US', 'CN', 'VN')
    """
    params = {
        "serviceKey": CUSTOMS_API_KEY,
        "strtYymm": strt_yymm,
        "endYymm": end_yymm,
        "hsSgn": hs_code,
        "cntyCd": cnty_cd,
        "type": "json",
    }
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()

    text = resp.text.lstrip()
    if text.startswith("<?xml") or text.startswith("<"):
        return _parse_xml_response(resp.text)
    return resp.json()


if __name__ == "__main__":
    # 동작 확인용: 최근 3개월 메모리반도체 대(對)미국 수출입 실적
    result = get_trade_stats(HS_CODES["메모리반도체"], "202605", "202607", cnty_cd="US")
    print(result)
