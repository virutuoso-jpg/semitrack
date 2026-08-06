"""
한국투자증권(KIS) Open API 클라이언트
- 접근토큰 발급/캐싱
- 종목 현재가 조회
- 외국인/기관 순매수 동향 조회 (외국인 vs 기관계까지만 구분됨.
  사모펀드/금융투자/연기금 세부 구분은 krx_investor.py 참고)

주의: App Key/Secret은 .env에서만 읽고, 절대 코드에 하드코딩하지 않는다.
"""

import os
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_ENV = os.getenv("KIS_ENV", "vps")  # vps=모의투자, prod=실전투자

BASE_URL = (
    "https://openapi.koreainvestment.com:9443"
    if KIS_ENV == "prod"
    else "https://openapivts.koreainvestment.com:29443"
)

_TOKEN_CACHE_PATH = os.path.join(os.path.dirname(__file__), ".token_cache.json")


def _load_cached_token():
    if not os.path.exists(_TOKEN_CACHE_PATH):
        return None
    with open(_TOKEN_CACHE_PATH, "r") as f:
        data = json.load(f)
    # 만료 10분 전까지만 유효한 것으로 간주 (여유 버퍼)
    if data.get("expire_at", 0) - 600 > time.time():
        return data.get("access_token")
    return None


def _save_token_cache(access_token: str, expires_in: int):
    data = {"access_token": access_token, "expire_at": time.time() + expires_in}
    with open(_TOKEN_CACHE_PATH, "w") as f:
        json.dump(data, f)


def get_access_token() -> str:
    """접근토큰 발급 (캐시되어 있으면 재사용, 1분당 1회 제한 주의)"""
    cached = _load_cached_token()
    if cached:
        return cached

    url = f"{BASE_URL}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    _save_token_cache(data["access_token"], data.get("expires_in", 86400))
    return data["access_token"]


def _headers(tr_id: str) -> dict:
    return {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {get_access_token()}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": tr_id,
    }


def get_current_price(stock_code: str) -> dict:
    """종목 현재가 조회 (예: 삼성전자 '005930')"""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
    }
    resp = requests.get(url, headers=_headers("FHKST01010100"), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("output", {})


def get_foreign_institution_trend(stock_code: str) -> dict:
    """종목별 외국인/기관 순매수 동향 (합계 기준).
    세부 기관 구분(사모펀드/금융투자/연기금)은 krx_investor.py의 함수를 사용할 것.
    """
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-investor"
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
    }
    resp = requests.get(url, headers=_headers("FHKST01010900"), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("output", [])


if __name__ == "__main__":
    # 간단한 동작 확인용 (.env 설정 후 로컬에서 실행)
    print("삼성전자 현재가:", get_current_price("005930"))
    print("SK하이닉스 외국인/기관 동향:", get_foreign_institution_trend("000660"))
