"""
KRX 투자자별 세부 매매동향 클라이언트 (pykrx 사용)
- 사모펀드 / 금융투자 / 보험 / 투신 / 은행 / 기타금융 / 연기금 / 국가지자체 / 개인 / 외국인 등
  세부 투자자 구분별 순매수 데이터를 종목 단위로 제공
- pykrx 최신 버전은 KRX 데이터마켓(data.krx.co.kr) 계정 로그인이 필요함
  .env 파일에 KRX_ID / KRX_PW를 설정해두면 자동으로 로그인함
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# pykrx는 KRX_ID / KRX_PW 환경변수를 직접 읽으므로, .env에서 읽어와 os.environ에 등록
if os.getenv("KRX_ID"):
    os.environ["KRX_ID"] = os.getenv("KRX_ID")
if os.getenv("KRX_PW"):
    os.environ["KRX_PW"] = os.getenv("KRX_PW")

from pykrx import stock

# 관심 종목의 세부 기관 구분 중, 이 프로젝트에서 특히 추적하려는 항목
TARGET_INVESTOR_TYPES = ["사모", "금융투자", "연기금"]


def get_investor_trend(stock_code: str, days: int = 5):
    """
    최근 N영업일 동안의 종목별 투자자 세부구분 순매수 거래대금을 조회한다.

    Args:
        stock_code: 종목코드 (예: '005930' 삼성전자, '000660' SK하이닉스)
        days: 조회 기간(영업일 기준 대략치, 캘린더 일수로 넉넉히 잡음)

    Returns:
        pandas.DataFrame — 인덱스: 날짜, 컬럼: 투자자구분(금융투자/보험/투신/사모/은행/
        기타금융/연기금/기타법인/개인/외국인/기타외국인)
    """
    end = datetime.today()
    start = end - timedelta(days=days * 2)  # 주말/휴장 감안 넉넉히

    df = stock.get_market_trading_value_by_date(
        start.strftime("%Y%m%d"),
        end.strftime("%Y%m%d"),
        stock_code,
        detail=True,
    )
    return df


def get_target_investor_summary(stock_code: str, days: int = 5):
    """사모펀드/금융투자/연기금만 추려서 요약 (대시보드 카드용)"""
    df = get_investor_trend(stock_code, days=days)
    available_cols = [c for c in TARGET_INVESTOR_TYPES if c in df.columns]
    return df[available_cols]


def get_foreign_institution_trend(stock_code: str, days: int = 10):
    """외국인/기관 합계 순매수 거래대금 + 종가 (일별). KIS API 대체용.

    KIS는 접근토큰이 1일 1회 발급 원칙이라 무료 호스팅 환경(재시작마다 캐시 초기화)에서는
    재발급이 잦아질 위험이 있어, 이미 로그인 중인 KRX 세션으로 대체한다.
    """
    end = datetime.today()
    start = end - timedelta(days=days * 2)

    trade = stock.get_market_trading_value_by_date(
        start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), stock_code
    )
    ohlcv = stock.get_market_ohlcv_by_date(
        start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), stock_code
    )

    df = trade[["외국인합계", "기관합계"]].join(ohlcv[["종가"]], how="inner")
    df.columns = ["foreign_net_value", "institution_net_value", "close"]
    return df


def get_valuation(stock_code: str) -> dict:
    """가장 최근 거래일 기준 PER/PBR/EPS/BPS + 종가 + 외국인 보유비율. KIS API 대체용."""
    end = datetime.today()
    start = end - timedelta(days=10)

    fundamental = stock.get_market_fundamental_by_date(
        start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), stock_code
    )
    ohlcv = stock.get_market_ohlcv_by_date(
        start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), stock_code
    )
    exhaustion = stock.get_exhaustion_rates_of_foreign_investment_by_date(
        start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), stock_code
    )

    latest_fundamental = fundamental.iloc[-1]
    latest_price = ohlcv.iloc[-1]
    latest_ratio = exhaustion.iloc[-1]

    return {
        "price": float(latest_price["종가"]),
        "per": float(latest_fundamental["PER"]),
        "pbr": float(latest_fundamental["PBR"]),
        "eps": float(latest_fundamental["EPS"]),
        "bps": float(latest_fundamental["BPS"]),
        "foreign_holding_ratio": float(latest_ratio["지분율"]),
    }


def get_foreign_investor_briefing(stock_code: str, days: int = 1) -> str:
    """아침 브리핑용 외국인 수급 한 줄 요약 (전일 순매수 방향 + 최근 연속 매매 동향)"""
    df = get_foreign_institution_trend(stock_code, days=max(days, 5))
    if df.empty:
        return "외국인 수급 데이터 없음"

    latest = df.iloc[-1]
    direction = "순매수" if latest["foreign_net_value"] >= 0 else "순매도"

    streak = 0
    streak_sign = latest["foreign_net_value"] >= 0
    for value in reversed(df["foreign_net_value"].tolist()):
        if (value >= 0) == streak_sign:
            streak += 1
        else:
            break

    return (
        f"전일 외국인 {direction} {abs(latest['foreign_net_value']):,.0f}원"
        f" ({streak}거래일 연속 {'순매수' if streak_sign else '순매도'})"
    )


if __name__ == "__main__":
    # 동작 확인용 (네트워크 필요, 로컬에서 실행)
    samsung = get_target_investor_summary("005930")
    print("삼성전자 사모/금융투자/연기금 순매수 동향:")
    print(samsung)
    print(get_foreign_investor_briefing("005930"))
