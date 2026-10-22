"""방문자별 메모리 저장소에 추가하는 날짜별 공고·최근 6개월 가상 기록."""
from collections import Counter

from demo.store import DemoStore


DAILY_NOTICE_COUNTS = {
    '2026-10-03': 1, '2026-10-05': 3, '2026-10-07': 8,
    '2026-10-09': 2, '2026-10-11': 6, '2026-10-13': 10,
    '2026-10-15': 4, '2026-10-17': 7, '2026-10-19': 1,
    '2026-10-21': 9, '2026-10-23': 3, '2026-10-25': 5,
    '2026-10-26': 8, '2026-10-28': 10,
}

_PROJECTS = (
    ('가상 시설', '보행로 정비'), ('가상 물품', '회의실 집기 구매'),
    ('가상 용역', '안내 콘텐츠 제작'), ('가상 시설', '조명 설비 교체'),
    ('가상 물품', '자료 보관함 구매'), ('가상 용역', '시설 안전점검'),
    ('가상 시설', '실내 바닥 보수'), ('가상 물품', '교육용 기자재 구매'),
    ('가상 용역', '기록물 전산화'),
)
_PLACES = ('북부생활센터', '서부학습관', '동부체육관', '남부문화관',
           '중앙도서관', '하늘공원', '마을회관', '늘봄학교')
_AGENCIES = ('가상 도시시설지원단', '가상 생활환경지원센터', '가상 문화교육지원원',
             '가상 공공구매센터', '가상 지역행정지원실')
_REGIONS = ('가상 북부', '가상 남부', '가상 동부', '가상 서부', '가상 중부')
_HISTORY = (
    (5, 2, (8_400_000,)),
    (6, 4, (11_000_000, 12_500_000)),
    (7, 3, (15_800_000,)),
    (8, 5, (14_200_000, 17_000_000)),
    (9, 4, (24_600_000,)),
)


def create_demo_store():
    """원본 12건을 보존한 95공고·22투찰·22결과의 독립된 데모 세션을 만든다."""
    store = DemoStore()
    try:
        originals = store.notices()
        counts = Counter(row['deadline'] for row in originals)
        number = len(originals) + 1
        for deadline, target in DAILY_NOTICE_COUNTS.items():
            for _ in range(target - counts[deadline]):
                index = number - len(originals) - 1
                category, project = _PROJECTS[index % len(_PROJECTS)]
                place = _PLACES[(index // len(_PROJECTS)) % len(_PLACES)]
                store.save_notice({
                    'code': f'DEMO-{number:03d}', 'title': f'가상 {place} {project}',
                    'agency': _AGENCIES[index % len(_AGENCIES)], 'category': category,
                    'region': _REGIONS[index % len(_REGIONS)],
                    'base_amount': 8_500_000 + index * 1_275_000, 'deadline': deadline,
                    'status': '접수중' if deadline > '2026-10-21' else '마감',
                    'memo': '일자별 공고 목록 확인을 위한 추가 가상 샘플입니다.',
                })
                number += 1
        index = 0
        for month, count, winning_amounts in _HISTORY:
            for position in range(count):
                category, project = _PROJECTS[index % len(_PROJECTS)]
                won = position < len(winning_amounts)
                amount = winning_amounts[position] if won else 9_000_000 + index * 850_000
                notice_id = store.save_notice({
                    'code': f'DEMO-{number:03d}',
                    'title': f'가상 {month}월 실적 샘플 {_PLACES[index % len(_PLACES)]} {project} {position + 1}',
                    'agency': _AGENCIES[index % len(_AGENCIES)], 'category': category,
                    'region': _REGIONS[index % len(_REGIONS)],
                    'base_amount': amount + 2_000_000, 'deadline': f'2026-{month:02d}-{4 + position * 6:02d}',
                    'status': '완료', 'memo': '최근 6개월 투찰·낙찰 추이를 체험하기 위한 가상 실적 샘플입니다.',
                })
                store.save_submission({
                    'notice_id': notice_id, 'company': '가상 실적체험기업', 'amount': amount,
                    'status': '제출완료', 'memo': f'가상 {month}월 성과 리포트 체험용 투찰 기록입니다.',
                })
                store.save_result({
                    'notice_id': notice_id, 'outcome': '샘플 낙찰' if won else '샘플 미선정',
                    'amount': amount, 'note': f'가상 {month}월 성과 리포트 체험용 개찰 결과입니다.',
                })
                number += 1
                index += 1
    except Exception:
        store.close()
        raise
    return store
