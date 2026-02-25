import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "yirumeng_text_join_ui",
  async nodeCreated(node) {
    if (node.comfyClass !== "文本联结") return;

    // 查找“数量”控件
    const countWidget = node.widgets.find((w) => w.name === "数量");
    if (!countWidget) return;

    // 同步输入连接点逻辑
    const syncInputs = (count) => {
      count = Math.max(2, count); // 至少2个

      // 获取当前已有的文本输入点数量
      // 我们假设输入点名字都是 "文本N"
      // 这里的 node.inputs 是一个数组
      if (!node.inputs) {
        node.inputs = [];
      }

      // 统计当前以 "文本" 开头的输入
      // 注意：ComfyUI 的 inputs 数组顺序很重要，我们最好不要打乱其他可能的输入（虽然这个节点只有这些）
      // 简单策略：确保前 count 个输入存在且名字正确，多余的移除
      
      // 1. 确保有足够的输入点
      for (let i = 1; i <= count; i++) {
        const inputName = `文本${i}`;
        // 检查第 i-1 个位置的输入是否存在且名字正确
        // 注意：数组索引从0开始，对应 文本1
        const inputIndex = i - 1;
        
        if (inputIndex < node.inputs.length) {
          // 已经有输入点，检查名字
          if (node.inputs[inputIndex].name !== inputName) {
            // 名字不对，改名？或者这是一个不相关的输入？
            // 鉴于我们的节点定义很简单，假设前N个就是文本输入
            node.inputs[inputIndex].name = inputName;
          }
        } else {
          // 缺少输入点，添加
          node.addInput(inputName, "STRING");
        }
      }

      // 2. 移除多余的输入点
      while (node.inputs.length > count) {
        node.removeInput(node.inputs.length - 1);
      }
      
      // 3. 强制重置节点尺寸，消除残留空白
      if (node.onResize) {
        node.onResize(node.size);
      } else {
        node.setSize(node.computeSize());
      }
      
      // 触发画布重绘，确保连接点更新
      app.graph.setDirtyCanvas(true, true);
    };

    // 添加手动更新按钮
    // 放在“分隔符”下方
    const refreshBtn = node.addWidget("button", "更新输入", null, () => {
      syncInputs(parseInt(countWidget.value ?? 2));
    }, { serialize: false });

    // 监听数量变化
    const origCb = countWidget.callback;
    countWidget.callback = (value) => {
      origCb?.call(node, value);
      syncInputs(parseInt(value ?? 2));
    };

    // 初始化/加载时的处理
    const origConfigure = node.onConfigure;
    node.onConfigure = function (data) {
      origConfigure?.call(this, data);
      
      // 加载时，widget的值已经被还原，我们根据这个值来同步输入点
      // 但是，加载的 workflow 本身可能已经包含了正确的 inputs 列表
      // 如果我们这里强行 sync，可能会打断连接？
      // 不，syncInputs 主要是确保 inputs 数量和 widget 一致。
      // 如果 workflow 里保存的 inputs 数量和 widget 值一致，sync 不会有副作用。
      // 如果不一致（比如版本差异），sync 会修正它。
      // 关键是 addInput/removeInput 是否会保留连接？
      // ComfyUI 中 addInput 是安全的。removeInput 会断开连接。
      // 所以我们只在必要时操作。
      
      if (countWidget.value) {
        syncInputs(parseInt(countWidget.value));
      }
    };
    
    // 首次创建时也执行一次（针对拖入节点的情况）
    setTimeout(() => {
        syncInputs(parseInt(countWidget.value ?? 2));
    }, 50);
  },
});
