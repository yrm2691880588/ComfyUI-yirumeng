import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "yirumeng_image_crop_ui",
  async nodeCreated(node) {
    if (node.comfyClass !== "图像裁剪") return;

    // 1. 定义UI组
    // const GROUPS = ... (逻辑隐含在 updateWidgets 中)

    // 2. 查找并保存所有可能的Widget初始定义
    const widgetConfig = {};
    const cachedValues = {};

    // 辅助：保存配置
    const saveConfig = (w) => {
      // 忽略按钮
      if (w.name === "更新模式") return;

      // 特殊处理：强制修正某些已知字段的类型
      let type = w.type;
      if (w.name === "对齐方式" || w.name === "裁剪模式" || w.name === "比例") {
          type = "combo";
      }

      // 只有当配置不存在时才保存，或者覆盖？
      // 我们应该保存最原始、最正确的配置（通常是首次创建时的）
      if (!widgetConfig[w.name]) {
          widgetConfig[w.name] = {
            type: type,
            options: w.options ? JSON.parse(JSON.stringify(w.options)) : {}, // 深拷贝
            callback: w.callback,
          };
      }
      
      // 更新缓存值
      // 如果当前值是 NaN 或无效，尽量不要污染缓存，但很难判断
      // 这里只负责存，取的时候再校验
      cachedValues[w.name] = w.value;
    };

    // 遍历当前所有widgets保存配置
    node.widgets.forEach(saveConfig);

    // 3. 核心更新函数
    const updateWidgets = () => {
      const modeWidget = node.widgets.find(w => w.name === "裁剪模式");
      if (!modeWidget) return;
      const mode = modeWidget.value;

      // 保存当前所有值到缓存
      node.widgets.forEach(w => {
        if (w.name !== "更新模式") {
          cachedValues[w.name] = w.value;
        }
      });

      // 确定需要显示的Widget列表顺序
      let targetNames = [];
      targetNames.push("裁剪模式");

      if (mode === "按数值裁剪") {
        targetNames.push("宽度", "高度");
        targetNames.push("对齐方式", "X偏移", "Y偏移");
      } else {
        targetNames.push("比例", "自定义比例宽", "自定义比例高", "最短边尺寸");
        targetNames.push("对齐方式", "X偏移", "Y偏移");
      }

      // 构建新的 widget 列表
      const newWidgets = [];

      targetNames.forEach(name => {
        // 获取配置（如果配置丢失，说明代码有问题或定义不匹配，跳过防止报错）
        const conf = widgetConfig[name];
        if (!conf) return;

        // 获取缓存值或默认值
        let val = cachedValues[name];

        // --- 数据清洗与校验 ---
        
        // 1. 处理 undefined/null
        if (val === undefined || val === null) {
            val = conf.options.default;
        }

        // 2. 处理数值类型的 NaN
        // ComfyUI 的数值控件通常是 "number", "INT", "FLOAT" 或 slider
        // 我们简单判断：如果它应该是数字但不是数字
        if (["INT", "FLOAT", "number"].includes(conf.type)) {
             if (typeof val !== 'number' || isNaN(val)) {
                 val = conf.options.default || 0;
             }
        }
        // 针对 "宽度", "高度" 等特定字段的额外保护
        if (["宽度", "高度", "自定义比例宽", "自定义比例高"].includes(name)) {
             if (typeof val !== 'number' || isNaN(val)) {
                 val = conf.options.default || 512;
             }
        }

        // 3. 处理 Combo 类型的非法值
        if (conf.type === "combo" && conf.options.values && Array.isArray(conf.options.values)) {
             if (!conf.options.values.includes(val)) {
                  // 当前值不在选项列表中
                  // 尝试使用默认值
                  val = conf.options.default;
                  // 如果默认值也不在列表中（罕见），使用第一个选项
                  if (!conf.options.values.includes(val) && conf.options.values.length > 0) {
                       val = conf.options.values[0];
                  }
             }
        }

        // --- 重建或更新 Widget ---
        let w = node.widgets.find(x => x.name === name);
        
        if (w) {
            // 存在：更新属性
            w.value = val;
            w.type = conf.type; // 修复类型
            w.options = conf.options; // 修复选项丢失
        } else {
            // 不存在：创建
            // 注意：addWidget 会自动添加到 node.widgets，导致数组变动
            // 但我们最后会覆盖 node.widgets，所以没关系
            // 关键是 addWidget 返回的对象
            w = node.addWidget(conf.type, name, val, conf.callback, conf.options);
            w.value = val; // 再次确保值正确
        }
        
        newWidgets.push(w);
      });

      // 替换 widgets 列表
      // 我们需要保留 inputs/outputs 吗？ node.widgets 通常只包含参数控件
      // 此时 newWidgets 包含了所有应该显示的控件
      
      // 必须确保“更新模式”按钮存在且在最后
      let btn = node.widgets.find(w => w.name === "更新模式");
      if (!btn) {
          // 如果原来的列表里没有（被我们过滤掉了？），新建一个
          // addWidget 会加到 node.widgets 末尾，但我们马上要覆盖它
          // 所以直接创建对象推入 newWidgets？不行，addWidget 做了很多初始化
          // 只能调用 addWidget，然后把它放进 newWidgets
          btn = node.addWidget("button", "更新模式", null, () => {
              updateWidgets();
          }, { serialize: false });
      }
      // 确保按钮在最后
      // 过滤掉按钮（如果它在前面被错误添加）
      const finalWidgets = newWidgets.filter(x => x.name !== "更新模式");
      finalWidgets.push(btn);

      node.widgets = finalWidgets;

      // 调整大小
      node.onResize ? node.onResize(node.size) : node.setSize(node.computeSize());
      app.graph.setDirtyCanvas(true, true);
    };

    // 4. 初始化按钮
    // 检查是否已有按钮
    if (!node.widgets.find(w => w.name === "更新模式")) {
        node.addWidget("button", "更新模式", null, () => {
            updateWidgets();
        }, { serialize: false });
    }

    // 5. 延迟执行初始化
    setTimeout(() => {
        // 补录可能遗漏的配置
        node.widgets.forEach(w => {
            if (w.name !== "更新模式") saveConfig(w);
        });
        updateWidgets();
    }, 100);

    // 6. 监听配置事件（修复复制/加载问题）
    const origConfigure = node.onConfigure;
    node.onConfigure = function (data) {
        origConfigure?.call(this, data);
        setTimeout(() => {
             // 再次补录，因为加载的值可能包含有效信息
             // 但注意不要用坏值覆盖好配置
             node.widgets.forEach(w => {
                 if(w.name !== "更新模式") {
                     // 只有当配置不存在时才保存
                     if(!widgetConfig[w.name]) saveConfig(w);
                     // 缓存值总是更新
                     cachedValues[w.name] = w.value; 
                 }
             });
             updateWidgets();
        }, 50);
    };
  },
});
