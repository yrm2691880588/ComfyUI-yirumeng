# -*- coding: utf-8 -*-
import os
import json
import urllib.request
import urllib.error
import base64
import io
import torch
from PIL import Image
import numpy as np

class DoubaoLLM:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "提示词": ("STRING", {"default": "", "multiline": True, "placeholder": "在此输入您的问题或提示词..."}),
                "模型": (["doubao-seed-2-0-pro-260215", "doubao-seed-2-0-mini-260215", "doubao-seed-1-5-pro-32k-250115", "doubao-lite-4k", "doubao-pro-4k", "doubao-pro-32k"], {"default": "doubao-seed-2-0-pro-260215"}),
                "API_KEY": ("STRING", {"default": "", "multiline": False, "placeholder": "Volcengine Ark API Key"}),
            },
            "optional": {
                "图像": ("IMAGE", ),
                "视频": ("VIDEO", ),
                "文档内容": ("STRING", {"forceInput": True, "multiline": True, "placeholder": "连接[加载文本文件]节点的输出，或直接输入文本内容"}),
                "系统提示词": ("STRING", {"default": "", "multiline": True, "placeholder": "系统提示词 (System Prompt)，用于设定AI的角色..."}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.1, "tooltip": "温度参数，越高越随机"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("回复内容",)
    FUNCTION = "generate_text"
    CATEGORY = "yirumeng/API/豆包大语言模型"
    DESCRIPTION = """
    集成火山引擎豆包大语言模型，支持文本对话、多模态理解（图像/视频/文档）。
    
    作者: @伊汝梦
    """

    def generate_text(self, 提示词, 模型, API_KEY, 图像=None, 视频=None, 文档内容="", 系统提示词="", temperature=0.7):
        # 1. 获取 API Key
        final_api_key = API_KEY.strip()
        if not final_api_key:
            final_api_key = os.environ.get("ARK_API_KEY", "")
        
        if not final_api_key:
            raise ValueError("请提供 API Key (在节点输入或设置 ARK_API_KEY 环境变量)")

        # 2. 构建消息内容 (Multimodal Message Construction)
        # 为了支持多模态，我们切换到 Chat API (v3/chat/completions)
        # 结构: messages: [{"role": "system", ...}, {"role": "user", "content": [...]}]
        
        messages = []
        
        # System Prompt
        if 系统提示词 and 系统提示词.strip():
            messages.append({"role": "system", "content": 系统提示词})
            
        # User Message Content
        user_content = []
        
        # 2.1 添加文本提示词
        if 提示词:
            user_content.append({"type": "text", "text": 提示词})
            
        # 2.2 处理文档内容
        if 文档内容 and 文档内容.strip():
             # 添加到 content
             user_content.append({
                 "type": "text", 
                 "text": f"\n\n[文档内容]:\n{文档内容}\n"
             })
             print(f"Loaded document content length: {len(文档内容)}")

        # 2.3 处理图像 (IMAGE tensor -> Base64)
        if 图像 is not None:
            # 图像是 [B, H, W, C] tensor
            # 我们可以遍历 batch，或者只取第一张? 通常支持多张。
            # 限制最大张数以防超限? 假设用户传多少发多少。
            
            # 确保是 tensor
            if isinstance(图像, torch.Tensor):
                # 遍历 batch
                for i in range(图像.shape[0]):
                    img_tensor = 图像[i]
                    base64_str = self._tensor_to_base64(img_tensor)
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_str}"
                        }
                    })
                print(f"Processed {图像.shape[0]} images.")

        # 2.4 处理视频 (VIDEO object -> Sampled Frames -> Images)
        if 视频 is not None:
            # 尝试从视频对象提取帧
            video_frames = self._extract_frames_from_video(视频, max_frames=8) # 限制8帧以防 Token 爆炸
            if video_frames is not None:
                for frame in video_frames:
                    base64_str = self._tensor_to_base64(frame)
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_str}"
                        }
                    })
                print(f"Processed video: extracted {len(video_frames)} frames.")
            else:
                 print("Warning: Failed to extract frames from video input.")

        # 构建最终消息
        if not user_content:
             raise ValueError("输入为空！请至少提供提示词、图像、视频或文档之一。")
             
        messages.append({"role": "user", "content": user_content})

        # 3. 构建请求
        # 使用 Chat API: https://ark.cn-beijing.volces.com/api/v3/chat/completions
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        
        payload = {
            "model": 模型,
            "messages": messages,
            "temperature": temperature
        }

        headers = {
            "Authorization": f"Bearer {final_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ComfyUI-Yirumeng-DoubaoLLM"
        }

        # 4. 发送请求
        print(f"Requesting Doubao LLM (Chat API): {模型}, Content parts: {len(user_content)}")
        try:
            response_text = self._safe_request("POST", url, headers=headers, json=payload, timeout=300) # 多模态可能慢
            res_json = json.loads(response_text)
            
            # 解析响应 (OpenAI Format)
            content = ""
            if "choices" in res_json and len(res_json["choices"]) > 0:
                choice = res_json["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]
            
            if not content:
                 # 错误处理
                 if "error" in res_json:
                     raise RuntimeError(f"API Error: {res_json['error']}")
                 content = str(res_json)
            
            return (content,)

        except Exception as e:
            raise RuntimeError(f"豆包 API 请求失败: {str(e)}")

    def _tensor_to_base64(self, img_tensor):
        # tensor [H, W, C] -> PIL -> Base64
        # 确保 range 0-1
        img_np = (img_tensor.cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
        img = Image.fromarray(img_np)
        
        # Resize if too large? LLM usually has limits.
        # Max 2048x2048 is usually safe.
        if img.width > 2048 or img.height > 2048:
            img.thumbnail((2048, 2048))
            
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def _extract_frames_from_video(self, video_input, max_frames=8):
        # 尝试从各种视频输入格式中提取 Tensor Frames [N, H, W, C]
        frames = None
        
        # 1. Image Tensor [B, H, W, C] (as batch images)
        if isinstance(video_input, torch.Tensor):
             frames = video_input
             
        # 2. List of Tensors
        elif isinstance(video_input, (list, tuple)):
             if len(video_input) > 0 and isinstance(video_input[0], torch.Tensor):
                 frames = torch.stack(list(video_input))
        
        # 3. Object / Dict (Video wrapper)
        elif hasattr(video_input, "images"): # Wrapper object
             frames = video_input.images
        elif isinstance(video_input, dict) and "images" in video_input:
             frames = video_input["images"]
             
        # 4. String Path (Load from file)
        elif isinstance(video_input, str) and os.path.exists(video_input):
             try:
                 import imageio
                 reader = imageio.get_reader(video_input)
                 frames_list = []
                 
                 # Subsample directly from reader to save memory
                 meta = reader.get_meta_data()
                 duration = meta.get("duration", 0)
                 n_frames = reader.count_frames()
                 
                 # Simple linspace indices
                 if n_frames > max_frames:
                     indices = np.linspace(0, n_frames-1, max_frames, dtype=int)
                     for i, frame in enumerate(reader):
                         if i in indices:
                             frames_list.append(torch.from_numpy(frame))
                 else:
                     for frame in reader:
                         frames_list.append(torch.from_numpy(frame))
                         
                 if frames_list:
                     frames = torch.stack(frames_list).float() / 255.0
             except ImportError:
                 print("imageio not installed, cannot read video path.")
             except Exception as e:
                 print(f"Error reading video path: {e}")

        # 5. VideoFromFile object (ComfyUI internal)
        if frames is None:
             obj_type = type(video_input).__name__
             if "VideoFromFile" in obj_type:
                  path_attr = f"_{obj_type}__file"
                  if hasattr(video_input, path_attr):
                       path_val = getattr(video_input, path_attr)
                       if isinstance(path_val, str):
                           # Recursive call with string path
                           return self._extract_frames_from_video(path_val, max_frames)

        if frames is None:
            return None
            
        # Sampling frames if too many
        if len(frames) > max_frames:
            indices = torch.linspace(0, len(frames)-1, max_frames).long()
            frames = frames[indices]
            
        return frames

    def _safe_request(self, method, url, **kwargs):
        """
        使用 urllib 标准库发送请求，解决 Windows 下的 ConnectionResetError
        """
        headers = kwargs.get("headers", {})
        timeout = kwargs.get("timeout", 60)
        data = kwargs.get("json", None)
        
        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            error_content = e.read().decode('utf-8')
            raise RuntimeError(f"HTTP {e.code}: {error_content}")
        except Exception as e:
            raise RuntimeError(f"Network Error: {str(e)}")

NODE_CLASS_MAPPINGS = {
    "Yirumeng_DoubaoLLM": DoubaoLLM
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Yirumeng_DoubaoLLM": "豆包大模型(文本生成) @伊汝梦"
}
