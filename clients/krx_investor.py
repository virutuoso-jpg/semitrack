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


if __name__ == "__main__":
    # 동작 확인용 (네트워크 필요, 로컬에서 실행)
    samsung = get_target_investor_summary("005930")
    print("삼성전자 사모/금융투자/연기금 순매수 동향:")
    print(samsung)
