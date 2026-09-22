/**
 * 批注覆盖层模板（可选启用）— pm-collaboration-deliver
 *
 * 用途：当交付的是 HTML 形态视觉资产、且评审人/PM 需要在资产上直接批注时使用。
 * 人的批注存放在本覆盖层文件，与生成的资产文件分离；资产重生成时永不覆写本文件。
 * 渲染合并逻辑：以 data-anno-id 为键，把 overrides/additions/removed 应用回生成层。
 *
 * 启用条件与完整约定见 references/视觉与原型.md §7.5「资产稳定定位协议」。
 * 只交付 PNG 的默认路径不需要本文件。
 *
 * 铁律：
 * 1. data-anno-id 一旦给出，只增、不改、不复用；删除的 id 留痕，不分给新内容。
 * 2. 本文件是"人的层"：生成层（HTML/脚本产物）可以随便重写，本文件永不被生成流程覆写。
 * 3. 建议命名 data-anno-id 为 "<资产id>.<类型>-<序号>"，如 "sb-change-period.note-3"。
 *
 * 用法：复制本文件到资产目录（建议命名 annotations.js），在资产 HTML 中先于渲染合并脚本引用：
 *   <script src="annotations.js"></script>
 */
window.__ANNO__ = {
  // 覆盖：把某个 data-anno-id 对应的文本替换为人的版本
  overrides: {
    // "sb-change-period.note-3": "评审人修改后的批注文字"
  },
  // 新增：向某个容器（容器本身带 data-anno-container）追加整条内容
  additions: {
    // "sb-change-period.tags": [
    //   { "id": "sb-change-period.tags.add-001", "text": "新增的批注条目" }
    // ]
  },
  // 删除：人的层要求隐藏的 data-anno-id 列表（生成层仍存在，渲染时隐藏）
  removed: [
    // "sb-change-period.note-7"
  ]
};
