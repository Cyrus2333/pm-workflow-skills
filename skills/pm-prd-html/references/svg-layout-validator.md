# SVG 布局校验器

`scripts/validate-svg-layout.mjs` 使用 Playwright 驱动 Chromium，以浏览器真实字体和矩阵能力检查全部页面状态。它只支持本规范定义的受控 SVG，不兼容任意手写结构；发现未支持结构时返回阻断错误，不用原始坐标或字符串规则继续给出 PASS。

## 1. 可复现运行环境

支持 Windows、macOS 和 Linux，统一要求：

- Node.js 20 或更高版本；
- Skill 目录内锁定的 Playwright 依赖；
- Playwright 自带 Chromium，或通过 `PLAYWRIGHT_CHROMIUM_EXECUTABLE` 指定 Chromium 兼容浏览器的绝对路径。

从干净仓库运行：

```bash
cd skills/pm-prd-html
npm ci
npm run install-browser
npm test
npm run validate -- path/to/prd.html
```

`npm ci` 只在 Skill 目录安装校验依赖；`npm run install-browser` 下载与 lockfile 中 Playwright 版本匹配的 Chromium，不进入 PRD HTML，也不提交到 Skill 仓库。受控环境若已有兼容浏览器，可跳过浏览器下载并在运行前设置：

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/absolute/path/to/chromium npm run validate -- path/to/prd.html
```

Windows PowerShell 使用 `$env:PLAYWRIGHT_CHROMIUM_EXECUTABLE='C:\absolute\path\to\browser.exe'`。不要依赖 Codex 机器特有的 `NODE_PATH`。

缺少 Node、Playwright 或浏览器时，CLI 输出 `VALIDATION NOT COMPLETED` 并返回退出码 2；这表示没有完成浏览器验证，不是布局通过。此时 Skill 最终结论最高只能是 `PASS_WITH_CONDITIONS`。

## 2. 状态渲染契约

每个 HTML 必须满足：

```html
<button class="state-btn active" data-state="STORY-01">默认态</button>
<button class="state-btn" data-state="STORY-02">长内容态</button>

<div id="svg-host"
     data-initial-state="STORY-01"
     data-rendered-state="STORY-01"
     data-render-status="ready">
  <svg viewBox="0 0 390 844"
       data-layout-contract="annotated-v1"
       data-rendered-state="STORY-01">...</svg>
</div>
```

- `[data-state]` 值唯一；校验器枚举整个 DOM 中的全部状态控制器，不按可见性裁剪。
- 切换开始时 host 写 `data-render-status="rendering"`；唯一 SVG 完成装配后，host 与 SVG 的 `data-rendered-state` 同时写为目标状态，最后把 host 状态改为 `ready`。
- host 中必须始终只有一个直属 SVG。缺失、多个、目标状态不一致、点击失败或超时均阻断。
- 禁用脚本时仍必须存在同一 initial state 的静态 SVG；静态 SVG 与脚本首次渲染 SVG 的完整结构、属性和文字必须一致。
- 校验器等待上述 ready 信号、`document.fonts.ready` 和最终绘制帧后才测量或截图。字体失败、页面脚本异常和等待超时均阻断。

## 3. 支持的 SVG 契约

根 SVG 必须声明且只能选择一种 `data-layout-contract`。

### 3.1 `flat-v1`

仅用于既有、简单的扁平线框：

- 可见图元必须是根 SVG 的直属基础图元；
- 不允许 group、任何 layout annotation、嵌套 SVG、`foreignObject` 或复杂文字；
- 卡片和控件按受限的矩形尺寸规则检查。

`flat-v1` 不作为新复杂页面的推荐生成模式。需要 transform、复合控件、角标或多行文字时使用 `annotated-v1`。

### 3.2 `annotated-v1`

顺序模块使用完整标注：

```html
<g data-layout-block="summary" data-layout-box="summary-card" transform="translate(20 40)">
  <rect data-layout-boundary x="0" y="0" width="350" height="120" />
  <text x="16" y="32">标题</text>
  <g data-layout-control="primary-action">
    <rect data-layout-boundary x="16" y="64" width="318" height="44" />
    <text x="175" y="92" text-anchor="middle">继续</text>
  </g>
</g>
```

- 每个 block 同时具有 `data-layout-block` 和 `data-layout-box`，并且恰有一个直属 `rect[data-layout-boundary]`；
- 每个 control 属于一个 block，并且恰有一个直属 boundary；
- 页面 chrome / 背景使用 `data-layout-role="chrome"` 或 `page-background`；规则线使用 `rule`；
- 不允许同类节点一部分标注、一部分推断。出现未归属根图元、缺少成对 block/box、缺少 boundary 或普通矩形未归属时，返回 `PARTIAL_LAYOUT_ANNOTATION`；
- group 和元素的轴对齐 translate / scale transform 通过浏览器 `getScreenCTM()` / `DOMMatrix` 转换到根 SVG 坐标系后比较；旋转、斜切或无法获得可靠矩阵的结构返回 `UNSUPPORTED_GEOMETRY_TRANSFORM`。

本期明确禁止嵌套 SVG 和 `foreignObject`，分别返回 `UNSUPPORTED_NESTED_SVG` 与 `UNSUPPORTED_FOREIGN_OBJECT`。

## 4. 文字边界

- 单行文字使用没有子元素的 `<text>`；
- 多行文字使用一个 `<text>`，且每一行都是直属 `<tspan data-layout-line>`，不得混入裸文本或嵌套元素；校验器按每个可见行分别测量；
- `display:none`、`visibility:hidden/collapse` 或自身/祖先不可见 opacity 的文字不参与碰撞；
- 其他复杂文字返回 `UNSUPPORTED_TEXT_STRUCTURE`。

## 5. 合法叠加

允许规则只作用于明确的最小装饰组合：

```html
<g data-layout-role="badge" data-layout-allow="overlap overflow" aria-label="角标">
  <rect .../><text ...>新</text>
</g>
```

- role 只能是 `decor`、`badge` 或 `overlay`；
- 不得标在根 SVG、页面根 group、block、box、control、普通内容卡片或包含布局节点的容器；
- 只豁免该最小装饰节点及其后代，不向普通祖先或相邻模块传播；
- 非法位置返回 `INVALID_ALLOW_SCOPE`。

## 6. 结果与退出码

- `0`：全部状态完成确定性渲染且无阻断问题；
- `1`：HTML、状态、受控结构或几何校验失败；
- `2`：运行环境或校验过程未完成，不得视为 PASS。

报告格式包含 `文件 :: 目标状态 :: 冲突类型 :: 元素 :: 原因`。校验器通过后仍需浏览全部状态截图，复核滚动锚点和阅读层级。
