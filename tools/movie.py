"""Inventory, transcribe, subtitle and validate the original PS1 movie streams.

Use Python 3.11 (64-bit). Japanese transcripts stay in ignored work/source/.
Mutating commands require --apply; the default prints their planned output.
"""
import argparse
import hashlib
from functools import lru_cache
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'work/source/movies'
ANALYSIS = ROOT / 'work/source/movie_analysis'
JAR = ROOT / 'tools/vendor/jpsxdec/jpsxdec_v2.1-beta/jpsxdec.jar'
TRANSLATION = ROOT / 'work/translation/en/movies.en.json'
PATCHED = ROOT / 'work/build/movies'
# Minimum decoded luma separation (0–255) between letter interiors and outlines.
MIN_SUBTITLE_CONTRAST = 175
RENDER_STYLE = {
    'revision': 2,
    'subtitle_background': 'transparent',
    'text_rgb': [240, 240, 240],
    'outline_rgb': [0, 0, 0],
    'outline_pixels': 1,
    'lyric_credit_viewport_height': 202,
}


def load_translation():
    data = json.loads(TRANSLATION.read_text(encoding='utf-8'))
    for entry in data['movies'].values():
        if 'credits_file' in entry:
            path = (TRANSLATION.parent / entry['credits_file']).resolve()
            if path.parent != TRANSLATION.parent.resolve():
                raise ValueError('Credits file must be in the translation directory')
            entry['credits'] = json.loads(path.read_text(encoding='utf-8'))
    return data


def fingerprint(entry):
    state = {'entry': entry, 'render_style': RENDER_STYLE}
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode('utf-8')).hexdigest()


def java(args, folder, log_name):
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / log_name).open('w', encoding='utf-8') as log:
        run = subprocess.run(['java', '-Xmx2g', '-jar', str(JAR)] + [str(x) for x in args],
                             cwd=folder, stdout=log, stderr=subprocess.STDOUT)
    if run.returncode:
        raise RuntimeError(f'jPSXdec failed; see {folder / log_name}')


def decode(apply=False, movies=None):
    for path in sorted(SOURCE.glob('*.STR')):
        if movies and path.stem not in movies:
            continue
        target = ANALYSIS / path.stem
        index = target / 'original.idx'
        frames = target / 'frames'
        print('decode', path.stem, '->', frames, flush=True)
        if not apply:
            continue
        if not index.exists():
            java(['-f', path, '-x', index], target, 'index.log')
        if not (target / 'decode.done').exists():
            java(['-x', index, '-i', '0', '-vf', 'png', '-dir', frames], target, 'decode.log')
            expected = len(inventory(path)['frames'])
            actual = len(list(frames.glob('*.png')))
            if actual != expected:
                raise ValueError(f'{path.stem}: expected {expected} frames, decoded {actual}')
            (target / 'decode.done').write_text(str(actual), encoding='ascii')


@lru_cache(maxsize=16)
def font(size=12, bold=False):
    from PIL import ImageFont
    return ImageFont.truetype('C:/Windows/Fonts/' + ('arialbd.ttf' if bold else 'arial.ttf'), size)


def wrap_text(text, face, width=282):
    from PIL import Image, ImageDraw
    draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split():
            candidate = (line + ' ' + word).strip()
            if draw.textlength(candidate, font=face) > width:
                if not line:
                    raise ValueError(f'Word too wide: {word}')
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def subtitle(image, text):
    from PIL import ImageDraw
    face = font(12, True)
    lines = wrap_text(text, face)
    if len(lines) > 2:
        raise ValueError(f'Subtitle needs {len(lines)} lines: {text}')
    draw = ImageDraw.Draw(image)
    for k, line in enumerate(lines):
        draw.text((160, 205 + (2-len(lines))*7 + k*14), line, font=face,
                  anchor='mt', fill=tuple(RENDER_STYLE['text_rgb']),
                  stroke_width=RENDER_STYLE['outline_pixels'],
                  stroke_fill=tuple(RENDER_STYLE['outline_rgb']))


def check_translation(data):
    ids = set()
    count = 0
    inventory_map = {p.stem: inventory(p) for p in sorted(SOURCE.glob('*.STR'))}
    if set(data['movies']) != set(inventory_map):
        raise ValueError('Translation manifest must cover all original movies')
    for movie, entry in data['movies'].items():
        last_end = 0
        for cue in entry.get('cues', []):
            if cue['id'] in ids:
                raise ValueError(f'Duplicate ID {cue["id"]}')
            ids.add(cue['id'])
            if not (last_end <= cue['start'] < cue['end'] <= inventory_map[movie]['seconds']):
                raise ValueError(f'Invalid timing {cue["id"]}')
            last_end = cue['end']
            if len(wrap_text(cue['en'], font(12, True))) > 2:
                raise ValueError(f'Overflow {cue["id"]}: {cue["en"]}')
            if not cue['en'].isascii():
                raise ValueError(f'Non-ASCII subtitle {cue["id"]}')
            count += 1
        for label in entry.get('labels', []):
            if label['id'] in ids:
                raise ValueError(f'Duplicate ID {label["id"]}')
            ids.add(label['id'])
            x,y,w,h = label['rect']
            if not (0 <= x < x+w <= 320 and 0 <= y < y+h <= 240):
                raise ValueError(f'Label outside frame: {label["id"]}')
            if not (0 <= label['start_frame'] < label['end_frame'] <= len(inventory_map[movie]['frames'])):
                raise ValueError(f'Label outside movie: {label["id"]}')
    print('checked', len(data['movies']), 'movies;', count, 'subtitles', flush=True)


def render(apply=False, movies=None):
    from PIL import Image, ImageDraw
    data = load_translation()
    check_translation(data)
    for name, entry in data['movies'].items():
        if movies and name not in movies:
            continue
        if not entry.get('cues') and not entry.get('labels') and not entry.get('credits'):
            continue
        inv = inventory(SOURCE / (name + '.STR'))
        target = ANALYSIS / name
        edits = target / 'edits'
        print('render', name, '->', edits, flush=True)
        if not apply:
            continue
        edits.mkdir(parents=True, exist_ok=True)
        xml = ET.Element('str-replace', version='0.3')
        originals = {int(p.stem.rsplit('[', 1)[1].rstrip(']')): p for p in (target/'frames').glob('*.png')}
        roll = None
        credits = entry.get('credits')
        if credits:
            rows = credits['rows']
            roll = Image.new('RGB', (320, len(rows)*16 + 16), 'black')
            draw = ImageDraw.Draw(roll)
            for k, row in enumerate(rows):
                if isinstance(row, list):
                    left, right = row
                    draw.text((12, k*16), left, font=font(10), fill=(224,224,224))
                    draw.text((308, k*16), right, font=font(10), anchor='rt', fill=(224,224,224))
                    if draw.textlength(left,font=font(10))+draw.textlength(right,font=font(10)) > 284:
                        raise ValueError(f'Credits columns overlap: {row}')
                else:
                    draw.text((160, k*16), row, font=font(11), anchor='mt', fill=(224,224,224))
                    if draw.textlength(row,font=font(11)) > 292:
                        raise ValueError(f'Credit overflow: {row}')
        for frame in inv['frames']:
            t = frame['sector'] / 150
            cue = next((c for c in entry.get('cues', []) if c['start'] <= t < c['end']), None)
            labels = [c for c in entry.get('labels', [])
                      if (c['start_frame'] <= frame['index'] < c['end_frame']
                          if 'start_frame' in c else c['start'] <= t < c['end'])]
            is_roll = bool(credits and t >= credits['start'])
            if not cue and not labels and not is_roll:
                continue
            if is_roll:
                image = Image.new('RGB', (320, 240), 'black')
                if t < credits['end']:
                    duration = credits['end'] - credits['start']
                    y = 240 - round((t - credits['start']) / duration * (roll.height + 240))
                    # Reserve credit layout space for lyrics without drawing a
                    # subtitle panel over the image. The roll's own background
                    # remains black, and the song text is drawn transparently.
                    height = RENDER_STYLE['lyric_credit_viewport_height'] if t < 156.2 else 240
                    viewport = Image.new('RGB', (320, height), 'black')
                    viewport.paste(roll, (0, y))
                    image.paste(viewport, (0, 0))
                elif t >= credits['end_card_start']:
                    ImageDraw.Draw(image).text((160, 110), 'THE END', font=font(28, True),
                                               anchor='mt', fill=(224,224,224))
            else:
                image = Image.open(originals[frame['index']]).convert('RGB')
            if cue:
                subtitle(image, cue['en'])
            for label in labels:
                rect = label['rect']
                draw = ImageDraw.Draw(image)
                draw.rectangle((rect[0], rect[1], rect[0]+rect[2]-1, rect[1]+rect[3]-1), fill=(10,10,10))
                draw.text((rect[0]+rect[2]/2,rect[1]+4), label['en'], font=font(12,True),
                          anchor='mt', fill=(240,240,240))
            output = edits / f'{frame["index"]:05d}.png'
            image.save(output)
            if is_roll:
                node = ET.SubElement(xml, 'replace', frame=str(frame['index']))
            elif labels:
                node = ET.SubElement(xml, 'partial-replace', frame=str(frame['index']))
            else:
                node = ET.SubElement(xml, 'partial-replace', frame=str(frame['index']), rect='0,192,320,48')
            node.text = str(output)
        ET.ElementTree(xml).write(target/'replace.xml', encoding='utf-8', xml_declaration=True)
        write_json(target/'render.json', {'translation_sha256':fingerprint(entry),
                                        'source_sha256':inv['sha256'],'frames':len(xml),
                                        'render_style':RENDER_STYLE})
        print(name, len(xml), 'frames to replace', flush=True)


def subtitle_contrast(path, entry):
    """Measure the actual decoded pixels in every frame with an active cue."""
    import numpy as np
    from PIL import Image

    frames = inventory(path)['frames']
    times = np.array([frame['sector'] / 150 for frame in frames])
    decoded = subprocess.check_output([
        'ffmpeg', '-v', 'error', '-xerror', '-i', str(path), '-map', '0:v:0',
        '-vf', 'crop=320:48:0:192,format=gray', '-fps_mode', 'passthrough',
        '-f', 'rawvideo', '-'])
    strips = np.frombuffer(decoded, dtype=np.uint8).reshape(len(frames), 48, 320)
    weak = []
    count = 0
    minimum = None
    for cue in entry.get('cues', []):
        # Gray outside the letters excludes the moving picture from both masks.
        reference = Image.new('RGB', (320, 240), (128, 128, 128))
        subtitle(reference, cue['en'])
        mask = np.asarray(reference)[192:, :, 0]
        indices = np.flatnonzero((times >= cue['start']) & (times < cue['end']))
        if not indices.size:
            raise ValueError(f"{path.stem}: no frame for {cue['id']}")
        pixels = strips[indices]
        scores = pixels[:, mask >= 226].mean(axis=1) - pixels[:, mask <= 16].mean(axis=1)
        if not np.isfinite(scores).all():
            raise ValueError(f"{path.stem}: empty glyph mask for {cue['id']}")
        lowest = float(scores.min())
        minimum = lowest if minimum is None else min(minimum, lowest)
        weak.extend(indices[scores < MIN_SUBTITLE_CONTRAST].tolist())
        count += len(indices)
    return weak, {'frames': count, 'minimum': minimum, 'threshold': MIN_SUBTITLE_CONTRAST}


def repair_subtitle_frames(output, entry):
    weak, _ = subtitle_contrast(output, entry)
    if not weak:
        return
    target = ANALYSIS / output.stem
    # On nearly full frames partial replacement can spend too few bits on the
    # text. Let the encoder distribute the same sector budget over the picture.
    retry = ET.Element('str-replace', version='0.3')
    edits = {int(node.attrib['frame']): node.text for node in ET.parse(target/'replace.xml').getroot()}
    for index in weak:
        ET.SubElement(retry, 'replace', frame=str(index)).text = edits[index]
    xml = target / 'subtitle-retry.xml'
    ET.ElementTree(retry).write(xml, encoding='utf-8', xml_declaration=True)
    java(['-x', target/'original.idx', '-f', output, '-i', '0', '-replaceframes', xml],
         target, 'subtitle-retry.log')
    print(output.stem, len(weak), 'low-contrast subtitle frames re-encoded', flush=True)


def patch(apply=False, movies=None):
    data = load_translation()
    check_translation(data)
    for name, entry in data['movies'].items():
        if movies and name not in movies:
            continue
        target = ANALYSIS / name
        xml = target / 'replace.xml'
        if not entry.get('cues') and not entry.get('labels') and not entry.get('credits'):
            continue
        print('patch', name, '->', PATCHED/(name+'.STR'), flush=True)
        if not apply:
            continue
        render_info = json.loads((target/'render.json').read_text(encoding='utf-8'))
        if render_info['translation_sha256'] != fingerprint(entry):
            raise ValueError(f'{name}: rendered frames are stale; render them again')
        if render_info['source_sha256'] != hashlib.sha256((SOURCE/(name+'.STR')).read_bytes()).hexdigest():
            raise ValueError(f'{name}: original movie changed after rendering')
        PATCHED.mkdir(parents=True, exist_ok=True)
        output = PATCHED / (name+'.STR')
        shutil.copyfile(SOURCE/(name+'.STR'), output)
        java(['-x', target/'original.idx', '-f', output, '-i', '0', '-replaceframes', xml],
             target, 'patch.log')
        log = (target/'patch.log').read_text(encoding='utf-8')
        if '100% Applying patch' not in log or 'SEVERE:' in log or 'ERROR:' in log:
            raise RuntimeError(f'{name}: replacement did not complete; see {target/"patch.log"}')
        repair_subtitle_frames(output, entry)
        verify_movie(SOURCE/(name+'.STR'), output, fingerprint(entry))


def verify_movie(original, patched, translation_sha256=None):
    before, after = original.read_bytes(), patched.read_bytes()
    if len(before) != len(after):
        raise ValueError('Movie sector count changed')
    audio = changed = 0
    max_rle = max_bs = 0
    for i in range(len(before)//2352):
        a, b = before[i*2352:(i+1)*2352], after[i*2352:(i+1)*2352]
        if a[:24] != b[:24]:
            raise ValueError(f'Sector {i}: CD header or XA subheader changed')
        if a[18] & 4:
            audio += 1
            if a != b:
                raise ValueError(f'Sector {i}: audio changed')
        elif a != b:
            changed += 1
            if a[24:28] != b'\x60\x01\x01\x80':
                raise ValueError(f'Sector {i}: changed a non-video sector')
            if a[24:36] != b[24:36] or a[40:44] != b[40:44]:
                raise ValueError(f'Sector {i}: frame layout changed')
        if b[24:30] == bytes.fromhex('600101800000'):
            chunks = struct.unpack_from('<H',b,30)[0]
            bs_size = struct.unpack_from('<I',b,36)[0]
            rle_size = struct.unpack_from('<H',b,56)[0]*4+4
            max_rle, max_bs = max(max_rle,rle_size), max(max_bs,bs_size)
            if bs_size > chunks*2016 or bs_size > 0x10000:
                raise ValueError(f'Sector {i}: compressed frame exceeds its original slots/ring buffer')
            if rle_size > 0x28000:
                raise ValueError(f'Sector {i}: RLE output exceeds native movie buffer')
            if b[44:52] != b[56:64]:
                raise ValueError(f'Sector {i}: STR/bitstream headers disagree')
            if b[62:64] != a[62:64]:
                raise ValueError(f'Sector {i}: MDEC bitstream version changed')
    result = {'movie': original.stem, 'sectors': len(before)//2352, 'changed_video_sectors':changed,
              'unchanged_audio_sectors': audio, 'source_sha256':hashlib.sha256(before).hexdigest(),
              'patched_sha256':hashlib.sha256(after).hexdigest()}
    result.update(max_rle_bytes=max_rle,rle_buffer_bytes=0x28000,max_bitstream_bytes=max_bs,
                  ring_buffer_bytes=0x10000,render_style=RENDER_STYLE)
    if translation_sha256:
        result['translation_sha256'] = translation_sha256
    write_json(ANALYSIS/original.stem/'verification.json',result)
    print(original.stem, changed, 'video sectors changed;', audio, 'audio sectors unchanged', flush=True)
    return result


def ready_movies(require_decoded=False):
    """Only validated, current movie assets may be included in a disc build."""
    data = load_translation()
    check_translation(data)
    ready = {}
    for name, entry in data['movies'].items():
        if not entry.get('cues') and not entry.get('labels') and not entry.get('credits'):
            continue
        report = json.loads((ANALYSIS/name/'verification.json').read_text(encoding='utf-8'))
        if report.get('translation_sha256') != fingerprint(entry):
            raise ValueError(f'{name}: missing/stale movie verification; render and patch again')
        original = inventory(SOURCE/(name+'.STR'))
        if report['source_sha256'] != original['sha256']:
            raise ValueError(f'{name}: original movie changed after verification')
        if require_decoded and report.get('independently_decoded_frames') != len(original['frames']):
            raise ValueError(f'{name}: run movie.py validate --apply before building')
        if require_decoded and report.get('subtitle_contrast', {}).get('threshold') != MIN_SUBTITLE_CONTRAST:
            raise ValueError(f'{name}: run movie.py validate --apply to verify subtitle visibility')
        output = PATCHED/(name+'.STR')
        raw = output.read_bytes()
        if hashlib.sha256(raw).hexdigest() != report['patched_sha256']:
            raise ValueError(f'{name}: patched movie changed after verification')
        ready[name+'.STR'] = raw
    return ready


def validate(apply=False,movies=None):
    """Decode every patched frame with an independent decoder, retaining the logs."""
    ready = ready_movies()
    entries = load_translation()['movies']
    for filename in ready:
        name = Path(filename).stem
        if movies and name not in movies:
            continue
        print('validate all frames:', filename, flush=True)
        if not apply:
            continue
        target = ANALYSIS/name
        with (target/'ffmpeg_decode.log').open('w',encoding='utf-8') as log:
            subprocess.run(['ffmpeg','-v','error','-xerror','-err_detect','explode','-i',
                            str(PATCHED/filename),'-map','0:v:0','-f','null','NUL'],
                           stdout=log,stderr=subprocess.STDOUT,check=True)
        result = subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-count_frames',
                                 '-show_entries','stream=nb_read_frames,width,height','-of','json',
                                 str(PATCHED/filename)],capture_output=True,text=True,check=True)
        stream = json.loads(result.stdout)['streams'][0]
        expected = len(inventory(SOURCE/filename)['frames'])
        if int(stream['nb_read_frames']) != expected or stream['width'] != 320 or stream['height'] != 240:
            raise ValueError(f'{name}: decoded frame count or dimensions changed')
        report = json.loads((target/'verification.json').read_text(encoding='utf-8'))
        weak, contrast = subtitle_contrast(PATCHED/filename, entries[name])
        if weak:
            raise ValueError(f'{name}: weak subtitles on {len(weak)} frames, starting at {weak[0]}')
        report['subtitle_contrast'] = contrast
        report['independently_decoded_frames'] = expected
        write_json(target/'verification.json',report)
        print(name, expected, 'frames decode without errors', flush=True)


def export_srt(apply=False):
    data = load_translation()
    check_translation(data)
    def timestamp(seconds):
        milliseconds = round(seconds*1000)
        hours, milliseconds = divmod(milliseconds,3600000)
        minutes, milliseconds = divmod(milliseconds,60000)
        seconds, milliseconds = divmod(milliseconds,1000)
        return f'{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}'
    for name, entry in data['movies'].items():
        if not entry['cues']:
            continue
        path = TRANSLATION.parent/'movies'/(name+'.srt')
        print('export',path,flush=True)
        if apply:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('\n\n'.join(f'{k+1}\n{timestamp(c["start"])} --> {timestamp(c["end"])}\n'+
                                       '\n'.join(wrap_text(c['en'],font(12,True)))
                                       for k,c in enumerate(entry['cues']))+'\n',encoding='utf-8')


def verify_disc(path, apply=False):
    import build_disc
    import cdsector
    data = load_translation()
    version = data['version']
    destination = ROOT/'work/ui/movies'/('v'+version.replace('.',''))/'validation.json'
    print('check original movie LBAs, raw sectors and checksum samples:',path,flush=True)
    print('report:',destination,flush=True)
    if not apply:
        return
    original = build_disc.Disc(str(ROOT/'Getter Robo Daikessen! (Japan).bin'),'rb')
    final = build_disc.Disc(str(path),'rb')
    results=[]
    try:
        for name, entry in data['movies'].items():
            filename=name+'.STR'
            a,b=original.entries[filename],final.entries[filename]
            if (a.lba,a.size)!=(b.lba,b.size):
                raise ValueError(f'{filename}: movie LBA/size changed')
            edited=bool(entry.get('cues') or entry.get('labels') or entry.get('credits'))
            expected=(PATCHED/filename if edited else SOURCE/filename).read_bytes()
            n=(b.size+2047)//2048
            final.f.seek(b.lba*2352);actual=final.f.read(n*2352)
            if len(actual)!=len(expected):
                raise ValueError(f'{filename}: wrong raw sector count')
            for i in range(n):
                p,q=expected[i*2352:(i+1)*2352],actual[i*2352:(i+1)*2352]
                # Disc writer deliberately regenerates parity; content/header must match.
                end=2348 if q[18]&0x20 else 2072
                if p[:end]!=q[:end]:
                    raise ValueError(f'{filename}: disc content mismatch at sector {i}')
            picks=sorted(set([0,n//4,n//2,3*n//4,n-1]))
            checks=cdsector.self_test(str(path),[b.lba+i for i in picks])
            if checks!=len(picks):
                raise ValueError(f'{filename}: bad sector checksum sample')
            inv=inventory(SOURCE/filename)
            result={'movie':name,'lba':b.lba,'iso_size':b.size,'raw_sectors':n,
                    'frames':len(inv['frames']),'edited':edited,'audio_sectors':inv['audio_sectors'],
                    'content_verified':True,'checksum_samples':checks}
            if edited:
                report=json.loads((ANALYSIS/name/'verification.json').read_text(encoding='utf-8'))
                if report.get('independently_decoded_frames')!=len(inv['frames']):
                    raise ValueError(f'{name}: full decoder validation is missing')
                result.update(report)
            else:
                if expected!=actual:
                    raise ValueError(f'{name}: supposedly unchanged movie differs')
                result['byte_identical_to_original']=True
            results.append(result)
            print(filename,'content/audio/layout and checksums OK',flush=True)
    finally:
        original.f.close();final.f.close()
    write_json(destination,{'version':version,'disc':str(path),'movies':results,
                            'human_listening_review_complete':False,'real_console_tested':False})


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def inventory(path):
    raw = path.read_bytes()
    frames = []
    audio = 0
    for i in range(len(raw) // 2352):
        sec = raw[i*2352:(i+1)*2352]
        if sec[18] & 4:
            audio += 1
        if sec[24:28] == b'\x60\x01\x01\x80':
            chunk, count, number, size, width, height = struct.unpack_from('<HHIIHH', sec, 28)
            if chunk == 0:
                frames.append({'index': len(frames), 'sector': i, 'number': number,
                               'chunks': count, 'bytes': size, 'width': width, 'height': height})
    if not frames:
        raise ValueError(f'No standard STR frames in {path}')
    return {'movie': path.name, 'sha256': hashlib.sha256(raw).hexdigest(),
            'sectors': len(raw)//2352, 'seconds': round(len(raw)/2352/150, 3),
            'audio_sectors': audio, 'frames': frames}


def prepare(apply=False):
    from PIL import Image, ImageDraw
    records = []
    for path in sorted(SOURCE.glob('*.STR')):
        record = inventory(path)
        records.append(record)
        print(path.name, len(record['frames']), 'frames', record['seconds'], 'seconds', flush=True)
        if not apply:
            continue
        target = ANALYSIS / path.stem
        target.mkdir(parents=True, exist_ok=True)
        audio = target / 'audio.wav'
        if not audio.exists():
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-vn',
                            '-ac', '1', '-ar', '16000', str(audio)], check=True)
        sheet = Image.new('RGB', (960, 540), '#202020')
        draw = ImageDraw.Draw(sheet)
        for k, fraction in enumerate((.03, .2, .4, .6, .8, .95)):
            seconds = record['seconds'] * fraction
            image_path = target / f'sample_{k}.png'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-ss', str(seconds),
                            '-frames:v', '1', str(image_path)], check=True)
            if image_path.exists():
                sheet.paste(Image.open(image_path).convert('RGB'), ((k%3)*320, (k//3)*270))
                draw.text(((k%3)*320+5, (k//3)*270+244), f'{path.stem} {seconds:.2f}s', fill='white')
        sheet.save(target / 'contact.png')
    if apply:
        write_json(ANALYSIS / 'inventory.json', records)


def transcribe(apply=False, model_name='large-v3', task='transcribe', vad=True, movies=None):
    paths = sorted(ANALYSIS.glob('*/audio.wav'))
    if movies:
        paths = [p for p in paths if p.parent.name in movies]
    if not apply:
        print(f'{task}: {len(paths)} local WAVs -> ignored movie_analysis/*/{task}.json')
        return
    # Keep CUDA DLL directory handles alive throughout inference.
    import site
    handles = []
    for base in site.getsitepackages():
        for directory in Path(base).glob('nvidia/*/bin'):
            handles.append(os.add_dll_directory(str(directory)))
            os.environ['PATH'] = str(directory) + os.pathsep + os.environ['PATH']
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device='cuda', compute_type='int8_float16', local_files_only=True)
    for path in paths:
        suffix = '' if model_name == 'large-v3' else '_' + model_name.replace('-', '_')
        if not vad:
            suffix += '_novad'
        output = path.parent / f'{task}{suffix}.json'
        if output.exists():
            continue
        segments, info = model.transcribe(str(path), language='ja', task=task, beam_size=5,
                                         vad_filter=vad, condition_on_previous_text=False,
                                         word_timestamps=True, temperature=0)
        result = []
        for seg in segments:
            result.append({'start': round(seg.start, 3), 'end': round(seg.end, 3),
                           'text': seg.text.strip(), 'logprob': round(seg.avg_logprob, 3),
                           'no_speech': round(seg.no_speech_prob, 3),
                           'words': [{'start': round(w.start, 3), 'end': round(w.end, 3),
                                      'word': w.word} for w in (seg.words or [])]})
        write_json(output, {'movie': path.parent.name, 'task': task, 'model': model_name,
                            'segments': result})
        print(path.parent.name, len(result), 'segments', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'transcribe', 'translate', 'decode', 'check', 'render', 'patch', 'validate', 'export-srt', 'verify-disc'])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--model', default='large-v3')
    parser.add_argument('--no-vad', action='store_true')
    parser.add_argument('--movies', nargs='+')
    parser.add_argument('--disc', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.apply)
    elif args.command == 'decode':
        decode(args.apply, args.movies)
    elif args.command == 'check':
        check_translation(load_translation())
    elif args.command == 'render':
        render(args.apply, args.movies)
    elif args.command == 'patch':
        patch(args.apply, args.movies)
    elif args.command == 'validate':
        validate(args.apply,args.movies)
    elif args.command == 'export-srt':
        export_srt(args.apply)
    elif args.command == 'verify-disc':
        if not args.disc:
            parser.error('verify-disc requires --disc')
        verify_disc(args.disc.resolve(),args.apply)
    else:
        transcribe(args.apply, args.model, args.command, not args.no_vad, args.movies)
