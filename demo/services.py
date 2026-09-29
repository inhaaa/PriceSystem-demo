"""외부 호출 및 실제 분석이 없는 고정 데모 서비스."""


def authenticate(username, password):
    """공개 체험용 계정만 비교한다. 실제 사용자 인증 기능이 아니다."""
    return username == "admin" and password == "admin"


def recommendation(scenario="샘플 A"):
    """입력 공고와 무관한 고정 표시값으로 화면만 시연한다."""
    samples = {
        "샘플 A": (24000000, (22, 48, 66, 45, 28), 88.45, 76.0),
        "샘플 B": (36000000, (31, 54, 39, 62, 36), 89.12, 81.5),
        "샘플 C": (18000000, (43, 27, 57, 34, 51), 87.96, 72.0),
    }
    if scenario not in samples:
        raise ValueError("분석 샘플을 선택해 주세요.")
    amount, values, bid_rate, confidence = samples[scenario]
    return {
        "scenario": scenario,
        "label": "가상 표시 금액",
        "amount": amount,
        "bid_rate": bid_rate,
        "confidence": confidence,
        "points": [{"label": f"표시 {index}", "value": value} for index, value in enumerate(values, 1)],
        "note": "고정 샘플 표시값입니다. 입력 공고와 무관하며 실제 추천·예측·낙찰 확률이 아닙니다.",
    }


def backtest_sample():
    """입력 데이터나 분석 엔진을 사용하지 않는 독립적인 백테스트 화면 샘플."""
    examples = (
        ("가상 전시공간 정비", 24000000, 24000000, 88.45, 76.0, "낙찰"),
        ("가상 교육자료 제작", 18000000, 17900000, 87.96, 72.0, "미낙찰"),
        ("가상 안내시설 설치", 36000000, 35700000, 89.12, 81.5, "미낙찰"),
        ("가상 체험장 물품 구매", 21000000, 20800000, 88.20, 74.5, "미낙찰"),
    )
    return {
        "note": "고정 샘플입니다. 실제 백테스트를 실행하지 않으며 실제 검증 성과가 아닙니다.",
        "rows": [{"공고번호": f"DEMO-BT-{index:03d}", "공고명": title,
                  "추천 금액 (원)": amount, "낙찰 금액 (원)": awarded,
                  "실투찰율 (%)": rate, "신뢰도 (%)": confidence, "결과": outcome}
                 for index, (title, amount, awarded, rate, confidence, outcome) in enumerate(examples, 1)],
    }


def api_response(scenario="정상"):
    """네트워크 접근 없이 정상·빈 결과·오류 응답을 메모리에서 구성한다."""
    if scenario not in ("정상", "빈 결과", "오류"):
        raise ValueError("API 시나리오를 선택해 주세요.")
    items = []
    if scenario == "정상":
        items = [
            dict(code="DEMO-API-001", title="가상 API 안내판 샘플", agency="가상 API 체험센터", category="가상 시설", region="가상 동부", base_amount=22000000, deadline="2026-10-27", status="접수중", memo="외부 호출 없는 데모 API 샘플"),
            dict(code="DEMO-API-002", title="가상 API 교구 샘플", agency="가상 API 체험센터", category="가상 물품", region="가상 서부", base_amount=11000000, deadline="2026-10-29", status="접수중", memo="외부 호출 없는 데모 API 샘플"),
        ]
    status, message = {
        "정상": ("ok", "가상 샘플 응답입니다. 외부 API를 호출하지 않았습니다."),
        "빈 결과": ("empty", "조회 결과가 없는 상황을 재현한 데모 응답입니다."),
        "오류": ("error", "연결 오류 상황을 재현한 데모 응답입니다. 실제 연결은 없습니다."),
    }[scenario]
    return dict(source="demo", items=items, total=len(items), status=status, message=message)
