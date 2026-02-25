import os
import json
import folder_paths
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import numpy as np
import torch

class SaveImageWithMetadata:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "图像": ("IMAGE", ),
                "文件名前缀": ("STRING", {"default": "ComfyUI"}),
                "图像格式": (["PNG", "JPG", "WEBP"], {"default": "PNG"}),
                "保存元数据": ("BOOLEAN", {"default": True, "label_on": "开启", "label_off": "关闭"}),
            },
            "optional": {
                "自定义保存路径": ("STRING", {"default": "", "placeholder": "留空则使用默认路径"}),
                "起始编号": ("INT", {"default": -1, "min": -1, "max": 99999999, "step": 1, "display": "number"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "yirumeng/Image"
    DESCRIPTION = """
    高级图像保存节点，支持自定义路径、格式 (PNG/JPG/WEBP) 及元数据管理。
    
    作者: @伊汝梦
    """

    def save_images(self, 图像, 文件名前缀="ComfyUI", 图像格式="PNG", 保存元数据=True, 自定义保存路径="", 起始编号=-1, prompt=None, extra_pnginfo=None):
        filename_prefix = 文件名前缀 + self.prefix_append
        
        # 确定保存目录
        output_dir = self.output_dir
        if 自定义保存路径:
            # 检查是否为绝对路径
            if os.path.isabs(自定义保存路径):
                try:
                    os.makedirs(自定义保存路径, exist_ok=True)
                    output_dir = 自定义保存路径
                except Exception:
                    print(f"Warning: Could not create directory {自定义保存路径}, using default output directory.")
            else:
                # 如果不是绝对路径，视为在 output 目录下的子文件夹
                sub_dir = os.path.join(self.output_dir, 自定义保存路径)
                try:
                    os.makedirs(sub_dir, exist_ok=True)
                    output_dir = sub_dir
                except Exception:
                    print(f"Warning: Could not create directory {sub_dir}, using default output directory.")

        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, output_dir, 图像[0].shape[1], 图像[0].shape[0])
        
        # 如果设置了起始编号（非-1），则覆盖默认的计数器
        if 起始编号 != -1:
             counter = 起始编号

        results = list()
        
        for image in 图像:
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            
            # 处理元数据
            if 保存元数据:
                if 图像格式 == "PNG":
                    metadata = PngInfo()
                    if prompt is not None:
                        metadata.add_text("prompt", json.dumps(prompt))
                    if extra_pnginfo is not None:
                        for x in extra_pnginfo:
                            metadata.add_text(x, json.dumps(extra_pnginfo[x]))
                # JPG 和 WEBP 的元数据处理比较复杂，通常 ComfyUI 主要支持 PNG 元数据读取
                # 这里暂只对 PNG 做完整元数据支持，其他格式可能仅保留基础 Exif 如果有的话

            # 确定扩展名和保存参数
            extension = 图像格式.lower()
            if extension == "jpg":
                extension = "jpeg"
            
            if 起始编号 != -1:
                # 如果使用了自定义起始编号，使用简化命名：[前缀_]编号.扩展名
                if filename_prefix:
                     file = f"{filename_prefix}_{counter}.{extension}"
                else:
                     file = f"{counter}.{extension}"
            else:
                # 默认 ComfyUI 命名：前缀_00001_.扩展名
                file = f"{filename}_{counter:05}_.{extension}"

            save_path = os.path.join(full_output_folder, file)
            
            if 图像格式 == "PNG":
                img.save(save_path, pnginfo=metadata, compress_level=4)
            elif 图像格式 == "JPG":
                img.save(save_path, quality=95)
            elif 图像格式 == "WEBP":
                img.save(save_path, quality=95, lossless=False)

            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })
            counter += 1

        return { "ui": { "images": results } }

NODE_CLASS_MAPPINGS = {
    "SaveImageWithMetadata": SaveImageWithMetadata
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageWithMetadata": "保存图像(高级版) @伊汝梦"
}
