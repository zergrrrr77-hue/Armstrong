"""에르덴 2단계: 게임 화면에 보이는 이름을 에르덴 용어 사전으로 바꾼다(코드 id·저장 id는 그대로).
실행: python3 forgotten-forge/tools/lineage/erden_rename.py
- 같은 파일에 두 번 돌려도 결과가 같다(이미 바뀐 글자는 다시 바뀌지 않음).
- 순서가 중요하다: 긴 이름을 먼저 바꿔야 짧은 이름이 그 안을 잘못 건드리지 않는다.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, 'game_template.html')

# (찾을 글자, 바꿀 글자) — 위에서부터 차례로 적용
RENAMES = [
    # 게임 이름
    ('<title>잊혀진 대장간</title>', '<title>에르덴 : 별의 심장</title>'),
    ('<h1>잊혀진 대장간</h1>', '<h1>에르덴 : 별의 심장</h1>'),
    ('// 잊혀진 대장간', '// 에르덴 : 별의 심장'),
    # 월드보스 (긴 이름부터)
    ('심연의 리치 군주 벨카르', '잊힌 기억의 리치 모르벤'),
    ('피의 군주 그롬마르', '몰락의 군주 그롬마르'),
    ('피의 군주', '몰락의 군주'),
    ('벨카르', '모르벤'),
    ('피의 제단', '몰락의 제단'),
    # 보스·던전
    ('몰락한 왕의 지하 묘소', '왕실 기사단 묘소'),
    ('몰락한 왕을', '봉인된 수호자를'),
    ('몰락한 왕', '봉인된 수호자'),
    ('지하 묘소', '기사단 묘소'),
    # 지역
    ("? '마을 · 안전 지대'", "? '아르델 마을 · 안전 지대'"),   # 앞 글자까지 넣어 두 번 돌려도 겹치지 않게
    ('마을 외곽', '아르델 평원'),
    ("name: '마을 광장'", "name: '아르델 광장'"),
    ("name: '북동 묘지'", "name: '옛 왕실 묘역'"),
    ("name: '기둥 회랑'", "name: '기사단 회랑'"),
    # 몬스터
    ('다이어울프', '검은 늑대'),
    ('거대 거미', '숲 거미'),
    ('늪 점액', '녹색 슬라임'),
    ('오크 전사', '고블린 전사'),
    ('오크 야영지', '고블린 야영지'),
    ('해골 병사·오크', '해골 병사·고블린 전사'),
    ('오크', '고블린 전사'),
    # 상점 NPC → 세리아 (신상은 '일곱 근원의 신상'으로 남는다)
    ('천상의 화로 신전 · 상점', '별빛 성소 · 상점'),
    ('화로의 신 헤스카르', '세리아'),
    ('헤스카르와 거래', '세리아와 거래'),
    ('aria-label="화로의 신 상점"', 'aria-label="세리아의 상점"'),
    ('화로의 신에게', '세리아에게'),
    ('화로의 신', '세리아'),
    # 화폐·등급
    ('골드', '에테르'),
    ('아데나', '에테르'),
    ('유니크', '고대'),
    # 시설
    ('웨이포인트', '별빛 표석'),
    ('신의 축복 뽑기', '별의 파편 공명'),
    ('뽑기', '공명'),
]

# 통째로 바꾸는 문장(세계관 소개·세리아 인사말)
INTRO_OLD_START = '    <p>기사·요정·마법사 중 하나를 골라'
INTRO_NEW = ('    <p><i>별이 태어난 세계, 잊힌 왕국의 마지막 이야기.</i><br>'
             '기사·요정·마법사 중 하나를 골라 아르델 평원의 숲과 늪에서 사냥하며 장비를 모으고 강해진 뒤, '
             '남동쪽 끝의 계단으로 왕실 기사단 묘소에 내려가 <b>봉인된 수호자</b>를 쓰러뜨리세요. '
             '강화 주문서로 장비를 +10까지 강화할 수 있지만, 안전 강화 구간을 넘으면 실패할 때 강화 수치가 사라집니다.</p>')
SAY_OLD_START = 'const NPC_SAY = ['
SAY_NEW = ("const NPC_SAY = ['어서 오게, 길 잃은 별이여. 오늘은 무엇이 필요하지?', "
           "'이 물약 말인가? 삼백 년 전에도 같은 값이었지… 아, 농담일세.', "
           "'강화는 욕심을 시험하지. 안전한 구간을 넘을 땐 각오하게.',\n"
           "  '월드보스의 기척이 느껴지는군… 여섯 시간마다 깨어난다네.', "
           "'쓸모없는 장비는 내게 넘기게. 값은 후하게 쳐 주지.'];")


def replace_block(text, start, new_block, end_mark):
    """start로 시작해 end_mark로 끝나는 부분을 new_block으로 바꾼다. 못 찾으면 이미 바뀐 것으로 본다."""
    i = text.find(start)
    if i < 0:
        return text, False
    j = text.find(end_mark, i)
    if j < 0:
        raise SystemExit(f'끝 표시를 찾지 못함: {end_mark!r}')
    return text[:i] + new_block + text[j + len(end_mark):], True


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else TEMPLATE
    text = open(path, encoding='utf-8').read()
    before = text
    text, a = replace_block(text, INTRO_OLD_START, INTRO_NEW, '</p>')
    b = False
    if SAY_NEW not in text:   # 이미 바뀌었으면 건너뜀
        text, b = replace_block(text, SAY_OLD_START, SAY_NEW, '];')
    counts = []
    for old, new in RENAMES:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            counts.append(f'{old} → {new}: {n}곳')
    if text == before:
        print('바꿀 것 없음 (이미 적용됨)')
        return
    open(path, 'w', encoding='utf-8').write(text)
    print('소개문' if a else '', '인사말' if b else '')
    print('\n'.join(counts))


if __name__ == '__main__':
    main()
