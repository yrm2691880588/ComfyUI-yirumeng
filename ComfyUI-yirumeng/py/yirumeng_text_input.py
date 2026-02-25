# -*- coding: utf-8 -*-
# 说明：这是一个简单的“文本输入”节点
# - 提供一个多行文本框供用户输入内容
# - 输出该文本内容，方便连接到其他节点

class YiruTextInput:
    """
    节点功能：
    - 提供一个多行文本输入框
    - 输出输入的文本字符串
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "文本": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("文本",)
    FUNCTION = "run"
    CATEGORY = "yirumeng/文本"
    DESCRIPTION = """
    简单的多行文本输入节点。
    
    作者: @伊汝梦
    """

    def run(self, 文本):
        return (文本,)


NODE_CLASS_MAPPINGS = {
    "文本输入": YiruTextInput
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "文本输入": "文本输入@伊汝梦"
}
