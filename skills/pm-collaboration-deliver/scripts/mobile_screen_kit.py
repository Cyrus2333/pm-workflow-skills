#!/usr/bin/env python3
"""Shared mobile-screen component kit for pm-collaboration-deliver visuals.

Both build_screen_html.py (key-page storyboards) and render_overview_board.py
(page interaction overview) render screens from the same block vocabulary, so
a page looks identical wherever it appears.

Design contract — this is what makes a PM-grade prototype instead of gray
boxes with "TBD":

- Every block shows DECIDED product content: real copy from the PRD, concrete
  example data, decided button labels and decided states (disabled, loading,
  error). A prototype never contains placeholder prompts like "待定/占位/
  这里放xxx" — undecided business questions live in the PRD text, not in UI.
- Rules and constraints (防误触、保留规则、资格校验) are rendered as the UI
  element the user will actually see (banner, disabled button, toast), not as
  dashed annotation boxes glued onto the screen.
- The frame is an honest structure prototype: labeled "结构示意", neutral
  styling, no fake brand — but visually clean enough for direct review.
"""

from __future__ import annotations

import html

SCREEN_W = 390
SCREEN_H = 844

FONT_STACK = '-apple-system, "SF Pro Text", "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif'

CSS = f"""
:root {{
  --ink: #17181a; --sub: #6b7280; --faint: #9aa0a6;
  --line: #e8eaee; --hairline: #f0f1f4;
  --card: #ffffff; --screen-bg: #f6f7f9; --board-bg: #ffffff;
  --primary: #1f2329; --primary-text: #ffffff;
  --link: #335cff;
  --success: #14804a; --success-bg: #e9f7ef;
  --warning: #b25e09; --warning-bg: #fdf3e4;
  --danger:  #c03434; --danger-bg: #fbecec;
  --info:    #2b4acb; --info-bg: #eef2ff;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ background: var(--board-bg); font-family: {FONT_STACK}; color: var(--ink);
  -webkit-font-smoothing: antialiased; }}

/* ------- phone frame ------- */
.phone {{ width: {SCREEN_W}px; height: {SCREEN_H}px; background: var(--screen-bg);
  border-radius: 44px; border: 1px solid #d7dae0; position: relative; overflow: hidden;
  box-shadow: 0 2px 10px rgba(20, 24, 40, .06), 0 12px 32px rgba(20, 24, 40, .08); }}
.statusbar {{ height: 44px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 26px; font-size: 14px; font-weight: 600; }}
.statusbar .icons {{ display: flex; gap: 6px; align-items: center; }}
.statusbar .sig {{ width: 17px; height: 11px; display: inline-block; }}
.navbar {{ height: 48px; display: flex; align-items: center; justify-content: center;
  position: relative; background: var(--card); border-bottom: 1px solid var(--hairline); }}
.navbar .title {{ font-size: 16px; font-weight: 600; }}
.navbar .back {{ position: absolute; left: 14px; top: 50%; transform: translateY(-50%);
  width: 12px; height: 12px; border-left: 2px solid var(--ink); border-bottom: 2px solid var(--ink);
  rotate: 45deg; }}
.navbar .more {{ position: absolute; right: 18px; top: 50%; transform: translateY(-50%);
  color: var(--sub); letter-spacing: 2px; font-weight: 700; }}
.content {{ padding: 12px 14px 20px; }}
.home-indicator {{ position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%);
  width: 134px; height: 5px; border-radius: 3px; background: #17181a; opacity: .85; }}

/* ------- blocks ------- */
.b-text {{ font-size: 14px; line-height: 1.75; color: var(--ink); margin: 4px 2px; }}
.b-text.dim {{ color: var(--sub); font-size: 12.5px; }}
.b-section {{ font-size: 13px; font-weight: 600; color: var(--sub); margin: 16px 2px 8px; }}
.b-card {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 14px; margin: 8px 0; box-shadow: 0 1px 2px rgba(20,24,40,.03); }}
.b-card .c-title {{ font-size: 15px; font-weight: 600; line-height: 1.5; }}
.b-card .c-body {{ font-size: 13px; color: var(--sub); line-height: 1.7; margin-top: 6px; }}
.b-card .c-action {{ display: inline-block; margin-top: 10px; background: var(--primary);
  color: var(--primary-text); font-size: 13px; font-weight: 600; padding: 8px 16px;
  border-radius: 18px; }}
.b-kv {{ display: flex; justify-content: space-between; gap: 12px; padding: 9px 2px;
  font-size: 13.5px; border-bottom: 1px solid var(--hairline); }}
.b-kv:last-child {{ border-bottom: none; }}
.b-kv .k {{ color: var(--sub); flex: none; }}
.b-kv .v {{ font-weight: 500; text-align: right; }}
.b-list {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  margin: 8px 0; overflow: hidden; }}
.b-li {{ display: flex; align-items: center; gap: 10px; padding: 13px 14px;
  border-bottom: 1px solid var(--hairline); }}
.b-li:last-child {{ border-bottom: none; }}
.b-li .li-main {{ flex: 1; min-width: 0; }}
.b-li .li-title {{ font-size: 14px; font-weight: 500; }}
.b-li .li-note {{ font-size: 12px; color: var(--sub); margin-top: 2px; }}
.b-li .li-value {{ font-size: 13px; color: var(--sub); text-align: right; flex: none; }}
.b-li .chev {{ width: 8px; height: 8px; border-top: 2px solid var(--faint);
  border-right: 2px solid var(--faint); rotate: 45deg; flex: none; }}
.b-btn {{ height: 46px; border-radius: 23px; display: flex; align-items: center;
  justify-content: center; font-size: 15px; font-weight: 600; margin: 10px 0; }}
.b-btn.primary {{ background: var(--primary); color: var(--primary-text); }}
.b-btn.secondary {{ background: var(--card); color: var(--ink); border: 1px solid var(--line); }}
.b-btn.disabled {{ background: #e5e7eb; color: var(--faint); }}
.b-btn .sub {{ font-weight: 400; font-size: 11px; opacity: .75; margin-left: 6px; }}
.b-btnrow {{ display: flex; gap: 10px; }}
.b-btnrow .b-btn {{ flex: 1; }}
.b-banner {{ display: flex; gap: 8px; border-radius: 10px; padding: 10px 12px;
  font-size: 12.5px; line-height: 1.65; margin: 8px 0; }}
.b-banner .dot {{ flex: none; width: 15px; height: 15px; border-radius: 50%; margin-top: 2px;
  color: #fff; font-size: 10px; display: flex; align-items: center; justify-content: center; }}
.b-banner.info {{ background: var(--info-bg); color: var(--info); }}
.b-banner.info .dot {{ background: var(--info); }}
.b-banner.warning {{ background: var(--warning-bg); color: var(--warning); }}
.b-banner.warning .dot {{ background: var(--warning); }}
.b-banner.error {{ background: var(--danger-bg); color: var(--danger); }}
.b-banner.error .dot {{ background: var(--danger); }}
.b-banner.success {{ background: var(--success-bg); color: var(--success); }}
.b-banner.success .dot {{ background: var(--success); }}
.b-tag {{ display: inline-block; font-size: 11px; padding: 3px 9px; border-radius: 9px;
  background: var(--hairline); color: var(--sub); margin: 2px 6px 2px 0; }}
.b-tag.on {{ background: var(--info-bg); color: var(--info); font-weight: 600; }}
.b-divider {{ height: 1px; background: var(--line); margin: 14px 0; }}
.b-empty {{ text-align: center; padding: 44px 24px; color: var(--faint); font-size: 13px;
  line-height: 1.8; white-space: pre-line; }}
.b-result {{ text-align: center; padding: 40px 24px 28px; }}
.b-result .r-icon {{ width: 56px; height: 56px; border-radius: 50%; margin: 0 auto 14px;
  display: flex; align-items: center; justify-content: center; font-size: 26px; color: #fff; }}
.b-result.success .r-icon {{ background: var(--success); }}
.b-result.error .r-icon {{ background: var(--danger); }}
.b-result .r-title {{ font-size: 17px; font-weight: 600; }}
.b-result .r-body {{ font-size: 12.5px; color: var(--sub); margin-top: 6px; line-height: 1.7; }}
.b-steps {{ display: flex; gap: 6px; margin: 8px 2px; }}
.b-steps .st {{ flex: 1; height: 4px; border-radius: 2px; background: var(--line); }}
.b-steps .st.on {{ background: var(--primary); }}
.b-toast {{ position: absolute; left: 50%; bottom: 120px; transform: translateX(-50%);
  background: rgba(23,24,26,.88); color: #fff; font-size: 13px; padding: 10px 18px;
  border-radius: 10px; white-space: nowrap; }}
.b-modal-mask {{ position: absolute; inset: 0; background: rgba(15,17,20,.45);
  display: flex; align-items: center; justify-content: center; }}
.b-modal {{ width: 300px; background: var(--card); border-radius: 16px; padding: 20px 18px 14px; }}
.b-modal .m-title {{ font-size: 16px; font-weight: 600; text-align: center; }}
.b-modal .m-body {{ font-size: 13px; color: var(--sub); line-height: 1.7;
  margin: 10px 0 16px; text-align: center; }}
.b-modal .m-actions {{ display: flex; flex-direction: column; gap: 8px; }}
.b-input {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px;
  padding: 12px; font-size: 13.5px; color: var(--ink); margin: 8px 0; }}
.b-input .ph {{ color: var(--faint); }}
.b-media {{ height: 120px; border-radius: 12px; background:
  repeating-linear-gradient(45deg, #eef0f3, #eef0f3 8px, #e6e9ee 8px, #e6e9ee 16px);
  display: flex; align-items: center; justify-content: center; color: var(--faint);
  font-size: 12px; margin: 8px 0; }}
.screen-note {{ position: absolute; top: 100px; right: 14px; font-size: 11px;
  color: var(--faint); }}
"""


def esc(value) -> str:
    return html.escape(str(value), quote=True)


_SIGNAL_SVG = (
    '<svg class="sig" viewBox="0 0 17 11"><g fill="#17181a">'
    '<rect x="0" y="7" width="3" height="4" rx="1"/>'
    '<rect x="4.5" y="5" width="3" height="6" rx="1"/>'
    '<rect x="9" y="2.5" width="3" height="8.5" rx="1"/>'
    '<rect x="13.5" y="0" width="3" height="11" rx="1"/></g></svg>'
    '<svg class="sig" viewBox="0 0 16 11" style="width:15px"><g fill="none" stroke="#17181a" '
    'stroke-width="1.6" stroke-linecap="round">'
    '<path d="M2 4.5a8.5 8.5 0 0 1 12 0"/><path d="M4.6 7a5 5 0 0 1 6.8 0"/>'
    '<circle cx="8" cy="9.4" r="1.1" fill="#17181a" stroke="none"/></g></svg>'
    '<svg viewBox="0 0 25 12" style="width:25px;height:12px"><rect x="0.5" y="0.5" width="21" '
    'height="11" rx="3.5" fill="none" stroke="#17181a" opacity=".4"/>'
    '<rect x="2" y="2" width="15" height="8" rx="2" fill="#17181a"/>'
    '<path d="M23.5 4v4a2.2 2.2 0 0 0 0-4z" fill="#17181a" opacity=".4"/></svg>'
)


def render_block(block: dict) -> str:
    kind = block.get("type")
    if kind == "text":
        cls = "b-text dim" if block.get("dim") else "b-text"
        return f'<div class="{cls}">{esc(block.get("text", ""))}</div>'
    if kind == "section":
        return f'<div class="b-section">{esc(block.get("title", ""))}</div>'
    if kind == "card":
        parts = ['<div class="b-card">']
        if block.get("title"):
            parts.append(f'<div class="c-title">{esc(block["title"])}</div>')
        if block.get("body"):
            parts.append(f'<div class="c-body">{esc(block["body"])}</div>')
        for field in block.get("fields", []):
            parts.append(
                f'<div class="b-kv"><span class="k">{esc(field.get("label", ""))}</span>'
                f'<span class="v">{esc(field.get("value", ""))}</span></div>')
        if block.get("action"):
            parts.append(f'<div class="c-action">{esc(block["action"])}</div>')
        parts.append("</div>")
        return "".join(parts)
    if kind == "kv_group":
        rows = "".join(
            f'<div class="b-kv"><span class="k">{esc(f.get("label", ""))}</span>'
            f'<span class="v">{esc(f.get("value", ""))}</span></div>'
            for f in block.get("fields", []))
        return f'<div class="b-card">{rows}</div>'
    if kind == "list":
        items = []
        for item in block.get("items", []):
            note = f'<div class="li-note">{esc(item["note"])}</div>' if item.get("note") else ""
            value = f'<div class="li-value">{esc(item["value"])}</div>' if item.get("value") else ""
            chev = '<div class="chev"></div>' if item.get("chevron") else ""
            items.append(
                f'<div class="b-li"><div class="li-main">'
                f'<div class="li-title">{esc(item.get("title", ""))}</div>{note}</div>'
                f'{value}{chev}</div>')
        return f'<div class="b-list">{"".join(items)}</div>'
    if kind == "button":
        style = block.get("style", "primary")
        sub = f'<span class="sub">{esc(block["sub"])}</span>' if block.get("sub") else ""
        return f'<div class="b-btn {esc(style)}">{esc(block.get("text", "按钮"))}{sub}</div>'
    if kind == "button_row":
        inner = "".join(render_block(b) for b in block.get("buttons", []))
        return f'<div class="b-btnrow">{inner}</div>'
    if kind == "banner":
        tone = block.get("tone", "info")
        icon = {"info": "i", "warning": "!", "error": "!", "success": "✓"}.get(tone, "i")
        return (f'<div class="b-banner {esc(tone)}"><span class="dot">{icon}</span>'
                f'<span>{esc(block.get("text", ""))}</span></div>')
    if kind == "tags":
        tags = "".join(
            f'<span class="b-tag{" on" if t in set(block.get("selected", [])) else ""}">'
            f'{esc(t)}</span>' for t in block.get("items", []))
        return f'<div style="margin:6px 2px">{tags}</div>'
    if kind == "divider":
        return '<div class="b-divider"></div>'
    if kind == "steps":
        total = int(block.get("total", 3))
        current = int(block.get("current", 1))
        bars = "".join(f'<div class="st{" on" if i < current else ""}"></div>'
                       for i in range(total))
        return f'<div class="b-steps">{bars}</div>'
    if kind == "input":
        if block.get("value"):
            inner = esc(block["value"])
        else:
            inner = f'<span class="ph">{esc(block.get("placeholder", ""))}</span>'
        label = f'<div class="b-section" style="margin-top:4px">{esc(block["label"])}</div>' \
            if block.get("label") else ""
        return f'{label}<div class="b-input">{inner}</div>'
    if kind == "media":
        return f'<div class="b-media">{esc(block.get("label", "图片 / 内容区域"))}</div>'
    if kind == "empty":
        return f'<div class="b-empty">{esc(block.get("text", "暂无内容"))}</div>'
    if kind == "result":
        tone = block.get("tone", "success")
        icon = "✓" if tone == "success" else "!"
        body = f'<div class="r-body">{esc(block["body"])}</div>' if block.get("body") else ""
        return (f'<div class="b-result {esc(tone)}"><div class="r-icon">{icon}</div>'
                f'<div class="r-title">{esc(block.get("title", ""))}</div>{body}</div>')
    raise ValueError(f"unsupported screen block type: {kind!r}")


def render_screen(screen: dict, *, mini: bool = False) -> str:
    """Render one phone frame. mini=True omits frame chrome for overview cards."""
    nav = screen.get("nav")
    modal = screen.get("modal")
    toast = screen.get("toast")
    blocks = "".join(render_block(b) for b in screen.get("blocks", []))
    nav_html = ""
    if nav:
        back = '<div class="back"></div>' if screen.get("back", True) else ""
        nav_html = (f'<div class="navbar">{back}<div class="title">{esc(nav)}</div>'
                    f'<div class="more">···</div></div>')
    statusbar = "" if mini else (
        f'<div class="statusbar"><span>9:41</span>'
        f'<span class="icons">{_SIGNAL_SVG}</span></div>')
    overlay = ""
    if modal:
        actions = "".join(
            render_block({"type": "button", **a}) for a in modal.get("actions", []))
        overlay = (f'<div class="b-modal-mask"><div class="b-modal">'
                   f'<div class="m-title">{esc(modal.get("title", ""))}</div>'
                   f'<div class="m-body">{esc(modal.get("body", ""))}</div>'
                   f'<div class="m-actions">{actions}</div></div></div>')
    if toast:
        overlay += f'<div class="b-toast">{esc(toast)}</div>'
    home = "" if mini else '<div class="home-indicator"></div>'
    return (f'<div class="phone">{statusbar}{nav_html}'
            f'<div class="content">{blocks}</div>{overlay}{home}</div>')


def page_html(title: str, body: str, width: int, height: int) -> str:
    return (
        "<!doctype html>\n<html lang=\"zh\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{esc(title)}</title>\n<style>{CSS}\n"
        f"html,body{{width:{width}px;height:{height}px;overflow:hidden;}}\n"
        "</style>\n</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )
