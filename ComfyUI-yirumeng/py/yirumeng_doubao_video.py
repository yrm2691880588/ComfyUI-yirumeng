# -*- coding: utf-8 -*-
import os
import time
import json
import base64
import requests
import torch
import numpy as np
from PIL import Image
import io
import folder_paths
import random
import socket
# import urllib3.util.connection as urllib3_cn

# --- 核心修复：移除强制 IPv4 ---
# 经过测试，IPv4 强制并未解决 10054 问题，反而可能在某些双栈环境下引起困扰
# 10054 的核心原因是 Payload 过大导致的 MTU/防火墙拦截
# def allowed_gai_family():
#     return socket.AF_INET

# urllib3_cn.allowed_gai_family = allowed_gai_family
# -----------------------------

class DoubaoVideoWrapper:
    def __init__(self, video_path, video_tensor, width, height, duration, fps=25):
        self.path = video_path
        self.images = video_tensor
        self.width = width
        self.height = height
        self.duration = duration
        self.fps = fps
        
    def get_dimensions(self):
        return (self.width, self.height)
        
    def save_to(self, path, format=None, codec=None, metadata=None):
        import shutil
        # 简单复制文件，忽略 format/codec 转换
        shutil.copy2(self.path, path)
        
    def get_components(self):
        from collections import namedtuple
        # 创建一个简单的对象来模拟 components
        Components = namedtuple("Components", ["images", "audio", "frame_rate"])
        return Components(self.images, None, self.fps)

class DoubaoVideoAPI:
    """
    豆包视频生成节点 (Doubao Video Generation Node)
    支持文生视频、图生视频（首尾帧控制）
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "生成模式": (["文生视频", "图生视频", "首尾帧视频"], {"default": "文生视频"}),
                "提示词": ("STRING", {"default": "", "multiline": True, "placeholder": "在此输入视频描述提示词..."}),
                "模型": (["doubao-seedance-1-5-pro-251215", "doubao-seedance-1-0-pro-250528", "doubao-seedance-1-0-pro-fast-251015"], {"default": "doubao-seedance-1-5-pro-251215"}),
                "比例": (["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"], {"default": "16:9"}),
                "分辨率": (["720p", "1080p", "480p"], {"default": "720p"}),
                "时长": (["5", "4", "6", "7", "8", "9", "10", "11", "12"], {"default": "5"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "API_KEY": ("STRING", {"default": "", "multiline": False, "placeholder": "Volcengine Ark API Key"}),
            },
            "optional": {
                "首帧图像": ("IMAGE",),
                "尾帧图像": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "VIDEO")
    RETURN_NAMES = ("视频画面(IMAGE)", "视频链接(STRING)", "本地路径(STRING)", "视频对象(VIDEO)")
    FUNCTION = "generate"
    CATEGORY = "yirumeng/API/豆包视频API"
    DESCRIPTION = """
    豆包视频生成节点，支持文生视频、图生视频（首尾帧控制）。
    
    作者: @伊汝梦
    """
    
    def generate(self, 生成模式, 提示词, 模型, 比例, 分辨率, 时长, seed, API_KEY, 首帧图像=None, 尾帧图像=None):
        # 参数映射
        prompt = 提示词
        
        # 直接使用模型选择的值作为 Endpoint ID (或模型名)
        model_endpoint_id = 模型.strip()
        
        ratio = 比例
        resolution = 分辨率
        duration = int(时长)
        # seed 已直接传入，但火山引擎 API 要求 seed 必须是 32 位整数 (<= 4294967296)
        # ComfyUI 的 seed 是 64 位的，所以这里需要取余处理，防止报错
        seed = seed % 4294967296
        
        # 清理 API Key (防止包含换行符或空格)
        api_key = API_KEY.strip() if API_KEY else ""

        # 校验模型功能限制
        if "fast" in model_endpoint_id and 生成模式 == "首尾帧视频":
            raise ValueError(f"模型 {model_endpoint_id} (Fast版本) 不支持'首尾帧视频'模式，仅支持'文生视频'和'图生视频(首帧)'。")

        # 校验模型时长限制 (宽松模式，如果用户修改了模型ID为自定义ep-xxx，则放宽限制)
        model_name_ref = model_endpoint_id
        if "doubao-seedance-1-5-pro" in model_name_ref or model_name_ref == "doubao-seedance-1-5-pro-251215":
             if duration < 4 or duration > 12:
                 raise ValueError(f"模型 {model_name_ref} 支持的时长范围为 4-12 秒，当前选择: {duration}")
        elif "doubao-seedance-1-0-pro" in model_name_ref or model_name_ref == "doubao-seedance-1-0-pro-250528":
             if duration < 5 or duration > 10:
                 raise ValueError(f"模型 {model_name_ref} 支持的时长范围为 5-10 秒，当前选择: {duration}")
        else:
             # 对于未知的 Endpoint ID，不进行严格校验，或者默认允许宽范围
             pass
        
        # 模式处理逻辑
        first_frame = None
        last_frame = None
        
        if 生成模式 == "图生视频":
            if 首帧图像 is None:
                raise ValueError("【图生视频】模式下，请务必连接 [首帧图像] 输入！")
            first_frame = 首帧图像
            print("Mode: Image2Video (First Frame used)")
            
        elif 生成模式 == "首尾帧视频":
            if 首帧图像 is None:
                raise ValueError("【首尾帧视频】模式下，请务必连接 [首帧图像] 输入！")
            if 尾帧图像 is None:
                raise ValueError("【首尾帧视频】模式下，请务必连接 [尾帧图像] 输入！")
            first_frame = 首帧图像
            last_frame = 尾帧图像
            print("Mode: Frame2Video (First & Last Frames used)")
            
        else: # 文生视频
            print("Mode: Text2Video (Images ignored)")

        # 1. 获取 API Key
        final_api_key = api_key
        if not final_api_key:
            final_api_key = os.environ.get("ARK_API_KEY", "")
        
        # 再次清理可能从环境变量获取的 Key
        if final_api_key:
            final_api_key = final_api_key.strip()
            
        if not final_api_key:
            raise ValueError("请提供 API Key (在节点输入或设置 ARK_API_KEY 环境变量)")
            
        # 简单校验 Key 格式 (Volcengine API Key 通常较长，且不包含空格)
        if len(final_api_key) < 20:
             raise ValueError(f"API Key 看起来不正确 (长度仅 {len(final_api_key)} 位)。请检查是否复制了正确的 API Key (非 Access Key)。")
             
        if " " in final_api_key:
             raise ValueError("API Key 不能包含空格，请检查输入。")

        # 2. 准备请求数据
        # 3. 处理图像 (转 Base64 并构建 Content List)
        content_list = []
        
        # 添加提示词
        content_list.append({"type": "text", "text": prompt})
        
        if first_frame is not None:
            # _tensor_to_base64 已包含 "data:image/jpeg;base64," 前缀
            img_url = self._tensor_to_base64(first_frame)
            content_list.append({
                "type": "image_url",
                "image_url": {"url": img_url},
                "role": "first_frame"
            })
            
        if last_frame is not None:
            # _tensor_to_base64 已包含 "data:image/jpeg;base64," 前缀
            img_url = self._tensor_to_base64(last_frame)
            content_list.append({
                "type": "image_url",
                "image_url": {"url": img_url},
                "role": "last_frame"
            })

        # 4. 构建额外参数 (Top-level Parameters)
        extra_args = {
            "resolution": resolution,
            "duration": duration,
        }
        
        # 仅在文生视频模式下添加 ratio
        if 生成模式 == "文生视频":
            extra_args["ratio"] = ratio
        else:
            print(f"Mode: {生成模式}, ignoring ratio parameter.")
        
        if seed != -1:
            extra_args["seed"] = seed

        # 5. 发起生成请求 (尝试 SDK)
        task_id = None
        use_sdk = False
        
        try:
            import volcenginesdkarkruntime
            print("Using Volcengine SDK for request...")
            client = volcenginesdkarkruntime.Ark(api_key=final_api_key)
            
            # 使用 SDK 发起请求
            print(f"SDK Request: model={model_endpoint_id}, content_len={len(content_list)}, args={extra_args}")
            
            resp = client.content_generation.tasks.create(
                model=model_endpoint_id,
                content=content_list,
                **extra_args
            )
            
            # SDK 返回的是 Task 对象或响应对象
            # 假设 resp 是 Task 对象，包含 id
            if hasattr(resp, "id"):
                task_id = resp.id
            elif isinstance(resp, dict) and "id" in resp:
                task_id = resp["id"]
            else:
                 # 尝试从 raw response 获取
                 print(f"SDK Response type: {type(resp)}")
                 if hasattr(resp, "data") and hasattr(resp.data, "id"):
                     task_id = resp.data.id
                 else:
                     # 可能是 Pydantic model
                     task_id = getattr(resp, "id", None)
            
            if not task_id:
                raise RuntimeError(f"SDK 未返回 Task ID. Response: {resp}")
                
            use_sdk = True
            
        except ImportError:
            print("Volcengine SDK not found, falling back to Requests...")
        except Exception as e:
            print(f"SDK Request Failed: {e}")
            print("Falling back to Requests...")

        # 如果 SDK 失败或未安装，使用 requests (手动 URL)
        if not use_sdk:
            # 手动构建请求
            # 根据火山引擎最新文档，URL 应该是 plural (contents/generations)
            url = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
            
            # 手动构建 JSON Payload
            full_payload = {
                "model": model_endpoint_id,
                "content": content_list,
                **extra_args
            }
            
            headers = {
                "Authorization": f"Bearer {final_api_key}",
                "Content-Type": "application/json"
            }
            
            print(f"Requesting Doubao Video API (Manual): {url}")
            try:
                response = self._safe_request("POST", url, headers=headers, json=full_payload, timeout=60)
                if response.status_code == 404:
                     raise RuntimeError(f"404 Not Found: 请检查 Endpoint ID / 模型名称 是否正确。当前使用 ID: '{model_endpoint_id}'。")
                
                response.raise_for_status()
                res_json = response.json()
                
                if "id" in res_json:
                    task_id = res_json["id"]
                elif "data" in res_json and "id" in res_json["data"]:
                    task_id = res_json["data"]["id"]
                else:
                    raise RuntimeError(f"无法获取 Task ID, 响应: {res_json}")
                    
            except Exception as e:
                raise RuntimeError(f"API 请求失败: {str(e)}")

        print(f"Task submitted, ID: {task_id}")
        
        # 6. 轮询状态
        # 如果使用了 SDK，可以使用 SDK 轮询 (暂未实现 SDK 轮询，统一使用手动轮询以保持兼容性)
        # 或者使用 SDK 的 client.content_generation.tasks.get(task_id)
        
        video_url = None
        if use_sdk:
             # 使用 SDK 轮询
             print("Polling with SDK...")
             start_time = time.time()
             while time.time() - start_time < 600:
                 try:
                     task_resp = client.content_generation.tasks.get(task_id=task_id)
                     # 假设 task_resp.status 是状态
                     status = getattr(task_resp, "status", "Unknown")
                     
                     if status.lower() == "succeeded":
                         # 获取 content
                         content = getattr(task_resp, "content", None)
                         if content and hasattr(content, "video_url"):
                             video_url = content.video_url
                             break
                         # 某些版本可能在 data 中
                         elif hasattr(task_resp, "data") and hasattr(task_resp.data, "video_url"):
                             video_url = task_resp.data.video_url
                             break
                     elif status.lower() == "failed":
                         raise RuntimeError(f"视频生成失败: {task_resp}")
                         
                     waited_time = int(time.time() - start_time)
                     if status.lower() == "queued":
                        print(f"Task status: {status}. Server queueing... (waited {waited_time}s)")
                     else:
                        print(f"Task status: {status}. Processing... (waited {waited_time}s)")
                        
                     time.sleep(5) # 增加轮询间隔，减少日志刷屏
                 except Exception as e:
                     print(f"SDK Polling error: {e}")
                     time.sleep(5)
             if not video_url:
                 raise TimeoutError("SDK 轮询超时或未找到视频 URL (请检查网络或稍后重试)")
        else:
             # 手动轮询
             video_url = self._poll_task(task_id, headers if 'headers' in locals() else {"Authorization": f"Bearer {final_api_key}"})

        # 7. 下载视频并转换为 Tensor
        video_tensor, video_path = self._download_and_convert_video(video_url, task_id)
        
        # 构建视频对象 wrapper (用于兼容需要 VIDEO 类型的节点)
        # video_tensor shape: [B, H, W, C]
        height = video_tensor.shape[1]
        width = video_tensor.shape[2]
        video_wrapper = DoubaoVideoWrapper(video_path, video_tensor, width, height, duration)
        
        return (video_tensor, video_url, video_path, video_wrapper)

    def _safe_request(self, method, url, **kwargs):
        """
        使用 urllib 标准库发送请求 (Reference: doubao_video_generate.py)
        完全替代 requests 库以彻底解决 Windows 下的 10054 ConnectionResetError 问题
        """
        import urllib.request
        import urllib.error
        import json

        # 提取参数
        headers = kwargs.get("headers", {})
        timeout = kwargs.get("timeout", 60)
        data = kwargs.get("json", None)
        
        # 确保 User-Agent
        if "User-Agent" not in headers:
            headers["User-Agent"] = "ComfyUI-DoubaoVideoAPI"
            
        # 处理 Body
        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
            # 自动添加 Content-Type 如果没有
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
        
        # 构建 Request 对象
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
        
        # 发送请求
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                resp_content = response.read()
                
                # 模拟 requests 的 Response 对象接口
                class MockResponse:
                    def __init__(self, content_bytes, status_code):
                        self.content = content_bytes
                        self.status_code = status_code
                        self._text = None
                        
                    @property
                    def text(self):
                        if self._text is None:
                            self._text = self.content.decode('utf-8', errors='replace')
                        return self._text
                        
                    def json(self):
                        return json.loads(self.text)
                        
                    def raise_for_status(self):
                        if 400 <= self.status_code < 600:
                            raise RuntimeError(f"HTTP Error {self.status_code}: {self.text}")
                            
                return MockResponse(resp_content, response.status)
                
        except urllib.error.HTTPError as e:
            # 读取错误响应内容
            error_content = e.read()
            # 同样返回一个 Response 对象，但带有错误码
            class ErrorResponse:
                def __init__(self, content_bytes, status_code):
                    self.content = content_bytes
                    self.status_code = status_code
                    self._text = None
                    
                @property
                def text(self):
                    if self._text is None:
                        self._text = self.content.decode('utf-8', errors='replace')
                    return self._text
                    
                def json(self):
                    try:
                        return json.loads(self.text)
                    except:
                        return {}
                        
                def raise_for_status(self):
                    # 尝试解析详细错误信息
                    try:
                        resp_json = self.json()
                        if "error" in resp_json:
                            err = resp_json["error"]
                            code = err.get("code", "")
                            message = err.get("message", "")
                            
                            if code == "InputImageSensitiveContentDetected":
                                raise RuntimeError(f"生成失败：输入图像包含敏感内容，被 API 拒绝。请更换图像或调整提示词。(Code: {code})")
                            
                            if code == "AuthenticationError" or self.status_code == 401:
                                raise RuntimeError(f"鉴权失败 (401): API Key 无效或格式错误。请检查您填写的 Key 是否正确，或是否已过期。(Code: {code})")

                            raise RuntimeError(f"API 错误 ({self.status_code}): {message} (Code: {code})")
                    except Exception as e:
                        if isinstance(e, RuntimeError): raise e
                        pass
                        
                    # Fallback generic handling
                    if self.status_code == 401:
                        raise RuntimeError(f"鉴权失败 (401): API Key 无效。请检查 Key 是否正确。(Raw: {self.text})")
                        
                    raise RuntimeError(f"HTTP Error {self.status_code}: {self.text}")
            
            return ErrorResponse(error_content, e.code)
            
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network Error (URLError): {e.reason}")
        except Exception as e:
            raise RuntimeError(f"Request Failed: {str(e)}")

    def _poll_task(self, task_id, headers, timeout=600):
        start_time = time.time()
        
        # 轮询 URL 列表 (优先尝试新的 content/generation 路径)
        urls_to_try = [
            f"https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}",
            f"https://ark.cn-beijing.volces.com/api/v3/content/generation/tasks/{task_id}",
            f"https://ark.cn-beijing.volces.com/api/v3/tasks/{task_id}",
            f"https://ark.cn-beijing.volces.com/api/v3/video/tasks/{task_id}",
            f"https://ark.cn-beijing.volces.com/api/v3/videos/tasks/{task_id}",
            f"https://ark.cn-beijing.volces.com/api/v3/cv/tasks/{task_id}"
        ]
        
        current_url_index = 0
        
        while time.time() - start_time < timeout:
            try:
                url = urls_to_try[current_url_index]
                # 使用 _safe_request
                response = self._safe_request("GET", url, headers=headers, timeout=10)
                
                # 如果遇到 404，尝试下一个 URL
                if response.status_code == 404:
                    if current_url_index < len(urls_to_try) - 1:
                        print(f"Polling URL {url} returned 404, switching to next...")
                        current_url_index += 1
                        continue
                
                response.raise_for_status()
                data = response.json()
                
                status = "Unknown"
                if "data" in data:
                    status = data["data"].get("status", status)
                    if status == "Succeeded" or status == "SUCCESS":
                         if "video_url" in data["data"]:
                             return data["data"]["video_url"]
                         elif "resp_data" in data["data"] and "video_url" in data["data"]["resp_data"]:
                             return data["data"]["resp_data"]["video_url"]
                         return self._find_url_in_dict(data["data"])
                    elif status == "Failed" or status == "FAILED":
                        raise RuntimeError(f"视频生成失败: {data}")
                
                print(f"Task status: {status}. Waiting... (waited {int(time.time() - start_time)}s)")
                time.sleep(5)
            except Exception as e:
                print(f"Polling error: {e}")
                time.sleep(5)
                
        raise TimeoutError("视频生成超时 (请检查网络或稍后重试)")

    def _find_url_in_dict(self, data):
        if isinstance(data, dict):
            for k, v in data.items():
                if k == "video_url" or k == "url":
                    return v
                res = self._find_url_in_dict(v)
                if res: return res
        return None

    def _tensor_to_base64(self, image_tensor):
        if image_tensor is None:
            return None
        img = image_tensor[0]
        img = (img * 255).cpu().numpy().astype(np.uint8)
        image = Image.fromarray(img)
        
        # 转换为 RGB (防止 RGBA 转 JPEG 报错)
        if image.mode == 'RGBA':
            image = image.convert('RGB')
            
        buffered = io.BytesIO()
        # 使用 JPEG 格式压缩以减小 Payload 大小 (避免 10054 错误)
        image.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"

    def _download_and_convert_video(self, video_url, task_id="temp"):
        try:
            import imageio
        except ImportError:
            raise ImportError("需要安装 imageio 库来处理视频: pip install imageio[ffmpeg]")
            
        print(f"Downloading video from {video_url}...")
        
        # 使用 _safe_request 下载视频
        response = self._safe_request("GET", video_url, stream=True)
        response.raise_for_status()
        
        # 保存到本地文件
        output_dir = folder_paths.get_output_directory()
        filename = f"doubao_{task_id}.mp4"
        file_path = os.path.join(output_dir, filename)
        
        # 如果文件名已存在，添加时间戳
        if os.path.exists(file_path):
            filename = f"doubao_{task_id}_{int(time.time())}.mp4"
            file_path = os.path.join(output_dir, filename)
            
        with open(file_path, "wb") as f:
            f.write(response.content)
            
        print(f"Video saved to: {file_path}")
        
        # 读取视频帧
        # 直接读取本地文件，避免 imageio 处理 BytesIO 时的兼容性问题
        reader = imageio.get_reader(file_path, "ffmpeg")
        frames = []
        for frame in reader:
            frames.append(frame)
            
        if not frames:
            raise RuntimeError("下载的视频中没有帧")
            
        video_np = np.array(frames).astype(np.float32) / 255.0
        video_tensor = torch.from_numpy(video_np)
        return video_tensor, file_path

NODE_CLASS_MAPPINGS = {
    "DoubaoVideoAPI": DoubaoVideoAPI
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DoubaoVideoAPI": "豆包视频API@伊汝梦"
}
