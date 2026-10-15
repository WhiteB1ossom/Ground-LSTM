$ErrorActionPreference = 'Stop'
$root = (Resolve-Path '.').Path
$build = Join-Path $root 'artifacts/presentation4-build'
$preview = Join-Path $build 'preview'
$candidate = Join-Path $build 'candidate.pptx'
if (Test-Path -LiteralPath $candidate) { throw 'Candidate already exists.' }
[void](New-Item -ItemType Directory -Path $preview -Force)
$experiment = Join-Path $root 'artifacts/models/demo-20261005-233045'
$report = Get-Content -LiteralPath (Join-Path $experiment 'report.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($report.epochs_completed -ne 50 -or $report.models.lstm.test.false_positives -ne 46) { throw 'Unexpected experiment data' }
$hadPowerPoint = @(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app = New-Object -ComObject PowerPoint.Application
$deck = $null
function Color([string]$hex) {
    return [Convert]::ToInt32($hex.Substring(0,2),16) + 256*[Convert]::ToInt32($hex.Substring(2,2),16) + 65536*[Convert]::ToInt32($hex.Substring(4,2),16)
}
$navy = Color '11263E'
$ink = Color '142B40'
$muted = Color '52667A'
$blue = Color '1766AE'
$teal = Color '087E7D'
$red = Color 'BB3C38'
$white = Color 'FFFFFF'
function Text($slide, [string]$text, [double]$x, [double]$y, [double]$w, [double]$h, [double]$size=22, [int]$color=$ink, [bool]$bold=$false) {
    $shape = $slide.Shapes.AddTextbox(1,$x,$y,$w,$h)
    $shape.TextFrame.MarginLeft=0; $shape.TextFrame.MarginRight=0
    $shape.TextFrame.MarginTop=0; $shape.TextFrame.MarginBottom=0
    $shape.TextFrame.WordWrap=-1; $shape.TextFrame.AutoSize=0
    $range=$shape.TextFrame.TextRange
    $range.Text=$text
    $range.Font.Name='맑은 고딕'; $range.Font.NameFarEast='맑은 고딕'
    $range.Font.Size=$size; $range.Font.Color.RGB=$color
    $range.Font.Bold= $(if ($bold) {-1} else {0})
    $range.ParagraphFormat.SpaceAfter=8
    return $shape
}
function Slide([string]$title, [string]$footer='') {
    $s=$deck.Slides.Add($deck.Slides.Count+1,12)
    $s.FollowMasterBackground=0; $s.Background.Fill.Solid(); $s.Background.Fill.ForeColor.RGB=$white
    [void](Text $s $title 54 38 850 56 34 $navy $true)
    if ($footer) {[void](Text $s $footer 54 503 800 24 14 $muted)}
    [void](Text $s ('{0:D2}' -f $s.SlideIndex) 892 503 35 24 14 $muted)
    return $s
}
function Notes($slide,[string]$script,[string]$source) {
    foreach ($shape in $slide.NotesPage.Shapes) {
        if ($shape.Type -eq 14 -and $shape.PlaceholderFormat.Type -eq 2) {
            $shape.TextFrame.TextRange.Text=$script+"`r`r자료: "+$source
            return
        }
    }
    throw 'Notes body placeholder missing'
}
function Picture($slide,[string]$file,[double]$x,[double]$y,[double]$w,[double]$h) {
    Add-Type -AssemblyName System.Drawing
    $img=[System.Drawing.Image]::FromFile($file)
    try { $ratio=[Math]::Min($w/$img.Width,$h/$img.Height); $iw=$img.Width*$ratio; $ih=$img.Height*$ratio }
    finally { $img.Dispose() }
    [void]($slide.Shapes.AddPicture($file,0,-1,$x+($w-$iw)/2,$y+($h-$ih)/2,$iw,$ih))
}
function Table($slide,$rows,$widths,[double]$x,[double]$y,[double]$w,[double]$h,[double]$font=18) {
    $shape=$slide.Shapes.AddTable($rows.Count,$widths.Count,$x,$y,$w,$h)
    $table=$shape.Table
    for($c=1;$c -le $widths.Count;$c++) {$table.Columns.Item($c).Width=$widths[$c-1]}
    for($r=1;$r -le $rows.Count;$r++) {
        for($c=1;$c -le $widths.Count;$c++) {
            $cell=$table.Cell($r,$c).Shape
            $cell.TextFrame.MarginLeft=12; $cell.TextFrame.MarginRight=8
            $cell.TextFrame.MarginTop=4; $cell.TextFrame.MarginBottom=3
            $cell.TextFrame.VerticalAnchor=3
            $range=$cell.TextFrame.TextRange; $range.Text=[string]$rows[$r-1][$c-1]
            $range.Font.Name='맑은 고딕'; $range.Font.NameFarEast='맑은 고딕'; $range.Font.Size=$font
            $range.Font.Color.RGB= $(if($r -eq 1){$white}else{$ink})
            $range.Font.Bold= $(if($r -eq 1){-1}else{0})
            $cell.Fill.Solid(); $cell.Fill.ForeColor.RGB= $(if($r -eq 1){$navy}elseif($r%2 -eq 0){Color 'EEF4F8'}else{$white})
        }
    }
    return $shape
}
try {
    $deck=$app.Presentations.Add(0)
    $deck.PageSetup.SlideWidth=960; $deck.PageSetup.SlideHeight=540
    # 1: cover and continuity with week 3
    $s=$deck.Slides.Add(1,12)
    $s.FollowMasterBackground=0; $s.Background.Fill.Solid(); $s.Background.Fill.ForeColor.RGB=$navy
    [void](Text $s '그라운드 오픈랩 4회차' 60 64 830 38 22 (Color 'A9C8DE'))
    [void](Text $s "낙뢰방호장치`rLSTM 학습·성능 평가" 60 150 850 170 46 $white $true)
    [void](Text $s '합성 데이터 기반 구현 및 검증' 62 348 830 38 24 (Color 'C9D9E6'))
    [void](Text $s '청주대학교 방경식' 62 456 500 30 19 $white)
    [void](Text $s '2026. 10. 07.' 760 456 150 30 17 (Color 'C9D9E6'))
    Notes $s '안녕하세요. 방경식입니다. 이번 4회차에서는 낙뢰방호장치 센서 데이터를 분석하기 위한 LSTM 모델을 구현하고 실제 학습과 성능 평가를 진행했습니다. 3회차에서는 전처리 방법과 시계열 입력 구성을 검토했습니다. 이번에는 이를 프로그램으로 구현해 데이터를 입력하고 모델을 학습한 뒤 결과를 확인하는 단계까지 진행했습니다. 센서 기준, 학습 과정, 평가 결과와 현재 한계 순서로 말씀드리겠습니다.' '그라운드 보고서 방경식 3회차.hwp 및 이번 4회차 대본. 실험: artifacts/models/demo-20261005-233045/report.json'
    # 2: source table, editable and compact
    $s=Slide '표준 센서 범위와 기준값' '표의 기준값 기록 완료. 자동 판정용 의미·비교 방향은 확인 필요'
    $rows=@(
        @('센서','센싱 범위','Threshold / 비교값','측정 주기'),
        @('대지전위 a','0~50 V AC','2 (V AC 맥락)','100 ms'),
        @('대지전위 b','0~50 V AC','2 (V AC 맥락)','100 ms'),
        @('누설전류','0.001~1 A','1 mA = 0.001 A','1초'),
        @('제한소자 온도 a','25~150 ℃','25 ℃','60초'),
        @('제한소자 온도 b','25~150 ℃','25 ℃','60초'),
        @('제한소자 온도 c','25~150 ℃','25 ℃','60초'),
        @('상대습도','20~90%','60%','60분'),
        @('외기온도','-20~80 ℃','비교값','60분'),
        @('입력전압 AC','0~1500','사용전압 비교','1초'),
        @('번개센서','H/L','H=1, L=0','100 ms')
    )
    [void](Table $s $rows @(210,185,270,175) 54 110 840 343 17)
    [void](Text $s '온도 25 ℃: 절대온도인지 상승량인지 확인 필요' 54 463 840 30 17 $red)
    Notes $s '교육계획서 마지막 표에서 센서 범위, Threshold 기준값과 주기를 확인했습니다. 대지전위는 100밀리초, 제한소자 온도는 60초, 습도와 외기온도는 60분 주기입니다. 누설전류 기준 1밀리암페어는 입력 단위 A에 맞춰 0.001A로 기록했습니다. 온도 기준 25도가 절대온도인지 상승량인지는 확인이 필요해 자동 위험 판정에 적용하지 않았습니다. 이 표는 센서 사양이며 시간별 측정값과 정답 label은 포함하지 않습니다. 이번 실행은 별도 합성 데이터로 진행했습니다. 모든 행의 바이트 표기는 원문에서 5 bytes입니다. 입력전압 범위 셀에는 단위가 직접 적혀 있지 않습니다.' '그라운드_회차별 오픈랩 진행 계획_ver a_260909.pdf, 6페이지. configs/sensor_standard_reference.yaml'
    # 3: dataset
    $s=Slide '학습 데이터 구성' '이번 실행: 기존 합성 데모. 표준 프로파일의 재학습은 후속 검증'
    [void](Text $s '882개 시퀀스' 54 110 700 65 42 $blue $true)
    $rows=@(@('학습 Train','검증 Validation','평가 Test'),@('441개','147개','294개'))
    [void](Table $s $rows @(280,280,280) 54 198 840 94 23)
    [void](Text $s '16개 시점 × 20개 특징' 54 325 840 42 28 $ink $true)
    [void](Text $s "100 ms 간격, 약 1.6초 입력`r이벤트 분리와 train-only 정규화" 54 384 840 86 23 $muted)
    Notes $s '데이터를 train 441개, validation 147개, test 294개로 나눴습니다. 합계 882개는 원본 행 수나 낙뢰 횟수가 아니라 전처리 후 입력 시퀀스 개수입니다. 각 입력은 100밀리초 간격의 16개 시점과 센서값, 결측 표시를 포함한 20개 특징으로 구성했습니다. 같은 이벤트가 서로 다른 분할에 섞이지 않도록 했고 정규화 기준은 train에서만 계산했습니다. 일부 시퀀스가 겹쳐 서로 독립적인 882개 사례는 아닙니다. 이번 실행은 기존 1.6초 데모입니다. 표준 프로파일에는 64개 시점과 측정값 나이를 사용하는 초기 설계를 추가했지만 그 프로파일로 실측 재학습을 완료하지는 않았습니다.' 'data/processed/phase3-training-demo/manifest.json, feature_order.json 및 artifacts/models/demo-20261005-233045/report.json'
    # 4: actual training screenshot
    $s=Slide 'LSTM 구조와 학습 실행' '화면의 val_f1은 validation 지표. 최종 성능은 별도 test로 평가'
    Picture $s (Join-Path $root '스크린샷 2026-10-05 233228.png') 54 121 560 337
    [void](Text $s '단방향 LSTM' 654 120 255 45 25 $blue $true)
    [void](Text $s "Hidden 16, 1 layer`rAdam 0.001`rBatch 32`r최대 50 epochs" 654 183 255 178 23 $ink)
    [void](Text $s "학습률 자동 감소`rEarly stopping" 654 387 255 76 20 $muted)
    Notes $s '이 화면은 실제 LSTM 학습 로그입니다. Hidden unit 16개, 단방향 LSTM 한 계층과 정상·위험을 구분하는 이진 출력을 구성했습니다. Adam 초기 학습률 0.001, batch size 32를 사용했습니다. 최대 50회 학습하며 validation loss가 정체되면 학습률을 줄이고 계속 개선이 없으면 조기 종료하도록 구성했습니다. 이번에는 마지막까지 validation loss가 개선되어 50회 완료했습니다. 화면의 val_f1 1.0은 validation 결과이며 최종 test F1과 평가 대상이 다릅니다.' '사용자 제공: 스크린샷 2026-10-05 233228.png. configs/model_demo.yaml 및 실험 report.json'
    # 5: original training / PR figure
    $s=Slide '학습 곡선과 PR 곡선' '50회까지 validation loss 개선. 최대 횟수 도달은 수렴 보장이 아님'
    Picture $s (Join-Path $experiment 'loss-and-pr.png') 54 103 850 340
    [void](Text $s '최종 Train loss  0.021' 65 456 410 32 20 $blue $true)
    [void](Text $s '최종 Validation loss  0.019' 500 456 410 32 20 $teal $true)
    Notes $s '왼쪽 그래프의 train loss는 약 0.676에서 0.021로, validation loss는 0.629에서 0.019로 감소했습니다. 두 곡선이 함께 내려가 합성 데이터에 대한 학습이 진행됨을 확인했습니다. 마지막까지 개선되었기 때문에 50회가 최적 횟수라고 확정하지는 않았습니다. 오른쪽 test PR 곡선의 LSTM PR-AUC는 약 0.9994입니다. 높은 면적만으로 개별 판정의 오경보가 없다고 볼 수 없어 혼동행렬과 FN, FP를 함께 확인합니다. 판단 임계값은 validation에서 선택해 test에는 고정했습니다.' 'artifacts/models/demo-20261005-233045/loss-and-pr.png, history.json, report.json. 이 그림은 합성 데이터 실험 결과입니다.'
    # 6: LSTM result
    $s=Slide 'LSTM의 미탐지와 오경보' '합성 test 294개 시퀀스. 위험 90개, 정상 204개'
    Picture $s (Join-Path $experiment 'lstm-confusion.png') 54 108 402 366
    [void](Text $s '미탐지 0개' 507 116 388 55 36 $teal $true)
    [void](Text $s '오경보 46개' 507 185 388 55 36 $red $true)
    [void](Text $s '정상 중 오경보 22.55%' 509 252 384 36 23 $red)
    $rows=@(@('Precision','Recall','F1'),@('66.18%','100%','79.65%'))
    [void](Table $s $rows @(128,128,128) 508 323 384 88 18)
    [void](Text $s '위험 판단 136개 중 실제 위험 90개' 509 434 384 43 19 $muted)
    Notes $s '실제 정상 시퀀스 204개 중 158개를 정상으로 판단했고 46개를 위험으로 판단했습니다. 실제 위험 시퀀스 90개는 모두 위험으로 판단해 이번 test에서 미탐지는 0개입니다. Recall은 100%, Precision은 66.18%, F1은 79.65%입니다. 위험 판단 136개 중 실제 위험은 90개이고 나머지 46개는 오경보입니다. 정상 구간에 대한 오경보 비율은 46 나누기 204로 약 22.55%입니다. Recall만으로 모델의 성능이 충분하다고 판단할 수 없으며 오경보 개선이 필요합니다. 여기서 개수는 시퀀스 수이며 실제 낙뢰 횟수가 아닙니다.' 'artifacts/models/demo-20261005-233045/lstm-confusion.png 및 report.json models.lstm.test'
    # 7: baseline comparison
    $s=Slide 'Logistic Regression과 비교' '이번 합성 데이터에서 LSTM의 추가 복잡성이 주는 이점은 미확인'
    Picture $s (Join-Path $experiment 'logistic-confusion.png') 54 111 365 352
    $rows=@(@('모델','F1','FN','FP'),@('Logistic','1.0000','0','0'),@('LSTM','0.7965','0','46'))
    [void](Table $s $rows @(165,110,100,100) 447 151 475 148 19)
    [void](Text $s 'Validation 점수 동률' 447 339 460 38 25 $blue $true)
    [void](Text $s '단순한 Logistic 모델 우선 추천' 447 391 460 72 24 $ink)
    Notes $s 'Logistic Regression은 이번 합성 데이터에서 test 시퀀스를 모두 올바르게 분류했습니다. Validation에서도 두 모델의 점수가 같아 단순한 Logistic Regression을 추천했습니다. 추천은 test 결과를 보고 선택한 것이 아닙니다. 이번 실험으로 LSTM이 더 우수하다는 결론을 내릴 수는 없습니다. 실제 데이터에서도 동일한 조건으로 비교하여 시간 패턴을 학습하는 LSTM의 이점이 있는지 검증해야 합니다. 일반화된 실제 장치 성능을 주장하는 결과는 아닙니다.' 'artifacts/models/demo-20261005-233045/logistic-confusion.png 및 report.json validation_recommendation, models'
    # 8: implementation achievements and boundaries
    $s=Slide '구현 성과와 검증 범위'
    [void](Text $s '구현·동작 검증' 54 119 405 45 28 $blue $true)
    [void](Text $s "자동 테스트 125개 통과`r모델 저장·재평가 일치`r링 버퍼·시퀀스 생성 구현" 54 190 410 160 24 $ink)
    [void](Text $s '현재 데이터의 한계' 516 119 400 45 28 $red $true)
    [void](Text $s "합성 데이터 실험`rTest 위험 이벤트 그룹 2개`r겹치는 시퀀스 포함" 516 190 395 160 24 $ink)
    [void](Text $s '기능 검증 완료, 실제 낙뢰 성능은 실측 평가 필요' 54 405 855 64 26 $navy $true)
    Notes $s '학습과 평가가 정상 작동하는 프로토타입을 구현했습니다. 전체 자동 테스트 125개가 통과했고 저장한 모델을 다시 불러온 평가 결과도 일치했습니다. 링 버퍼는 고정 크기로 최신 특징을 유지하고 유효한 시퀀스를 생성하는 기능까지 구현했습니다. 다만 이번 데이터는 합성 데이터이고 test 위험 이벤트 그룹이 두 개뿐입니다. 위험 시퀀스 90개는 독립적인 실제 낙뢰 사례 90개가 아닙니다. 현재 데이터는 학습·평가 프로그램의 기능 검증에 의미가 있으며 실제 낙뢰 감지 성능의 근거로는 추가 실측 평가가 필요합니다.' 'docs/training-design.md 및 artifacts/reports/training-design-verification.json. 실험 report.json의 event_summary, synthetic_demo'
    # 9: next steps aligned with embedded target
    $s=Slide '실측 검증과 임베디드 적용'
    [void](Text $s '실측 검증' 54 117 850 43 28 $blue $true)
    [void](Text $s "표준 단위·주기와 정답 label 확인`r동일 조건에서 두 모델 재학습·오경보 비교" 54 181 850 94 25 $ink)
    [void](Text $s '임베디드 적용' 54 310 850 43 28 $blue $true)
    [void](Text $s "모델 경량화·변환 및 링 버퍼 연결`rMCU 메모리와 실행시간 실측" 54 374 850 94 25 $ink)
    Notes $s '앞으로는 실제 측정 데이터와 확인된 정답 label, 센서 기준값의 의미를 바탕으로 표준 설정에 맞춰 전처리와 학습을 다시 진행하겠습니다. 표준 프로파일의 6.4초 입력은 검증할 초기 후보이며 확정된 최적 길이가 아닙니다. 온습도와 같은 느린 센서는 현재 상태와 측정값 나이를 사용하며 긴 시간 추세를 학습하려면 별도 맥락이 필요합니다. 이후에는 모델 경량화와 TFLite 또는 TFLite Micro 변환, 링 버퍼와 추론 연결을 검토하고 목표 MCU에서 메모리와 실행시간을 실제로 측정하겠습니다. 이번 4회차에서는 전처리 계획을 실제 학습·평가 프로그램으로 발전시키고 결과와 한계를 확인하는 단계까지 수행했습니다. 이상으로 발표를 마치겠습니다.' 'docs/training-design.md, docs/sensor-standard.md 및 대화에서 확인한 임베디드 최종 목표. 후속 계획이며 완료 성과가 아닙니다.'
    $deck.SaveAs($candidate,24)
    $deck.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck); $deck=$null
    # Reopen the saved file in PowerPoint to inspect and render its actual content.
    $deck=$app.Presentations.Open($candidate,-1,0,0)
    if($deck.Slides.Count -ne 9) {throw 'Slide count mismatch'}
    $deck.Export($preview,'PNG',1600,900)
    $notesPath=Join-Path $build 'notes.txt'
    $notes=@()
    foreach($slide in $deck.Slides) {
        $notes += "SLIDE $($slide.SlideIndex)"
        foreach($shape in $slide.NotesPage.Shapes) {
            if($shape.Type -eq 14 -and $shape.PlaceholderFormat.Type -eq 2) {$notes += $shape.TextFrame.TextRange.Text}
        }
    }
    $notes | Set-Content -LiteralPath $notesPath -Encoding UTF8
    Write-Output "Created and reopened in PowerPoint: $candidate"
    Write-Output "Rendered: $($deck.Slides.Count) slides"
} finally {
    if($null -ne $deck) {$deck.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck)}
    if(-not $hadPowerPoint) {$app.Quit()}
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
