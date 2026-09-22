"""외부 호출 및 실제 분석이 없는 고정 데모 서비스."""


def authenticate(username, password):
    """공개 체험용 계정만 비교한다. 실제 사용자 인증 기능이 아니다."""
    return username == "admin" and password == "admin"


def recommendation(scenario="샘플 A"):
    """입력 공고와 무관한 고정 표시값으로 화면만 시연한다."""
    samples = {
        "샘플 A": (24000000, (22, 48, 66, 45, 28)),
        "샘플 B": (36000000, (31, 54, 39, 62, 36)),
        "샘플 C": (18000000, (43, 27, 57, 34, 51)),
    }
    if scenario not in samples:
        raise ValueError("분석 샘플을 선택해 주세요.")
    amount, values = samples[scenario]
    return {
        "scenario": scenario,
        "label": "가상 표시 금액",
        "amount": amount,
        "points": [{"label": f"표시 {index}", "value": value} for index, value in enumerate(values, 1)],
        "note": "고정 샘플 표시값입니다. 입력 공고와 무관하며 실제 추천·예측·낙찰 확률이 아닙니다.",
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
