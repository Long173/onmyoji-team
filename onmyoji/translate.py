"""Dịch tên 式神 từ tiếng Trung sang tiếng Việt (âm Hán-Việt) + tên thông dụng."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .hanviet import CHAR_TO_HANVIET, PUNCTUATION_PASSTHROUGH

# Tên quen dùng trong cộng đồng (romaji Nhật hoặc tên bản quốc tế).
# Chỉ khai những cái phổ biến chắc chắn; phần còn lại để trống và dùng Hán-Việt.
COMMON_NAMES: Mapping[str, str] = {
    "大天狗": "Daitengu",
    "酒吞童子": "Shuten-doji",
    "鬼王酒吞童子": "Shuten-doji Onikiri",
    "茨木童子": "Ibaraki-doji",
    "阎魔": "Enma",
    "大夜摩天阎魔": "Enma Yama",
    "妖狐": "Yoko",
    "一目连": "Ichimokuren",
    "荒": "Susanoo",
    "神启荒": "Susanoo Kagura",
    "犬夜叉": "Inuyasha",
    "惠比寿": "Ebisu",
    "雪女": "Yuki-onna",
    "般若": "Hannya",
    "孟婆": "Meng Po",
    "座敷童子": "Zashiki-warashi",
    "海坊主": "Umibozu",
    "络新妇": "Jorogumo",
    "姑获鸟": "Ubume",
    "食梦貘": "Baku",
    "荒川之主": "Arakawa no Aruji",
    "青行灯": "Aoandon",
    "两面佛": "Ryomen-butsu",
    "帝释天": "Taishakuten",
    "毗沙门天": "Bishamonten",
    "不知火": "Shiranui",
    "葛叶": "Kuzunoha",
    "荒骷髅": "Gashadokuro",
    "神乐": "Kagura",
    "源赖光": "Minamoto no Raiko",
    "阿修罗": "Asura",
    "伊邪那美": "Izanami",
    "大岳丸": "Otakemaru",
    "花鸟卷": "Kacho-fugetsu",
    "神堕荒": "Susanoo Fallen",
    "妖刀姬": "Yotohime",
    "御饭团": "Onigiri",
    "判官": "Hangan",
    "凤凰火": "Ho-oh no Hi",
    "青蛙瓷器": "Kaeru",
    "跳跳哥哥": "Hopping Brother",
    "跳跳弟弟": "Hopping Younger Brother",
    "跳跳妹妹": "Hopping Sister",
    "首无": "Kubinashi",
    "赤舌": "Akajita",
    "铁鼠": "Tesso",
    "萤草": "Hotarugusa",
    "山兔": "Yamausagi",
    "管狐": "Kudagitsune",
    "椒图": "Shozu",
    "河童": "Kappa",
    "骨女": "Hone-onna",
    "雨女": "Ame-onna",
    "犬神": "Inugami",
    "鸦天狗": "Karasu-tengu",
    "鬼使白": "Kiyohime no Shiro",
    "鬼使黑": "Kiyohime no Kuro",
    "清姬": "Kiyohime",
    "镰鼬": "Kamaitachi",
    "二口女": "Futakuchi-onna",
    "白狼": "Byakuro",
    "樱花妖": "Sakura no Yokai",
    "桃花妖": "Momo no Yokai",
    "灯笼鬼": "Chochin-obake",
    "傀儡师": "Kugutsu-shi",
    "独眼小僧": "Hitotsume-kozo",
    "提灯小僧": "Chochin-kozo",
    "鬼女红叶": "Kijo Momiji",
    "武士之灵": "Bushi no Rei",
    "丑时之女": "Ushi no Toki",
    "食发鬼": "Kamikui",
    "饿鬼": "Gaki",
    "九命猫": "Kyumyoneko",
    "鲤鱼精": "Koi no Sei",
    "三尾狐": "Sanbi no Kitsune",
    "巫蛊师": "Fugu-shi",
    "蝴蝶精": "Chocho no Sei",
    "妖琴师": "Yokinshi",
    "小鹿男": "Kojika",
    "吸血姬": "Kyuketsuki",
    "山童": "Yamawaro",
    "兵俑": "Heiyo",
    "狸猫": "Tanuki",
    "童男": "Doran",
    "童女": "Donyo",
    "觉": "Satori",
}

TITLE_EXCEPTIONS = frozenset()


@dataclass(frozen=True)
class ShishenName:
    """Tên một 式神 ở cả ba dạng."""

    shishen_id: int
    chinese: str
    hanviet: str
    common: str = ""

    @property
    def display(self) -> str:
        """Tên hiển thị ưu tiên: Hán-Việt, kèm tên thông dụng nếu có."""
        return f"{self.hanviet} ({self.common})" if self.common else self.hanviet


def _titleize(word: str) -> str:
    return word[:1].upper() + word[1:] if word else word


def to_hanviet(chinese: str) -> str:
    """Chuyển tên tiếng Trung sang âm Hán-Việt, viết hoa từng âm.

    Ký tự không có trong bảng được giữ nguyên để lộ ra ngay khi thiếu dữ liệu.
    """
    if not chinese:
        return ""

    syllables = [
        CHAR_TO_HANVIET.get(char, char)
        for char in chinese
        if char not in PUNCTUATION_PASSTHROUGH
    ]
    return " ".join(_titleize(syllable) for syllable in syllables)


def unmapped_chars(chinese: str) -> tuple[str, ...]:
    """Các ký tự chưa có trong bảng Hán-Việt — dùng để cảnh báo."""
    return tuple(
        char
        for char in chinese
        if char not in CHAR_TO_HANVIET and char not in PUNCTUATION_PASSTHROUGH
    )


def build_name_table(shishen_map: Mapping[int, str]) -> Mapping[int, ShishenName]:
    """Từ {id: tên Trung} dựng {id: ShishenName} — không sửa input."""
    return {
        shishen_id: ShishenName(
            shishen_id=shishen_id,
            chinese=chinese,
            hanviet=to_hanviet(chinese),
            common=COMMON_NAMES.get(chinese, ""),
        )
        for shishen_id, chinese in shishen_map.items()
    }
