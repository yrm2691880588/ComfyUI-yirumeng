# -*- coding: utf-8 -*-
class ContainsAnyDict(dict):
    # 允许可选输入字典包含任意键名（用于前端动态创建的输入）
    def __contains__(self, key):
        return True

    def __getitem__(self, key):
        return ("STRING", {"default": ""})

    def get(self, key, default=None):
        return ("STRING", {"default": ""})


class YiruTextJoin:
    """
    节点功能：
    - 文本联结：将多个文本输入连接成一个字符串
    - 支持自定义分隔符
    - 支持通过“数量”动态增减输入连接点
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "数量": ("INT", {"default": 2, "min": 2, "max": 50, "step": 1}),
                "分隔符": ("STRING", {"default": ",", "multiline": False}),
                "文本1": ("STRING", {"forceInput": True}),
                "文本2": ("STRING", {"forceInput": True}),
            },
            "optional": ContainsAnyDict(),
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("文本",)
    FUNCTION = "join_text"
    CATEGORY = "yirumeng/文本"
    DESCRIPTION = """
    文本联结节点，支持自定义分隔符和动态数量。
    
    作者: @伊汝梦
    """

    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
        return True

    def join_text(self, 数量, 分隔符, **kwargs):
        # 保护性处理：确保数量处于合法范围
        try:
            count = int(数量)
        except Exception:
            count = 2
        if count < 2:
            count = 2
        
        text_list = []
        for i in range(1, count + 1):
            key = f"文本{i}"
            # 从 kwargs 中获取文本，如果不存在则为空字符串
            # 注意：即使是 文本1 和 文本2，因为没有在函数参数中显式声明，也会进入 kwargs
            val = kwargs.get(key, "")
            if val is None:
                val = ""
            text_list.append(str(val))

        # 使用分隔符连接所有文本
        result = 分隔符.join(text_list)
        return (result,)


NODE_CLASS_MAPPINGS = {
    "文本联结": YiruTextJoin
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "文本联结": "文本联结@伊汝梦"
}
