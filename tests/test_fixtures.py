"""测试图片必须能真的解码。

背景：tests/fixtures/classifier/ 下的三张 PNG 曾经被 Git 的 CRLF 规范化改坏
（签名从 `89 50 4E 47 0D 0A 1A 0A` 变成少了 0D 的样子），而唯一会用到它们的是
`test_known_photos`——那个测试需要 onnxruntime，CI 默认不装，于是永久 skip，
坏图挂了很久都没人发现。

这组断言不依赖模型、也不依赖 onnxruntime，所以跑在最普通的 CI job 里：
图片一旦被改坏，当天就红。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

FIXTURES = Path(__file__).resolve().parent / "fixtures"
IMAGES = sorted(p for p in FIXTURES.rglob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg"})


def test_fixture_dir_is_not_empty():
    """目录被整体删掉时，参数化会收集到 0 个用例而静默通过，这条兜住它。"""
    assert IMAGES, f"{FIXTURES} 下没有任何测试图片"


@pytest.mark.parametrize("img", IMAGES, ids=lambda p: p.name)
def test_fixture_image_decodes(img: Path):
    """完整解码，而不只是读文件头——坏掉的 PNG 往往连文件头都过不了。"""
    with Image.open(img) as im:
        im.load()
        assert im.width >= 50 and im.height >= 50, f"{img.name} 尺寸异常: {im.size}"
        assert im.mode in {"RGB", "RGBA", "L", "P"}, f"{img.name} 颜色模式异常: {im.mode}"


def test_png_signature_is_intact():
    """显式比对 PNG 魔数：这正是当年被改坏的那几个字节，报错信息要能一眼看懂。"""
    expected = b"\x89PNG\r\n\x1a\n"
    for img in IMAGES:
        if img.suffix.lower() != ".png":
            continue
        head = img.read_bytes()[:8]
        assert head == expected, (
            f"{img.name} 的 PNG 签名不对：{head!r}，应为 {expected!r}。"
            "多半是又被 Git 按文本规则做了换行规范化，检查 .gitattributes 里的 *.png binary"
        )
