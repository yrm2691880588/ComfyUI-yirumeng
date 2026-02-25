# -*- coding: utf-8 -*-
import torch
from PIL import Image, ImageEnhance

# 尽量复用现有插件里的通用图像转换函数；如果不可用则回退到本地实现
try:
    from ComfyUI_LayerStyle.py.imagefunc import tensor2pil, pil2tensor, image_channel_split, image_channel_merge, normalize_gray, gamma_trans, chop_image_v2, RGB2RGBA
except Exception:
    # 兼容回退：自己实现最基础的转换与通道处理，满足本节点使用
    import numpy as np

    def tensor2pil(t: torch.Tensor) -> Image.Image:
        # 输入形状约定：[1, H, W, C]，值域0-1
        if t.ndim == 4 and t.shape[0] == 1:
            arr = t[0].detach().cpu().numpy()
        elif t.ndim == 3:
            arr = t.detach().cpu().numpy()
        else:
            raise ValueError("tensor2pil 期望输入形状为 [1,H,W,C] 或 [H,W,C]")
        arr = np.clip(arr, 0.0, 1.0)
        arr = (arr * 255.0).astype(np.uint8)
        if arr.shape[2] == 4:
            return Image.fromarray(arr, mode="RGBA")
        return Image.fromarray(arr, mode="RGB")

    def pil2tensor(img: Image.Image) -> torch.Tensor:
        arr = np.array(img).astype(np.float32) / 255.0
        if arr.ndim == 2:
            arr = np.stack([arr, arr, arr], axis=-1)
        if arr.shape[2] == 3:
            pass
        elif arr.shape[2] == 4:
            pass
        else:
            raise ValueError("不支持的通道数")
        arr = np.expand_dims(arr, axis=0)
        return torch.from_numpy(arr)

    def image_channel_split(img: Image.Image, mode="RGB"):
        if mode == "RGB":
            if img.mode == "RGBA":
                r, g, b, a = img.split()
                return r, g, b, a
            else:
                r, g, b = img.convert("RGB").split()
                return r, g, b, None
        raise ValueError("仅支持RGB模式")

    def image_channel_merge(chs, mode="RGB"):
        if mode == "RGB":
            return Image.merge("RGB", chs)
        raise ValueError("仅支持RGB模式")

    def normalize_gray(gray: Image.Image) -> Image.Image:
        # 将灰度图规范为L模式
        return gray.convert("L")

    def gamma_trans(gray: Image.Image, gamma: float) -> Image.Image:
        # 简单Gamma校正
        import numpy as np
        arr = np.array(gray).astype(np.float32) / 255.0
        arr = np.power(arr, gamma)
        arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
        return Image.fromarray(arr, mode="L")

    def chop_image_v2(orig: Image.Image, new_img: Image.Image, blend_mode="normal", opacity=100) -> Image.Image:
        # 简化版：仅支持normal混合与不透明度
        if opacity >= 100:
            return new_img
        if opacity <= 0:
            return orig
        alpha = opacity / 100.0
        return Image.blend(orig.convert("RGB"), new_img.convert("RGB"), alpha)

    def RGB2RGBA(rgb_img: Image.Image, alpha_channel: Image.Image) -> Image.Image:
        rgb = rgb_img.convert("RGB")
        return Image.merge("RGBA", (*rgb.split(), alpha_channel))


def get_levels_lut(black, white):
    # black, white: -100 to 100
    # black > 0: lift black (output black increases) -> 画面变灰
    # black < 0: crush black (input black increases) -> 黑色更黑
    # white > 0: brighten white (input white decreases) -> 白色更亮
    # white < 0: dim white (output white decreases) -> 画面变暗
    
    in_min = 0
    in_max = 255
    out_min = 0
    out_max = 255
    
    if black < 0:
        in_min = abs(black)
    else:
        out_min = black
        
    if white > 0:
        in_max = 255 - white
    else:
        out_max = 255 + white
        
    # Avoid division by zero
    if in_max <= in_min:
        in_max = in_min + 1
        
    lut = []
    for i in range(256):
        if i <= in_min:
            val = out_min
        elif i >= in_max:
            val = out_max
        else:
            val = out_min + ((i - in_min) * (out_max - out_min) / (in_max - in_min))
        lut.append(int(max(0, min(255, val))))
    return lut


class YiruColorAdjustPreview:
    """
    节点功能：
    - 接受图像输入，提供亮度、对比度、饱和度与RGB三通道微调
    - 支持预览输出：缩放的预览图像更快，便于实时查看效果
    - 支持“发送”开关：关闭时主输出为原图，开启后主输出为调色后图像
    """

    def __init__(self):
        self.NODE_NAME = '图层颜色：自动调色'

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图像": ("IMAGE",),
                "强度": ("INT", {"default": 100, "min": 0, "max": 100, "step": 1}),
                "亮度": ("INT", {"default": 0, "min": -100, "max": 100, "step": 1}),
                "对比度": ("INT", {"default": 0, "min": -100, "max": 100, "step": 1}),
                "饱和度": ("INT", {"default": 0, "min": -100, "max": 100, "step": 1}),
                "红色": ("INT", {"default": 0, "min": -100, "max": 100, "step": 1}),
                "绿色": ("INT", {"default": 0, "min": -100, "max": 100, "step": 1}),
                "蓝色": ("INT", {"default": 0, "min": -100, "max": 100, "step": 1}),
                "黑色": ("INT", {"default": 0, "min": -100, "max": 100, "step": 1}),
                "白色": ("INT", {"default": 0, "min": -100, "max": 100, "step": 1}),
            },
            "optional": {
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图像",)
    FUNCTION = 'adjust'
    CATEGORY = 'yirumeng/图像'
    DESCRIPTION = """
    图像调色节点，支持亮度、对比度、饱和度及RGB通道调整。
    
    作者: @伊汝梦
    """

    def adjust(self, 图像, 强度, 亮度, 对比度, 饱和度, 红色, 绿色, 蓝色, 黑色, 白色):
        # 说明：
        # - ComfyUI 会按 INPUT_TYPES 的声明顺序将参数传入函数，因此即使参数名为中文也可正常工作
        # - 为了兼容性，内部变量名仍采用英文便于阅读
        image = 图像
        strength = 强度
        brightness = 亮度
        contrast = 对比度
        saturation = 饱和度
        red = 红色
        green = 绿色
        blue = 蓝色
        black_level = 黑色
        white_level = 白色
        # 计算各项增强系数（与LayerStyle保持一致的手感）
        brightness_offset = (brightness / 100 + 1) if brightness < 0 else (brightness / 50 + 1)
        contrast_offset   = (contrast / 100 + 1) if contrast < 0 else (contrast / 50 + 1)
        saturation_offset = (saturation / 100 + 1) if saturation < 0 else (saturation / 50 + 1)

        red_gamma   = self._balance_to_gamma(red)
        green_gamma = self._balance_to_gamma(green)
        blue_gamma  = self._balance_to_gamma(blue)

        batched_images = []
        alpha_masks = []
        for l in image:
            batched_images.append(torch.unsqueeze(l, 0))
            pil_img = tensor2pil(l)
            if pil_img.mode == 'RGBA':
                alpha_masks.append(pil_img.split()[-1])
            else:
                alpha_masks.append(Image.new('L', pil_img.size, 'white'))

        ret_images = []

        max_batch = max(len(batched_images), len(alpha_masks))
        for i in range(max_batch):
            _image = batched_images[i] if i < len(batched_images) else batched_images[-1]
            _mask = alpha_masks[i] if i < len(alpha_masks) else alpha_masks[-1]
            orig_image = tensor2pil(_image)

            r, g, b, _ = image_channel_split(orig_image, mode='RGB')
            r = normalize_gray(r)
            g = normalize_gray(g)
            b = normalize_gray(b)

            if red:
                r = gamma_trans(r, red_gamma).convert('L')
            if green:
                g = gamma_trans(g, green_gamma).convert('L')
            if blue:
                b = gamma_trans(b, blue_gamma).convert('L')

            ret_image = image_channel_merge((r, g, b), 'RGB')

            if black_level != 0 or white_level != 0:
                lut = get_levels_lut(black_level, white_level)
                if ret_image.mode == "RGB":
                    lut = lut * 3
                ret_image = ret_image.point(lut)

            if brightness:
                brightness_image = ImageEnhance.Brightness(ret_image)
                ret_image = brightness_image.enhance(factor=brightness_offset)
            if contrast:
                contrast_image = ImageEnhance.Contrast(ret_image)
                ret_image = contrast_image.enhance(factor=contrast_offset)
            if saturation:
                color_image = ImageEnhance.Color(ret_image)
                ret_image = color_image.enhance(factor=saturation_offset)

            ret_image = chop_image_v2(orig_image, ret_image, blend_mode="normal", opacity=strength)
            if orig_image.mode == 'RGBA':
                ret_image = RGB2RGBA(ret_image, orig_image.split()[-1])

            ret_images.append(pil2tensor(ret_image))

        return (torch.cat(ret_images, dim=0),)

    def _balance_to_gamma(self, balance: int) -> float:
        # 与LayerStyle保持一致的曲线，保证手感统一
        return 0.00005 * balance * balance - 0.01 * balance + 1

    def _resize_keep_ratio(self, img: Image.Image, target_long: int) -> Image.Image:
        w, h = img.size
        if w >= h:
            new_w = target_long
            new_h = max(1, int(h * target_long / w))
        else:
            new_h = target_long
            new_w = max(1, int(w * target_long / h))
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


NODE_CLASS_MAPPINGS = {
    "图层颜色：自动调色": YiruColorAdjustPreview
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "图层颜色：自动调色": "图层颜色：自动调色@伊汝梦"
}
