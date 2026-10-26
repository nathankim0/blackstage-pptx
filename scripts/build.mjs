#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import pptxgen from 'pptxgenjs';
import {imageSize} from 'image-size';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const W = 1280, H = 720;
const WHITE = 'FFFFFF', MUTED = 'BFC0C7', GOLD = 'FFD54A';
const check = (condition, message) => { if (!condition) throw new Error(message); };
const word = (value, name) => check(typeof value === 'string' && value.trim().length > 0, `${name}: 비어 있지 않은 문자열이 필요합니다.`);

export function dateLabel(value) {
  check(typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value), `날짜는 YYYY-MM-DD 형식이어야 합니다: ${value}`);
  const date = new Date(`${value}T00:00:00Z`);
  check(Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value, `존재하지 않는 날짜: ${value}`);
  return `${date.getUTCMonth() + 1}/${date.getUTCDate()}(${'일월화수목금토'[date.getUTCDay()]})`;
}

function runs(line) {
  if (typeof line === 'string') return [{text: line, options: {color: WHITE}}];
  check(Array.isArray(line) && line.length > 0, '본문은 문자열 또는 text/date 조각 목록이어야 합니다.');
  return line.map(part => {
    check(part && typeof part === 'object', '본문 조각이 올바르지 않습니다.');
    check(('date' in part) !== ('text' in part), '본문 조각은 text 또는 date 중 하나여야 합니다.');
    if ('date' in part) return {text: dateLabel(part.date), options: {color: GOLD}};
    word(part.text, '본문');
    return {text: part.text, options: {color: WHITE}};
  });
}

export function validate(spec) {
  check(spec && typeof spec === 'object', 'JSON 객체가 필요합니다.');
  word(spec.title, 'title');
  check(Array.isArray(spec.sections) && spec.sections.length >= 1 && spec.sections.length <= 4, '상단 목차는 1~4개입니다.');
  const ids = new Set();
  for (const section of spec.sections) {
    word(section.id, 'section.id'); word(section.label, 'section.label');
    check(!ids.has(section.id), `중복 section.id: ${section.id}`); ids.add(section.id);
  }
  check(Array.isArray(spec.slides) && spec.slides.length > 0, '슬라이드가 필요합니다.');
  function content(slide, reveal = false) {
    check(slide && typeof slide === 'object', '슬라이드 객체가 필요합니다.');
    check(['cover', 'toc', 'title', 'text', 'image', 'gallery', 'roadmap'].includes(slide.kind), `알 수 없는 kind: ${slide.kind}`);
    if (slide.section !== undefined) check(ids.has(slide.section), `없는 section: ${slide.section}`);
    if (['cover', 'title', 'text'].includes(slide.kind)) word(slide.title, 'slide.title');
    if (slide.kind === 'toc') {
      check(Array.isArray(slide.items) && slide.items.length >= 1 && slide.items.length <= 6, '목차 항목은 1~6개입니다.');
      slide.items.forEach(item => word(item, '목차 항목'));
    }
    if (slide.kind === 'text') {
      check(Array.isArray(slide.lines) && slide.lines.length <= 2, '큰 글씨 본문은 최대 두 줄입니다. 내용을 나누세요.');
      slide.lines.forEach(runs);
    }
    if (slide.kind === 'image') word(slide.path, 'image.path');
    if (slide.kind === 'gallery') {
      check(Array.isArray(slide.images) && slide.images.length >= 1 && slide.images.length <= 4, '갤러리는 1~4개 사진입니다.');
      slide.images.forEach(image => {word(image.path, 'image.path'); word(image.label, 'image.label');});
    }
    if (slide.kind === 'roadmap') {
      check(!reveal && ids.has(slide.section), '로드맵에는 목적지 section이 필요합니다.');
      check(Array.isArray(slide.steps) && slide.steps.length === 3, '로드맵은 세 단계입니다.');
      check(Number.isInteger(slide.focus) && slide.focus >= 0 && slide.focus < 3, 'focus는 0~2 정수입니다.');
      slide.steps.forEach(step => {word(step.label, 'step.label'); if (step.date) dateLabel(step.date);});
      check(slide.steps[slide.focus].label === spec.sections.find(s => s.id === slide.section).label, '이동할 글씨와 목적지 목차의 표기를 똑같이 맞추세요.');
      check(slide.nav !== false, '이동 목적지가 필요한 로드맵은 nav:false를 지원하지 않습니다.');
      check(['text', 'gallery'].includes(slide.reveal?.kind), 'reveal은 text 또는 gallery여야 합니다.');
      content(slide.reveal, true);
    }
  }
  spec.slides.forEach(slide => content(slide));
  return spec;
}

// 보수적인 폭 검사이며 실제 글꼴의 렌더링 검수를 대신하지 않는다.
function estimatedWidth(value, points) {
  return [...value].reduce((n, c) => n + (/\s/.test(c) ? 0.3 : c.codePointAt(0) > 0x2fff ? 1 : 0.56), 0) * points;
}

export async function build(specPath, output, pdf = false) {
  const spec = validate(JSON.parse(fs.readFileSync(specPath, 'utf8')));
  check(output.endsWith('.pptx'), '출력 파일 확장자는 .pptx여야 합니다.');
  const base = output.slice(0, -5);
  const targets = [output, `${base}.static.pptx`, `${base}.checks.json`, ...(pdf ? [`${base}.pdf`] : [])].map(p => path.resolve(p));
  targets.forEach(p => check(!fs.existsSync(p), `기존 파일을 보존합니다. 새 출력 경로를 쓰세요: ${p}`));
  fs.mkdirSync(path.dirname(targets[0]), {recursive: true});
  const temp = fs.mkdtempSync(path.join(path.dirname(targets[0]), '.blackstage-'));
  const deck = new pptxgen();
  deck.defineLayout({name: 'BLACKSTAGE', width: W / 96, height: H / 96}); deck.layout = 'BLACKSTAGE';
  deck.author = 'Blackstage'; deck.subject = 'Blackstage minimalist presentation'; deck.title = spec.title;
  const font = spec.font || 'NanumGothic';
  deck.theme = {headFontFace: font, bodyFontFace: font, lang: 'ko-KR'};
  let serial = 0;
  const name = prefix => `${prefix}${++serial}`;
  function text(slide, value, box, size, objectName, color = WHITE, align = 'center') {
    const rich = Array.isArray(value) ? value : [{text: value, options: {color}}];
    const plain = rich.map(r => r.text).join('');
    check(!plain.includes('\n') && estimatedWidth(plain, size) <= box.w * 0.75, `글씨가 영역보다 깁니다. 크기를 줄이지 말고 내용을 나누세요: ${plain}`);
    slide.addText(rich, {x: box.x/96, y: box.y/96, w: box.w/96, h: box.h/96, fontFace: font,
      fontSize: size, bold: true, color, align, valign: 'mid', margin: 0, breakLine: false,lang:'ko-KR',
      objectName: objectName || name('bs-text-')});
  }
  function rect(slide, box, fill, objectName, line = fill) {
    slide.addShape(deck.ShapeType.rect, {x:box.x/96,y:box.y/96,w:box.w/96,h:box.h/96,
      fill:{color:fill,transparency:fill === '000000' && objectName === 'bs-anchor' ? 100 : 0},
      line:{color:line,width:0},objectName});
  }
  function nav(slide, section, prefix, omitFocus = false) {
    let anchor;
    spec.sections.forEach((item, i) => {
      const box={x:40+i*1200/spec.sections.length,y:8,w:1200/spec.sections.length,h:52};
      const active=item.id===section;
      if (active && omitFocus) {anchor=box; rect(slide,box,'000000','bs-anchor');}
      else text(slide,item.label,box,27,name(prefix),active?WHITE:MUTED);
      if(active)rect(slide,{x:box.x+box.w/2-90,y:59,w:180,h:4},WHITE,name(prefix));
    });
    rect(slide,{x:40,y:72,w:1200,h:1},'28282C',name(prefix));
    return anchor;
  }
  function image(slide, item, box, prefix) {
    const imagePath=path.resolve(path.dirname(specPath),item.path);
    check(fs.existsSync(imagePath), `이미지 파일이 없습니다: ${item.path}`);
    const original=imageSize(fs.readFileSync(imagePath));
    const scale=Math.min(box.w/original.width,box.h/original.height);
    const width=original.width*scale,height=original.height*scale;
    slide.addImage({path:imagePath,x:(box.x+(box.w-width)/2)/96,y:(box.y+(box.h-height)/2)/96,w:width/96,h:height/96,
      altText:item.alt||item.label||'Presentation image',objectName:name(prefix)});
  }
  function body(slide, item, prefix='bs-body-') {
    if(item.kind==='text') {
      text(slide,item.title,{x:50,y:190,w:1180,h:120},64.5,name(prefix));
      item.lines.forEach((line,i)=>text(slide,runs(line),{x:50,y:340+125*i,w:1180,h:96},39,name(prefix)));
    } else if(item.kind==='gallery') {
      if(item.title)text(slide,item.title,{x:40,y:88,w:1200,h:65},39,name(prefix));
      item.images.forEach((entry,i)=>{
        const x=50+(i%2)*620,y=166+Math.floor(i/2)*258;
        text(slide,entry.label,{x,y,w:560,h:42},27,name(prefix));
        slide.addShape(deck.ShapeType.rect,{x:x/96,y:(y+48)/96,w:560/96,h:190/96,
          fill:{color:'000000',transparency:100},line:{color:MUTED,width:1},objectName:name(prefix)});
        image(slide,entry,{x:x+4,y:y+52,w:552,h:182},prefix);
      });
    }
  }
  try {
    for(const item of spec.slides) {
      const slide=deck.addSlide();slide.background={color:'000000'};
      if(item.notes)slide.addNotes(item.notes);
      if(item.kind==='roadmap') {
        body(slide,item.reveal,'bs-reveal-');
        nav(slide,item.section,'bs-reveal-',true);
        rect(slide,{x:0,y:0,w:W,h:H},'000000','bs-mask');
        nav(slide,undefined,'bs-exit-');
        item.steps.forEach((step,i)=>{
          text(slide,step.label,{x:40+i*420,y:292,w:360,h:82},42,i===item.focus?'bs-focus':name('bs-exit-'));
          if(step.date)text(slide,dateLabel(step.date),{x:40+i*420,y:410,w:360,h:70},36,name('bs-exit-'),GOLD);
          if(i<2)slide.addShape(deck.ShapeType.rightArrow,{x:(418+i*420)/96,y:320/96,w:82/96,h:40/96,
            fill:{color:WHITE},line:{color:WHITE,width:0},objectName:name('bs-exit-')});
        });
      } else {
        if(!['cover','toc'].includes(item.kind) && item.nav!==false)nav(slide,item.section,'bs-nav-');
        if(item.kind==='cover') {
          if(item.kicker)text(slide,item.kicker,{x:50,y:150,w:1180,h:60},30);
          text(slide,item.title,{x:50,y:265,w:1180,h:130},73.5);
          if(item.subtitle)text(slide,item.subtitle,{x:50,y:430,w:1180,h:80},39);
        } else if(item.kind==='toc') {
          const labels=item.items.map((label,i)=>`${i+1}. ${label}`);
          const width=Math.max(...labels.map(s=>estimatedWidth(s,42)))/0.75+20;
          check(width<=1180,'목차가 너무 깁니다. 문구를 정리하세요.');
          labels.forEach((label,i)=>text(slide,label,{x:(W-width)/2,y:(H-labels.length*70)/2+i*70,w:width,h:64},42,undefined,WHITE,'left'));
        } else if(item.kind==='title')text(slide,item.title,{x:50,y:280,w:1180,h:140},73.5);
        else if(item.kind==='image')image(slide,item,{x:40,y:90,w:1200,h:610},'bs-image-');
        else body(slide,item);
      }
    }
    const raw=path.join(temp,'raw.pptx');await deck.writeFile({fileName:raw,compression:true});
    const generated=['live.pptx','static.pptx','checks.json'].map(n=>path.join(temp,n));
    function python(args) {
      const result=spawnSync(process.env.PYTHON || 'python3',[path.join(ROOT,'scripts/pptx.py'),...args],{encoding:'utf8'});
      check(!result.error && result.status===0,result.error?.message || result.stderr || result.stdout);
    }
    python(['finalize',raw,...generated]);
    if(pdf) {generated.push(path.join(temp,'static.pdf'));python(['pdf',generated[1],generated[3]]);}
    const published=[];
    try {generated.forEach((file,i)=>{fs.linkSync(file,targets[i]);published.push(targets[i]);});}
    catch(error) {published.forEach(p=>fs.unlinkSync(p));throw error;}
    return targets;
  } finally {fs.rmSync(temp,{recursive:true,force:true});}
}

if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const [spec,output,...flags]=process.argv.slice(2);
  if(!spec || !output || flags.some(f=>f!=='--pdf')) {
    console.error('사용법: node scripts/build.mjs spec.json output/deck.pptx [--pdf]');process.exitCode=1;
  } else {
    try {for(const file of await build(path.resolve(spec),path.resolve(output),flags.includes('--pdf')))console.log(file);}
    catch(error) {console.error(error.message);process.exitCode=1;}
  }
}
