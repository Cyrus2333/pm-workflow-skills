#!/usr/bin/env node

import fs from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const HOST_SELECTOR = '#svg-host, [data-prd-svg-host]';
const DEFAULT_RENDER_TIMEOUT = 3000;
const MIN_NODE_MAJOR = 20;

export class ValidationEnvironmentError extends Error {}

export function resolvePlaywright(requireFn = require) {
  try {
    return requireFn('playwright');
  } catch (error) {
    throw new ValidationEnvironmentError(
      `validation not completed: playwright is unavailable (${error.message}). Run npm ci in skills/pm-prd-html.`,
    );
  }
}

export function resolveBrowserExecutable(chromium, env = process.env, exists = existsSync) {
  const candidates = [env.PLAYWRIGHT_CHROMIUM_EXECUTABLE, chromium.executablePath()].filter(Boolean);
  const executablePath = candidates.find((candidate) => exists(candidate));
  if (!executablePath) {
    throw new ValidationEnvironmentError(
      'validation not completed: Chromium is unavailable. Run npx playwright install chromium or set PLAYWRIGHT_CHROMIUM_EXECUTABLE.',
    );
  }
  return executablePath;
}

function assertNodeVersion() {
  const major = Number(process.versions.node.split('.')[0]);
  if (!Number.isFinite(major) || major < MIN_NODE_MAJOR) {
    throw new ValidationEnvironmentError(`validation not completed: Node.js >= ${MIN_NODE_MAJOR} is required.`);
  }
}

function parseArgs(argv) {
  const files = [];
  let screenshots = null;
  let json = false;
  let renderTimeout = DEFAULT_RENDER_TIMEOUT;
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--json') json = true;
    else if (arg === '--screenshots') screenshots = argv[++index];
    else if (arg === '--render-timeout') renderTimeout = Number(argv[++index]);
    else if (arg.startsWith('-')) throw new Error(`unknown option: ${arg}`);
    else files.push(arg);
  }
  if (!files.length) throw new Error('usage: validate-svg-layout.mjs [--json] [--screenshots DIR] [--render-timeout MS] file.html [...]');
  if (screenshots === undefined) throw new Error('--screenshots requires a directory');
  if (!Number.isFinite(renderTimeout) || renderTimeout < 50) throw new Error('--render-timeout must be at least 50 ms');
  return { files, screenshots, json, renderTimeout };
}

const inspectRenderState = (expectedState) => {
  const hosts = [...document.querySelectorAll('#svg-host, [data-prd-svg-host]')];
  const host = hosts[0] || null;
  const svgs = host ? [...host.querySelectorAll(':scope > svg')] : [];
  const svg = svgs[0] || null;
  return {
    expectedState,
    hostCount: hosts.length,
    svgCount: svgs.length,
    renderStatus: host?.dataset.renderStatus || null,
    hostState: host?.dataset.renderedState || null,
    svgState: svg?.dataset.renderedState || null,
    ready: hosts.length === 1 && svgs.length === 1
      && host.dataset.renderStatus === 'ready'
      && host.dataset.renderedState === expectedState
      && svg.dataset.renderedState === expectedState,
  };
};

const browserMeasure = (expectedState) => {
  const hosts = [...document.querySelectorAll('#svg-host, [data-prd-svg-host]')];
  const renderHost = hosts[0] || null;
  const renderedSvgs = renderHost ? [...renderHost.querySelectorAll(':scope > svg')] : [];
  const renderedSvg = renderedSvgs[0] || null;
  const render = {
    expectedState,
    hostCount: hosts.length,
    svgCount: renderedSvgs.length,
    renderStatus: renderHost?.dataset.renderStatus || null,
    hostState: renderHost?.dataset.renderedState || null,
    svgState: renderedSvg?.dataset.renderedState || null,
    ready: hosts.length === 1 && renderedSvgs.length === 1
      && renderHost.dataset.renderStatus === 'ready'
      && renderHost.dataset.renderedState === expectedState
      && renderedSvg.dataset.renderedState === expectedState,
  };
  if (!render.ready) return { signature: null, issues: [], render };
  const host = document.querySelector('#svg-host, [data-prd-svg-host]');
  const svg = host.querySelector(':scope > svg');
  const issues = [];
  const tolerance = 0.75;
  const normalize = (value) => value.replace(/\s+/g, ' ').trim();
  const push = (type, elements, detail) => issues.push({ type, elements, detail });
  const elementName = (element) => {
    const name = element.getAttribute?.('data-layout-block')
      || element.getAttribute?.('data-layout-box')
      || element.getAttribute?.('data-layout-control')
      || element.getAttribute?.('aria-label')
      || element.id
      || normalize(element.textContent || '').slice(0, 32);
    return `<${element.localName}${name ? ` ${name}` : ''}>`;
  };
  const signatureNode = (node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      const value = normalize(node.textContent || '');
      return value ? `#${value}` : '';
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return '';
    const attrs = [...node.attributes].sort((a, b) => a.name.localeCompare(b.name))
      .map((attr) => `${attr.name}=${normalize(attr.value)}`).join('|');
    return `<${node.localName}|${attrs}>${[...node.childNodes].map(signatureNode).join('')}</${node.localName}>`;
  };
  const isVisible = (element) => {
    for (let current = element; current && current !== svg.parentElement; current = current.parentElement) {
      const style = getComputedStyle(current);
      if (style.display === 'none' || style.visibility === 'hidden' || style.visibility === 'collapse' || Number(style.opacity) <= 0) return false;
      if (current === svg) break;
    }
    return true;
  };

  const contract = svg.dataset.layoutContract;
  if (!['flat-v1', 'annotated-v1'].includes(contract)) {
    push('UNSUPPORTED_LAYOUT_CONTRACT', [elementName(svg)], 'root SVG must declare data-layout-contract="flat-v1" or "annotated-v1"');
  }
  if (svg.querySelector('svg')) push('UNSUPPORTED_NESTED_SVG', [elementName(svg.querySelector('svg'))], 'nested SVG is not supported by this contract');
  if (svg.querySelector('foreignObject')) push('UNSUPPORTED_FOREIGN_OBJECT', [elementName(svg.querySelector('foreignObject'))], 'foreignObject is not supported');

  const allowNodes = [...(svg.hasAttribute('data-layout-allow') ? [svg] : []), ...svg.querySelectorAll('[data-layout-allow]')];
  const validAllowNodes = new Set();
  for (const node of allowNodes) {
    const tokens = (node.dataset.layoutAllow || '').split(/\s+/).filter(Boolean);
    const role = node.dataset.layoutRole;
    const invalidToken = tokens.some((token) => !['overlap', 'overflow'].includes(token));
    const containsLayout = node.matches('svg, [data-layout-block], [data-layout-box], [data-layout-control]')
      || Boolean(node.querySelector('[data-layout-block], [data-layout-box], [data-layout-control]'));
    const tooBroad = node === svg || containsLayout || !['decor', 'badge', 'overlay'].includes(role)
      || node.children.length > 4 || [...node.children].some((child) => child.localName === 'g' && !child.dataset.layoutRole);
    if (!tokens.length || invalidToken || tooBroad) {
      push('INVALID_ALLOW_SCOPE', [elementName(node)], 'allow is limited to a minimal decor/badge/overlay element or group');
    } else {
      validAllowNodes.add(node);
    }
  }
  const allowance = (element, kind) => {
    const owner = element.closest('[data-layout-allow]');
    return owner && validAllowNodes.has(owner) && owner.dataset.layoutAllow.split(/\s+/).includes(kind);
  };

  const textLines = [];
  for (const text of svg.querySelectorAll('text')) {
    const children = [...text.children];
    const rawText = [...text.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE && normalize(node.textContent || ''));
    if (!children.length) {
      if (isVisible(text) && normalize(text.textContent || '')) textLines.push(text);
      continue;
    }
    const supported = !rawText.length && children.every((child) => child.localName === 'tspan'
      && child.hasAttribute('data-layout-line') && child.children.length === 0);
    if (!supported) {
      push('UNSUPPORTED_TEXT_STRUCTURE', [elementName(text)], 'multiline text requires direct tspan[data-layout-line] children and no mixed text');
      continue;
    }
    children.filter((line) => isVisible(line) && normalize(line.textContent || '')).forEach((line) => textLines.push(line));
  }

  const blocks = [];
  const controls = [];
  let rects = [];
  const rootVisualChildren = [...svg.children].filter((child) => !['defs', 'title', 'desc', 'metadata'].includes(child.localName));
  const annotationNodes = svg.querySelectorAll('[data-layout-block], [data-layout-box], [data-layout-control]');
  if (contract === 'flat-v1') {
    if (annotationNodes.length || rootVisualChildren.some((child) => child.localName === 'g')) {
      push('PARTIAL_LAYOUT_ANNOTATION', [elementName(svg)], 'flat-v1 requires only direct root primitives and no layout annotations/groups');
    }
  } else if (contract === 'annotated-v1') {
    const blockNodes = [...svg.querySelectorAll('g[data-layout-block], g[data-layout-box]')];
    const uniqueBlocks = [...new Set(blockNodes)];
    if (!uniqueBlocks.length) push('PARTIAL_LAYOUT_ANNOTATION', [elementName(svg)], 'annotated-v1 requires at least one layout block');
    for (const block of uniqueBlocks) {
      if (!block.dataset.layoutBlock || !block.dataset.layoutBox) {
        push('PARTIAL_LAYOUT_ANNOTATION', [elementName(block)], 'each layout block must declare both data-layout-block and data-layout-box');
        continue;
      }
      const boundaries = block.querySelectorAll(':scope > rect[data-layout-boundary]');
      if (boundaries.length !== 1) {
        push('PARTIAL_LAYOUT_ANNOTATION', [elementName(block)], 'each layout block must have exactly one direct rect[data-layout-boundary]');
        continue;
      }
      blocks.push({ element: block, boundary: boundaries[0] });
    }
    for (const control of svg.querySelectorAll('g[data-layout-control]')) {
      const boundaries = control.querySelectorAll(':scope > rect[data-layout-boundary]');
      if (boundaries.length !== 1 || !control.closest('g[data-layout-block][data-layout-box]')) {
        push('PARTIAL_LAYOUT_ANNOTATION', [elementName(control)], 'each control must belong to a block and have one direct rect[data-layout-boundary]');
        continue;
      }
      controls.push({ element: control, boundary: boundaries[0], annotated: true });
    }
    for (const child of rootVisualChildren) {
      const accepted = child.matches('g[data-layout-block][data-layout-box], [data-layout-role="chrome"], [data-layout-role="page-background"], [data-layout-allow]');
      if (!accepted) push('PARTIAL_LAYOUT_ANNOTATION', [elementName(child)], 'annotated-v1 has an unowned root visual node');
    }
    for (const block of uniqueBlocks) {
      for (const rect of block.querySelectorAll('rect')) {
        const accepted = rect.matches('[data-layout-boundary], [data-layout-role="rule"]')
          || Boolean(rect.closest('[data-layout-control], [data-layout-allow]'));
        if (!accepted) push('PARTIAL_LAYOUT_ANNOTATION', [elementName(rect)], 'rect inside a block must be its boundary, a rule, a control boundary, or decoration');
      }
    }
  }

  const boxCache = new Map();
  const box = (element) => {
    if (boxCache.has(element)) return boxCache.get(element);
    try {
      const value = element.getBBox();
      const elementMatrix = element.getScreenCTM();
      const rootMatrix = svg.getScreenCTM();
      if (!elementMatrix || !rootMatrix) throw new Error('missing browser matrix');
      const elementDomMatrix = new DOMMatrix([elementMatrix.a, elementMatrix.b, elementMatrix.c, elementMatrix.d, elementMatrix.e, elementMatrix.f]);
      const rootDomMatrix = new DOMMatrix([rootMatrix.a, rootMatrix.b, rootMatrix.c, rootMatrix.d, rootMatrix.e, rootMatrix.f]);
      const matrix = rootDomMatrix.inverse().multiply(elementDomMatrix);
      if (Math.abs(matrix.b) > 1e-9 || Math.abs(matrix.c) > 1e-9) throw new Error('rotation/skew transforms are outside the axis-aligned layout contract');
      const corners = [
        new DOMPoint(value.x, value.y), new DOMPoint(value.x + value.width, value.y),
        new DOMPoint(value.x, value.y + value.height), new DOMPoint(value.x + value.width, value.y + value.height),
      ].map((point) => point.matrixTransform(matrix));
      if (corners.some((point) => !Number.isFinite(point.x) || !Number.isFinite(point.y))) throw new Error('non-finite transformed geometry');
      const xs = corners.map((point) => point.x);
      const ys = corners.map((point) => point.y);
      const result = { x: Math.min(...xs), y: Math.min(...ys), width: Math.max(...xs) - Math.min(...xs), height: Math.max(...ys) - Math.min(...ys) };
      boxCache.set(element, result);
      return result;
    } catch (error) {
      push('UNSUPPORTED_GEOMETRY_TRANSFORM', [elementName(element)], error.message);
      boxCache.set(element, null);
      return null;
    }
  };
  const right = (value) => value.x + value.width;
  const bottom = (value) => value.y + value.height;
  const area = (value) => Math.max(0, value.width) * Math.max(0, value.height);
  const contains = (outer, inner, margin = tolerance) => inner.x >= outer.x - margin && inner.y >= outer.y - margin
    && right(inner) <= right(outer) + margin && bottom(inner) <= bottom(outer) + margin;
  const intersects = (a, b) => {
    const width = Math.min(right(a), right(b)) - Math.max(a.x, b.x);
    const height = Math.min(bottom(a), bottom(b)) - Math.max(a.y, b.y);
    return width > tolerance && height > tolerance ? width * height : 0;
  };
  const describe = (element) => {
    const value = box(element);
    return `${elementName(element)}${value ? ` @(${value.x.toFixed(1)},${value.y.toFixed(1)},${value.width.toFixed(1)},${value.height.toFixed(1)})` : ''}`;
  };

  const viewBox = svg.viewBox.baseVal;
  const viewport = { x: viewBox.x, y: viewBox.y, width: viewBox.width, height: viewBox.height };
  if (!(viewport.width > 0 && viewport.height > 0)) push('UNSUPPORTED_VIEWBOX', [elementName(svg)], 'root SVG requires a positive viewBox');
  const visibleElements = [...svg.querySelectorAll('text, tspan, rect, circle, ellipse, line, path, polygon, polyline, image')]
    .filter((element) => isVisible(element) && (element.localName !== 'text' || !element.children.length));
  for (const element of visibleElements) {
    const value = box(element);
    if (value && !allowance(element, 'overflow') && !contains(viewport, value)) {
      push('VIEWBOX_OVERFLOW', [describe(element)], 'visible geometry exceeds the SVG viewBox');
    }
  }

  if (contract === 'flat-v1') {
    rects = [...svg.querySelectorAll(':scope > rect')].map((element) => ({ element, value: box(element) })).filter(({ value }) => value);
    const candidates = rects.filter(({ value }) => value.width >= 80 && value.height >= 32 && area(value) < area(viewport) * 0.92);
    candidates.forEach((candidate) => blocks.push({ element: candidate.element, boundary: candidate.element }));
    candidates.filter(({ value }) => value.height >= 24 && value.height <= 72 && value.width >= 40)
      .forEach((candidate) => controls.push({ element: candidate.element, boundary: candidate.element, annotated: false }));
  }

  const blockBoxes = blocks.map((item) => ({ ...item, value: box(item.boundary) })).filter(({ value }) => value);
  for (let first = 0; first < blockBoxes.length; first += 1) {
    for (let second = first + 1; second < blockBoxes.length; second += 1) {
      const a = blockBoxes[first];
      const b = blockBoxes[second];
      if (allowance(a.element, 'overlap') || allowance(b.element, 'overlap')) continue;
      if (contains(a.value, b.value) || contains(b.value, a.value)) continue;
      if (intersects(a.value, b.value)) push('BLOCK_OVERLAP', [describe(a.element), describe(b.element)], 'layout blocks overlap');
    }
  }

  const lines = textLines.map((element) => ({ element, value: box(element) })).filter(({ value }) => value);
  for (const line of lines) {
    if (allowance(line.element, 'overflow')) continue;
    let owner = null;
    if (contract === 'annotated-v1') {
      const control = line.element.closest('g[data-layout-control]');
      const block = line.element.closest('g[data-layout-block][data-layout-box]');
      const entry = control ? controls.find((item) => item.element === control) : blocks.find((item) => item.element === block);
      if (entry) owner = { element: entry.boundary, value: box(entry.boundary) };
      else if (!line.element.closest('[data-layout-role="chrome"], [data-layout-allow]')) {
        push('PARTIAL_LAYOUT_ANNOTATION', [describe(line.element)], 'visible text is not owned by a block, control, chrome, or decoration');
      }
    } else {
      const center = { x: line.value.x + line.value.width / 2, y: line.value.y + line.value.height / 2, width: 0, height: 0 };
      owner = blockBoxes.filter((candidate) => contains(candidate.value, center, 0)).sort((a, b) => area(a.value) - area(b.value))[0] || null;
    }
    if (owner?.value && !contains(owner.value, line.value)) push('TEXT_OUTSIDE_CARD', [describe(line.element), describe(owner.element)], 'text exceeds its owning card/control');
  }

  const controlBoxes = controls.map((item) => ({ ...item, value: box(item.boundary) })).filter(({ value }) => value);
  for (const control of controlBoxes) {
    for (const line of lines) {
      if (allowance(control.element, 'overlap') || allowance(line.element, 'overlap')) continue;
      if (control.annotated && control.element.contains(line.element)) continue;
      if (!intersects(control.value, line.value)) continue;
      if (!control.annotated && contains(control.value, line.value)) continue;
      push('CONTROL_TEXT_OVERLAP', [describe(line.element), describe(control.element)], 'text overlaps a control it does not belong to');
    }
  }
  for (let first = 0; first < lines.length; first += 1) {
    for (let second = first + 1; second < lines.length; second += 1) {
      const a = lines[first];
      const b = lines[second];
      if (allowance(a.element, 'overlap') || allowance(b.element, 'overlap')) continue;
      if (intersects(a.value, b.value)) push('TEXT_OVERLAP', [describe(a.element), describe(b.element)], 'rendered text line bounding boxes overlap');
    }
  }

  return { signature: signatureNode(svg), issues, render };
};

async function installPageDiagnostics(page) {
  await page.addInitScript(() => {
    globalThis.__prdFontErrors = [];
    document.fonts?.addEventListener('loadingerror', (event) => {
      const families = [...(event.fontfaces || [])].map((face) => face.family).join(', ');
      globalThis.__prdFontErrors.push(families || 'unknown font');
    });
  });
}

async function waitForFonts(page, timeout) {
  try {
    await page.evaluate(async (limit) => {
      if (!document.fonts) throw new Error('FontFaceSet API is unavailable');
      await Promise.race([
        document.fonts.ready,
        new Promise((_, reject) => setTimeout(() => reject(new Error('font readiness timeout')), limit)),
      ]);
      if (document.fonts.status !== 'loaded') throw new Error(`font status is ${document.fonts.status}`);
      if (globalThis.__prdFontErrors?.length) throw new Error(`font loading failed: ${globalThis.__prdFontErrors.join(', ')}`);
    }, timeout);
    return null;
  } catch (error) {
    return error.message.includes('font loading failed') ? 'FONT_LOAD_FAILED' : 'FONT_READY_TIMEOUT';
  }
}

async function waitForRenderedState(page, stateId, timeout) {
  try {
    await page.waitForFunction((state) => {
      const hosts = [...document.querySelectorAll('#svg-host, [data-prd-svg-host]')];
      if (hosts.length !== 1) return false;
      const svgs = hosts[0].querySelectorAll(':scope > svg');
      return svgs.length === 1 && hosts[0].dataset.renderStatus === 'ready'
        && hosts[0].dataset.renderedState === state && svgs[0].dataset.renderedState === state;
    }, stateId, { timeout });
    const fontError = await waitForFonts(page, timeout);
    if (fontError) return { ok: false, type: fontError, detail: 'fonts did not reach a successful ready state' };
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    return { ok: true };
  } catch {
    const snapshot = await page.evaluate(inspectRenderState, stateId).catch(() => null);
    if (!snapshot) return { ok: false, type: 'STATE_RENDER_TIMEOUT', detail: 'page became unavailable while waiting for state rendering' };
    if (snapshot.hostCount !== 1) return { ok: false, type: 'SVG_HOST_COUNT_INVALID', detail: `expected 1 host, found ${snapshot.hostCount}` };
    if (snapshot.svgCount === 0) return { ok: false, type: 'SVG_MISSING', detail: 'host contains no SVG' };
    if (snapshot.svgCount > 1) return { ok: false, type: 'MULTIPLE_SVG', detail: `host contains ${snapshot.svgCount} SVG elements` };
    if (snapshot.hostState !== stateId || snapshot.svgState !== stateId) {
      return { ok: false, type: 'RENDERED_STATE_MISMATCH', detail: `target=${stateId}, host=${snapshot.hostState || '(none)'}, svg=${snapshot.svgState || '(none)'}` };
    }
    return { ok: false, type: 'STATE_RENDER_TIMEOUT', detail: `render status remained ${snapshot.renderStatus || '(none)'}` };
  }
}

async function staticSnapshot(browser, url, initialState) {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1440, height: 1000 } });
  try {
    const page = await context.newPage();
    await page.goto(url, { waitUntil: 'load' });
    return await page.evaluate(browserMeasure, initialState);
  } finally {
    await context.close();
  }
}

async function validateFile(browser, file, options) {
  const absolute = path.resolve(file);
  await fs.access(absolute);
  const url = pathToFileURL(absolute).href;
  const result = { file: absolute, states: [], attemptedStates: [], issues: [] };
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  try {
    const page = await context.newPage();
    await installPageDiagnostics(page);
    const pageErrors = [];
    page.on('pageerror', (error) => pageErrors.push(error.message));
    await page.goto(url, { waitUntil: 'load' });

    const hostCount = await page.locator(HOST_SELECTOR).count();
    const initialState = hostCount === 1 ? await page.locator(HOST_SELECTOR).getAttribute('data-initial-state') : null;
    if (hostCount !== 1) result.issues.push({ state: '(initial)', type: 'SVG_HOST_COUNT_INVALID', elements: [HOST_SELECTOR], detail: `expected 1 host, found ${hostCount}` });
    if (!initialState) result.issues.push({ state: '(initial)', type: 'INITIAL_STATE_MISSING', elements: [HOST_SELECTOR], detail: 'data-initial-state is required' });

    const stateIds = await page.locator('[data-state]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-state')));
    if (!stateIds.length) result.issues.push({ state: '(document)', type: 'STATE_ENUMERATION_EMPTY', elements: ['[data-state]'], detail: 'no page states were found' });
    const invalidIds = stateIds.filter((id, index) => !id || stateIds.indexOf(id) !== index);
    if (invalidIds.length) result.issues.push({ state: '(document)', type: 'STATE_ID_INVALID', elements: ['[data-state]'], detail: `missing or duplicate ids: ${[...new Set(invalidIds)].join(', ')}` });
    if (initialState && !stateIds.includes(initialState)) result.issues.push({ state: initialState, type: 'INITIAL_STATE_NOT_ENUMERATED', elements: ['[data-state]'], detail: 'initial state has no controller' });

    if (initialState) {
      const staticData = await staticSnapshot(browser, url, initialState);
      if (!staticData.render.ready) {
        const rendered = staticData.render;
        const type = rendered.svgCount === 0 ? 'STATIC_INITIAL_MISSING' : rendered.svgCount > 1 ? 'MULTIPLE_SVG' : 'INITIAL_STATE_MISMATCH';
        result.issues.push({ state: initialState, type, elements: [HOST_SELECTOR], detail: `static host=${rendered.hostState || '(none)'}, svg=${rendered.svgState || '(none)'}, status=${rendered.renderStatus || '(none)'}` });
      }
      const ready = await waitForRenderedState(page, initialState, options.renderTimeout);
      if (!ready.ok) {
        result.issues.push({ state: initialState, type: ready.type, elements: [HOST_SELECTOR], detail: ready.detail });
      } else {
        const runtime = await page.evaluate(browserMeasure, initialState);
        runtime.issues.forEach((issue) => result.issues.push({ state: initialState, ...issue }));
        if (staticData.signature && runtime.signature !== staticData.signature) {
          result.issues.push({ state: initialState, type: 'INITIAL_SVG_MISMATCH', elements: [`${HOST_SELECTOR} svg`], detail: 'static SVG differs from the first runtime SVG' });
        }
      }
    }

    for (const stateId of [...new Set(stateIds.filter(Boolean))]) {
      result.attemptedStates.push(stateId);
      const beforeErrors = pageErrors.length;
      try {
        await page.locator(`[data-state=${JSON.stringify(stateId)}]`).first().click({ timeout: options.renderTimeout });
      } catch (error) {
        result.issues.push({ state: stateId, type: 'CONTROL_CLICK_FAILED', elements: [`[data-state="${stateId}"]`], detail: error.message.split('\n')[0] });
        continue;
      }
      const ready = await waitForRenderedState(page, stateId, options.renderTimeout);
      if (!ready.ok) {
        result.issues.push({ state: stateId, type: ready.type, elements: [HOST_SELECTOR], detail: ready.detail });
        continue;
      }
      if (pageErrors.length > beforeErrors) {
        pageErrors.slice(beforeErrors).forEach((detail) => result.issues.push({ state: stateId, type: 'PAGE_SCRIPT_ERROR', elements: ['script'], detail }));
        continue;
      }
      const measured = await page.evaluate(browserMeasure, stateId);
      measured.issues.forEach((issue) => result.issues.push({ state: stateId, ...issue }));
      result.states.push(stateId);
      if (options.screenshots) {
        const fileBase = path.basename(absolute, path.extname(absolute)).replace(/[<>:"/\\|?*\u0000-\u001f]+/g, '-');
        const stateBase = stateId.replace(/[^a-zA-Z0-9_-]+/g, '-');
        await fs.mkdir(options.screenshots, { recursive: true });
        await page.locator(HOST_SELECTOR).screenshot({ path: path.join(options.screenshots, `${fileBase}--${stateBase}.png`) });
      }
    }
    pageErrors.forEach((detail) => {
      if (!result.issues.some((issue) => issue.type === 'PAGE_SCRIPT_ERROR' && issue.detail === detail)) {
        result.issues.push({ state: '(document)', type: 'PAGE_SCRIPT_ERROR', elements: ['script'], detail });
      }
    });
  } finally {
    await context.close();
  }
  return result;
}

export async function validatePaths(options, dependencies = {}) {
  assertNodeVersion();
  const playwright = dependencies.playwright || resolvePlaywright();
  const executablePath = dependencies.executablePath
    || resolveBrowserExecutable(playwright.chromium, dependencies.env, dependencies.exists);
  const browser = await playwright.chromium.launch({ headless: true, executablePath });
  try {
    const results = [];
    for (const file of options.files) results.push(await validateFile(browser, file, {
      screenshots: options.screenshots || null,
      renderTimeout: options.renderTimeout || DEFAULT_RENDER_TIMEOUT,
    }));
    return results;
  } finally {
    await browser.close();
  }
}

async function main() {
  try {
    const options = parseArgs(process.argv.slice(2));
    const results = await validatePaths(options);
    if (options.json) console.log(JSON.stringify(results, null, 2));
    else {
      for (const result of results) {
        console.log(`${result.issues.length ? 'FAIL' : 'PASS'} ${result.file} (${result.states.length}/${result.attemptedStates.length} states validated)`);
        result.issues.forEach((issue) => console.error(`  ${issue.state} :: ${issue.type} :: ${issue.elements.join(' + ')} :: ${issue.detail}`));
      }
    }
    return results.some((result) => result.issues.length) ? 1 : 0;
  } catch (error) {
    const prefix = error instanceof ValidationEnvironmentError ? 'VALIDATION NOT COMPLETED' : 'ERROR';
    console.error(`${prefix}: ${error.message}`);
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) process.exitCode = await main();
