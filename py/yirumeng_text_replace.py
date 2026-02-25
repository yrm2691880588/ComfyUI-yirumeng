# -*- coding: utf-8 -*-
# 说明：这是一个“文本替换”节点，支持最多 10 组“搜索→替换”规则
# - 输入一段文本，按顺序执行多组替换，输出处理后的文本
# - 可通过“数量”控制实际使用的规则组数（从第1组开始依次应用）
# - 所有字段均为字符串类型，允许为空；当“搜索”为空时会跳过该规则
# - 面向零基础用户，注释尽量友好易懂

class ContainsAnyDict(dict):
    # 允许可选输入字典包含任意键名（用于前端动态创建的输入）
    def __contains__(self, key):
        return True

    def __getitem__(self, key):
        return ("STRING", {"default": ""})

    def get(self, key, default=None):
        return ("STRING", {"default": ""})


class YiruTextReplace:
    """
    节点功能：
    - 接受一段“文本”（字符串）
    - 根据用户填写的若干“搜索/替换”规则，依次执行字符串替换
    - “数量”用于控制实际启用的规则组数（最多 10 组）
    - 返回替换完成后的“文本”
    使用提示：
    - 建议从“搜索1/替换1”开始填写，逐组往下；当“数量”为 N 时，仅前 N 组会被应用
    - 若某一组“搜索”为空字符串，则会自动跳过该组，避免产生意外的无限替换
    """

    @classmethod
    def INPUT_TYPES(cls):
        # 基础输入：只保留“文本”和“数量”
        # 动态增减的“搜索/替换”对由前端 JS 根据“数量”生成，
        # 后端通过 optional 的“通配字典”接收这些任意命名的输入。
        return {
            "required": {
                "数量": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
                "文本": ("STRING", {"forceInput": True}),
                "搜索1": ("STRING", {"default": ""}),
                "替换1": ("STRING", {"default": ""}),
            },
            "optional": ContainsAnyDict(),
        }

    # 输出类型声明：返回一段字符串
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("文本",)
    FUNCTION = "replace"
    CATEGORY = "yirumeng/文本"
    DESCRIPTION = """
    文本替换节点，支持多组查找替换规则。
    
    作者: @伊汝梦
    """

    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
        # 允许所有输入，忽略前端按钮带来的验证错误
        return True


    def replace(self, 文本, 数量, **kwargs):
        """
        核心处理逻辑：
        - 将“数量”限制在 1~10 之间，以防填入异常值
        - 依次读取每一组“搜索/替换”（来自 kwargs）
        - 当“搜索”不为空时，使用 Python 的 str.replace 进行替换
        - 替换是“从上到下顺序执行”，后面的规则会基于前面的结果继续处理
        """
        # 保护性处理：确保数量处于合法范围
        try:
            count = int(数量)
        except Exception:
            count = 1
        if count < 1:
            count = 1
        if count > 10:
            count = 10

        # 开始处理文本
        result = str(文本 if 文本 is not None else "")
        for i in range(1, count + 1):
            search = kwargs.get(f"搜索{i}", None)
            repl = kwargs.get(f"替换{i}", None)
            # 跳过空搜索，避免无意义替换
            if search is None:
                continue
            search = str(search)
            if search == "":
                continue
            # 将替换值规范为字符串（允许为空字符串，表示删除匹配内容）
            repl = "" if repl is None else str(repl)
            result = result.replace(search, repl)

        return (result,)


NODE_CLASS_MAPPINGS = {
    "文本替换": YiruTextReplace
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "文本替换": "文本替换@伊汝梦"
}

# 前端资源目录声明：让 ComfyUI 自动加载 ./js 下的扩展脚本
WEB_DIRECTORY = "./js"
