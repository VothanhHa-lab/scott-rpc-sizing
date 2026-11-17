import subprocess, sys
from PIL import Image, ImageDraw, ImageFont
OLD = "/home/claude/urt_v3/%s.pdf"
def render(pdf, out, width_px):
    subprocess.run(["pdftoppm", "-png", "-singlefile", "-scale-to-x", str(width_px), "-scale-to-y", "-1", pdf, out], check=True)
font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 28)
for name in ("fig1_structure", "fig2_model"):
    W = 1500
    render(OLD % name, f"/tmp/cmp_old_{name}", W)
    render(f"/home/claude/subtasks2/1/{name}.pdf", f"/tmp/cmp_new_{name}", W)
    a = Image.open(f"/tmp/cmp_old_{name}.png").convert("RGB"); b = Image.open(f"/tmp/cmp_new_{name}.png").convert("RGB")
    pad = 50
    img = Image.new("RGB", (W + 40, a.height + b.height + 2 * pad + 20), "white")
    d = ImageDraw.Draw(img)
    d.text((20, 10), "OLD (original, Times New Roman / STIX)", fill="black", font=font)
    img.paste(a, (20, pad))
    y2 = pad + a.height + 10
    d.text((20, y2), "NEW (redrawn, Liberation Sans)", fill="black", font=font)
    img.paste(b, (20, y2 + pad - 10))
    d.rectangle([20, pad, 20 + a.width - 1, pad + a.height - 1], outline="#999999")
    d.rectangle([20, y2 + pad - 10, 20 + b.width - 1, y2 + pad - 10 + b.height - 1], outline="#999999")
    img.save(f"/home/claude/subtasks2/1/compare_{name}.png")
