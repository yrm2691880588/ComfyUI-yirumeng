import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "ComfyUI-yirumeng.DoubaoVideoAPI",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "DoubaoVideoAPI") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                const modeWidget = this.widgets.find((w) => w.name === "生成模式");
                const modelWidget = this.widgets.find((w) => w.name === "模型");
                const durationWidget = this.widgets.find((w) => w.name === "时长");
                const ratioWidget = this.widgets.find((w) => w.name === "比例");
                const resolutionWidget = this.widgets.find((w) => w.name === "分辨率");
                const seedWidget = this.widgets.find((w) => w.name === "seed" || w.name === "随机种子");

                // --- 逻辑 0: 脏数据清洗 (自动修复因移除 Endpoint_ID 导致的参数错位) ---
                const cleanDirtyValues = () => {
                    // 1. 检查比例 Widget
                    if (ratioWidget) {
                        const validRatios = ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"];
                        // 如果当前值不在合法列表中 (比如变成了模型名或分辨率)，则重置
                        if (!validRatios.includes(ratioWidget.value)) {
                            console.warn("Detected invalid Ratio value (migration error), resetting to 16:9");
                            ratioWidget.value = "16:9";
                        }
                    }

                    // 2. 检查分辨率 Widget
                    if (resolutionWidget) {
                        const validResolutions = ["720p", "1080p", "480p"];
                        // 如果当前值不在合法列表中 (比如变成了 16:9)，则重置
                        if (!validResolutions.includes(resolutionWidget.value)) {
                            console.warn("Detected invalid Resolution value (migration error), resetting to 720p");
                            resolutionWidget.value = "720p";
                        }
                    }
                };

                // 保存原始属性用于恢复
                if (ratioWidget) {
                    ratioWidget.origType = ratioWidget.type;
                    ratioWidget.origComputeSize = ratioWidget.computeSize;
                }

                // --- 逻辑 1: 动态更新输入连接点 & 比例选项显隐 ---
                const updateInputs = () => {
                    if (!modeWidget) return;
                    const mode = modeWidget.value;
                    
                    // Helper: Check if input exists
                    const hasInput = (name) => this.inputs && this.inputs.some((i) => i.name === name);
                    
                    // Helper: Remove input by name
                    const removeInput = (name) => {
                        if (!this.inputs) return;
                        const index = this.inputs.findIndex((i) => i.name === name);
                        if (index !== -1) {
                            this.removeInput(index);
                        }
                    };
                    
                    // Helper: Add input if not exists
                    const addInput = (name, type) => {
                        if (!hasInput(name)) {
                            this.addInput(name, type);
                        }
                    };

                    // 处理比例 Widget 显隐
                    if (ratioWidget) {
                        // 强制恢复类型为 combo，防止因历史原因（type='hidden'）导致参数错位
                        // 这是修复 "Value not in list" 和 "seed INT conversion" 错误的关键
                        ratioWidget.type = ratioWidget.origType || "combo";

                        if (mode === "文生视频") {
                            // 恢复显示
                            if (ratioWidget.origComputeSize) {
                                ratioWidget.computeSize = ratioWidget.origComputeSize;
                            } else {
                                delete ratioWidget.computeSize; // 恢复默认行为
                            }

                            // 恢复之前保存的值（如果存在）
                            if (ratioWidget._hiddenValue !== undefined) {
                                ratioWidget.value = ratioWidget._hiddenValue;
                            }
                        } else {
                            // 隐藏前保存当前值
                            if (ratioWidget.computeSize !== undefined && ratioWidget.computeSize.toString().includes("0, -4")) {
                                // 已经是隐藏状态，无需重复保存
                            } else {
                                ratioWidget._hiddenValue = ratioWidget.value;
                            }

                            // 视觉隐藏：将高度设为 0 (依然保留在 DOM 和序列化列表中)
                            // 注意：绝对不能设为 type='hidden'，否则 ComfyUI 序列化时会跳过该 Widget，导致后端参数错位！
                            ratioWidget.computeSize = () => [0, -4];
                        }
                    }

                    if (mode === "文生视频") {
                        removeInput("首帧图像");
                        removeInput("尾帧图像");
                    } else if (mode === "图生视频") {
                        addInput("首帧图像", "IMAGE");
                        removeInput("尾帧图像");
                    } else if (mode === "首尾帧视频") {
                        addInput("首帧图像", "IMAGE");
                        addInput("尾帧图像", "IMAGE");
                    }
                    
                    // 触发布局更新，但保留用户手动调整的大小（只增不减）
                    const minSize = this.computeSize();
                    const currentSize = this.size;
                    this.setSize([
                        Math.max(currentSize[0], minSize[0]),
                        Math.max(currentSize[1], minSize[1])
                    ]);
                };

                // --- 逻辑 2: 动态更新时长选项 ---
                const updateDurationOptions = () => {
                    if (!modelWidget || !durationWidget) return;
                    const model = modelWidget.value;
                    let validOptions = [];

                    if (model === "doubao-seedance-1-5-pro-251215") {
                        // 支持 4-12s
                        validOptions = ["4", "5", "6", "7", "8", "9", "10", "11", "12"];
                    } else if (model === "doubao-seedance-1-0-pro-250528" || model === "doubao-seedance-1-0-pro-fast-251015") {
                        // 支持 5-10s
                        validOptions = ["5", "6", "7", "8", "9", "10"];
                    } else {
                        // 默认回退
                        validOptions = ["5", "6", "7", "8", "9", "10"];
                    }

                    // 更新选项
                    durationWidget.options.values = validOptions;

                    // 如果当前值不在合法列表中，重置为第一个合法值（通常是5）
                    if (!validOptions.includes(durationWidget.value)) {
                        durationWidget.value = validOptions.includes("5") ? "5" : validOptions[0];
                    }
                };

                // --- 逻辑 3: 动态模型列表 ---
                const updateModelOptions = () => {
                    if (!modeWidget || !modelWidget) return;
                    const mode = modeWidget.value;
                    
                    const allModels = ["doubao-seedance-1-5-pro-251215", "doubao-seedance-1-0-pro-250528", "doubao-seedance-1-0-pro-fast-251015"];
                    const restrictedModels = ["doubao-seedance-1-5-pro-251215", "doubao-seedance-1-0-pro-250528"];
                    
                    let validModels = allModels;
                    
                    // Fast 模型不支持首尾帧视频
                    if (mode === "首尾帧视频") {
                        validModels = restrictedModels;
                    }
                    
                    // 更新选项
                    modelWidget.options.values = validModels;
                    
                    // 如果当前选择的模型不在合法列表中，重置为第一个合法值
                    if (!validModels.includes(modelWidget.value)) {
                        console.warn("Current model not supported in this mode, switching to default.");
                        modelWidget.value = validModels[0];
                        // 模型改变了，必须同步更新时长选项
                        updateDurationOptions(); 
                    }
                };

                // Add callback to mode widget
                if (modeWidget) {
                    const originalCallback = modeWidget.callback;
                    modeWidget.callback = function() {
                        if (originalCallback) originalCallback.apply(this, arguments);
                        updateModelOptions(); // 先更新模型列表
                        updateInputs();
                        app.graph.setDirtyCanvas(true, true);
                    };
                }

                // Add callback to model widget
                if (modelWidget) {
                    const originalCallback = modelWidget.callback;
                    modelWidget.callback = function() {
                        if (originalCallback) originalCallback.apply(this, arguments);
                        updateDurationOptions();
                        app.graph.setDirtyCanvas(true, true);
                    };
                }

                // Add callback to seed widget to prevent empty value
                if (seedWidget) {
                    const originalCallback = seedWidget.callback;
                    seedWidget.callback = function() {
                        if (originalCallback) originalCallback.apply(this, arguments);
                        if (this.value === "" || this.value === null || this.value === undefined) {
                            this.value = 0;
                        }
                    };
                }

                // Initial update (delay to ensure node is fully initialized)
                setTimeout(() => {
                    // 初始执行一次脏数据清洗
                    cleanDirtyValues();

                    updateModelOptions(); // 初始更新模型列表
                    updateInputs();
                    updateDurationOptions();

                    // 修复 Seed 可能为空的问题（迁移兼容）
                    if (seedWidget) {
                         if (seedWidget.value === "" || seedWidget.value === undefined || seedWidget.value === null) {
                             seedWidget.value = 0;
                         }
                    }

                    app.graph.setDirtyCanvas(true, true);
                }, 50);

                return r;
            };
        }
    },
});
