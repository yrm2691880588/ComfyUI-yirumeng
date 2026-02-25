# -*- coding: utf-8 -*-
"""
字符串输入节点
"""

class YiruString:
    """
    节点功能：
    - 作为一个基础的字符串输入节点
    - 用户可以在文本框中输入或粘贴任何文字
    - 将输入的文字传递给其他节点使用
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        """
        定义节点的输入参数
        """
        return {
            "required": {
                # "字符串" 是参数名，显示在节点界面上
                # ("STRING", {...}) 定义类型为字符串
                # default: 默认值为空字符串
                # multiline: True 表示这是一个多行文本框，可以输入多行文字
                # dynamicPrompts: True 允许使用动态提示词语法（如果安装了相关插件）
                "字符串": ("STRING", {"default": "", "multiline": True, "dynamicPrompts": True}),
            }
        }

    # 定义输出类型，这里输出一个 STRING 类型
    RETURN_TYPES = ("STRING",)
    
    # 定义输出连接点的名称，显示为 "字符串"
    RETURN_NAMES = ("字符串",)

    # 定义处理函数的主函数名，对应下方定义的 func 方法
    FUNCTION = "func"

    # 定义节点在菜单中的分类
    # 按照规则使用 yirumeng/字符串
    CATEGORY = "yirumeng/字符串"
    DESCRIPTION = """
    基础字符串输入节点，支持多行文本和动态提示词。
    
    作者: @伊汝梦
    """

    def func(self, 字符串):
        """
        主处理函数
        :param 字符串: 用户输入的文本内容
        :return: 直接返回输入的字符串
        """
        return (字符串,)

# 节点映射字典，用于 ComfyUI 注册节点
# 键名 YiruString 必须唯一
NODE_CLASS_MAPPINGS = {
    "YiruString": YiruString
}

# 节点显示名称映射字典
# 键名对应 NODE_CLASS_MAPPINGS 中的键
# 值是节点在界面上显示的名称，必须以 @伊汝梦 结尾
NODE_DISPLAY_NAME_MAPPINGS = {
    "YiruString": "字符串@伊汝梦"
}
