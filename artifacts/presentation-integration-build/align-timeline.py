"""Align state strips to the rendered axes after native layout recalculation."""
from pathlib import Path
import re
import zipfile

build = Path(__file__).parent
source, target = build / "candidate-v9.pptx", build / "candidate-v10.pptx"
if target.exists(): raise FileExistsError(target)
count = 0
def align(match):
    global count
    shape = match.group(0)
    coordinates = re.search(r'<a:off x="(\d+)" y="(\d+)"', shape)
    if coordinates and 'prst="rect"' in shape:
        x, y = map(int, coordinates.groups())
        if 416 * 12700 <= y <= 484 * 12700 and x >= 210 * 12700:
            count += 1
            shape = shape.replace(coordinates.group(0), f'<a:off x="{x+4*12700}" y="{y}"', 1)
    return shape
with zipfile.ZipFile(source) as original, zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as output:
    for entry in original.infolist():
        value = original.read(entry.filename)
        if entry.filename == "ppt/slides/slide5.xml":
            value = re.sub(r'<p:sp>.*?</p:sp>', align, value.decode("utf-8"), flags=re.S).encode("utf-8")
        output.writestr(entry,value)
assert count == 6, count
print("Aligned six state-strip shapes; source chart data unchanged")
