#!/usr/bin/env python3
"""PresentationML timing, static export and package checks; standard library only."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import posixpath
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as E
from zipfile import ZipFile, ZIP_DEFLATED

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
for prefix, uri in NS.items():
    E.register_namespace(prefix, uri)


def q(tag):
    return '{' + NS['p'] + '}' + tag


def sub(parent, tag, **attrs):
    return E.SubElement(parent, q(tag), {key: str(value) for key, value in attrs.items()})


def require(condition, message):
    if not condition:
        raise ValueError(message)


def parts_of(path):
    with ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate ZIP member')
        require(archive.testzip() is None, 'Damaged ZIP member')
        return {name: archive.read(name) for name in names if not name.endswith('/')}


def shapes(doc):
    tree = doc.find('p:cSld/p:spTree', NS)
    return [(obj, obj.find('.//p:cNvPr', NS)) for obj in tree
            if obj.find('.//p:cNvPr', NS) is not None]


def shape(doc, name):
    matches = [obj for obj, prop in shapes(doc) if prop.get('name') == name]
    require(len(matches) == 1, f'Expected exactly one {name}')
    return matches[0]


def geometry(obj):
    transform = obj.find('p:spPr/a:xfrm', NS)
    offset, extent = transform.find('a:off', NS), transform.find('a:ext', NS)
    return tuple(int(element.get(key)) for element, key in
                 [(offset, 'x'), (offset, 'y'), (extent, 'cx'), (extent, 'cy')])


def font_size(obj):
    sizes = {int(el.get('sz')) for el in obj.findall('.//a:rPr', NS) if el.get('sz')}
    require(len(sizes) == 1, 'Focus text must have one font size')
    return sizes.pop()


def move_to_nav(doc, dimensions):
    focus, anchor, mask = (shape(doc, name) for name in ['bs-focus', 'bs-anchor', 'bs-mask'])
    focus_id = focus.find('.//p:cNvPr', NS).get('id')
    start, end = geometry(focus), geometry(anchor)
    movement = [(end[i] + end[i + 2]/2 - start[i] - start[i + 2]/2) / dimensions[i] for i in (0, 1)]
    scale = round(2700 / font_size(focus) * 100000)
    require(0 < scale <= 100000, 'Invalid focus scale')
    require(doc.find('p:timing', NS) is None, 'Refusing to replace an existing timeline')
    timing = E.Element(q('timing'))
    tm = sub(sub(sub(timing, 'tnLst'), 'par'), 'cTn', id=1, dur='indefinite', restart='never', nodeType='tmRoot')
    seq = sub(sub(tm, 'childTnLst'), 'seq', concurrent=1, nextAc='seek')
    main = sub(seq, 'cTn', id=2, dur='indefinite', nodeType='mainSeq')
    start_clock = sub(sub(sub(main, 'childTnLst'), 'par'), 'cTn', id=3, fill='hold')
    sub(sub(start_clock, 'stCondLst'), 'cond', delay='indefinite')
    effects, next_id = sub(start_clock, 'childTnLst'), 4

    def clock(parent, **attrs):
        nonlocal next_id
        node = sub(parent, 'cTn', id=next_id, **attrs)
        next_id += 1
        return node

    def effect(preset, kind, delay, duration, first=False):
        node = clock(sub(effects, 'par'), presetID=preset, presetClass=kind, presetSubtype=0,
                     dur=duration, fill='hold', grpId=0, nodeType='clickEffect' if first else 'withEffect')
        sub(sub(node, 'stCondLst'), 'cond', delay=delay)
        return sub(node, 'childTnLst')

    def behavior(parent, target, duration, attributes):
        node = sub(parent, 'cBhvr')
        clock(node, dur=duration, fill='hold')
        sub(sub(node, 'tgtEl'), 'spTgt', spid=target)
        if attributes:
            names = sub(node, 'attrNameLst')
            for attribute in attributes:
                sub(names, 'attrName').text = attribute

    children = effect(0, 'path', 0, 1200, True)
    motion = sub(children, 'animMotion', origin='layout', path=f'M 0 0 L {movement[0]:.12f} {movement[1]:.12f} E', pathEditMode='relative')
    behavior(motion, focus_id, 1200, ['ppt_x', 'ppt_y'])
    children = effect(6, 'emph', 0, 1200)
    resize = sub(children, 'animScale', zoomContents=1)
    behavior(resize, focus_id, 1200, ['ppt_w', 'ppt_h'])
    sub(resize, 'from', x=100000, y=100000)
    sub(resize, 'to', x=scale, y=scale)
    for obj, prop in shapes(doc):
        is_mask = prop.get('name') == 'bs-mask'
        if not (is_mask or prop.get('name', '').startswith('bs-exit-')):
            continue
        delay, duration = (1200, 250) if is_mask else (0, 800)
        children = effect(10, 'exit', delay, duration)
        fade = sub(children, 'animEffect', transition='out', filter='fade')
        behavior(fade, prop.get('id'), duration, [])
        hide = sub(children, 'set')
        common = sub(hide, 'cBhvr')
        time = clock(common, dur=1, fill='hold')
        sub(sub(time, 'stCondLst'), 'cond', delay=duration)
        sub(sub(common, 'tgtEl'), 'spTgt', spid=prop.get('id'))
        sub(sub(common, 'attrNameLst'), 'attrName').text = 'style.visibility'
        sub(sub(hide, 'to'), 'strVal', val='hidden')
    for event, tag in [('onPrev', 'prevCondLst'), ('onNext', 'nextCondLst')]:
        condition = sub(sub(seq, tag), 'cond', evt=event, delay=0)
        sub(sub(condition, 'tgtEl'), 'sldTgt')
    builds = sub(timing, 'bldLst')
    sub(builds, 'bldP', spid=focus_id, grpId=0)
    doc.append(timing)
    return {'shape_id': focus_id, 'start_emu': start, 'destination_emu': end,
            'motion_delta': movement, 'scale_to': scale, 'duration_ms': 1200,
            'reveal_ms': [1200, 1450], 'trigger': 'click-on-original-slide'}


def static_frame(doc):
    focus, anchor = shape(doc, 'bs-focus'), shape(doc, 'bs-anchor')
    transform = focus.find('p:spPr/a:xfrm', NS)
    transform.clear()
    for child in shape(doc, 'bs-anchor').find('p:spPr/a:xfrm', NS):
        transform.append(deepcopy(child))
    for el in focus.iter():
        if el.tag in ['{' + NS['a'] + '}' + name for name in ['rPr', 'defRPr', 'endParaRPr']]:
            el.set('sz', '2700')
    tree = doc.find('p:cSld/p:spTree', NS)
    for obj, prop in shapes(doc):
        if prop.get('name') in ['bs-anchor', 'bs-mask'] or prop.get('name', '').startswith('bs-exit-'):
            tree.remove(obj)
    for node in doc.findall('p:timing', NS):
        doc.remove(node)


def validate(parts):
    require('ppt/presentation.xml' in parts, 'Missing presentation')
    for name, data in parts.items():
        if not (name.endswith('.xml') or name.endswith('.rels')):
            continue
        doc = E.fromstring(data)
        if name.endswith('.rels'):
            owner = name.replace('/_rels/', '/').removesuffix('.rels') if name != '_rels/.rels' else ''
            for rel in doc:
                if rel.get('TargetMode') == 'External':
                    continue
                target = rel.get('Target', '')
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(owner), target)) if not target.startswith('/') else target.lstrip('/')
                require(resolved in parts, f'Broken relationship: {name} -> {target}')
        if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
            ids = [prop.get('id') for _, prop in shapes(doc)]
            require(len(ids) == len(set(ids)), f'Duplicate shape ID: {name}')
            times = [node.get('id') for node in doc.findall('.//p:cTn', NS)]
            require(len(times) == len(set(times)), f'Duplicate timeline ID: {name}')
            for target in doc.findall('.//p:spTgt', NS):
                require(target.get('spid') in ids, f'Missing animation target: {name}')
            require(doc.get('show') != '0', f'Unexpected hidden duplicate slide: {name}')
            require(all('advTm' not in node.attrib for node in doc.findall('p:transition', NS)), 'Unexpected automatic slide advance')
    presentation = E.fromstring(parts['ppt/presentation.xml'])
    return len(presentation.find('p:sldIdLst', NS))


def write_parts(path, parts):
    with ZipFile(path, 'x', ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)


def finalize(source, live_path, static_path, report_path):
    original = parts_of(source)
    require(validate(original) > 0, 'Empty deck')
    marker = E.fromstring(original['docProps/core.xml'])
    require(any(el.text == 'Blackstage' for el in marker), 'Only Blackstage-generated drafts are supported')
    dims = E.fromstring(original['ppt/presentation.xml']).find('p:sldSz', NS)
    dimensions = tuple(int(dims.get(key)) for key in ['cx', 'cy'])
    live, still, animations = original.copy(), original.copy(), []
    for name, data in original.items():
        if not (name.startswith('ppt/slides/slide') and name.endswith('.xml')):
            continue
        doc = E.fromstring(data)
        transition = E.Element(q('transition'), {'spd': 'fast', 'advClick': '1'})
        sub(transition, 'fade')
        doc.append(transition)
        is_roadmap = any(prop.get('name') == 'bs-focus' for _, prop in shapes(doc))
        if is_roadmap:
            entry = move_to_nav(doc, dimensions)
            entry['owner_part'] = name
            animations.append(entry)
        live[name] = E.tostring(doc, encoding='UTF-8', xml_declaration=True)
        if is_roadmap:
            static_frame(doc)
        still[name] = E.tostring(doc, encoding='UTF-8', xml_declaration=True)
    count = validate(live)
    require(validate(still) == count, 'Static and playable slide counts differ')
    require(all(live[n] == data and still[n] == data for n, data in original.items() if not n.startswith('ppt/slides/slide')), 'Unrelated package data changed')
    write_parts(live_path, live)
    write_parts(static_path, still)
    report = {'slide_count': count, 'animations': animations, 'package_checks_passed': True,
              'unrelated_parts_preserved': True, 'powerpoint_playback_verified': False,
              'sha256': {key: hashlib.sha256(Path(value).read_bytes()).hexdigest()
                         for key, value in [('playable', live_path), ('static', static_path)]}}
    with Path(report_path).open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)


def conversion_fonts(parts):
    directory = os.environ.get('BLACKSTAGE_FONT_DIR')
    if directory:
        files = sorted(p for p in Path(directory).iterdir() if p.suffix.lower() in ['.ttf', '.otf', '.ttc', '.otc'])
        require(files, 'BLACKSTAGE_FONT_DIR has no TTF/OTF/TTC font files')
        return files
    matcher = shutil.which('fc-match')
    files = set()
    if matcher:
        families = set()
        for name, data in parts.items():
            if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
                families.update(el.get('typeface') for el in E.fromstring(data).findall('.//a:rPr/a:latin', NS))
        for family in sorted(families):
            result = subprocess.run([matcher, '-f', '%{family}\n%{file}', family + ':style=Bold'],
                                    capture_output=True, text=True, timeout=10)
            lines = result.stdout.splitlines()
            if len(lines) == 2 and family.replace(' ', '').casefold() in [alias.replace(' ', '').casefold() for alias in lines[0].split(',')]:
                candidate = Path(lines[1])
                if candidate.is_file():
                    files.add(candidate)
    # 일부 macOS headless 변환기는 시스템 폰트를 읽지 않으므로 변환 프로필에만 복사한다.
    require(sys.platform != 'darwin' or files,
            'macOS PDF conversion needs fc-match with the requested font, or BLACKSTAGE_FONT_DIR pointing to its font files')
    return sorted(files)


def export_pdf(source, output):
    require(not Path(output).exists(), 'PDF already exists; use a new output path')
    parts = parts_of(source)
    count = validate(parts)
    require(all(b'<p:timing' not in data for name, data in parts.items() if name.startswith('ppt/slides/slide')), 'Export the static deck, not the playable timeline')
    executable = shutil.which('soffice') or shutil.which('libreoffice')
    mac_binary = Path('/Applications/LibreOffice.app/Contents/MacOS/soffice')
    if not executable and mac_binary.exists():
        executable = str(mac_binary)
    require(executable, 'LibreOffice is needed for --pdf; PPTX and static export work without it')
    with tempfile.TemporaryDirectory(prefix='blackstage-pdf-') as temp:
        directory = Path(temp)
        fonts = conversion_fonts(parts)
        font_directory = directory/'profile/user/fonts'
        font_directory.mkdir(parents=True)
        for index, font in enumerate(fonts):
            shutil.copyfile(font, font_directory/(str(index) + '-' + font.name))
        command = [executable, '-env:UserInstallation=' + (directory/'profile').as_uri(), '--headless',
                   '--convert-to', 'pdf', '--outdir', str(directory), str(Path(source).resolve())]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        pdf = directory / (Path(source).stem + '.pdf')
        require(result.returncode == 0 and pdf.is_file() and pdf.stat().st_size > 0,
                'PDF conversion did not produce a file: ' + result.stderr + result.stdout)
        with Path(output).open('xb') as stream:
            stream.write(pdf.read_bytes())
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    finalize_parser = commands.add_parser('finalize')
    for name in ['draft', 'playable', 'static', 'report']:
        finalize_parser.add_argument(name)
    commands.add_parser('check').add_argument('file')
    pdf_parser = commands.add_parser('pdf')
    pdf_parser.add_argument('static'); pdf_parser.add_argument('output')
    args = parser.parse_args()
    if args.command == 'finalize':
        finalize(args.draft, args.playable, args.static, args.report)
    elif args.command == 'check':
        print(json.dumps({'slides': validate(parts_of(args.file)), 'powerpoint_playback_verified': False}))
    else:
        export_pdf(args.static, args.output)


if __name__ == '__main__':
    main()
