"""방문자 인스턴스마다 생성되는 메모리 전용 SQLite 데모 저장소."""

import csv
from datetime import date
import io
import sqlite3

from demo.samples import CATEGORIES, seed_rows

NOTICE_FIELDS = ("code", "title", "agency", "category", "region", "base_amount", "deadline", "status", "memo")
NOTICE_STATUSES = ("접수중", "마감", "완료")
SUBMISSION_STATUSES = ("작성중", "제출완료")
RESULT_OUTCOMES = ("샘플 낙찰", "샘플 미선정", "검토중")


def _text(value, label, required=True):
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f"{label}을(를) 입력해 주세요.")
    return value.strip()


def _amount(value):
    if isinstance(value, str) and value.strip().isascii() and value.strip().isdecimal():
        digits = value.strip().lstrip("0") or "0"
        value = int(digits) if len(digits) <= 13 else None
    if type(value) is not int or not 0 <= value <= 10**12:
        raise ValueError("금액은 0 이상 1조 이하의 정수로 입력해 주세요.")
    return value


class DemoStore:
    def __init__(self):
        self._db = None
        self.reset()

    def __del__(self):
        self.close()

    def reset(self):
        self.close()
        self._db = sqlite3.connect(":memory:", check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript("""
            CREATE TABLE categories (name TEXT PRIMARY KEY);
            CREATE TABLE notices (
                id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL, agency TEXT NOT NULL,
                category TEXT NOT NULL REFERENCES categories(name) ON UPDATE CASCADE,
                region TEXT NOT NULL, base_amount INTEGER NOT NULL,
                deadline TEXT NOT NULL, status TEXT NOT NULL, memo TEXT NOT NULL
            );
            CREATE TABLE submissions (
                id INTEGER PRIMARY KEY,
                notice_id INTEGER NOT NULL REFERENCES notices(id) ON DELETE CASCADE,
                company TEXT NOT NULL, amount INTEGER NOT NULL,
                status TEXT NOT NULL, memo TEXT NOT NULL
            );
            CREATE TABLE results (
                notice_id INTEGER PRIMARY KEY REFERENCES notices(id) ON DELETE CASCADE,
                outcome TEXT NOT NULL, amount INTEGER NOT NULL, note TEXT NOT NULL
            );
        """)
        for category in CATEGORIES:
            self.add_category(category)
        notices, submissions, results = seed_rows()
        for notice in notices:
            self.save_notice(notice)
        for submission in submissions:
            self.save_submission(submission)
        for result in results:
            self.save_result(result)

    def close(self):
        if self._db is not None:
            self._db.close()
            self._db = None

    def _rows(self, sql, parameters=()):
        return [dict(row) for row in self._db.execute(sql, parameters)]

    def _require(self, table, row_id, column="id"):
        if type(row_id) is not int or row_id <= 0:
            raise ValueError("항목을 찾을 수 없습니다.")
        row = self._db.execute(f"SELECT * FROM {table} WHERE {column} = ?", (row_id,)).fetchone()
        if row is None:
            raise ValueError("항목을 찾을 수 없습니다.")
        return dict(row)

    def categories(self):
        return [row[0] for row in self._db.execute("SELECT name FROM categories ORDER BY name")]

    def add_category(self, name):
        name = _text(name, "분류 이름")
        if name in self.categories():
            raise ValueError("이미 존재하는 분류입니다.")
        with self._db:
            self._db.execute("INSERT INTO categories VALUES (?)", (name,))

    def rename_category(self, old, new):
        new = _text(new, "분류 이름")
        if old not in self.categories():
            raise ValueError("분류를 찾을 수 없습니다.")
        if old != new and new in self.categories():
            raise ValueError("이미 존재하는 분류입니다.")
        with self._db:
            self._db.execute("UPDATE categories SET name = ? WHERE name = ?", (new, old))

    def delete_category(self, name):
        if name not in self.categories():
            raise ValueError("분류를 찾을 수 없습니다.")
        if self._db.execute("SELECT 1 FROM notices WHERE category = ?", (name,)).fetchone():
            raise ValueError("공고에서 사용 중인 분류는 삭제할 수 없습니다.")
        with self._db:
            self._db.execute("DELETE FROM categories WHERE name = ?", (name,))

    def notices(self, query="", category="전체", status="전체"):
        rows = self._rows("SELECT * FROM notices ORDER BY id")
        query = query.strip().casefold()
        return [row for row in rows
                if (category == "전체" or row["category"] == category)
                and (status == "전체" or row["status"] == status)
                and (not query or any(query in row[field].casefold() for field in ("code", "title", "agency", "region", "memo")))]

    def get_notice(self, notice_id):
        return self._require("notices", notice_id)

    def _notice_values(self, data):
        if not isinstance(data, dict):
            raise ValueError("공고 입력 형식이 올바르지 않습니다.")
        row = {key: _text(data.get(key), label) for key, label in (
            ("code", "공고 코드"), ("title", "공고 제목"), ("agency", "기관명"),
            ("category", "분류"), ("region", "지역"), ("deadline", "마감일"), ("status", "상태"),
        )}
        if not row["code"].startswith("DEMO-"):
            raise ValueError("공고 코드는 DEMO-로 시작해야 합니다.")
        if row["category"] not in self.categories():
            raise ValueError("등록된 분류를 선택해 주세요.")
        if row["status"] not in NOTICE_STATUSES:
            raise ValueError("공고 상태가 올바르지 않습니다.")
        try:
            if date.fromisoformat(row["deadline"]).isoformat() != row["deadline"]:
                raise ValueError
        except ValueError:
            raise ValueError("마감일은 유효한 YYYY-MM-DD 날짜로 입력해 주세요.") from None
        if not "2000-01-01" <= row["deadline"] <= "2100-12-31":
            raise ValueError("마감일은 2000-01-01부터 2100-12-31 사이로 입력해 주세요.")
        row["base_amount"] = _amount(data.get("base_amount"))
        row["memo"] = _text(data.get("memo", ""), "메모", required=False)
        return tuple(row[field] for field in NOTICE_FIELDS)

    def save_notice(self, data, notice_id=None):
        if notice_id is not None:
            self.get_notice(notice_id)
        values = self._notice_values(data)
        existing = self._db.execute("SELECT id FROM notices WHERE code = ?", (values[0],)).fetchone()
        if existing and existing[0] != notice_id:
            raise ValueError("이미 존재하는 공고 코드입니다.")
        with self._db:
            if notice_id is None:
                return self._db.execute(f"INSERT INTO notices ({','.join(NOTICE_FIELDS)}) VALUES (?,?,?,?,?,?,?,?,?)", values).lastrowid
            self._db.execute(f"UPDATE notices SET {','.join(field + '=?' for field in NOTICE_FIELDS)} WHERE id=?", (*values, notice_id))
        return notice_id

    def delete_notice(self, notice_id):
        self.get_notice(notice_id)
        with self._db:
            self._db.execute("DELETE FROM notices WHERE id = ?", (notice_id,))

    def submissions(self):
        return self._rows("""SELECT s.*, n.title AS notice_title, n.code AS notice_code
                             FROM submissions s JOIN notices n ON n.id = s.notice_id ORDER BY s.id""")

    def save_submission(self, data, submission_id=None):
        if not isinstance(data, dict):
            raise ValueError("참가 입력 형식이 올바르지 않습니다.")
        if submission_id is not None:
            self._require("submissions", submission_id)
        notice_id = self.get_notice(data.get("notice_id"))["id"]
        company = _text(data.get("company"), "가상 참가자 이름")
        amount = _amount(data.get("amount"))
        status = _text(data.get("status"), "참가 상태")
        if status not in SUBMISSION_STATUSES:
            raise ValueError("참가 상태가 올바르지 않습니다.")
        values = (notice_id, company, amount, status, _text(data.get("memo", ""), "메모", required=False))
        with self._db:
            if submission_id is None:
                return self._db.execute("INSERT INTO submissions (notice_id,company,amount,status,memo) VALUES (?,?,?,?,?)", values).lastrowid
            self._db.execute("UPDATE submissions SET notice_id=?,company=?,amount=?,status=?,memo=? WHERE id=?", (*values, submission_id))
        return submission_id

    def delete_submission(self, submission_id):
        self._require("submissions", submission_id)
        with self._db:
            self._db.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))

    def results(self):
        return self._rows("""SELECT r.*, n.title AS notice_title, n.code AS notice_code
                             FROM results r JOIN notices n ON n.id = r.notice_id ORDER BY r.notice_id""")

    def save_result(self, data):
        if not isinstance(data, dict):
            raise ValueError("결과 입력 형식이 올바르지 않습니다.")
        notice_id = self.get_notice(data.get("notice_id"))["id"]
        outcome = _text(data.get("outcome"), "결과 상태")
        if outcome not in RESULT_OUTCOMES:
            raise ValueError("결과 상태가 올바르지 않습니다.")
        amount = _amount(data.get("amount"))
        note = _text(data.get("note", ""), "결과 메모", required=False)
        with self._db:
            self._db.execute("""INSERT INTO results (notice_id,outcome,amount,note) VALUES (?,?,?,?)
                                ON CONFLICT(notice_id) DO UPDATE SET outcome=excluded.outcome, amount=excluded.amount, note=excluded.note""",
                             (notice_id, outcome, amount, note))
        return notice_id

    def delete_result(self, notice_id):
        self._require("results", notice_id, "notice_id")
        with self._db:
            self._db.execute("DELETE FROM results WHERE notice_id = ?", (notice_id,))

    def csv_template(self):
        categories = self.categories()
        if not categories:
            raise ValueError("CSV 샘플을 만들려면 분류를 먼저 등록해 주세요.")
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(NOTICE_FIELDS)
        writer.writerow(("DEMO-CSV-001", "가상 CSV 체험 공고", "가상 CSV 체험센터", categories[0], "가상 동부", 15000000, "2026-10-30", "접수중", "새로 만든 CSV 데모 샘플"))
        return output.getvalue().encode("utf-8-sig")

    def import_csv(self, content):
        if not isinstance(content, bytes) or len(content) > 2 * 1024 * 1024:
            raise ValueError("CSV 파일은 2MB 이하의 파일이어야 합니다.")
        try:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
            if reader.fieldnames != list(NOTICE_FIELDS):
                raise ValueError("CSV 열 이름과 순서는 제공된 샘플과 같아야 합니다.")
            rows = []
            codes = {row[0] for row in self._db.execute("SELECT code FROM notices")}
            for number, data in enumerate(reader, 1):
                if number > 100:
                    raise ValueError("CSV는 한 번에 100행까지 가져올 수 있습니다.")
                if set(data) != set(NOTICE_FIELDS) or any(value is None for value in data.values()):
                    raise ValueError(f"CSV {number}번째 데이터 행의 열 개수가 올바르지 않습니다.")
                values = self._notice_values(data)
                if values[0] in codes:
                    raise ValueError(f"CSV 공고 코드가 중복되었습니다: {values[0]}")
                codes.add(values[0])
                rows.append(values)
        except (UnicodeDecodeError, csv.Error):
            raise ValueError("UTF-8 형식의 올바른 CSV 파일을 선택해 주세요.") from None
        if not rows:
            raise ValueError("CSV에 가져올 데이터가 없습니다.")
        with self._db:
            self._db.executemany(f"INSERT INTO notices ({','.join(NOTICE_FIELDS)}) VALUES (?,?,?,?,?,?,?,?,?)", rows)
        return len(rows)
