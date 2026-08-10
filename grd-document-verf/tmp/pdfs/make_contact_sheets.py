from pathlib import Path

from PIL import Image, ImageDraw


def build(source: Path, output: Path, columns: int, thumb_width: int):
    paths = sorted(source.glob("page-*.png"), key=lambda path: int(path.stem.split("-")[-1]))
    images = [Image.open(path).convert("RGB") for path in paths]
    ratio = thumb_width / images[0].width
    thumb_height = int(images[0].height * ratio)
    gap = 18
    label_height = 28
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (
            columns * thumb_width + (columns + 1) * gap,
            rows * (thumb_height + label_height) + (rows + 1) * gap,
        ),
        "#D9E1EC",
    )
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(images):
        thumbnail = image.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        column = index % columns
        row = index // columns
        x = gap + column * (thumb_width + gap)
        y = gap + row * (thumb_height + label_height + gap)
        sheet.paste(thumbnail, (x, y))
        draw.text((x, y + thumb_height + 6), f"Page {index + 1}", fill="#13233A")
    sheet.save(output)


ROOT = Path(__file__).resolve().parent
build(ROOT / "technical_render", ROOT / "technical_contact.png", 3, 350)
build(ROOT / "flow_render", ROOT / "flow_contact.png", 2, 450)
build(ROOT / "issues_render", ROOT / "issues_contact.png", 4, 270)
