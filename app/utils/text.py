# -*- coding: utf-8 -*-
"""
文本处理工具函数

Author: music-monitor development team
"""


def normalize_cn_brackets(text: str) -> str:
    """
    归一化中文括号为英文括号，并移除所有空格以最大化匹配容错率。

    用途: 歌曲标题匹配时消除中英文括号差异。

    Args:
        text: 待归一化的文本

    Returns:
        归一化后的文本
    """
    if not text:
        return ""
    text = text.replace('（', '(').replace('）', ')')
    text = text.replace('【', '[').replace('】', ']')
    return text.replace(" ", "").strip()
