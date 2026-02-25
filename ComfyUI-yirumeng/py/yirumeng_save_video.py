import os
import json
import folder_paths
from PIL import Image
import numpy as np
import torch

print("Yirumeng_SaveVideo: Loading module...")

try:
    import imageio
except ImportError:
    imageio = None

class SaveVideo:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "文件名前缀": ("STRING", {"default": "ComfyUI_Video"}),
                "帧率": ("INT", {"default": 24, "min": 1, "max": 120, "step": 1}),
                "格式": (["auto", "mp4", "gif", "webp", "mov", "avi"], {"default": "auto"}),
                "编码器": (["auto", "h264", "h265", "libx264", "libx265", "vp9", "prores", "mpeg4"], {"default": "auto"}),
                "质量": ("INT", {"default": 22, "min": 0, "max": 51, "step": 1, "tooltip": "CRF value for video (lower is better quality, 0 is lossless), or Quality 0-100 for GIF/WebP (higher is better)"}),
            },
            "optional": {
                "视频帧": ("IMAGE", ),
                "视频对象": ("VIDEO", ),
                "自定义保存路径": ("STRING", {"default": "", "placeholder": "留空则使用默认路径"}),
                "起始编号": ("INT", {"default": -1, "min": -1, "max": 99999999, "step": 1, "display": "number"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_video"
    OUTPUT_NODE = True
    CATEGORY = "yirumeng/Video"
    DESCRIPTION = """
    保存视频文件，支持多种格式 (mp4, gif, webp) 和编码器设置。
    
    作者: @伊汝梦
    """

    def save_video(self, 文件名前缀="ComfyUI_Video", 帧率=24, 格式="auto", 编码器="auto", 质量=22, 自定义保存路径="", 起始编号=-1, 视频帧=None, 视频对象=None, prompt=None, extra_pnginfo=None):
        if imageio is None:
            raise ImportError("Saving video requires 'imageio' and 'imageio-ffmpeg'. Please install them via pip.")
            
        # 1. 优先处理视频对象 (VIDEO input)
        frames = None
        current_fps = 帧率

        if 视频对象 is not None:
            print(f"DEBUG: Received 视频对象 type: {type(视频对象)}")
            # 尝试从视频对象中获取 frames 和 fps
            
            # Case 1: Object with attributes (e.g. DoubaoVideoWrapper)
            if hasattr(视频对象, "images"):
                frames = 视频对象.images
            
            if hasattr(视频对象, "fps"):
                 current_fps = 视频对象.fps
            elif hasattr(视频对象, "frame_rate"):
                 current_fps = 视频对象.frame_rate
            
            # Case 2: Dictionary
            if frames is None and isinstance(视频对象, dict):
                print(f"DEBUG: 视频对象 keys: {视频对象.keys()}")
                if "images" in 视频对象:
                    frames = 视频对象["images"]
                elif "frames" in 视频对象:
                    frames = 视频对象["frames"]
                elif "video" in 视频对象:
                    frames = 视频对象["video"]
                
                if "fps" in 视频对象:
                    current_fps = 视频对象["fps"]
                elif "frame_rate" in 视频对象:
                    current_fps = 视频对象["frame_rate"]

            # Case 3: Tuple/List
            if frames is None and isinstance(视频对象, (list, tuple)):
                 # Check if it's (frames, fps) tuple
                 if len(视频对象) >= 2 and (isinstance(视频对象[1], (int, float))):
                     frames = 视频对象[0]
                     current_fps = 视频对象[1]
                 # Check if it's just a list of tensors
                 elif len(视频对象) > 0 and isinstance(视频对象[0], torch.Tensor):
                     frames = torch.stack(list(视频对象))
            
            # Case 4: Direct Tensor
            if frames is None:
                if isinstance(视频对象, torch.Tensor):
                    frames = 视频对象

            # Case 4.5: Handle ComfyUI internal Video objects (VideoFromFile)
            if frames is None:
                 # Try to extract path from known internal attributes
                 # VideoFromFile typically has __file (name mangled to _VideoFromFile__file)
                 obj_type = type(视频对象).__name__
                 if "VideoFromFile" in obj_type:
                      path_attr = f"_{obj_type}__file"
                      if hasattr(视频对象, path_attr):
                           path_val = getattr(视频对象, path_attr)
                           if isinstance(path_val, str):
                                print(f"DEBUG: Extracted path from {obj_type}: {path_val}")
                                # Convert to string so Case 5 can handle it
                                视频对象 = path_val

            # Case 5: String (Path)
            if frames is None and isinstance(视频对象, str):
                 # Try to load video from path
                 print(f"DEBUG: 视频对象 is string: {视频对象}")
                 # Check if path exists or relative to input
                 video_path = 视频对象
                 if not os.path.exists(video_path):
                     # Try finding in input directory
                     input_dir = folder_paths.get_input_directory()
                     test_path = os.path.join(input_dir, video_path)
                     if os.path.exists(test_path):
                         video_path = test_path
                
                 if os.path.exists(video_path):
                     try:
                         reader = imageio.get_reader(video_path)
                         frames_list = []
                         for frame in reader:
                             # imageio reads as HWC uint8, convert to BHWC float 0-1
                             frames_list.append(torch.from_numpy(frame))
                         
                         if frames_list:
                             frames = torch.stack(frames_list).float() / 255.0
                             # Handle potential alpha channel or grayscale? Assume RGB for now
                             if frames.shape[-1] == 4:
                                 # Convert RGBA to RGB if needed, or keep it. Comfy usually likes RGB.
                                 # But SaveVideo might handle 4 channels.
                                 pass
                         
                         # Update FPS from metadata
                         meta = reader.get_meta_data()
                         if "fps" in meta:
                             current_fps = meta["fps"]
                     except Exception as e:
                         print(f"DEBUG: Failed to load video from path: {e}")

        # 2. 如果没有视频对象，使用视频帧 (IMAGE input)
        if frames is None:
            if 视频帧 is not None:
                frames = 视频帧
            else:
                # Construct detailed error message
                debug_info = f"Type: {type(视频对象)}"
                if 视频对象 is not None:
                    try:
                        debug_info += f", Dir: {dir(视频对象)[:20]}" # Limit to first 20 attributes
                        debug_info += f", Str: {str(视频对象)[:100]}" # Limit string length
                    except:
                        pass
                
                print(f"DEBUG: Failed to extract frames. {debug_info}")
                raise ValueError(f"未接收到视频数据！\n调试信息: {debug_info}\n请连接 [视频帧] 或 [视频对象]。")

        # 确保 frames 是 tensor
        if not isinstance(frames, torch.Tensor):
             # 尝试转换
             try:
                 frames = torch.stack(frames)
             except:
                 pass
        
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

        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, output_dir, frames[0].shape[1], frames[0].shape[0])
        
        # 如果设置了起始编号（非-1），则覆盖默认的计数器
        if 起始编号 != -1:
             counter = 起始编号

        # 确定扩展名
        if 格式 == "auto":
            # 默认为 mp4
            ext = "mp4"
        else:
            ext = 格式

        # 确定文件名
        if 起始编号 != -1:
            if filename_prefix:
                 file_name = f"{filename_prefix}_{counter}.{ext}"
            else:
                 file_name = f"{counter}.{ext}"
        else:
            file_name = f"{filename}_{counter:05}_.{ext}"
            
        save_path = os.path.join(full_output_folder, file_name)

        # 准备帧数据 (0-255 uint8 numpy array)
        # 视频帧 is [B, H, W, C] float tensor
        output_frames = (255. * frames.cpu().numpy()).clip(0, 255).astype(np.uint8)
        
        # 使用 imageio 保存
        try:
            kwargs = {}
            if ext in ["mp4", "mov", "avi"]:
                if 编码器 == "auto":
                    # auto codec for mp4 is usually libx264 or h264 depending on backend
                    pass 
                else:
                    kwargs["codec"] = 编码器
                
                # mp4/video specific settings
                kwargs["fps"] = current_fps
                # quality (crf) handling for ffmpeg
                # imageio-ffmpeg uses 'quality' parameter (0-10) or 'pixelformat'
                # but standard ffmpeg wrapper often takes 'crf' in output_params
                # For simplicity with imageio.mimsave, we might need to be careful.
                # Standard imageio 'ffmpeg' plugin supports 'fps', 'codec', 'quality' (0-10 for some, crf for others via output_params)
                
                # Simple implementation using imageio
                # Note: 'quality' in imageio for ffmpeg is often 5-10 range or None.
                # Let's use output_params for better control if needed, but keep simple first.
                
                # For h264/h265, use crf via output_params
                output_params = []
                if 编码器 in ["libx264", "h264", "libx265", "h265", "auto"]:
                     # CRF handling
                     # 质量 input is 0-51 (ffmpeg standard), imageio might expect something else or we pass it directly
                     output_params.append("-crf")
                     output_params.append(str(质量))
                     output_params.append("-preset")
                     output_params.append("medium") # default preset
                
                if output_params:
                     kwargs["output_params"] = output_params
                
                # Ensure pixel format is compatible (yuv420p is standard for compatibility)
                kwargs["pixelformat"] = "yuv420p"

            elif ext in ["gif", "webp"]:
                kwargs["fps"] = current_fps
                kwargs["loop"] = 0 # Infinite loop
                # GIF/WebP quality is often optimization related
                # WebP supports quality 0-100
                if ext == "webp":
                     # map 0-51 (CRF-like input) to 0-100? Or just treat input as 0-100 for these formats?
                     # Let's treat input as quality 0-100 if user understands, but default is 22 which is low for webp.
                     # Let's adjust logic: if format is image-like, quality should be higher.
                     # But we can't change input default dynamically.
                     # Let's assume user sets it correctly or we map.
                     # CRF 22 ~ Quality 80?
                     # Simple map: if quality < 60 and ext in gif/webp: assume it was CRF and map it?
                     # No, let's just pass it and document it.
                     if 质量 < 52: # Assume user left it as CRF default
                          q = 100 - 质量 # Rough mapping: CRF 0 -> 100, CRF 50 -> 50
                          kwargs["quality"] = q
                     else:
                          kwargs["quality"] = 质量

            imageio.mimsave(save_path, output_frames, **kwargs)
            
        except Exception as e:
            print(f"SaveVideo Error: {e}")
            # Fallback or re-raise
            raise RuntimeError(f"Failed to save video: {e}")

        return { "ui": { "images": [{ "filename": file_name, "subfolder": subfolder, "type": self.type }] } }

NODE_CLASS_MAPPINGS = {
    "Yirumeng_SaveVideo": SaveVideo
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Yirumeng_SaveVideo": "保存视频(高级版) @伊汝梦"
}
