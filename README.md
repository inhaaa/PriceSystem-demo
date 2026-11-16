# PriceSystem

입찰 공고 조회부터 투찰 내역과 개찰 결과 관리까지 한곳에서 처리하는 입찰가격선정시스템의 포트폴리오 데모입니다.

**[온라인 데모 열기](https://demo.inhaaa.com/)** · 체험 계정 `admin` / `admin`

**기술 스택** · Python, Streamlit, pandas, SQLite

## 데모 체험

샘플 공고를 등록한 뒤 개찰일별로 조회하고, 추천 결과 확인과 투찰 내역 등록을 체험할 수 있습니다.

> 데모는 가상 데이터와 고정된 추천·분석 샘플을 사용합니다. 입력한 내용은 현재 세션에만 저장됩니다.

![PriceSystem 데모의 개찰일별 공고 일정](https://raw.githubusercontent.com/inhaaa/PriceSystem-demo/611a46553f12b2926cb04bb7b46e40351cc0fb35/docs/images/home.png)

## 운영 성과

실제 운영 시스템은 2026년 7월부터 입찰 업무에 활용됐으며, 운영 기간 중 낙찰 2건을 기록했습니다.

## 빠른 시작

저장소 폴더에서 `python -m venv .venv`로 Python 3.11 이상 가상환경을 만들고 활성화한 뒤 실행합니다.

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

[개발 안내](docs/DEVELOPMENT.md) · [자산 및 권리 안내](ASSET_NOTICE.md)
