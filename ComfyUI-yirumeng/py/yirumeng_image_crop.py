# -*- coding: utf-8 -*-
import torch

class YiruImageCrop:
    """
    节点功能：
    - 接受图像输入，根据指定的数值或比例进行裁剪
    - 支持两种优先级模式：
      1. 按数值裁剪：直接指定宽、高
      2. 按比例裁剪：指定长宽比，自动计算最大的裁剪区域
    - 支持多种对齐方式（居中、左上、自定义坐标等）
    - 输出裁剪后的图像以及裁剪的起始坐标(X, Y)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图像": ("IMAGE",),
                "裁剪模式": (["按数值裁剪", "按比例裁剪"], {"default": "按数值裁剪"}),
            },
            "optional": {
                # --- 按数值裁剪的参数 ---
                "宽度": ("INT", {"default": 512, "min": 0, "max": 16384, "step": 1}),
                "高度": ("INT", {"default": 512, "min": 0, "max": 16384, "step": 1}),
                
                # --- 按比例裁剪的参数 ---
                "比例": (["1:1", "16:9", "4:3", "3:2", "2:3", "3:4", "9:16", "21:9", "自定义"], {"default": "1:1"}),
                "自定义比例宽": ("INT", {"default": 1, "min": 0, "max": 100}),
                "自定义比例高": ("INT", {"default": 1, "min": 0, "max": 100}),
                "最短边尺寸": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 1, "tooltip": "设置为0时自动最大化裁剪，大于0时以此尺寸为基准计算裁剪框"}),
                
                # --- 通用位置参数 ---
                "对齐方式": (["居中", "左上", "中上", "右上", "中左", "中右", "左下", "中下", "右下", "自定义坐标"], {"default": "居中"}),
                "X偏移": ("INT", {"default": 0, "min": -16384, "max": 16384}),
                "Y偏移": ("INT", {"default": 0, "min": -16384, "max": 16384}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "INT", "INT")
    RETURN_NAMES = ("图像", "X", "Y", "实际宽度", "实际高度")
    FUNCTION = "crop"
    CATEGORY = "yirumeng/图像"
    DESCRIPTION = """
    图像裁剪节点，支持按数值或比例裁剪，支持多种对齐方式。
    
    作者: @伊汝梦
    """

    # 允许缺少部分参数（由前端动态控制显示/隐藏）
    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
        return True

    def crop(self, 图像, 裁剪模式, **kwargs):
        # 提取参数，设置默认值以防前端未发送
        # 注意：由于前端动态隐藏参数可能导致 ComfyUI 传入 0，需手动修正为合法值
        宽度 = max(1, kwargs.get("宽度", 512))
        高度 = max(1, kwargs.get("高度", 512))
        比例 = kwargs.get("比例", "1:1")
        自定义比例宽 = max(1, kwargs.get("自定义比例宽", 1))
        自定义比例高 = max(1, kwargs.get("自定义比例高", 1))
        最短边尺寸 = kwargs.get("最短边尺寸", 0)
        对齐方式 = kwargs.get("对齐方式", "居中")
        X偏移 = kwargs.get("X偏移", 0)
        Y偏移 = kwargs.get("Y偏移", 0)

        # 图像数据的形状是 [Batch, Height, Width, Channel]
        _, img_h, img_w, _ = 图像.shape
        
        target_w = img_w
        target_h = img_h
        
        # 1. 计算目标尺寸 (Target Width/Height)
        if 裁剪模式 == "按数值裁剪":
            # 直接使用用户输入的宽高，但不能超过原图尺寸
            target_w = min(宽度, img_w)
            target_h = min(高度, img_h)
            
        else: # 按比例裁剪
            # 确定比例值
            ratio = 1.0
            if 比例 == "自定义":
                ratio = float(自定义比例宽) / float(自定义比例高)
            else:
                w_str, h_str = 比例.split(":")
                ratio = float(w_str) / float(h_str)
            
            # 基础计算：最大化裁剪
            if (img_w / img_h) > ratio:
                # 原图更宽，高度占满
                base_h = img_h
                base_w = int(img_h * ratio)
            else:
                # 原图更高，宽度占满
                base_w = img_w
                base_h = int(img_w / ratio)
                
            # 应用“最短边尺寸”约束
            if 最短边尺寸 > 0:
                # 计算当前基础尺寸的最短边
                current_min = min(base_w, base_h)
                if current_min > 0:
                    scale = 最短边尺寸 / current_min
                    target_w = int(base_w * scale)
                    target_h = int(base_h * scale)
                    
                    # 再次检查是否超过原图尺寸（如果用户设置的最短边过大）
                    # 如果超过，则回退到最大化，或者保持比例但被裁切？
                    # 通常为了保证不报错，我们限制在原图范围内
                    if target_w > img_w or target_h > img_h:
                        # 必须缩小以适应原图
                        scale_w = img_w / target_w
                        scale_h = img_h / target_h
                        final_scale = min(scale_w, scale_h)
                        target_w = int(target_w * final_scale)
                        target_h = int(target_h * final_scale)
                else:
                    target_w = base_w
                    target_h = base_h
            else:
                target_w = base_w
                target_h = base_h

        # 2. 计算起始坐标 (X, Y)
        # 先根据对齐方式计算基础坐标
        base_x = 0
        base_y = 0
        
        if 对齐方式 == "居中":
            base_x = (img_w - target_w) // 2
            base_y = (img_h - target_h) // 2
        elif 对齐方式 == "左上":
            base_x = 0
            base_y = 0
        elif 对齐方式 == "中上":
            base_x = (img_w - target_w) // 2
            base_y = 0
        elif 对齐方式 == "右上":
            base_x = img_w - target_w
            base_y = 0
        elif 对齐方式 == "中左":
            base_x = 0
            base_y = (img_h - target_h) // 2
        elif 对齐方式 == "中右":
            base_x = img_w - target_w
            base_y = (img_h - target_h) // 2
        elif 对齐方式 == "左下":
            base_x = 0
            base_y = img_h - target_h
        elif 对齐方式 == "中下":
            base_x = (img_w - target_w) // 2
            base_y = img_h - target_h
        elif 对齐方式 == "右下":
            base_x = img_w - target_w
            base_y = img_h - target_h
        elif 对齐方式 == "自定义坐标":
            base_x = 0
            base_y = 0
            
        # 加上偏移量
        final_x = base_x + X偏移
        final_y = base_y + Y偏移
        
        # 3. 边界修正 (Clamping)
        final_x = max(0, min(final_x, img_w - target_w))
        final_y = max(0, min(final_y, img_h - target_h))
        
        # 4. 执行裁剪
        cropped_image = 图像[:, final_y:final_y+target_h, final_x:final_x+target_w, :]
        
        return (cropped_image, final_x, final_y, target_w, target_h)

# 节点映射
NODE_CLASS_MAPPINGS = {
    "图像裁剪": YiruImageCrop
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "图像裁剪": "图像裁剪@伊汝梦"
}
