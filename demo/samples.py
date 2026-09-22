"""새로 작성한 가상 데모 데이터. 실제 공고·업체·분석 규칙과 무관하다."""

CATEGORIES = ("가상 시설", "가상 물품", "가상 용역")


def seed_rows():
    """호출마다 독립된 샘플 목록을 반환한다. 날짜는 고정된 데모 날짜다."""
    examples = (
        ("가상 산책로 안내판 설치", "가상 시설", "가상 동부", 42000000, "2026-10-03", "접수중"),
        ("가상 도서공간 책상 구매", "가상 물품", "가상 서부", 18000000, "2026-10-05", "접수중"),
        ("가상 전시 안내 콘텐츠 제작", "가상 용역", "가상 동부", 27000000, "2026-10-07", "접수중"),
        ("가상 마을쉼터 조명 교체", "가상 시설", "가상 서부", 36000000, "2026-10-09", "접수중"),
        ("가상 학습공간 의자 구매", "가상 물품", "가상 동부", 12500000, "2026-10-11", "접수중"),
        ("가상 문화행사 안내 운영", "가상 용역", "가상 서부", 23000000, "2026-10-13", "접수중"),
        ("가상 정원 보행로 정비", "가상 시설", "가상 동부", 58000000, "2026-10-15", "마감"),
        ("가상 자료실 선반 구매", "가상 물품", "가상 서부", 9500000, "2026-10-17", "마감"),
        ("가상 생활지도 디자인", "가상 용역", "가상 동부", 14500000, "2026-10-19", "완료"),
        ("가상 커뮤니티실 바닥 정비", "가상 시설", "가상 서부", 31000000, "2026-10-21", "완료"),
        ("가상 체험교실 교구 구매", "가상 물품", "가상 동부", 7500000, "2026-10-23", "완료"),
        ("가상 공원 안내자료 제작", "가상 용역", "가상 서부", 16500000, "2026-10-25", "완료"),
    )
    notices = [dict(
        code=f"DEMO-{number:03d}", title=title, agency="가상 데모 운영센터",
        category=category, region=region, base_amount=amount, deadline=deadline,
        status=status, memo="화면 체험을 위해 새로 만든 가상 샘플입니다.",
    ) for number, (title, category, region, amount, deadline, status) in enumerate(examples, 1)]
    submissions = [
        dict(notice_id=1, company="가상 참가자 구름", amount=39000000, status="작성중", memo="데모 작성 예시"),
        dict(notice_id=7, company="가상 참가자 별빛", amount=54000000, status="제출완료", memo="데모 제출 예시"),
        dict(notice_id=9, company="가상 참가자 물결", amount=13000000, status="제출완료", memo="데모 제출 예시"),
        dict(notice_id=10, company="가상 참가자 새싹", amount=29000000, status="제출완료", memo="데모 제출 예시"),
    ]
    results = [
        dict(notice_id=9, outcome="샘플 낙찰", amount=13000000, note="실제 결과가 아닌 가상 표시값"),
        dict(notice_id=10, outcome="샘플 미선정", amount=28000000, note="실제 결과가 아닌 가상 표시값"),
        dict(notice_id=11, outcome="샘플 낙찰", amount=7000000, note="실제 결과가 아닌 가상 표시값"),
        dict(notice_id=12, outcome="검토중", amount=0, note="실제 결과가 아닌 가상 표시값"),
    ]
    return notices, submissions, results
