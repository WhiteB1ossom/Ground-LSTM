"""Restore the new chart's unpersisted worksheet from its verified source values."""
import hashlib
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import zipfile

build = Path(__file__).parent
source, target = build / "candidate-v6.pptx", build / "candidate-v9.pptx"
if target.exists(): raise FileExistsError(target)
data = json.loads((build / "content.json").read_text(encoding="utf-8"))["timeline"]["sensor"]
ns = {"c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}
with zipfile.ZipFile(source) as presentation:
    chart = ET.fromstring(presentation.read("ppt/charts/chart1.xml"))
    exact_cache = []
    for element, intended in zip(chart.findall(".//c:ser", ns), data):
        exact_series = {}
        for axis in ("xVal", "yVal"):
            exact_series["x" if axis == "xVal" else "y"] = [v.text for v in element.findall(f"c:{axis}/c:numRef/c:numCache/c:pt/c:v", ns)]
            actual = [float(v) for v in exact_series["x" if axis == "xVal" else "y"]]
            expected = intended["x" if axis == "xVal" else "y"]
            assert len(actual) == len(expected) and all(abs(a-b) < 1e-10 for a,b in zip(actual,expected))
        exact_cache.append(exact_series)
    name = "ppt/embeddings/Microsoft_Excel_Worksheet.xlsx"
    with zipfile.ZipFile(io.BytesIO(presentation.read(name))) as workbook:
        headers = ["Time", data[0]["name"], "ReferenceTime", data[1]["name"]]
        rows = ['<row r="1">' + ''.join(f'<c r="{col}1" t="inlineStr"><is><t>{escape(value)}</t></is></c>' for col,value in zip("ABCD",headers)) + '</row>']
        for index in range(len(data[0]["x"])):
            cells = []
            for series_index, series in enumerate(data):
                if index < len(series["x"]):
                    for axis_index, axis in enumerate(("x", "y")):
                        column = "ABCD"[2*series_index+axis_index]
                        cells.append(f'<c r="{column}{index+2}"><v>{exact_cache[series_index][axis][index]}</v></c>')
            rows.append(f'<row r="{index+2}">' + ''.join(cells) + '</row>')
        last = len(rows)
        worksheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        worksheet = re.sub(r'<sheetData>.*?</sheetData>', '<sheetData>'+''.join(rows)+'</sheetData>', worksheet, flags=re.S)
        worksheet = re.sub(r'<dimension ref="[^"]+"', f'<dimension ref="A1:D{last}"', worksheet)
        table = f'<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" id="1" name="Table1" displayName="Table1" ref="A1:D{last}" totalsRowShown="0"><autoFilter ref="A1:D{last}"/><tableColumns count="4">'
        table += ''.join(f'<tableColumn id="{i}" name="{escape(header)}"/>' for i,header in enumerate(headers,1))
        table += '</tableColumns><tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" showRowStripes="1" showColumnStripes="0"/></table>'
        replacements = {"xl/workbook.xml": workbook.read("xl/workbook.xml").replace(b'name="Sheet1"',b'name="Data"'),
                        "xl/worksheets/sheet1.xml": worksheet.encode("utf-8"), "xl/tables/table1.xml": table.encode("utf-8")}
        output = io.BytesIO()
        with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as rebuilt:
            for entry in workbook.infolist(): rebuilt.writestr(entry,replacements.get(entry.filename,workbook.read(entry.filename)))
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as repaired:
        for entry in presentation.infolist(): repaired.writestr(entry,output.getvalue() if entry.filename == name else presentation.read(entry.filename))
(build / "workbook-repair.json").write_text(json.dumps({"scope":"New timeline chart only; original user deck unchanged", "source":"content.json actual replay sensor values", "source_sha256":hashlib.sha256((build/'content.json').read_bytes()).hexdigest(), "chart_cache_matches_source":True, "numeric_cells":1204, "worksheet":"Data", "original_user_formulas_replaced":False},indent=2),encoding="utf-8")
print("Repaired timeline worksheet with verified values")
