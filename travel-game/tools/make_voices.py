"""Gate 27 음성 파일 생성기.

audio/lines.json 의 대사를 Supertonic 3(Supertone, MIT) 신경망 음성으로 읽어
audio/<id>_ko.mp3, audio/<id>_en.mp3 로 저장한다. 공항 방송(kind=pa)은 스피커 느낌의
대역 제한, 압축, 짧은 잔향을 입힌다.

실행:
  pip install sherpa-onnx soundfile numpy      # ffmpeg 도 필요
  SUPERTONIC_DIR=/path/to/supertonic-3-model python tools/make_voices.py [id ...]

SUPERTONIC_DIR 에는 duration_predictor.onnx, text_encoder.onnx, vector_estimator.onnx,
vocoder.onnx, tts.json, unicode_indexer.bin, voice.bin 이 있어야 한다.
"""
import json, os, re, subprocess, sys, tempfile

import numpy as np
import sherpa_onnx as so
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, '..', 'audio')
MODEL = os.environ.get('SUPERTONIC_DIR', '')

# 화면 자막의 숫자·약어를 방송에서 실제로 읽는 말로 바꾼다 (게임 코드의 KO_SAY/EN_SAY 와 같은 규칙)
KO_SAY = [(r'071편', '공칠일 편'), (r'723편', '칠이삼 편'), (r'오후 6시 30분', '오후 여섯 시 삼십 분'), (r'eTA', '이티에이'),
          (r'27번', '이십칠 번'), (r'14번', '십사 번'), (r'1인당', '한 분당'), (r'가방 1개', '가방 한 개'),
          (r'소지품 1개', '소지품 한 개'), (r'1번', '일 번'), (r'2번', '이 번'), (r'3번', '삼 번'), (r'4번', '사 번'),
          (r'32A', '삼십이 에이'), (r'3만 5천 피트', '삼만 오천 피트'), (r'9시간 40분', '아홉 시간 사십 분'),
          (r'오후 1시 10분', '오후 한 시 십 분'), (r'30분 후', '삼십 분 후'), (r'카페 27', '카페 이십칠')]
EN_SAY = [(r'flight 071', 'flight zero seven one'), (r'flight 723', 'flight seven two three'), (r'gate 27', 'gate twenty-seven'),
          (r'gate 14', 'gate fourteen'), (r'eTA', 'E.T.A.'), (r'6:30 p\.m\.', 'six thirty p.m.'),
          (r'groups 1 and 2', 'groups one and two'), (r'[Gg]roups 3 and 4', 'Groups three and four'),
          (r'35,000 feet', 'thirty-five thousand feet'), (r'9 hours and 40 minutes', 'nine hours and forty minutes'),
          (r'1:10 p\.m\.', 'one ten p.m.'), (r'30 minutes', 'thirty minutes')]

PA_FILTER = ('highpass=f=170,lowpass=f=6800,'
             'acompressor=threshold=-20dB:ratio=3:attack=5:release=150,'
             'aecho=0.85:0.55:38|83:0.22|0.12,loudnorm=I=-17:TP=-1.5:LRA=7')
# 기내 방송: 천장 스피커처럼 더 좁은 대역, 짧은 울림
CABIN_FILTER = ('highpass=f=240,lowpass=f=5200,acompressor=threshold=-20dB:ratio=3.5:attack=5:release=120,'
                'aecho=0.8:0.4:18|31:0.18|0.1,loudnorm=I=-17:TP=-1.5:LRA=6')
TALK_FILTER = 'highpass=f=90,loudnorm=I=-18:TP=-1.5:LRA=7'


def to_say(text, rules):
    for a, b in rules:
        text = re.sub(a, b, text)
    return text


def sentences(text):
    return [s for s in re.split(r'(?<=[.!?])\s+', text) if s]


def load_tts():
    if not MODEL:
        sys.exit('SUPERTONIC_DIR 를 지정하세요')
    p = lambda n: os.path.join(MODEL, n)
    cfg = so.OfflineTtsConfig(model=so.OfflineTtsModelConfig(
        supertonic=so.OfflineTtsSupertonicModelConfig(
            duration_predictor=p('duration_predictor.onnx'), text_encoder=p('text_encoder.onnx'),
            vector_estimator=p('vector_estimator.onnx'), vocoder=p('vocoder.onnx'), tts_json=p('tts.json'),
            unicode_indexer=p('unicode_indexer.bin'), voice_style=p('voice.bin')),
        num_threads=4))
    return so.OfflineTts(cfg)


def speak(tts, text, lang, sid, speed):
    """문장마다 따로 읽고 사이에 쉼을 넣어 방송처럼 또박또박 이어 붙인다."""
    sr, parts = tts.sample_rate, []
    for s in sentences(text):
        g = so.GenerationConfig()
        g.sid, g.num_steps, g.speed, g.extra = sid, 10, speed, {'lang': lang}
        a = tts.generate(s, g)
        x = np.asarray(a.samples, dtype=np.float32)
        parts += [x, np.zeros(int(sr * (0.42 if lang == 'ko' else 0.36)), np.float32)]
    lead = np.zeros(int(sr * 0.08), np.float32)
    return np.concatenate([lead] + parts), sr


def encode(x, sr, out, kind):
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        sf.write(f.name, x, sr)
        wav = f.name
    flt = {'pa': PA_FILTER, 'cabin': CABIN_FILTER}.get(kind, TALK_FILTER)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-af', flt, '-ac', '1', '-ar', '32000',
                    '-c:a', 'libmp3lame', '-b:a', '56k', out], check=True)
    os.unlink(wav)


def main():
    lines = json.load(open(os.path.join(AUDIO, 'lines.json'), encoding='utf-8'))
    only = set(sys.argv[1:])
    tts = load_tts()
    for lid, ln in lines.items():
        if lid.startswith('_') or (only and lid not in only):
            continue
        speed = 0.94 if ln['kind'] in ('pa', 'cabin') else 1.0
        for lang, rules in (('ko', KO_SAY), ('en', EN_SAY), ('fr', [])):
            # say='en' 인 대사의 ko 는 자막 번역일 뿐이라 읽지 않는다
            if lang not in ln or (lang == 'ko' and ln.get('say') == 'en'):
                continue
            x, sr = speak(tts, to_say(ln[lang], rules), lang, ln['voice'], speed)
            out = os.path.join(AUDIO, f'{lid}_{lang}.mp3')
            encode(x, sr, out, ln['kind'])
            print(f'{out}  {len(x) / sr:.1f}s')


if __name__ == '__main__':
    main()
