// 前端交互：根据“数量”动态增减“搜索/替换”输入框
// 放到 custom_nodes/ComfyUI-yirumeng/js/ 目录下，ComfyUI 会自动加载
import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "yirumeng_text_replace_ui",
  async nodeCreated(node) {
    if (node.comfyClass !== "文本替换") return;

    // 查找“数量”控件
    const countWidget = node.widgets.find((w) => w.name === "数量");
    if (!countWidget) return;

    // 核心同步逻辑
    const syncPairs = (count) => {
      // 1. 确保范围合法
      count = Math.max(1, Math.min(10, count));

      // 2. 获取当前已有的值，避免重建时丢失
      const values = {};
      for (let i = 2; i <= 10; i++) {
        const s = node.widgets.find((w) => w.name === `搜索${i}`);
        const r = node.widgets.find((w) => w.name === `替换${i}`);
        if (s) values[`搜索${i}`] = s.value;
        if (r) values[`替换${i}`] = r.value;
      }

      // 3. 移除所有 2~10 的控件（先清理，再按需重建，确保干净）
      // 注意：不能移除“数量”、“更新输入”和第1组
      for (let i = 2; i <= 10; i++) {
        const s = node.widgets.find((w) => w.name === `搜索${i}`);
        const r = node.widgets.find((w) => w.name === `替换${i}`);
        if (s) node.removeWidget(s);
        if (r) node.removeWidget(r);
      }

      // 4. 重建需要的控件
      for (let i = 2; i <= count; i++) {
        node.addWidget("text", `搜索${i}`, values[`搜索${i}`] ?? "", (v) => {}, {});
        node.addWidget("text", `替换${i}`, values[`替换${i}`] ?? "", (v) => {}, {});
      }

      // 5. 确保“更新输入”按钮存在
      // 注意：按钮不应被序列化（serialize: false），且最好放在最后，避免影响 input 数据的索引对应
      let refreshBtn = node.widgets.find((w) => w.name === "更新输入");
      if (!refreshBtn) {
        refreshBtn = node.addWidget("button", "更新输入", null, () => {
          const c = parseInt(countWidget.value ?? 1);
          syncPairs(c);
        }, { serialize: false });
      } else {
        // 确保现有的按钮也不保存
        refreshBtn.options = refreshBtn.options || {};
        refreshBtn.options.serialize = false;
      }

      // 6. 全量重排顺序
      // 将按钮移到最后，保证前面的 [数量, 搜索1, 替换1...] 与保存的数据顺序一致
      const order = ["数量", "搜索1", "替换1"];
      for (let i = 2; i <= 10; i++) {
        order.push(`搜索${i}`);
        order.push(`替换${i}`);
      }
      // 按钮放到最后
      order.push("更新输入");

      node.widgets.sort((a, b) => {
        const idxA = order.indexOf(a.name);
        const idxB = order.indexOf(b.name);
        // 如果不在列表里（比如其他未知的widget），放到最后
        const valA = idxA === -1 ? 999 : idxA;
        const valB = idxB === -1 ? 999 : idxB;
        return valA - valB;
      });

      // 7. 强制重置节点尺寸，消除残留空白
      if (node.onResize) {
        node.onResize(node.size);
      } else {
        node.setSize(node.computeSize());
      }

      // 触发重绘
      app.graph.setDirtyCanvas(true, true);
    };

    // 初始执行一次
    setTimeout(() => {
        syncPairs(parseInt(countWidget.value ?? 1));
    }, 100);

    // 监听数量变化
    const origCb = countWidget.callback;
    countWidget.callback = (value) => {
      origCb?.call(node, value);
      syncPairs(parseInt(value ?? 1));
    };

    // 修复复制节点时数值丢失的问题：
    // 原因：LiteGraph 在调用 onConfigure 之前尝试应用 widgets_values，但此时动态控件尚未创建，导致赋值失败。
    // 解决：在 onConfigure 中根据保存的数据重建控件，并手动重新赋值。
    const origConfigure = node.onConfigure;
    node.onConfigure = function (data) {
      // 先调用原始钩子（如果有）
      origConfigure?.call(this, data);

      if (data?.widgets_values?.length > 0) {
        // 1. 提取并修正数量（假设第一个值永远是数量）
        let qty = parseInt(data.widgets_values[0]);
        if (isNaN(qty)) qty = 1;

        // 2. 重建控件结构
        // 这一步会创建 S2, R2 等动态控件，并对 widgets 进行正确排序
        syncPairs(qty);

        // 3. 数据清洗与准备
        // 过滤掉非文本、null、以及旧版本残留的按钮值
        // 从索引1开始（跳过数量），只保留有效字符串
        const rawValues = data.widgets_values.slice(1);
        const validStrings = rawValues.filter(v => 
          (typeof v === 'string' && v !== "更新输入") || typeof v === 'number'
        );
        
        // 构造完整的值数组：[数量, S1, R1, S2, R2, ...]
        const cleanValues = [qty, ...validStrings];

        // 4. 手动回填数据
        // 因为 LiteGraph 之前的赋值操作错过了动态控件，我们需要在这里手动补上
        // 注意：node.widgets 此时包含了 [数量, S1, R1, S2, R2, ..., 按钮]
        // 我们只需要按顺序填充前 cleanValues.length 个控件
        for (let i = 0; i < cleanValues.length; i++) {
          if (node.widgets[i]) {
            node.widgets[i].value = cleanValues[i];
          }
        }
      }
    };
  },
});
