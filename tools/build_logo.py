import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent

FIELD = (17, 21, 31, 255)
TILE = (24, 30, 44, 255)
TILE_EDGE = (44, 54, 78, 255)
INK = (9, 13, 22, 255)
WHITE = (240, 244, 250, 255)
MUTED = (134, 146, 172, 255)

STONE_TOP = (238, 240, 184, 255)
STONE_LEFT = (214, 216, 154, 255)
STONE_RIGHT = (178, 180, 122, 255)
STONE_RIDGE = (250, 252, 212, 255)
STONE_OUTLINE = (58, 60, 36, 255)

BOLT = (72, 232, 255, 255)
BOLT_LIGHT = (196, 250, 255, 255)
BOLT_DARK = (22, 160, 196, 255)

ICON_CELLS = 64
ICON_SIZE = 1024

TOP = (32, 7)
RIGHT = (54, 18)
CENTRE = (32, 29)
LEFT = (10, 18)
LOW_RIGHT = (54, 40)
LOW_CENTRE = (32, 51)
LOW_LEFT = (10, 40)

FACES = (
    ((TOP, RIGHT, CENTRE, LEFT), STONE_TOP, 46),
    ((LEFT, CENTRE, LOW_CENTRE, LOW_LEFT), STONE_LEFT, 40),
    ((CENTRE, RIGHT, LOW_RIGHT, LOW_CENTRE), STONE_RIGHT, 40),
)
SILHOUETTE = (TOP, RIGHT, LOW_RIGHT, LOW_CENTRE, LOW_LEFT, LEFT)
RIDGES = ((LEFT, CENTRE), (CENTRE, RIGHT), (CENTRE, LOW_CENTRE))

BOLT_SHAPE = ((33, 13), (42, 13), (36, 30), (44, 30), (25, 56), (30, 37), (21, 37))
BOLT_LIT_EDGES = (((33, 13), (21, 37)), ((30, 37), (25, 56)))
BOLT_SHADED_EDGES = (((42, 13), (36, 30)), ((44, 30), (25, 56)))

BANNER_CELLS = (320, 160)
BANNER_SIZE = (1280, 640)
BANNER_ICON_AT = (0, 16)
BANNER_ICON_SCALE = 2
TEXT_LEFT = 132

GLYPHS = {
    "L": ("X....", "X....", "X....", "X....", "X....", "X....", "XXXXX"),
    "E": ("XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "XXXXX"),
    "T": ("XXXXX", "..X..", "..X..", "..X..", "..X..", "..X..", "..X.."),
    "M": ("X...X", "XX.XX", "X.X.X", "X.X.X", "X...X", "X...X", "X...X"),
    "P": ("XXXX.", "X...X", "X...X", "XXXX.", "X....", "X....", "X...."),
    "R": ("XXXX.", "X...X", "X...X", "XXXX.", "X.X..", "X..X.", "X...X"),
    "F": ("XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "X...."),
    "O": (".XXX.", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."),
    "N": ("X...X", "XX..X", "X.X.X", "X..XX", "X...X", "X...X", "X...X"),
    "D": ("XXXX.", "X...X", "X...X", "X...X", "X...X", "X...X", "XXXX."),
    "S": (".XXXX", "X....", "X....", ".XXX.", "....X", "....X", "XXXX."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
}
GLYPH_WIDTH = 5
GLYPH_GAP = 1


def shade(colour, amount: int):
    red, green, blue, alpha = colour
    return (clamp(red + amount), clamp(green + amount), clamp(blue + amount), alpha)


def clamp(value: int) -> int:
    return max(0, min(255, value))


def draw_block(image) -> None:
    draw = ImageDraw.Draw(image)
    speckles = random.Random(7)
    for corners, colour, count in FACES:
        draw.polygon(corners, fill=colour)
        scatter_speckles(image, corners, colour, count, speckles)

    for start, end in RIDGES:
        draw.line((start, end), fill=STONE_RIDGE)
    draw.line((*SILHOUETTE, SILHOUETTE[0]), fill=STONE_OUTLINE)


def scatter_speckles(image, corners, colour, count: int, speckles) -> None:
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).polygon(corners, fill=255)
    inside = [(x, y) for x in range(image.width) for y in range(image.height) if mask.getpixel((x, y))]

    for _ in range(count):
        x, y = speckles.choice(inside)
        tone = shade(colour, speckles.choice((-26, -16, 12)))
        image.putpixel((x, y), tone)
        if mask.getpixel((min(x + 1, image.width - 1), y)):
            image.putpixel((x + 1, y), tone)


def draw_bolt(image) -> None:
    draw = ImageDraw.Draw(image)
    for shift_x in (-2, -1, 0, 1, 2):
        for shift_y in (-2, -1, 0, 1, 2):
            if abs(shift_x) + abs(shift_y) < 4:
                draw.polygon([(x + shift_x, y + shift_y) for x, y in BOLT_SHAPE], fill=INK)

    draw.polygon(BOLT_SHAPE, fill=BOLT)
    for edge in BOLT_SHADED_EDGES:
        draw.line(edge, fill=BOLT_DARK)
    for edge in BOLT_LIT_EDGES:
        draw.line(edge, fill=BOLT_LIGHT)


def draw_mark():
    mark = Image.new("RGBA", (ICON_CELLS, ICON_CELLS), (0, 0, 0, 0))
    draw_block(mark)
    draw_bolt(mark)
    return mark


def build_icon():
    icon = Image.new("RGBA", (ICON_CELLS, ICON_CELLS), (0, 0, 0, 0))
    ImageDraw.Draw(icon).rounded_rectangle((1, 1, ICON_CELLS - 2, ICON_CELLS - 2), radius=10, fill=TILE, outline=TILE_EDGE)
    icon.alpha_composite(draw_mark())
    return icon.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.NEAREST)


def draw_words(draw, text: str, left: int, top: int, scale: int, colour) -> None:
    for offset, fill in ((scale // 2 or 1, shade(colour, -150)), (0, colour)):
        x = left + offset
        for letter in text:
            for row, line in enumerate(GLYPHS[letter]):
                for column, mark in enumerate(line):
                    if mark == "X":
                        cell_x = x + column * scale
                        cell_y = top + offset + row * scale
                        draw.rectangle((cell_x, cell_y, cell_x + scale - 1, cell_y + scale - 1), fill=fill)
            x += (GLYPH_WIDTH + GLYPH_GAP) * scale


def build_banner():
    banner = Image.new("RGBA", BANNER_CELLS, FIELD)
    side = ICON_CELLS * BANNER_ICON_SCALE
    banner.alpha_composite(draw_mark().resize((side, side), Image.Resampling.NEAREST), BANNER_ICON_AT)

    draw = ImageDraw.Draw(banner)
    draw_words(draw, "LET ME", TEXT_LEFT, 32, 4, WHITE)
    draw_words(draw, "PERFORM", TEXT_LEFT, 68, 4, BOLT)
    draw_words(draw, "FOR ENDSTONE", TEXT_LEFT, 110, 2, MUTED)
    return banner.resize(BANNER_SIZE, Image.Resampling.NEAREST)


def main() -> None:
    build_icon().save(ROOT / "logo.png")
    build_banner().save(ROOT / "banner.png")
    print(f"Wrote logo.png and banner.png to {ROOT}")


if __name__ == "__main__":
    main()
