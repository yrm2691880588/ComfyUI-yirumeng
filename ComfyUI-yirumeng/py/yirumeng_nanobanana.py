import torch
import numpy as np
from PIL import Image
import io
import requests
import json
import os
import folder_paths
import base64

# 节点类定义
class NanoBanana2Pro:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "提示词": ("STRING", {"multiline": True, "dynamicPrompts": True, "placeholder": "请输入提示词..."}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "画幅比例": (["自动", "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"], {"default": "16:9"}),
                "分辨率": (["1K", "2K", "4K"], {"default": "2K"}),
                "跳过错误": ("BOOLEAN", {"default": False, "label_on": "True", "label_off": "False"}),
                "API密钥": ("STRING", {"multiline": False, "placeholder": "Bearer sk-..."}),
                "API地址": ("STRING", {"default": "https://ai.t8star.cn", "multiline": False, "placeholder": "请输入API Base URL (例如 https://api.openai.com)"}),
            },
            "optional": {
                "图1": ("IMAGE",),
                "图2": ("IMAGE",),
                "图3": ("IMAGE",),
                "图4": ("IMAGE",),
                "图5": ("IMAGE",),
                "图6": ("IMAGE",),
                "图7": ("IMAGE",),
                "图8": ("IMAGE",),
                "图9": ("IMAGE",),
                "图10": ("IMAGE",),
                "图11": ("IMAGE",),
                "图12": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("图像", "图像链接", "响应结果")
    FUNCTION = "generate_image"
    CATEGORY = "yirumeng/API"
    DESCRIPTION = """
    NanoBanana2 Pro 图像生成节点，支持多画幅、多分辨率及API调用。
    
    作者: @伊汝梦
    """

    def tensor2base64(self, tensor):
        # tensor [B, H, W, C] -> PIL -> Base64
        i = 255. * tensor[0].cpu().numpy()
        img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{img_str}"

    def generate_image(self, 提示词, seed, 画幅比例, 分辨率, 跳过错误, API密钥, API地址,
                       图1=None, 图2=None, 图3=None, 图4=None, 图5=None, 
                       图6=None, 图7=None, 图8=None, 图9=None, 图10=None, 图11=None, 图12=None):
        
        # 1. API 配置
        # 优先从 config.json 读取 API Key，如果没有则使用输入框的值
        # 这里为了简单直接使用输入框，或者用户可以在 config.json 中配置默认值（需额外实现读取逻辑）
        # 按照规则：读取优先级：环境变量 > 本地 Config > 节点 Widget 输入
        # 这里简化实现，优先使用 widget 输入，如果为空则尝试环境变量 (实际项目中建议实现 config 读取)
        
        final_api_key = API密钥
        if not final_api_key:
             # 尝试从环境变量读取
             final_api_key = os.environ.get("NANOBANANA_API_KEY", "")
        
        if not final_api_key:
            if 跳过错误:
                print("NanoBanana2 pro: 未提供 API Key，跳过执行。")
                return (torch.zeros((1, 512, 512, 3)), "", "No API Key")
            raise ValueError("请提供 API Key")

        # 处理 API Key 格式，确保包含 'Bearer '
        if not final_api_key.startswith("Bearer "):
             headers = {
                 "Authorization": f"Bearer {final_api_key}",
                 "Content-Type": "application/json"
             }
        else:
             headers = {
                 "Authorization": final_api_key,
                 "Content-Type": "application/json"
             }

        # 2. 收集所有输入的图像
        input_images_list = []
        for img in [图1, 图2, 图3, 图4, 图5, 图6, 图7, 图8, 图9, 图10, 图11, 图12]:
            if img is not None:
                input_images_list.append(img)
        
        # 处理自动画幅比例
        final_aspect_ratio = 画幅比例
        if 画幅比例 == "自动":
            if input_images_list:
                # 获取第一张图的尺寸
                # img tensor: [B, H, W, C]
                _, h, w, _ = input_images_list[0].shape
                ratio = w / h
                
                # 定义支持的比例列表
                supported_ratios = {
                    "1:1": 1.0,
                    "2:3": 2/3,
                    "3:2": 3/2,
                    "3:4": 3/4,
                    "4:3": 4/3,
                    "4:5": 4/5,
                    "5:4": 5/4,
                    "9:16": 9/16,
                    "16:9": 16/9,
                    "21:9": 21/9
                }
                
                # 寻找最接近的比例
                closest_ratio = "16:9" # 默认 fallback
                min_diff = float('inf')
                
                for r_name, r_val in supported_ratios.items():
                    diff = abs(ratio - r_val)
                    if diff < min_diff:
                        min_diff = diff
                        closest_ratio = r_name
                
                final_aspect_ratio = closest_ratio
            else:
                # 如果没有输入图片，默认使用 16:9
                final_aspect_ratio = "16:9"

        # 3. 准备请求数据
        # 自动拼接 URL
        url = API地址.strip()
        if not url.endswith("/v1/images/edits"):
            if url.endswith("/"):
                url = url + "v1/images/edits"
            else:
                url = url + "/v1/images/edits"
        
        print(f"NanoBanana2 pro: Request URL: {url}")
        
        # 根据分辨率自动切换模型
        # nano-banana-hd 是高清版 4K 画质
        # image_size 仅 nano-banana-2 支持
        model_name = "nano-banana"
        if 分辨率 == "4K":
            model_name = "nano-banana-hd"
        elif 分辨率 == "2K":
            model_name = "nano-banana-2"

        # 准备 multipart/form-data 数据
        payload = {
            "model": model_name, # 动态模型名称
            "prompt": 提示词,
            "response_format": "url", # 或者 b64_json，这里使用 url
            "aspect_ratio": final_aspect_ratio,
            "image_size": 分辨率,
            "seed": str(seed) # seed 转为字符串
        }

        files = []
        # 如果有输入图像，转换为文件上传
        if input_images_list:
            for idx, img_tensor in enumerate(input_images_list):
                # tensor [B, H, W, C] -> PIL -> Bytes
                i = 255. * img_tensor[0].cpu().numpy()
                img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
                
                # 保存到内存
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                # 添加到 files 列表
                # 注意：API 文档显示 image 字段支持多图，requests 中可以使用 ('image', (filename, filedata, content_type))
                files.append(('image', (f'image_{idx}.png', img_byte_arr, 'image/png')))
        
        try:
            # 发送请求 (使用 multipart/form-data)
            # headers 中不需要手动设置 Content-Type，requests 会自动设置
            if 'Content-Type' in headers:
                del headers['Content-Type']
                
            if files:
                response = requests.post(url, headers=headers, data=payload, files=files)
            else:
                response = requests.post(url, headers=headers, data=payload)
            
            # 打印调试信息
            # print(f"DEBUG: Status Code: {response.status_code}")
            # print(f"DEBUG: Response Text: {response.text[:500]}") # 打印前500个字符

            response.raise_for_status()
            res_json = response.json()
            
            # 4. 解析响应
            image_url = ""
            output_image = None
            
            # 尝试解析 URL
            # 常见结构: res_json['data'][0]['url']
            if 'data' in res_json and len(res_json['data']) > 0:
                if 'url' in res_json['data'][0]:
                    image_url = res_json['data'][0]['url']
                elif 'b64_json' in res_json['data'][0]:
                    # 如果返回 base64
                    import base64
                    image_data = base64.b64decode(res_json['data'][0]['b64_json'])
                    img = Image.open(io.BytesIO(image_data))
                    output_image = self.pil2tensor(img)
            
            # 如果获取到了 URL，下载图片
            if image_url and output_image is None:
                img_res = requests.get(image_url)
                if img_res.status_code == 200:
                    img = Image.open(io.BytesIO(img_res.content))
                    output_image = self.pil2tensor(img)

            if output_image is None:
                 # 如果没有解析到图片，返回空白图和错误信息
                 print(f"NanoBanana2 pro Error: 无法解析响应图片。响应内容: {json.dumps(res_json, ensure_ascii=False)}")
                 if not 跳过错误:
                      raise ValueError(f"API 返回成功但无法解析图片: {json.dumps(res_json, ensure_ascii=False)}")
                 return (torch.zeros((1, 512, 512, 3)), "", json.dumps(res_json, ensure_ascii=False))

            return (output_image, image_url, json.dumps(res_json, ensure_ascii=False))

        except Exception as e:
            error_msg = f"NanoBanana2 pro Error: {str(e)}"
            if 'response' in locals():
                 error_msg += f"\nStatus Code: {response.status_code}"
                 try:
                     # 限制响应内容长度，防止 HTML 过长刷屏
                     content_preview = response.text[:1000] 
                     error_msg += f"\nResponse Content: {content_preview}"
                 except:
                     pass
            
            print(error_msg)
            
            if 跳过错误:
                return (torch.zeros((1, 512, 512, 3)), "", error_msg)
            raise ValueError(error_msg)

    def pil2tensor(self, image):
        return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

# 注册节点映射
NODE_CLASS_MAPPINGS = {
    "NanoBanana2Pro": NanoBanana2Pro
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NanoBanana2Pro": "RH NanoBanana2 pro @伊汝梦"
}
