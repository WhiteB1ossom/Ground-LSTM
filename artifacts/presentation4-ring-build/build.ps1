$ErrorActionPreference='Stop'
$root=(Resolve-Path '.').Path
$source=Join-Path $root 'output/presentations/그라운드_4회차_LSTM_학습평가_방경식.pptx'
$build=Join-Path $root 'artifacts/presentation4-ring-build'
$candidate=Join-Path $build 'candidate.pptx'
if(Test-Path -LiteralPath $candidate){throw 'Candidate already exists'}
$sourceHash=(Get-FileHash -LiteralPath $source).Hash
$report=Get-Content -LiteralPath (Join-Path $root 'artifacts/reports/ring-buffer-demo.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if($report.replayed_samples -ne 3600 -or $report.buffer_capacity -ne 66 -or $report.status_counts.READY -ne 882 -or $report.buffer_storage_bytes -ne 5874 -or $report.model_inference_performed){throw 'Unexpected ring demo data'}
$hadPowerPoint=@(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app=New-Object -ComObject PowerPoint.Application
$deck=$null
function RGB([string]$hex){return [Convert]::ToInt32($hex.Substring(0,2),16)+256*[Convert]::ToInt32($hex.Substring(2,2),16)+65536*[Convert]::ToInt32($hex.Substring(4,2),16)}
$navy=RGB '11263E';$ink=RGB '142B40';$white=RGB 'FFFFFF';$blue=RGB '1766AE';$teal=RGB '087E7D';$muted=RGB '52667A'
function Text($slide,[string]$text,[double]$x,[double]$y,[double]$w,[double]$h,[double]$size=22,[int]$color=$ink,[bool]$bold=$false){
    $shape=$slide.Shapes.AddTextbox(1,$x,$y,$w,$h)
    $shape.TextFrame.MarginLeft=0;$shape.TextFrame.MarginRight=0
    $shape.TextFrame.MarginTop=0;$shape.TextFrame.MarginBottom=0
    $shape.TextFrame.WordWrap=-1;$shape.TextFrame.AutoSize=0
    $range=$shape.TextFrame.TextRange;$range.Text=$text
    $range.Font.Name='맑은 고딕';$range.Font.NameFarEast='맑은 고딕';$range.Font.Size=$size
    $range.Font.Color.RGB=$color;$range.Font.Bold=$(if($bold){-1}else{0})
    $range.ParagraphFormat.SpaceAfter=8
    return $shape
}
function Slide([int]$index,[string]$title,[string]$footer){
    $s=$deck.Slides.Add($index,12)
    $s.FollowMasterBackground=0;$s.Background.Fill.Solid();$s.Background.Fill.ForeColor.RGB=$white
    [void](Text $s $title 54 38 850 56 34 $navy $true)
    [void](Text $s $footer 54 503 800 24 14 $muted)
    [void](Text $s '00' 892 503 35 24 14 $muted)
    return $s
}
function Table($slide,$rows,$widths,[double]$x,[double]$y,[double]$w,[double]$h,[double]$font=22){
    $shape=$slide.Shapes.AddTable($rows.Count,$widths.Count,$x,$y,$w,$h)
    $table=$shape.Table
    for($c=1;$c -le $widths.Count;$c++){$table.Columns.Item($c).Width=$widths[$c-1]}
    for($r=1;$r -le $rows.Count;$r++){
        for($c=1;$c -le $widths.Count;$c++){
            $cell=$table.Cell($r,$c).Shape
            $cell.TextFrame.MarginLeft=14;$cell.TextFrame.MarginRight=10
            $cell.TextFrame.MarginTop=5;$cell.TextFrame.MarginBottom=4;$cell.TextFrame.VerticalAnchor=3
            $range=$cell.TextFrame.TextRange;$range.Text=[string]$rows[$r-1][$c-1]
            $range.Font.Name='맑은 고딕';$range.Font.NameFarEast='맑은 고딕';$range.Font.Size=$font
            $range.Font.Color.RGB=$(if($r -eq 1){$white}else{$ink});$range.Font.Bold=$(if($r -eq 1){-1}else{0})
            $cell.Fill.Solid();$cell.Fill.ForeColor.RGB=$(if($r -eq 1){$navy}elseif($r%2 -eq 0){RGB 'EEF4F8'}else{$white})
        }
    }
}
function Notes($slide,[string]$script,[string]$sourceText){
    foreach($shape in $slide.NotesPage.Shapes){
        if($shape.Type -eq 14 -and $shape.PlaceholderFormat.Type -eq 2){
            $shape.TextFrame.TextRange.Text=$script+"`r`r자료: "+$sourceText
            return
        }
    }
    throw 'Speaker notes placeholder missing'
}
try {
    $deck=$app.Presentations.Open($source,-1,0,0)
    if($deck.Slides.Count -ne 9){throw 'Source slide count changed'}
    $deck.SaveAs($candidate,24)
    $cover=$deck.Slides.Item(1)
    foreach($shape in $cover.Shapes){
        if($shape.HasTextFrame -eq -1 -and $shape.TextFrame.HasText -eq -1){
            $range=$shape.TextFrame.TextRange
            if($range.Text.Contains('LSTM 학습·성능 평가')){$range.Text=$range.Text.Replace('LSTM 학습·성능 평가','LSTM 학습·평가와 링 버퍼')}
        }
    }
    foreach($shape in $cover.NotesPage.Shapes){
        if($shape.Type -eq 14 -and $shape.PlaceholderFormat.Type -eq 2){
            $range=$shape.TextFrame.TextRange
            $range.Text=$range.Text.Replace('센서 기준, 학습 과정, 평가 결과와 현재 한계 순서로 말씀드리겠습니다.','센서 기준과 데이터 구성, 링 버퍼의 역할, 학습 과정과 평가 결과 순서로 말씀드리겠습니다.')
        }
    }
    $s=Slide 4 '링 버퍼의 역할' '전처리한 특징을 고정 공간에 저장. 표는 샘플 번호로 설명한 동작 예시'
    [void](Text $s '고정 66개 보관, 최신 16개로 입력 생성' 54 119 850 54 29 $blue $true)
    $rows=@(@('동작 예시','새 입력 전','새 입력 후'),@('버퍼 보관 샘플','1~66','2~67'),@('최신 입력 16개','51~66','52~67'))
    Table $s $rows @(320,260,260) 54 200 840 168 23
    [void](Text $s '67번이 들어오면 가장 오래된 1번 자리 사용' 54 411 840 45 25 $ink)
    Notes $s '링 버퍼는 최근 센서 데이터를 일정한 크기의 공간에 유지하는 구조입니다. 이 프로젝트에서는 전처리하고 정규화한 특징과 timestamp, 유효성 정보를 저장합니다. 새 데이터가 들어오면 가장 오래된 데이터의 자리를 사용하므로 저장 배열이 계속 커지지 않습니다. 표는 동작을 설명하기 위해 붙인 샘플 번호입니다. 1번부터 66번까지 보관하다가 67번이 들어오면 1번을 덮어쓰고 2번부터 67번을 유지합니다. 입력 시퀀스도 최신 16개인 52번부터 67번으로 바뀝니다. 데모 용량 66개는 입력 16개와 100밀리초 간격의 과거 5초분인 50개를 합한 값입니다. 실제 운용값은 센서 데이터와 MCU 예산에 맞춰 결정해야 합니다. 최신 16개가 유효하고 시간 간격이 맞을 때 SequenceBuilder가 입력을 준비합니다.' 'src/realtime/ring_buffer.py, src/realtime/sequence_builder.py, configs/realtime_demo.yaml, docs/ring-buffer-usage.md. 1~67은 구조 설명용 번호이며 측정값이나 위험 label이 아닙니다.'
    $s=Slide 5 '링 버퍼 실행·검증 결과' 'PC 합성 CSV 데모. 배열 메모리만 집계하며 모델 추론·MCU 검증은 후속 단계'
    [void](Text $s '3,600개 샘플 재생' 54 119 430 50 30 $blue $true)
    [void](Text $s '최대 66개 유지' 530 119 380 50 30 $teal $true)
    $rows=@(@('확인 항목','실행 결과'),@('준비된 입력 시퀀스','882개'),@('입력 텐서 크기','1 × 16 × 20'),@('오래된 샘플 덮어쓰기','3,204회'),@('버퍼 배열 메모리','5,874 bytes'))
    Table $s $rows @(510,330) 54 192 840 239 22
    [void](Text $s '데이터 부족·무효 입력·시간 간격 오류 검사' 54 453 840 38 20 $muted)
    Notes $s '링 버퍼 데모에서는 합성 CSV의 3,600개 샘플을 재생했습니다. 새 데이터가 계속 들어와도 버퍼에는 최대 66개만 남았고, 오래된 샘플을 3,204회 덮어썼습니다. SequenceBuilder는 882개의 입력 시퀀스를 준비했으며 입력 크기는 1, 16, 20입니다. 버퍼 배열의 데이터 크기는 5,874바이트입니다. 이 숫자에는 Python 객체, 전처리, 모델과 MCU 실행 메모리가 포함되지 않습니다. 데이터가 충분하지 않거나, 최신 구간에 무효 입력 또는 시간 간격 오류가 있으면 준비 완료 상태를 내보내지 않도록 구현하고 테스트했습니다. 이번 데모의 6개 합성 구간은 이벤트 경계에서 입력 상태를 초기화했습니다. 실제 연속 수신에서는 데이터 획득 재시작 같은 명시적 경계를 사용해 검증해야 합니다. 현재 완료 범위는 최근 데이터를 유지하고 모델에 전달할 입력을 준비하는 기능입니다. 모델 추론, 위험 판단과 자동 이벤트 기록 연결은 다음 단계입니다.' 'artifacts/reports/ring-buffer-demo.json, docs/ring-buffer-usage.md, tests/test_ring_buffer.py. 별도 Phase 2 합성 입력 데모이며 학습된 모델의 실시간 추론 결과가 아닙니다.'
    foreach($slide in $deck.Slides){
        if($slide.SlideIndex -eq 1){continue}
        foreach($shape in $slide.Shapes){
            if($shape.HasTextFrame -eq -1 -and $shape.Left -ge 880 -and $shape.Top -ge 495 -and $shape.Width -le 45){
                $shape.TextFrame.TextRange.Text=('{0:D2}' -f $slide.SlideIndex)
            }
        }
    }
    if($deck.Slides.Count -ne 11){throw 'Unexpected final slide count'}
    $deck.Save();$deck.Close();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck);$deck=$null
    $deck=$app.Presentations.Open($candidate,-1,0,0)
    $preview=Join-Path $build 'preview';[void](New-Item -ItemType Directory -Path $preview -Force)
    $deck.Export($preview,'PNG',1600,900)
    if((Get-FileHash -LiteralPath $source).Hash -ne $sourceHash){throw 'Source changed'}
    Write-Output "Saved, reopened and rendered $($deck.Slides.Count) slides: $candidate"
} finally {
    if($null -ne $deck){$deck.Close();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck)}
    if(-not $hadPowerPoint){$app.Quit()}
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
