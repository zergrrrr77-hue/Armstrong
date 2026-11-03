"""게임 에셋을 '새 프로젝트용 에셋 팩'으로 내보낸다.

실행: python3 forgotten-forge/tools/lineage/export_pack.py <출력 폴더>
- 원본 시트(sheets/) + 쓰기 쉬운 낱개 파일(characters/, monsters/, effects/, props/, tiles/, items/, ui/)
- 각 폴더에 JSON(프레임 크기·기준점·프레임 수)과 미리보기(previews/)
효과음 WAV는 tests 쪽 node 스크립트(export_sounds.js)가 sounds/ 에 만든다.
"""
import json
import os
import shutil
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, '..', '..', 'lineage-assets'))
DIRS = ['S', 'SE', 'E', 'NE', 'N', 'NW', 'W', 'SW']
GROUP_EN = {'자연': 'nature', '마을': 'village', '마을 생활': 'town_life', '묘지·폐허': 'graveyard', '성채': 'castle', '던전': 'dungeon', '기타': 'misc'}
CAT_EN = {'무기': 'weapons', '방어구': 'armor', '장신구': 'accessories', '소모품': 'consumables', '기타': 'misc'}


def save(im, out, *p):
    path = os.path.join(out, *p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True)
    return os.path.relpath(path, out).replace(os.sep, '/')


def dump(obj, out, *p):
    path = os.path.join(out, *p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def actor(meta, group, name, out, folder):
    """캐릭터·몬스터: 동작 × 방향마다 가로 띠 PNG + 낱장 프레임 + JSON."""
    s = meta[group][name]
    sheet = Image.open(os.path.join(SRC, s['sheet'])).convert('RGBA')
    fw, fh = s['fw'], s['fh']
    info = dict(name=name, label=s['label'], frame_w=fw, frame_h=fh, anchor_x=s['ax'], anchor_y=s['ay'],
                anchor_note='기준점 = 발 중앙(바닥 접점). 그릴 때 (x - anchor_x, y - anchor_y)',
                directions=DIRS, animations={}, fps=10, files={})
    for an, (st, n) in s['anims'].items():
        info['animations'][an] = n
        for di, d in enumerate(DIRS):
            strip = sheet.crop((st * fw, di * fh, (st + n) * fw, (di + 1) * fh))
            info['files'][f'{an}_{d}'] = save(strip, out, folder, name, 'strips', f'{name}_{an}_{d}.png')
            for f in range(n):
                save(strip.crop((f * fw, 0, (f + 1) * fw, fh)), out, folder, name, 'frames', an, d, f'{f:02d}.png')
    info['full_sheet'] = save(sheet, out, 'sheets', group, f'{name}.png')
    dump(info, out, folder, name, f'{name}.json')
    # 미리보기: 남동(SE) 방향 각 동작 첫 프레임
    pv = Image.new('RGBA', (fw * len(s['anims']), fh), (40, 44, 36, 255))
    for k, (an, (st, n)) in enumerate(s['anims'].items()):
        fr = sheet.crop(((st + min(n - 1, n // 2)) * fw, 1 * fh, (st + min(n - 1, n // 2) + 1) * fw, 2 * fh))
        pv.alpha_composite(fr, (k * fw, 0))
    save(pv, out, 'previews', folder, f'{name}.png')
    return info


def main(out):
    if os.path.exists(out):
        shutil.rmtree(out)
    meta = json.load(open(os.path.join(SRC, 'meta.json'), encoding='utf-8'))
    index = {'characters': {}, 'monsters': {}, 'props': {}, 'effects': {}, 'tiles': {}, 'items': {}, 'ui': {}}

    for k in meta['characters']:
        index['characters'][k] = actor(meta, 'characters', k, out, 'characters')['label']
    for k in meta['monsters']:
        index['monsters'][k] = actor(meta, 'monsters', k, out, 'monsters')['label']

    # 소품(건물·나무·던전 소품): 낱개 PNG(애니메이션은 프레임별) + 기준점
    props = {}
    for k, p in meta['props'].items():
        sh = Image.open(os.path.join(SRC, p['sheet'])).convert('RGBA')
        files = []
        for f in range(p['frames']):
            fr = sh.crop((f * p['fw'], 0, (f + 1) * p['fw'], p['fh']))
            files.append(save(fr, out, 'props', GROUP_EN.get(p.get('group') or '기타', 'misc'), f"{k}.png" if p['frames'] == 1 else f"{k}_{f}.png"))
        save(sh, out, 'sheets', 'props', f'{k}.png')
        props[k] = dict(label=p['label'], group=p.get('group'), w=p['fw'], h=p['fh'], anchor_x=p['ax'], anchor_y=p['ay'], frames=p['frames'], files=files)
        index['props'][k] = p['label']
    dump(dict(note='기준점 = 타일 중심 바닥. 쿼터뷰 2:1(타일 64×32)에서 그대로 쓰면 됨', props=props), out, 'props', 'props.json')

    # 이펙트: 층(under=캐릭터 뒤, over=캐릭터 앞, solid=일반 혼합)·방향별 띠
    fx = {}
    for k, e in meta['effects'].items():
        sh = Image.open(os.path.join(SRC, e['sheet'])).convert('RGBA')
        files = {}
        groups = DIRS if e['dirs'] else ['all']
        row = 0
        for g in groups:
            for ly in e['layers']:
                strip = sh.crop((0, row * e['fh'], e['frames'] * e['fw'], (row + 1) * e['fh']))
                files[f'{ly}_{g}'] = save(strip, out, 'effects', k, f'{k}_{ly}_{g}.png')
                row += 1
        save(sh, out, 'sheets', 'effects', f'{k}.png')
        fx[k] = dict(label=e['label'], frame_w=e['fw'], frame_h=e['fh'], anchor_x=e['ax'], anchor_y=e['ay'], frames=e['frames'],
                     by_direction=e['dirs'], layers=e['layers'], blend={ly: e['blend'][ly] for ly in e['layers']}, color=e['color'], files=files)
        index['effects'][k] = e['label']
    dump(dict(note="under·over 층은 'lighter'(가산 혼합)로, solid 층은 일반 혼합으로 그린다. 10fps", effects=fx), out, 'effects', 'effects.json')

    # 바닥 타일: 지형 9종 × 변형 4(물은 애니메이션 4프레임)
    T = meta['tiles']
    tim = Image.open(os.path.join(SRC, T['sheet'])).convert('RGBA')
    tiles = {}
    for r, row in enumerate(T['rows']):
        tiles[row['name']] = dict(label=row['label'], files=[save(tim.crop((c * T['w'], r * T['h'], (c + 1) * T['w'], (r + 1) * T['h'])), out, 'tiles', row['name'], f"{row['name']}_{c}.png") for c in range(T['cols'])])
        index['tiles'][row['name']] = row['label']
    save(tim, out, 'sheets', 'tiles.png')
    dump(dict(tile_w=T['w'], tile_h=T['h'], note='2:1 마름모 타일. 화면 좌표 = ((i-j)*32, (i+j)*16)', tiles=tiles), out, 'tiles', 'tiles.json')

    # 아이템 아이콘 32×32 + 등급 테두리 + 강화 무기 아이콘
    A = meta['item_atlas']
    atlas = Image.open(os.path.join(SRC, A['sheet'])).convert('RGBA')
    items = {}
    for k, it in meta['items'].items():
        i = it['index']
        ic = atlas.crop(((i % A['cols']) * A['w'], (i // A['cols']) * A['h'], (i % A['cols'] + 1) * A['w'], (i // A['cols'] + 1) * A['h']))
        items[k] = dict(name=it['name'], category=it['cat'], grade=it['grade'], file=save(ic, out, 'items', CAT_EN.get(it['cat'], 'misc'), f'{k}.png'),
                        file_x2=save(ic.resize((64, 64), Image.NEAREST), out, 'items', CAT_EN.get(it['cat'], 'misc'), 'x2', f'{k}.png'))
        index['items'][k] = it['name']
    save(atlas, out, 'sheets', 'items_icons.png')
    dump(dict(icon=32, items=items), out, 'items', 'items.json')
    G = meta['grades']
    gim = Image.open(os.path.join(SRC, G['sheet'])).convert('RGBA')
    grades = {g['id']: dict(label=g['label'], color=g['color'], file=save(gim.crop((k * 36, 0, (k + 1) * 36, 36)), out, 'ui', 'grade_frames', f"{g['id']}.png")) for k, g in enumerate(G['list'])}
    E = meta['enchant_icons']
    eim = Image.open(os.path.join(SRC, E['sheet'])).convert('RGBA')
    ench = {w: {f'+{lv}': save(eim.crop((c * 32, r * 32, (c + 1) * 32, (r + 1) * 32)), out, 'ui', 'enchant_weapons', f'{w}_plus{lv}.png') for c, lv in enumerate(E['levels'])} for r, w in enumerate(E['rows'])}
    dump(dict(grade_frames=grades, enchant_weapon_icons=ench, note='등급 테두리 36×36(가운데 32×32에 아이콘). 강화 아이콘은 +7부터 빛남'), out, 'ui', 'ui.json')
    index['ui'] = {'grade_frames': '등급 테두리 5종', 'enchant_weapons': '강화 단계별 무기 아이콘'}

    # 음악
    if os.path.isdir(os.path.join(SRC, 'audio', 'bgm')):
        for f in os.listdir(os.path.join(SRC, 'audio', 'bgm')):
            os.makedirs(os.path.join(out, 'music'), exist_ok=True)
            shutil.copy(os.path.join(SRC, 'audio', 'bgm', f), os.path.join(out, 'music', f))
    shutil.copy(os.path.join(SRC, 'audio', 'sfx.js'), os.path.join(out, 'sounds_engine_sfx.js'))
    shutil.copy(os.path.join(SRC, 'meta.json'), os.path.join(out, 'sheets', 'meta.json'))
    dump(index, out, 'index.json')
    print('done', out)


if __name__ == '__main__':
    main(sys.argv[1])
