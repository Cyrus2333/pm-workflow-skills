#!/usr/bin/env node

import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ValidationEnvironmentError,
  resolveBrowserExecutable,
  resolvePlaywright,
  validatePaths,
} from './validate-svg-layout.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const fixtures = path.join(here, '..', 'tests', 'fixtures');
const examples = path.join(here, '..', 'examples');
const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'pm-prd-html-layout-'));

const flatSvg = (state, text = '正常内容', extra = '', rootAttrs = '') => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 220" data-layout-contract="flat-v1" data-rendered-state="${state}" ${rootAttrs}>
  <rect width="300" height="220" fill="#fff"/>
  <rect x="20" y="20" width="260" height="80" fill="#fff" stroke="#222"/>
  <text x="32" y="55" font-size="16">${text}</text>${extra}
</svg>`;

const block = (id, transform, y, content, attrs = '') => `<g data-layout-block="${id}" data-layout-box="${id}-card" transform="${transform}" ${attrs}>
  <rect data-layout-boundary x="0" y="${y}" width="240" height="60" fill="#fff" stroke="#222"/>
  ${content}
</g>`;

const annotatedSvg = (state, body, rootAttrs = '') => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 260" data-layout-contract="annotated-v1" data-rendered-state="${state}" ${rootAttrs}>${body}</svg>`;

function pageHtml({ states, staticSvg, initial = 'S1', buttons = null, renderScript = null }) {
  const stateButtons = buttons ?? Object.keys(states).map((id, index) => `<button class="state-btn${index === 0 ? ' active' : ''}" data-state="${id}">${id}</button>`).join('');
  const normalRender = `function render(id){const host=document.getElementById('svg-host');host.dataset.renderStatus='rendering';controls.forEach((control)=>control.classList.toggle('active',control.dataset.state===id));host.innerHTML=states[id];host.dataset.renderedState=id;host.dataset.renderStatus='ready';}`;
  return `<!doctype html><html><meta charset="utf-8"><body>${stateButtons}
<div id="svg-host" data-initial-state="${initial}" data-rendered-state="${initial}" data-render-status="ready">${staticSvg}</div>
<script>const states=${JSON.stringify(states)};const controls=[...document.querySelectorAll('[data-state]')];${renderScript || normalRender}
controls.forEach((control)=>control.addEventListener('click',()=>render(control.dataset.state)));render('${initial}');</script></body></html>`;
}

async function writeCase(name, html) {
  const file = path.join(tempRoot, `${name}.html`);
  await fs.writeFile(file, html, 'utf8');
  return file;
}

function issueTypes(result, state = null) {
  return result.issues.filter((issue) => !state || issue.state === state).map((issue) => issue.type);
}

assert.throws(
  () => resolvePlaywright(() => { throw new Error('module missing'); }),
  (error) => error instanceof ValidationEnvironmentError && /playwright is unavailable/.test(error.message),
  'missing Playwright must be a validation environment failure',
);
assert.throws(
  () => resolveBrowserExecutable({ executablePath: () => '/missing/chromium' }, {}, () => false),
  (error) => error instanceof ValidationEnvironmentError && /Chromium is unavailable/.test(error.message),
  'missing browser must be a validation environment failure',
);

const s1 = flatSvg('S1');
const s2 = flatSvg('S2', '第二状态');
const generated = [];
generated.push(['zero-states', await writeCase('zero-states', pageHtml({ states: { S1: s1 }, staticSvg: s1, buttons: '' }))]);
generated.push(['stale-svg', await writeCase('stale-svg', pageHtml({
  states: { S1: s1, S2: s2 }, staticSvg: s1,
  renderScript: `function render(id){const host=document.getElementById('svg-host');controls.forEach((control)=>control.classList.toggle('active',control.dataset.state===id));if(id==='S1'){host.innerHTML=states[id];host.dataset.renderedState=id;host.dataset.renderStatus='ready';}}`,
}))]);
generated.push(['multiple-svg', await writeCase('multiple-svg', pageHtml({
  states: { S1: s1, S2: s2 }, staticSvg: s1,
  renderScript: `function render(id){const host=document.getElementById('svg-host');controls.forEach((control)=>control.classList.toggle('active',control.dataset.state===id));host.innerHTML=id==='S2'?states[id]+states[id]:states[id];host.dataset.renderedState=id;host.dataset.renderStatus='ready';}`,
}))]);
generated.push(['missing-svg', await writeCase('missing-svg', pageHtml({
  states: { S1: s1, S2: s2 }, staticSvg: s1,
  renderScript: `function render(id){const host=document.getElementById('svg-host');controls.forEach((control)=>control.classList.toggle('active',control.dataset.state===id));host.innerHTML=id==='S2'?'':states[id];host.dataset.renderedState=id;host.dataset.renderStatus='ready';}`,
}))]);
generated.push(['render-timeout', await writeCase('render-timeout', pageHtml({
  states: { S1: s1, S2: s2 }, staticSvg: s1,
  renderScript: `function render(id){const host=document.getElementById('svg-host');controls.forEach((control)=>control.classList.toggle('active',control.dataset.state===id));host.innerHTML=states[id];host.dataset.renderedState=id;host.dataset.renderStatus=id==='S2'?'rendering':'ready';}`,
}))]);
generated.push(['click-failure', await writeCase('click-failure', pageHtml({
  states: { S1: s1, S2: s2 }, staticSvg: s1,
  buttons: '<button class="active" data-state="S1">S1</button><button data-state="S2" style="display:none">S2</button>',
}))]);
generated.push(['static-mismatch', await writeCase('static-mismatch', pageHtml({ states: { S1: flatSvg('S1', '运行时内容') }, staticSvg: flatSvg('S1', '静态内容') }))]);

const transformPass = annotatedSvg('S1',
  block('one', 'translate(20 20)', 0, '<text x="12" y="34" font-size="14">模块一</text>')
  + block('two', 'translate(20 100)', 0, '<text x="12" y="34" font-size="14">模块二</text>'));
const transformOverlap = annotatedSvg('S1',
  block('one', 'translate(20 20)', 0, '<text x="12" y="34" font-size="14">模块一</text>')
  + block('two', 'translate(20 65)', 0, '<text x="12" y="34" font-size="14">模块二</text>'));
const transformUnsupported = annotatedSvg('S1', block('one', 'rotate(5 120 30)', 0, '<text x="12" y="34" font-size="14">旋转模块</text>'));
generated.push(['transform-pass', await writeCase('transform-pass', pageHtml({ states: { S1: transformPass }, staticSvg: transformPass }))]);
generated.push(['transform-overlap', await writeCase('transform-overlap', pageHtml({ states: { S1: transformOverlap }, staticSvg: transformOverlap }))]);
generated.push(['transform-unsupported', await writeCase('transform-unsupported', pageHtml({ states: { S1: transformUnsupported }, staticSvg: transformUnsupported }))]);

const hiddenText = annotatedSvg('S1', block('one', 'translate(20 20)', 0,
  '<text x="12" y="34" font-size="14">可见文字</text><text x="12" y="34" font-size="14" visibility="hidden">隐藏文字</text>'));
generated.push(['hidden-text', await writeCase('hidden-text', pageHtml({ states: { S1: hiddenText }, staticSvg: hiddenText }))]);
const multiline = annotatedSvg('S1', block('one', 'translate(20 20)', 0,
  '<text font-size="14"><tspan data-layout-line x="12" y="25">第一行</tspan><tspan data-layout-line x="12" y="45">第二行</tspan></text>'));
generated.push(['multiline-pass', await writeCase('multiline-pass', pageHtml({ states: { S1: multiline }, staticSvg: multiline }))]);
const badMultiline = annotatedSvg('S1', block('one', 'translate(20 20)', 0,
  '<text font-size="14"><tspan x="12" y="25">未标注行</tspan><tspan x="12" y="45">第二行</tspan></text>'));
generated.push(['multiline-unsupported', await writeCase('multiline-unsupported', pageHtml({ states: { S1: badMultiline }, staticSvg: badMultiline }))]);

const partial = annotatedSvg('S1', `${block('one', 'translate(20 20)', 0, '<text x="12" y="34">模块</text>')}<rect x="20" y="120" width="200" height="40"/>`);
generated.push(['partial-annotation', await writeCase('partial-annotation', pageHtml({ states: { S1: partial }, staticSvg: partial }))]);
const rootAllow = flatSvg('S1', '内容', '', 'data-layout-role="decor" data-layout-allow="overlap"');
generated.push(['root-allow', await writeCase('root-allow', pageHtml({ states: { S1: rootAllow }, staticSvg: rootAllow }))]);
const moduleAllow = annotatedSvg('S1', block('one', 'translate(20 20)', 0, '<text x="12" y="34">模块</text>', 'data-layout-role="badge" data-layout-allow="overlap"'));
generated.push(['module-allow', await writeCase('module-allow', pageHtml({ states: { S1: moduleAllow }, staticSvg: moduleAllow }))]);
const nestedSvg = `${flatSvg('S1', '内容', '<svg x="20" y="100" width="50" height="50" viewBox="0 0 50 50"><rect width="50" height="50"/></svg>')}`;
generated.push(['nested-svg', await writeCase('nested-svg', pageHtml({ states: { S1: nestedSvg }, staticSvg: nestedSvg }))]);
const foreignObject = flatSvg('S1', '内容', '<foreignObject x="20" y="110" width="100" height="50"><div xmlns="http://www.w3.org/1999/xhtml">HTML</div></foreignObject>');
generated.push(['foreign-object', await writeCase('foreign-object', pageHtml({ states: { S1: foreignObject }, staticSvg: foreignObject }))]);

const files = [
  ...generated.map(([, file]) => file),
  path.join(fixtures, 'overlap-fail.html'),
  path.join(fixtures, 'cursor-pass.html'),
  path.join(examples, '活动详情页-资格提示-prd.html'),
  path.join(examples, '异步合唱内部MVP-prd.html'),
];

try {
  const reports = await validatePaths({ files, screenshots: null, renderTimeout: 300 });
  const byName = new Map(reports.map((report) => [path.basename(report.file, '.html'), report]));
  const expectIssue = (name, type, state = null) => assert.ok(issueTypes(byName.get(name), state).includes(type), `${name} must report ${type}: ${JSON.stringify(byName.get(name).issues)}`);
  const expectPass = (name) => assert.equal(byName.get(name).issues.length, 0, `${name} must pass: ${JSON.stringify(byName.get(name).issues)}`);

  expectIssue('zero-states', 'STATE_ENUMERATION_EMPTY');
  expectIssue('stale-svg', 'RENDERED_STATE_MISMATCH', 'S2');
  expectIssue('multiple-svg', 'MULTIPLE_SVG', 'S2');
  expectIssue('missing-svg', 'SVG_MISSING', 'S2');
  expectIssue('render-timeout', 'STATE_RENDER_TIMEOUT', 'S2');
  expectIssue('click-failure', 'CONTROL_CLICK_FAILED', 'S2');
  expectIssue('static-mismatch', 'INITIAL_SVG_MISMATCH', 'S1');
  expectPass('transform-pass');
  expectIssue('transform-overlap', 'BLOCK_OVERLAP', 'S1');
  expectIssue('transform-unsupported', 'UNSUPPORTED_GEOMETRY_TRANSFORM', 'S1');
  expectPass('hidden-text');
  expectPass('multiline-pass');
  expectIssue('multiline-unsupported', 'UNSUPPORTED_TEXT_STRUCTURE', 'S1');
  expectIssue('partial-annotation', 'PARTIAL_LAYOUT_ANNOTATION', 'S1');
  expectIssue('root-allow', 'INVALID_ALLOW_SCOPE', 'S1');
  expectIssue('module-allow', 'INVALID_ALLOW_SCOPE', 'S1');
  expectIssue('nested-svg', 'UNSUPPORTED_NESTED_SVG', 'S1');
  expectIssue('foreign-object', 'UNSUPPORTED_FOREIGN_OBJECT', 'S1');
  expectIssue('overlap-fail', 'BLOCK_OVERLAP', 'STORY-LONG');
  expectPass('cursor-pass');
  expectPass('活动详情页-资格提示-prd');
  expectPass('异步合唱内部MVP-prd');
  assert.equal(byName.get('活动详情页-资格提示-prd').states.length, 5, 'activity example must validate all states');
  assert.equal(byName.get('异步合唱内部MVP-prd').states.length, 7, 'chorus example must validate all states');
  console.log(`SVG layout validator tests passed: ${reports.length} browser cases plus missing dependency/browser checks.`);
} finally {
  await fs.rm(tempRoot, { recursive: true, force: true });
}
