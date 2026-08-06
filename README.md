# SEMI.TRACK — 반도체 투자 대시보드 데이터 파이프라인

삼성전자 / SK하이닉스 중심 반도체 투자 데이터를 자동 수집하는 백엔드 파이프라인 시작 코드입니다.

## 1. 설치

```bash
cd semitrack
python -m venv venv
source venv/bin/activate   # Windows는 venv\Scripts\activate
pip install -r requirements.txt
```

## 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 아래 값을 채워 넣으세요. **이 파일은 절대 깃허브에 올리지 마세요** (`.gitignore`에 이미 등록됨).

- `KIS_APP_KEY`, `KIS_APP_SECRET`: KIS Developers(apiportal.koreainvestment.com)에서 발급
- `KIS_ENV`: 처음엔 `vps`(모의투자)로 테스트 후 `prod`(실전투자)로 전환
- `DART_API_KEY`: opendart.fss.or.kr 에서 무료 발급

## 3. 개별 모듈 동작 확인

```bash
# 한투 API 연결 확인 (시세/수급)
python clients/kis_client.py

# KRX 세부 투자자 동향 확인 (사모펀드/금융투자/연기금)
python clients/krx_investor.py

# DART 분기 실적 확인
python clients/dart_client.py
```

## 4. 스케줄러 상시 구동

```bash
python scheduler/jobs.py
```

섹션별 업데이트 주기:

| 섹션 | 주기 |
|---|---|
| 외국인 투자 현황 | 3시간 간격 (09/12/15시) |
| 사모펀드·금융투자·연기금 | 하루 2회 (장전 08:30 / 장후 16:00) |
| 반도체 수출입통계 | 10일 단위 (매월 1/11/21일) — **관세청/무역협회 API 별도 신청 필요** |
| 분기 실적(DART) | 매일 09:00 신규 공시 폴링 |

수집 결과는 `data/` 폴더에 섹션별 JSON 스냅샷으로 쌓입니다 (추후 실제 DB로 교체 예정).

## 5. 아직 구현되지 않은 부분 (다음 단계)

- [ ] 반도체 수출입통계: 관세청/무역협회 K-stat API 신청 및 연동
- [ ] 하이퍼스케일러 capex/AI매출: 정형 API가 없어 반자동 입력 도구 별도 필요
- [ ] `data/` JSON → 실제 DB(PostgreSQL 등) 마이그레이션
- [ ] 대시보드 프론트엔드와 API 연결 (현재는 목업 화면만 존재)
