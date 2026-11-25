"""KRDict (한국어기초사전, National Institute of Korean Language) as a local SQLite dictionary.

Source: the official Excel export as converted on Hugging Face (hac541309/basic_korean_dict, CC BY-SA 3.0): one row
of text per meaning, '표제어: 눈, 구분: 단어, 품사: 명사, …'. We keep Korean + English. Built once, at image build time
(ADR-12): `python -m lmx.languages.korean.krdict <parquet> <out.sqlite>` (needs pyarrow, which the app itself doesn't).
"""

import re
import sqlite3
import sys
from collections.abc import Iterable
from pathlib import Path

from ..dictionary import Idiom, Sense

SOURCE = {
    'source': 'KRDict (한국어기초사전), via huggingface.co/datasets/hac541309/basic_korean_dict',
    'revision': '1ba29964518a8e859e5898cdeacfc46ff8215a60',
    'sha256': 'ea7fc8a2fba3d5d4b3f2e561371e72543300c08a2e54f8acd3e27878bbb29e78',
    'license': 'CC BY-SA 3.0 (https://krdict.korean.go.kr)',
}

BASE_FIELDS = [
    '표제어',
    '구분',
    '품사',
    '고유어 여부',
    '원어',
    '발음',
    '어휘 등급',
    '활용',
    '문형',
    '문형 참고',
    '관련어',
    '파생어',
    '가봐라',
    '뜻풀이',
    '용례',
    '의미 참고',
    '전체 참고',
    '의미 범주',
    '주제 및 상황 범주',
    '다중 매체 정보',
    '부표제어',
    '부표제어 문형',
    '부표제어 뜻풀이',
    '부표제어 용례',
    '부표제어 관련어',
]
LANGS = [
    '영어',
    '몽골어',
    '베트남어',
    '타이어',
    '인도네시아어',
    '러시아어',
    '일본어',
    '프랑스어',
    '스페인어',
    '아랍어',
    '중국어',
]
FIELDS = [
    *BASE_FIELDS,
    *(
        f'{lang} {part}'
        for lang in LANGS
        for part in ('대역어', '대역어 뜻풀이', '부표제어 대역어', '부표제어 대역어 뜻풀이')
    ),
]
# values may contain ", " themselves, so only split before a KNOWN key
# (longest first, so '영어 대역어 뜻풀이' wins over '영어 대역어')
KEY = re.compile(r'(?:^|, )(' + '|'.join(sorted(map(re.escape, FIELDS), key=len, reverse=True)) + r'): ')

POS = {
    '명사': 'noun',
    '의존 명사': 'noun',
    '대명사': 'noun',
    '수사': 'noun',
    '동사': 'verb',
    '보조 동사': 'verb',
    '형용사': 'adjective',
    '보조 형용사': 'adjective',
    '부사': 'adverb',
}
LEVEL = {'초급': 'beginner', '중급': 'intermediate', '고급': 'advanced'}
KIND = {'단어': 'word', '구': 'phrase', '문법‧표현': 'grammar'}
IDIOM_KIND = {'관용구': 'idiom', '속담': 'proverb'}
EXAMPLE = re.compile(r'^<문장>\s*(.+)$', re.M)

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE senses (id INTEGER PRIMARY KEY, headword TEXT NOT NULL, kind TEXT NOT NULL, pos TEXT NOT NULL,
  gloss TEXT, definition TEXT, native TEXT, level TEXT, origin TEXT, pronunciation TEXT, examples TEXT);
CREATE INDEX senses_headword ON senses(headword);
CREATE TABLE idioms (id INTEGER PRIMARY KEY, base TEXT NOT NULL, text TEXT NOT NULL, kind TEXT NOT NULL,
  gloss TEXT, definition TEXT, native TEXT);
CREATE INDEX idioms_base ON idioms(base);
"""


def fields(text: str) -> dict[str, str]:
    """'표제어: 방광, 구분: 단어, …' -> {'표제어': '방광', '구분': '단어', …}"""
    marks = list(KEY.finditer(text))
    return {
        m.group(1): text[m.end() : marks[i + 1].start() if i + 1 < len(marks) else len(text)].strip()
        for i, m in enumerate(marks)
    }


def level(raw: str) -> str:
    return LEVEL.get(raw.split(',')[0].strip(), '')  # '중급, 검색용 이형태: 복스' -> intermediate


def build(rows: Iterable[str], db_path: Path, meta: dict[str, str] | None = None) -> tuple[int, int]:
    """Rows of export text -> SQLite dictionary at db_path (replaced). -> (senses, idioms)"""
    db_path.unlink(missing_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    n_s = n_i = 0
    for text in rows:
        f = fields(text)
        head = f.get('표제어', '').strip()
        if not head:
            continue
        if f.get('구분') == '부표제어':
            m = re.match(r'\[([^\]]+)\]\s*(.+)', f.get('부표제어', ''))
            if not m:
                continue
            con.execute(
                'INSERT INTO idioms (base, text, kind, gloss, definition, native) VALUES (?,?,?,?,?,?)',
                (
                    head,
                    m.group(2).strip(),
                    IDIOM_KIND.get(m.group(1), 'idiom'),
                    f.get('영어 부표제어 대역어', ''),
                    f.get('영어 부표제어 대역어 뜻풀이', ''),
                    f.get('부표제어 뜻풀이', ''),
                ),
            )
            n_i += 1
            continue
        examples = '\n'.join(EXAMPLE.findall(f.get('용례', ''))[:3])
        con.execute(
            'INSERT INTO senses (headword, kind, pos, gloss, definition, native, level, origin, pronunciation,'
            ' examples) VALUES (?,?,?,?,?,?,?,?,?,?)',
            (
                head,
                KIND.get(f.get('구분', ''), 'word'),
                POS.get(f.get('품사', ''), 'other'),
                f.get('영어 대역어', ''),
                f.get('영어 대역어 뜻풀이', ''),
                f.get('뜻풀이', ''),
                level(f.get('어휘 등급', '')),
                f.get('원어', ''),
                f.get('발음', ''),
                examples,
            ),
        )
        n_s += 1
    con.executemany(
        'INSERT INTO meta VALUES (?,?)', sorted({**(meta or {}), 'senses': str(n_s), 'idioms': str(n_i)}.items())
    )
    con.commit()
    con.execute('VACUUM')
    con.close()
    return n_s, n_i


class KrDict:
    """Read-only lookups. A missing file gives an empty dictionary (the app still runs, just without meanings)."""

    def __init__(self, path: Path | None):
        self.con = (
            sqlite3.connect(f'file:{path}?mode=ro', uri=True, check_same_thread=False)
            if path is not None and path.is_file()
            else None
        )

    @property
    def available(self) -> bool:
        return self.con is not None

    def meta(self) -> dict[str, str]:
        return dict(self.con.execute('SELECT key, value FROM meta').fetchall()) if self.con else {}

    def senses(self, headword: str) -> list[Sense]:
        """Word senses (not grammar/phrases) in dictionary order."""
        if self.con is None:
            return []
        rows = self.con.execute(
            'SELECT headword, pos, gloss, definition, native, level, origin, pronunciation, examples FROM senses '
            "WHERE headword = ? AND kind = 'word' ORDER BY id",
            (headword,),
        ).fetchall()
        return [
            Sense(
                headword=h,
                pos=p,
                gloss=g or '',
                definition=d or '',
                native=n or '',
                level=lv or '',
                origin=o or '',
                pronunciation=pr or '',
                examples=tuple(x for x in (ex or '').split('\n') if x),
            )
            for h, p, g, d, n, lv, o, pr, ex in rows
        ]

    def has(self, headword: str) -> bool:
        if self.con is None:
            return False
        return (
            self.con.execute("SELECT 1 FROM senses WHERE headword = ? AND kind = 'word'", (headword,)).fetchone()
            is not None
        )

    def idioms(self, headword: str) -> list[Idiom]:
        """Idioms/proverbs listed under the headword."""
        if self.con is None:
            return []
        rows = self.con.execute(
            'SELECT text, kind, gloss, definition, native FROM idioms WHERE base = ? ORDER BY id', (headword,)
        ).fetchall()
        return [Idiom(t, k, g or '', d or '', n or '') for t, k, g, d, n in rows]


def main(argv: list[str]) -> None:  # pragma: no cover  (build-time tool, exercised by the Docker build)
    import pyarrow.parquet as pq  # pyright: ignore[reportMissingImports]

    rows: list[str] = pq.read_table(argv[0]).column('text').to_pylist()
    print(build(rows, Path(argv[1]), SOURCE))


if __name__ == '__main__':  # pragma: no cover
    main(sys.argv[1:])
