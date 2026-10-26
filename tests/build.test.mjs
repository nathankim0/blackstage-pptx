import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {build,dateLabel,validate} from '../scripts/build.mjs';

const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const demo=JSON.parse(fs.readFileSync(path.join(root,'examples/demo.json'),'utf8'));
function python(args) {
  const result=spawnSync(process.env.PYTHON||'python3',[path.join(root,'tests/check_package.py'),...args],{encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);
  return result.stdout ? JSON.parse(result.stdout) : null;
}
async function withDeck(spec,run) {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'blackstage-test-'));
  try {
    python(['fixture',temp]);
    const input=path.join(temp,'spec.json'), output=path.join(temp,'deck.pptx');
    fs.writeFileSync(input,JSON.stringify(spec));
    await build(input,output);
    await run(python([output]),{input,output,temp});
  } finally {fs.rmSync(temp,{recursive:true,force:true});}
}

test('원래 개체를 현재 로드맵에서 클릭 이동·축소하고 정적 완료 상태는 별도로 보존한다',async()=>{
  await withDeck(demo,result=>{
    assert.equal(result.count,8);
    assert.deepEqual(result.owners,['ppt/slides/slide5.xml']);
    assert.ok(result.text_runs.some(([text,color])=>text==='기간: ' && color==='FFFFFF'));
    assert.ok(result.text_runs.some(([text,color])=>text==='11/9(월)' && color==='FFD54A'));
    assert.ok(result.text_runs.some(([text,color])=>text==='팀별로 진행' && color==='FFFFFF'));
  });
});

test('포스터 추가·목차 순서 변경 후에도 고정 장 번호나 고정 도형 ID에 의존하지 않는다',async()=>{
  const spec=structuredClone(demo);
  spec.sections=[spec.sections[1],spec.sections[3],spec.sections[0],spec.sections[2]];
  spec.slides.splice(3,0,{kind:'image',path:'tall.png',nav:false});
  const road=spec.slides.find(s=>s.kind==='roadmap');
  road.reveal={kind:'gallery',title:'준비 기록',images:[{path:'wide.png',label:'1일차'},{path:'tall.png',label:'2일차'}]};
  await withDeck(spec,result=>{
    assert.equal(result.count,9);
    assert.deepEqual(result.owners,['ppt/slides/slide6.xml']);
    assert.equal(result.image_ratios.length,3);
    assert.ok(result.image_ratios.filter(r=>Math.abs(r-0.5)<1e-5).length===2);
    assert.ok(result.image_ratios.some(r=>Math.abs(r-2)<1e-5));
  });
});

test('포스터 삭제·상단 항목 제거 후에도 본문·표기·같은 개체 이동을 보존한다',async()=>{
  const spec=structuredClone(demo);
  spec.sections=spec.sections.filter(s=>s.id!=='overview');
  spec.slides=spec.slides.filter(s=>s.section!=='overview');
  await withDeck(spec,result=>{
    assert.equal(result.count,7);
    assert.deepEqual(result.owners,['ppt/slides/slide4.xml']);
  });
});

test('기존 파일을 덮어쓰지 않고 실패한 결과 세트를 공개하지 않는다',async()=>{
  await withDeck(demo,async(_,{input,output,temp})=>{
    const original=fs.readFileSync(output);
    await assert.rejects(build(input,output),/기존 파일/);
    assert.deepEqual(fs.readFileSync(output),original);
    const invalid=structuredClone(demo);
    invalid.slides[0].title='매우긴제목'.repeat(50);
    fs.writeFileSync(input,JSON.stringify(invalid));
    const failed=path.join(temp,'failed.pptx');
    await assert.rejects(build(input,failed),/내용을 나누세요/);
    assert.ok(!fs.existsSync(failed));
    assert.ok(!fs.existsSync(path.join(temp,'failed.static.pptx')));
    assert.ok(!fs.readdirSync(temp).some(n=>n.startsWith('.blackstage-')));
  });
});

test('요일을 실제 날짜에서 계산하고 잘못된 날짜·목차·본문은 거부한다',()=>{
  assert.equal(dateLabel('2026-10-24'),'10/24(토)');
  assert.equal(dateLabel('2026-11-23'),'11/23(월)');
  assert.throws(()=>dateLabel('2026-02-30'),/존재하지 않는/);
  assert.throws(()=>dateLabel('11/23'),/YYYY-MM-DD/);
  const missing=structuredClone(demo);missing.slides[3].section='missing';
  assert.throws(()=>validate(missing),/없는 section/);
  const duplicate=structuredClone(demo);duplicate.sections[1].id=duplicate.sections[0].id;
  assert.throws(()=>validate(duplicate),/중복 section/);
  const spelling=structuredClone(demo);spelling.slides[4].steps[1].label='준 비';
  assert.throws(()=>validate(spelling),/표기를 똑같이/);
  const long=structuredClone(demo);long.slides[3].lines=['하나','둘','셋'];
  assert.throws(()=>validate(long),/최대 두 줄/);
});

const pdfTools=['soffice','pdffonts','pdfinfo'].every(tool=>spawnSync(tool,['-v'],{encoding:'utf8'}).error===undefined);
test('정적 PDF의 페이지 수와 실제 나눔 글꼴 포함을 확인한다',{skip:!pdfTools},async()=>{
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'blackstage-pdf-test-'));
  try {
    const spec=path.join(temp,'spec.json'),out=path.join(temp,'deck.pptx');
    fs.writeFileSync(spec,JSON.stringify(demo));
    await build(spec,out,true);
    const pdf=path.join(temp,'deck.pdf');
    const info=spawnSync('pdfinfo',[pdf],{encoding:'utf8'});
    assert.equal(info.status,0,info.stderr);
    assert.match(info.stdout,/Pages:\s+8\b/);
    const fonts=spawnSync('pdffonts',[pdf],{encoding:'utf8'});
    assert.equal(fonts.status,0,fonts.stderr);
    assert.match(fonts.stdout,/NanumGothic/i);
    assert.doesNotMatch(fonts.stdout,/FrankRuhl|Libertine/i);
  } finally {fs.rmSync(temp,{recursive:true,force:true});}
});
