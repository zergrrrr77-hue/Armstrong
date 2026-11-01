"""meta.json을 넣어 lineage-assets/gallery.html 을 만든다(이미지는 상대 경로)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def write(out_dir):
    with open(os.path.join(out_dir, 'meta.json'), encoding='utf-8') as fp:
        meta = json.load(fp)
    with open(os.path.join(HERE, 'gallery_template.html'), encoding='utf-8') as fp:
        tpl = fp.read()
    html = tpl.replace('/*META*/{}/*END*/', json.dumps(meta, ensure_ascii=False, separators=(',', ':')))
    p = os.path.join(out_dir, 'gallery.html')
    with open(p, 'w', encoding='utf-8') as fp:
        fp.write(html)
    return p


if __name__ == '__main__':
    print(write(sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(os.path.join(HERE, '..', '..', 'lineage-assets'))))
