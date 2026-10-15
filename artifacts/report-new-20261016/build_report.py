"""Retain the HWP form and replace only the new fifth-session report content."""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch


ROOT = Path.cwd()
WORK = ROOT / "artifacts/report-new-20261016"
CLI = WORK / "hwp-cli/bin/hwp.exe"
FONT_DIRS = ["C:/Windows/Fonts"]
REF = WORK / "reference-4.json"
FONT = "C:/Windows/Fonts/malgun.ttf"
font_manager.fontManager.addfont(FONT)
plt.rcParams.update({"font.family": font_manager.FontProperties(fname=FONT).get_name(),
                     "font.size": 9, "axes.unicode_minus": False, "savefig.facecolor": "white"})


def run(*args):
    result = subprocess.run([str(CLI), *map(str, args)], check=True, capture_output=True, encoding="utf-8")
    print(result.stdout, result.stderr, flush=True)


def graphics():
    fig, ax = plt.subplots(figsize=(6.2, .79), dpi=300)
    fig.subplots_adjust(left=.005, right=.995, bottom=.02, top=.98)
    ax.set(xlim=(0, 1), ylim=(0, 1)); ax.axis("off")
    labels = ["센서 10종", "정렬\n39개 특징", "링 버퍼 114\n추론 창 64", "장비 점검 LSTM\n서지 활동 LSTM", "경보 판단\n전후 기록"]
    positions = [(.0, .148), (.187, .148), (.374, .168), (.581, .193), (.813, .177)]
    for i, ((x, width), label) in enumerate(zip(positions, labels)):
        ax.add_patch(FancyBboxPatch((x + .005, .18), width - .01, .64, boxstyle="round,pad=.004,rounding_size=.02",
                                    edgecolor="#747d88", facecolor="#f3f5f7", linewidth=.65))
        ax.text(x + width / 2, .50, label, ha="center", va="center", fontsize=8.8, linespacing=1.35)
        if i < 4:
            end = positions[i + 1][0]
            ax.annotate("", (end, .50), (x + width, .50), arrowprops={"arrowstyle": "->", "lw": .8, "color": "#5b626b"})
    fig.savefig(WORK / "flow.png", dpi=300)
    plt.close(fig)

    proof = json.loads((ROOT / "artifacts/demo-check-20261016-002419-382/live-verification.json").read_text(encoding="utf-8"))
    trace = ROOT / proof["cases"]["both"]["output"] / "timeline.jsonl"
    series = {t: ([], []) for t in ("degradation", "surge")}
    first = None
    with trace.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            stamp = row["timestamp_ns"]
            if first is None:
                first = stamp
            for task, (x, y) in series.items():
                prediction = row["tasks"][task]["prediction"]
                if prediction:
                    x.append((stamp - first) / 1e9)
                    y.append(prediction["risk_score"])
    fig, ax = plt.subplots(figsize=(6.2, 1.34), dpi=300)
    fig.subplots_adjust(left=.065, right=.985, top=.65, bottom=.24)
    for task, label, color, style in [("degradation", "장비 점검", "#234d7b", "-"), ("surge", "서지 활동", "#ab5618", "--")]:
        x, y = series[task]
        ax.plot(x, y, style, color=color, lw=1.3, label=label)
    ax.axhline(.5, color="#6c737a", ls=":", lw=.8, label="임계값 0.5")
    ax.axvspan(0, 6.3, color="#e8eaec")
    ax.annotate("60초 온도 상승", xy=(60, .95), xytext=(.16, .755), textcoords="figure fraction", fontsize=8.2,
                arrowprops={"arrowstyle": "-", "color": "#747d88", "lw": .6})
    ax.annotate("65초부터 서지 증가", xy=(65, 1), xytext=(.50, .755), textcoords="figure fraction", fontsize=8.2,
                arrowprops={"arrowstyle": "-", "color": "#747d88", "lw": .6})
    ax.set(xlim=(0, 180), ylim=(-.04, 1.06), xticks=[0, 30, 60, 90, 120, 150, 180], yticks=[0, .5, 1])
    ax.tick_params(labelsize=8, width=.5, length=2, pad=2)
    ax.set_xlabel("센서 시간 (초)", fontsize=8, labelpad=2)
    ax.set_ylabel("점수", fontsize=8, labelpad=3)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["bottom", "left"]].set_color("#a3a9af")
    ax.grid(axis="y", color="#e1e4e6", lw=.5)
    fig.legend(*ax.get_legend_handles_labels(), loc="upper right", bbox_to_anchor=(.99, 1.025), fontsize=7.8, frameon=False, ncol=3)
    fig.savefig(WORK / "timeline.png", dpi=300)
    plt.close(fig)
    (WORK / "figure-source.json").write_text(json.dumps({"source": str(trace.relative_to(ROOT)), "scenario": "both", "actual_lstm": True,
         "synthetic_demo": True, "inferences_per_task": {t: len(x) for t, (x, _y) in series.items()}}, indent=2), encoding="utf-8")


def text(paragraph):
    return "".join(c.get("Text", "") for c in paragraph["chars"] if isinstance(c, dict))


def replace(paragraph, value, *, shape=None, char=None):
    paragraph["chars"] = [{"Text": c} for c in value] + [{"CharCtrl": 13}]
    paragraph["controls"], paragraph["extras"], paragraph["line_segs"] = [], [], []
    paragraph["header"]["ctrl_mask"] = 0
    paragraph["header"].pop("hwp5_child_order", None)
    paragraph["char_shape_runs"] = [[0, char if char is not None else paragraph["char_shape_runs"][0][1]]]
    if shape is not None:
        paragraph["para_shape"] = shape


def main():
    target = ROOT.parent / "그라운드 보고서 방경식 5회차.hwp"
    prior = target.read_bytes()
    prior_hash = hashlib.sha256(prior).hexdigest()
    backup = WORK / f"before-feedback-{prior_hash[:12]}.hwp"
    if backup.exists():
        if backup.read_bytes() != prior:
            raise ValueError("Existing report backup differs")
    else:
        backup.write_bytes(prior)
    (WORK / "prior-publication.json").write_text(json.dumps({"target": str(target), "sha256": prior_hash,
        "backup": str(backup)}, ensure_ascii=False, indent=2), encoding="utf-8")
    graphics()
    doc = json.loads(REF.read_text(encoding="utf-8"))
    paragraphs = doc["sections"][0]["paragraphs"]
    date_table = paragraphs[9]["controls"][0]["Table"]
    replace(date_table["cells"][1]["paragraphs"][0], "2026.     .     . ~ 2026.     .     . ( 1 일간)")
    replace(date_table["cells"][3]["paragraphs"][0], "       :       ~       :       ")
    signature = paragraphs[18]["controls"][0]["Table"]
    replace(signature["cells"][0]["paragraphs"][0], "2026.       .       .")
    report_title = paragraphs[23]["controls"][0]["Table"]["cells"][0]["paragraphs"][1]
    replace(report_title, text(report_title).replace("( 4 )", "( 5 )"))
    paragraphs[23]["header"]["break_type"] |= 4
    form = paragraphs[24]["controls"][0]["Table"]
    replace(form["cells"][1]["paragraphs"][0], "2026 년     월     일 (    요일)")
    body = form["cells"][14]
    template = deepcopy(body["paragraphs"][2])
    normal_style = 0
    bold_style = len(doc["header"]["char_shapes"])
    heading_char = deepcopy(doc["header"]["char_shapes"][0]); heading_char["attr"] |= 2
    doc["header"]["char_shapes"].append(heading_char)
    caption_style = len(doc["header"]["char_shapes"])
    caption_char = deepcopy(doc["header"]["char_shapes"][0]); caption_char["base_size"] = 850
    doc["header"]["char_shapes"].append(caption_char)
    content_page1 = [
        ("수행내용", 14),
        ("서버 추론 통합 및 검토 의견 반영", bold_style),
        ("5회차에서는 오탐지 기준 명확화, 실시간 타임라인 표시, 데이터·시험 사례 확대에 관한 검토 의견을 반영하였다. 링 버퍼와 실제 학습 모델을 연결하고, 장비 열화 점검과 서지 활동을 구분하는 서버 시연 환경을 구현하였다.", normal_style),
        ("1. 피드백 반영과 센서 점검 기준 정비", bold_style),
        ("대지전위 A/B는 각각 2V AC 이상, 누설전류는 2mA 이상(0.002A), 제한소자 A/B/C는 각각 절대온도 45℃ 이상, 습도는 70% 이상으로 갱신하였다. 기준과 같은 값도 조건 충족이다.", normal_style),
        ("예: 누설전류 1.999mA는 미달, 2.000mA는 동일·충족, 2.001mA는 초과·충족이다.", normal_style),
        ("7개 기준에 대해 미달·동일·초과의 21개 경계 상황을 실모델 경로로 검증하였다. 이 수치는 검토용 점검 기준이며 제조사 인증 고장 한계는 아니다. 기준 충족을 곧바로 고장 정답으로 만들지 않았고, 경계 시험의 물리 고장 정답은 미확인으로 유지하였다.", normal_style),
        ("외기온도 25℃는 환경 참조값으로 두었다. 입력전압은 측정값과 지정 기준의 편차를 사용하며, 이번 합성 실험의 220V를 모든 장비의 정격으로 가정하지 않았다.", normal_style),
        ("2. 발열·서지 구분과 센서 해석 보완", bold_style),
        ("서지가 없어도 소자 온도가 오를 수 있다는 의견을 반영해 A/B/C 발열을 독립적으로 처리하였다. 누적 카운터는 증가량·최근 발생률·리셋으로 변환하여 오래 누적된 횟수와 현재 서지를 구분하였다. 서지에는 과전압도 포함될 수 있어 실제 낙뢰 확정과 구별하였다.", normal_style),
        ("3. 실시간 타임라인과 링 버퍼 통합", bold_style),
        ("10개 센서를 39개 특징으로 구성하고, 0.1초 정렬 격자의 최근 114개 시점을 링 버퍼에 유지하였다. 64개 시점부터 추론하고 이후 10개마다 갱신한다. 센서값·점수·경보 변화를 시간축에 표시하고, 각 센서의 관측 주기와 값의 경과 시간을 함께 관리하였다.", normal_style),
        ("그림삽입1", caption_style),
        ("그림 1  센서 입력과 링 버퍼 및 두 모델의 연결", caption_style),
        ("입력 오류·통신 공백·추론 실패는 판정 불가로 표시하고 기존 경보를 자동 해제하지 않도록 보완하였다. 이벤트 전후 기록, 저장 한도와 종료 처리도 추가하였다.", normal_style),
    ]
    content_page2 = [
        ("수행내용 (계속)", 14),
        ("4. 오탐지·미탐지 및 경보 평가 기준 명확화", bold_style),
        ("오탐지(FP)는 정답이 정상인데 AI가 위험으로 예측한 창, 미탐지(FN)는 정답이 위험인데 정상으로 예측한 창으로 정의하였다. 센서값의 기준 미달·동일·초과만으로 오탐지를 판정하지 않고, 점검 조건 충족 여부 × 정답 × AI 예측을 함께 비교하도록 하였다.", normal_style),
        ("창 단위 오탐지율은 정답이 정상인 창 중 위험 예측 비율이며, 경보 횟수와 별도로 집계한다. 운전 중 오경보는 정답이 정상이고 판정 가능한 시간에 경보가 새로 시작된 경우로 정의하고, 정상 유효 시간당 시작 횟수·경보 지속 비율·감지 지연·판정 가능 비율을 기록한다. 정답 미확인과 판정 불가를 정상으로 간주하지 않는다.", normal_style),
        ("두 모델은 점수 0.5 이상을 위험 예측으로 구분한다. 장비 점검은 연속 2회, 서지 활동은 1회 확인 후 경보를 시작한다. 점검 기준과 서지 정답은 따로 평가하여 고온이나 습도 상승을 곧바로 낙뢰로 해석하지 않았다.", normal_style),
        ("5. 데이터 확대와 학습·평가 결과", bold_style),
        ("데이터·시험 사례 확대 의견에 따라 합성 데이터 153,000행(85세션·17상황)을 구성하였다. 세션별로 학습 91,800행, 검증 30,600행, 시험 30,600행을 분리하였다. 최대 50회 학습과 검증 손실 기반 조기 종료를 적용하고, 서버 목적에 맞춰 크기 제한 없이 LSTM 32/64/128을 비교해 검증 성능으로 작업별 32유닛 모델을 선택하였다.", normal_style),
        ("작업별 시험 창 2,958개에서 장비 점검은 F1 0.9993·FP 0·FN 2, 서지 활동은 F1 1.0000·FP 0·FN 0이었다. 이는 창 단위 합성 시험 결과이며 실제 장비 고장·낙뢰 정확도로 해석하지 않는다.", normal_style),
        ("그림삽입2", caption_style),
        ("그림 2  합성 시험 세션 1,800행의 실제 LSTM 추론 점수", caption_style),
        ("6. 시연·오류 검증 및 향후 보완", bold_style),
        ("정상·서지만 발생·서지 없는 발열·동시 발생·카운터 리셋의 5개 상황을 실제 모델로 시연 검증하고, 자동 테스트 345개 통과를 확인하였다. 노트북용 설치·검증 도구와 전달 ZIP을 준비하였다. 0V 방향의 전압 응답은 가상 시험이며 실제 에너지 변환이나 보호 동작을 수행한 것은 아니다.", normal_style),
        ("향후 실측 데이터·독립 정답 확보, 장비별 기준과 전압 응답 확인, 실제 통신 연동, 잡음·복합 장애 사례 확대와 모델 재평가를 진행할 계획이다. 실제 노트북의 새 설치 환경 및 임베디드 탑재 검증도 추가로 필요하다.", normal_style),
    ]
    # Repeat the original body-page form so the cover plus two report pages
    # retain the reference geometry and blank attendance fields.
    continuation_title, continuation_form = deepcopy(paragraphs[23]), deepcopy(paragraphs[24])
    for node in (continuation_title, continuation_form):
        table = node["controls"][0]["Table"]
        common = bytearray.fromhex(table["common_data"])
        instance = int.from_bytes(common[32:36], "little")
        common[32:36] = (instance + 1024).to_bytes(4, "little")
        table["common_data"] = common.hex()
    paragraphs.extend([continuation_title, continuation_form])
    for cell, content in ((body, content_page1), (continuation_form["controls"][0]["Table"]["cells"][14], content_page2)):
        cell["paragraphs"] = []
        for value, char in content:
            paragraph = deepcopy(template)
            replace(paragraph, value, shape=0, char=char)
            cell["paragraphs"].append(paragraph)
    # Preserve all form tables and original page settings. Only the obsolete
    # body pictures are removed; the CLI inserts two new native picture objects.
    doc["bin_streams"] = []
    doc["header"]["bin_data"] = []
    doc["metadata"]["title"] = "그라운드 오픈랩 구직자 수행일지 5회차"
    doc["metadata"]["author"] = "방경식"
    doc["metadata"]["last_saved_by"] = "방경식"
    filetime = int((datetime.now(timezone.utc).timestamp() + 11644473600) * 10000000)
    doc["metadata"]["create_time"] = doc["metadata"]["modify_time"] = filetime
    def clear_cache(value):
        if isinstance(value, dict):
            if "line_segs" in value:
                value["line_segs"] = []
            for child in value.values():
                clear_cache(child)
        elif isinstance(value, list):
            for child in value:
                clear_cache(child)
    clear_cache(doc)
    (WORK / "report-5-base.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    run("new", "--from", WORK / "report-5-base.json", "-o", WORK / "report-5-base.hwp")
    run("edit", WORK / "report-5-base.hwp", "-o", WORK / "report-5-pictures.hwp", "--verify",
        "--insert-image", f"그림삽입1=>{WORK / 'flow.png'}@155x20",
        "--insert-image", f"그림삽입2=>{WORK / 'timeline.png'}@155x34")
    run("edit", WORK / "report-5-pictures.hwp", "-o", WORK / "report-5.hwp", "--verify",
        "--replace", "그림삽입1=>", "--replace", "그림삽입2=>")
    run("render", WORK / "report-5.hwp", "-o", WORK / "report-5.png", "--dpi", "150", "--font-dir", FONT_DIRS[0],
        "--report", WORK / "render-report.json", "--layout-json", WORK / "layout.json")
    run("render", WORK / "report-5.hwp", "-o", WORK / "report-5.pdf", "--font-dir", FONT_DIRS[0])
    (WORK / "report-content.txt").write_text("\n\n".join("\n".join(t for t, _c in page) for page in (content_page1, content_page2)), encoding="utf-8")
    originals = {str(ROOT.parent / f"그라운드 보고서 방경식 {n}회차.hwp"):
                 hashlib.sha256((ROOT.parent / f"그라운드 보고서 방경식 {n}회차.hwp").read_bytes()).hexdigest() for n in range(1, 5)}
    (WORK / "original-hashes.json").write_text(json.dumps(originals, ensure_ascii=False, indent=2), encoding="utf-8")
    run("convert", WORK / "report-5.hwp", "-o", WORK / "report-5-roundtrip.json", "--embed-bin")
    print("Revised report authored; inspect cover and both body pages before delivery.")


if __name__ == "__main__":
    main()
