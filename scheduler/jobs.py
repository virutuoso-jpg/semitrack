"""
섹션별 업데이트 스케줄러

- 외국인 투자 현황       : 3~6시간 간격 (장중 09~15시대 커버)
- 사모펀드/금융투자/연기금 : 하루 2회 (장개시 전 08:30, 장종료 후 16:00)
- 반도체 수출입통계       : 10일 단위(1/11/21일) 09:00 체크
- 분기 실적(DART)        : 매일 09:00 신규 공시 여부 체크 (공시는 비정기 발생이라 폴링 방식)

실행: python scheduler/jobs.py  (서버/PC에서 상시 구동, cron 대신 APScheduler로 프로세스 내 관리)
"""

import sys
import os
import json
import logging
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from clients import kis_client, krx_investor, dart_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TICKERS = {"삼성전자": "005930", "SK하이닉스": "000660"}
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)


def _save_snapshot(section: str, payload: dict):
    """섹션별 결과를 타임스탬프 붙여 JSON으로 적재 (추후 DB로 교체 가능)"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DATA_DIR, f"{section}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, default=str, indent=2)
    logger.info(f"[{section}] 저장 완료 -> {path}")


def update_foreign_investor():
    """외국인 수급 - 3~6시간 주기"""
    result = {}
    for name, code in TICKERS.items():
        try:
            result[name] = kis_client.get_foreign_institution_trend(code)
        except Exception as e:
            logger.error(f"[외국인수급] {name} 조회 실패: {e}")
    _save_snapshot("foreign_investor", result)


def update_institution_flow():
    """사모펀드/금융투자/연기금 - 장전/장후 하루 2회"""
    result = {}
    for name, code in TICKERS.items():
        try:
            df = krx_investor.get_target_investor_summary(code)
            df.index = df.index.strftime("%Y-%m-%d")
            result[name] = df.to_dict()
        except Exception as e:
            logger.error(f"[기관동향] {name} 조회 실패: {e}")
    _save_snapshot("institution_flow", result)


def update_export_stats():
    """반도체 수출입통계 - 10일 단위 체크 (매월 1/11/21일)
    관세청/무역협회 API 연동은 별도 신청 필요 - 여기서는 훅만 마련"""
    logger.info("[수출입통계] 10일 단위 갱신 훅 - 관세청/무역협회 API 연동 필요 (TODO)")


def check_new_earnings():
    """DART 공시 - 신규 분기 실적 발표 여부 폴링"""
    for name in TICKERS:
        try:
            # 실제로는 최신 공시 목록 API로 '신규 공시 여부'부터 판단해야 함 (TODO)
            logger.info(f"[실적체크] {name} 신규 공시 확인 (구현 예정)")
        except Exception as e:
            logger.error(f"[실적체크] {name} 확인 실패: {e}")


def add_jobs(scheduler):
    # 외국인 수급: 09,12,15시 (3시간 간격, 장중 위주)
    scheduler.add_job(update_foreign_investor, CronTrigger(hour="9,12,15", minute=0))

    # 기관 세부동향: 장개시 전 08:30, 장종료 후 16:00
    scheduler.add_job(update_institution_flow, CronTrigger(hour="8,16", minute=30))

    # 수출입통계: 매월 1/11/21일 09:00
    scheduler.add_job(update_export_stats, CronTrigger(day="1,11,21", hour=9, minute=0))

    # 실적 공시 체크: 매일 09:00
    scheduler.add_job(check_new_earnings, CronTrigger(hour=9, minute=0))


def start_background(run_immediately: bool = True):
    """웹 서버(server.py) 프로세스 안에서 백그라운드로 스케줄러를 띄운다.
    무료 호스팅은 재배포/재시작 때마다 저장된 파일이 초기화되므로,
    시작하자마자 한 번 즉시 수집해 빈 화면을 방지한다."""
    if run_immediately:
        try:
            update_foreign_investor()
            update_institution_flow()
        except Exception as e:
            logger.error(f"초기 데이터 수집 실패: {e}")

    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    add_jobs(scheduler)
    scheduler.start()
    logger.info("백그라운드 스케줄러 시작됨.")
    return scheduler


def main():
    scheduler = BlockingScheduler(timezone="Asia/Seoul")
    add_jobs(scheduler)
    logger.info("스케줄러 시작. Ctrl+C로 종료.")
    scheduler.start()


if __name__ == "__main__":
    main()
