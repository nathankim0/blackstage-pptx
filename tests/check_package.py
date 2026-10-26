"""Assert observable package invariants, without pretending to replay PowerPoint."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as E
import zlib

ROOT = Path(__file__).resolve().parents[1]
module = importlib.util.spec_from_file_location('blackstage_package', ROOT/'scripts/pptx.py')
package = importlib.util.module_from_spec(module)
module.loader.exec_module(package)
NS = package.NS


def fixture(directory):
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
    for name, width, height in [('wide.png', 80, 40), ('tall.png', 40, 80)]:
        rows = b''.join(b'\x00' + bytes([30, 120, 200])*width for _ in range(height))
        data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0))
        data += chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')
        (Path(directory)/name).write_bytes(data)


def inspect(live_path):
    path = Path(live_path)
    live = package.parts_of(path)
    still = package.parts_of(path.with_suffix('.static.pptx'))
    report = json.loads(path.with_suffix('.checks.json').read_text())
    count = package.validate(live)
    assert package.validate(still) == count == report['slide_count']
    assert report['powerpoint_playback_verified'] is False
    assert report['package_checks_passed'] and report['unrelated_parts_preserved']
    owners = []
    for name, data in live.items():
        if not (name.startswith('ppt/slides/slide') and name.endswith('.xml')):
            continue
        doc = E.fromstring(data)
        if not doc.findall('.//p:animMotion', NS):
            assert doc.find('p:timing', NS) is None
            continue
        owners.append(name)
        focus = package.shape(doc, 'bs-focus')
        ordered = [(obj,prop.get('name','')) for obj,prop in package.shapes(doc)]
        mask_index = next(i for i,(_,name) in enumerate(ordered) if name == 'bs-mask')
        focus_index = next(i for i,(_,name) in enumerate(ordered) if name == 'bs-focus')
        assert mask_index < focus_index
        assert all(i < mask_index for i,(_,name) in enumerate(ordered) if name.startswith('bs-reveal-'))
        focus_id = focus.find('.//p:cNvPr', NS).get('id')
        motion = doc.find('.//p:animMotion', NS)
        scale = doc.find('.//p:animScale', NS)
        assert motion.find('p:cBhvr/p:tgtEl/p:spTgt', NS).get('spid') == focus_id
        assert scale.find('p:cBhvr/p:tgtEl/p:spTgt', NS).get('spid') == focus_id
        assert all(node.find('p:cBhvr/p:tgtEl/p:spTgt', NS).get('spid') != focus_id for node in doc.findall('.//p:animEffect', NS))
        assert len(doc.findall('.//p:cTn[@nodeType="clickEffect"]', NS)) == 1
        parent = doc.find('.//p:cTn[@nodeType="mainSeq"]/p:childTnLst/p:par/p:cTn/p:stCondLst/p:cond', NS)
        assert parent.get('delay') == 'indefinite'
        anchor = package.shape(doc, 'bs-anchor')
        begin, end = package.geometry(focus), package.geometry(anchor)
        dims = E.fromstring(live['ppt/presentation.xml']).find('p:sldSz', NS)
        delta = motion.get('path').split()[4:6]
        expected = [(end[i]+end[i+2]/2-begin[i]-begin[i+2]/2)/int(dims.get(key)) for i,key in enumerate(['cx','cy'])]
        assert all(abs(float(a)-b)<1e-10 for a,b in zip(delta,expected))
        assert int(scale.find('p:to', NS).get('x')) == round(2700/package.font_size(focus)*100000)
        static = E.fromstring(still[name])
        assert static.find('p:timing', NS) is None
        static_focus = package.shape(static, 'bs-focus')
        assert package.geometry(static_focus) == end
        assert package.font_size(static_focus) == 2700
        assert ''.join(static_focus.itertext()) == ''.join(focus.itertext())
        assert not [prop for _,prop in package.shapes(static) if prop.get('name') in ['bs-mask','bs-anchor'] or prop.get('name','').startswith('bs-exit-')]
        assert doc.find('.//p:animEffect[@transition="in"]', NS) is None
        damaged = live.copy()
        broken = deepcopy(doc)
        broken.find('.//p:spTgt', NS).set('spid', '999999')
        damaged[name] = E.tostring(broken)
        try:
            package.validate(damaged)
        except ValueError:
            pass
        else:
            raise AssertionError('Missing animation target was accepted')
    assert owners == [entry['owner_part'] for entry in report['animations']]
    # 타임라인과 무관한 관계·미디어는 정적 결과에서도 그대로 보존한다.
    for name in live:
        if not name.startswith('ppt/slides/slide'):
            assert live[name] == still[name]
    image_ratios = []
    text_runs = []
    for name,data in live.items():
        if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
            doc = E.fromstring(data)
            for picture in doc.findall('.//p:pic', NS):
                crop = picture.find('p:blipFill/a:srcRect', NS)
                assert crop is None or all(int(value)==0 for value in crop.attrib.values())
                extent = picture.find('p:spPr/a:xfrm/a:ext', NS)
                image_ratios.append(int(extent.get('cx'))/int(extent.get('cy')))
            for run in doc.findall('.//a:r', NS):
                text = run.find('a:t', NS)
                color = run.find('a:rPr/a:solidFill/a:srgbClr', NS)
                if text is not None and color is not None:
                    text_runs.append([text.text,color.get('val')])
    return {'count':count,'owners':owners,'image_ratios':image_ratios,'text_runs':text_runs}


if __name__ == '__main__':
    if sys.argv[1] == 'fixture':
        fixture(sys.argv[2])
    else:
        print(json.dumps(inspect(sys.argv[1]), ensure_ascii=False))
