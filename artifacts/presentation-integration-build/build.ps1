$ErrorActionPreference='Stop'
$root=(Resolve-Path '.').Path
$build=Join-Path $root 'artifacts/presentation-integration-build'
$source=Join-Path $root 'output/presentations/그라운드_4회차_LSTM_링버퍼_추가_방경식.pptx'
$candidate=Join-Path $build 'candidate-v5.pptx'
if(Test-Path -LiteralPath $candidate){throw 'Candidate exists'}
$sourceHash=(Get-FileHash -LiteralPath $source).Hash
$data=Get-Content (Join-Path $build 'content.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$hadPowerPoint=@(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$hadExcel=@(Get-Process EXCEL -ErrorAction SilentlyContinue).Count -gt 0
$app=New-Object -ComObject PowerPoint.Application
$excelApp=New-Object -ComObject Excel.Application
if(-not $hadExcel){$excelApp.Visible=$false}
$keepAliveWorkbook=$excelApp.Workbooks.Add()
$deck=$null
function RGB([string]$hex){return [Convert]::ToInt32($hex.Substring(0,2),16)+256*[Convert]::ToInt32($hex.Substring(2,2),16)+65536*[Convert]::ToInt32($hex.Substring(4,2),16)}
$navy=RGB '11263E';$ink=RGB '142B40';$white=RGB 'FFFFFF';$blue=RGB '1766AE';$teal=RGB '087E7D';$muted=RGB '52667A';$red=RGB 'B34B47';$pale=RGB 'EEF4F8'
function Text($s,[string]$text,[double]$x,[double]$y,[double]$w,[double]$h,[double]$size=22,[int]$color=$ink,[bool]$bold=$false){
 $sh=$s.Shapes.AddTextbox(1,$x,$y,$w,$h)
 $sh.TextFrame.MarginLeft=0;$sh.TextFrame.MarginRight=0;$sh.TextFrame.MarginTop=0;$sh.TextFrame.MarginBottom=0
 $sh.TextFrame.WordWrap=-1;$sh.TextFrame.AutoSize=0
 $r=$sh.TextFrame.TextRange;$r.Text=$text;$r.Font.Name='맑은 고딕';$r.Font.NameFarEast='맑은 고딕';$r.Font.Size=$size;$r.Font.Color.RGB=$color;$r.Font.Bold=$(if($bold){-1}else{0});$r.ParagraphFormat.SpaceAfter=8
 return $sh
}
function Notes($s){
 foreach($sh in $s.NotesPage.Shapes){if($sh.Type -eq 14 -and $sh.PlaceholderFormat.Type -eq 2){$sh.TextFrame.TextRange.Text=$data.notes[$s.SlideIndex-1]+"`r`r자료: "+$data.sources[$s.SlideIndex-1];return}}
 throw 'Missing notes placeholder'
}
function Slide([string]$title,[string]$footer){
 $s=$deck.Slides.Add($deck.Slides.Count+1,12);$s.FollowMasterBackground=0;$s.Background.Fill.Solid();$s.Background.Fill.ForeColor.RGB=$white
 [void](Text $s $title 54 38 850 56 34 $navy $true)
 [void](Text $s $footer 54 503 820 24 14 $muted)
 [void](Text $s ('{0:D2}' -f $s.SlideIndex) 892 503 35 24 14 $muted)
 return $s
}
function Table($s,$rows,$widths,[double]$x,[double]$y,[double]$w,[double]$h,[double]$font=22){
 $sh=$s.Shapes.AddTable($rows.Count,$widths.Count,$x,$y,$w,$h);$table=$sh.Table
 for($c=1;$c -le $widths.Count;$c++){$table.Columns.Item($c).Width=$widths[$c-1]}
 for($r=1;$r -le $rows.Count;$r++){for($c=1;$c -le $widths.Count;$c++){
  $cell=$table.Cell($r,$c).Shape;$cell.TextFrame.MarginLeft=12;$cell.TextFrame.MarginRight=8;$cell.TextFrame.MarginTop=5;$cell.TextFrame.MarginBottom=4;$cell.TextFrame.VerticalAnchor=3
  $txt=$cell.TextFrame.TextRange;$txt.Text=[string]$rows[$r-1][$c-1];$txt.Font.Name='맑은 고딕';$txt.Font.NameFarEast='맑은 고딕';$txt.Font.Size=$font;$txt.Font.Color.RGB=$(if($r -eq 1){$white}else{$ink});$txt.Font.Bold=$(if($r -eq 1){-1}else{0})
  $cell.Fill.Solid();$cell.Fill.ForeColor.RGB=$(if($r -eq 1){$navy}elseif($r%2 -eq 0){$pale}else{$white})
 }}
 return $sh
}
function Curve($s,$series,[string]$title,[string]$xlabel,[string]$ylabel,[double]$x,[double]$y,[double]$w,[double]$h,[double]$xmax,[double]$ymax,[bool]$small=$false){
 $sh=$s.Shapes.AddChart2(-1,75,$x,$y,$w,$h,$false);$chart=$sh.Chart;[void]$chart.ChartData.Activate();$book=$null
 for($attempt=0;$attempt -lt 20;$attempt++){
  $book=$chart.ChartData.Workbook
  if($null -ne $book -and $null -ne $book.Worksheets){break}
  Start-Sleep -Milliseconds 250
 }
 if($null -eq $book -or $null -eq $book.Worksheets){throw 'PowerPoint chart workbook failed to initialize'}
 try{
  $sheet=$book.Worksheets.Item(1);$sheet.Name='Data';[void]$sheet.Cells.Clear()
  $n=1+($series | ForEach-Object {$_.x.Count} | Measure-Object -Maximum).Maximum;$matrix=New-Object 'object[,]' $n,4
  for($j=0;$j -lt 2;$j++){$matrix[0,(2*$j)]=$xlabel;$matrix[0,(2*$j+1)]=$series[$j].name
   for($i=0;$i -lt $series[$j].x.Count;$i++){$matrix[($i+1),(2*$j)]=[double]$series[$j].x[$i];$matrix[($i+1),(2*$j+1)]=[double]$series[$j].y[$i]}}
  $sheet.Range('A1:D'+$n).Value2=$matrix
  while($chart.SeriesCollection().Count -gt 0){$chart.SeriesCollection(1).Delete()}
  for($j=0;$j -lt 2;$j++){$r=$chart.SeriesCollection().NewSeries();$a=@('A','C')[$j];$b=@('B','D')[$j];$last=$series[$j].x.Count+1
   $r.Name=('=Data!$'+$b+'$1');$r.XValues=('=Data!$'+$a+'$2:$'+$a+'$'+$last);$r.Values=('=Data!$'+$b+'$2:$'+$b+'$'+$last)
   $r.Format.Line.ForeColor.RGB=$(if($j -eq 0){$blue}else{$teal});$r.Format.Line.Weight=2;$r.MarkerStyle=-4142
   if($small -and $j -eq 1){$r.Format.Line.DashStyle=4}
  }
  $chart.HasTitle=(-not $small);if(-not $small){$chart.ChartTitle.Text=$title;$chart.ChartTitle.Format.TextFrame2.TextRange.Font.Name='맑은 고딕';$chart.ChartTitle.Format.TextFrame2.TextRange.Font.Size=21}
  $chart.HasLegend=(-not $small);if(-not $small){$chart.Legend.Position=-4107;$chart.Legend.Font.Name='맑은 고딕';$chart.Legend.Font.Size=16}
  $chart.ChartArea.Font.Name='맑은 고딕';$chart.ChartArea.Font.Size=$(if($small){13}else{16});$chart.ChartArea.Format.Line.Visible=0;$chart.ChartArea.Format.Fill.ForeColor.RGB=$white
  foreach($axisType in @(1,2)){$axis=$chart.Axes($axisType,1);$axis.MinimumScale=0;$axis.MaximumScale=$(if($axisType -eq 1){$xmax}else{$ymax})
   $axis.HasTitle=(-not $small);if(-not $small){$axis.AxisTitle.Text=$(if($axisType -eq 1){$xlabel}else{$ylabel});$axis.AxisTitle.Font.Name='맑은 고딕';$axis.AxisTitle.Font.Size=17}
   $axis.TickLabels.Font.Name='맑은 고딕';$axis.TickLabels.Font.Size=$(if($small){12}else{15});$axis.TickLabels.NumberFormat=$(if($axisType -eq 1 -and $xmax -gt 1){'0'}else{'0.0'})}
  $chart.Axes(2,1).HasMajorGridlines=$true;$chart.Axes(2,1).MajorGridlines.Format.Line.ForeColor.RGB=RGB 'E1E8EF'
  [void]$book.Close($true);$book=$null
 }finally{if($null -ne $book){[void]$book.Close($true);$book=$null}}
}
function Strip($s,[string]$label,$spans,[double]$y,[int]$color){
 [void](Text $s $label 54 $y 118 23 16 $muted)
 $x=228;$width=659
 $base=$s.Shapes.AddShape(1,$x,$y+3,$width,14);$base.Fill.ForeColor.RGB=$pale;$base.Line.Visible=0
 foreach($span in $spans){$sh=$s.Shapes.AddShape(1,$x+$width*[double]$span[0]/60,$y+3,[Math]::Max(.5,$width*([double]$span[1]-[double]$span[0])/60),14);$sh.Fill.ForeColor.RGB=$color;$sh.Line.Visible=0}
}
try{
 $app.Visible=-1;$deck=$app.Presentations.Open($source,-1,0,-1);$deck.SaveAs($candidate,24)
 if($deck.PageSetup.SlideWidth -ne 960 -or $deck.PageSetup.SlideHeight -ne 540){throw 'Unexpected reference canvas'}
 while($deck.Slides.Count -gt 0){$deck.Slides.Item($deck.Slides.Count).Delete()}
 $s=$deck.Slides.Add(1,12);$s.FollowMasterBackground=0;$s.Background.Fill.Solid();$s.Background.Fill.ForeColor.RGB=$navy
 [void](Text $s '그라운드 오픈랩 · 통합 개발' 60 64 830 38 22 (RGB 'A9C8DE'))
 [void](Text $s "낙뢰방호장치`r실시간 추론과 이벤트 기록" 60 150 850 170 43 $white $true)
 [void](Text $s '합성 데이터 기반 PC 구현·검증' 62 348 830 38 24 (RGB 'C9D9E6'))
 [void](Text $s '청주대학교 방경식' 62 456 500 30 19 $white)
 [void](Text $s '2026. 10. 12.' 760 456 150 30 17 (RGB 'C9D9E6'));Notes $s
 $s=Slide '센서 범위와 판정 기준' '자료 숫자 보존. 위험 방향·온도 기준이 미확정이므로 물리 규칙 비활성'
 $rows=@(@('센서','센싱 범위','자료 기준값','확인할 의미'),@('대지전위 a','0~50 V AC','2','초과 / 미달'),@('대지전위 b','0~50 V AC','2','초과 / 미달'),@('누설전류','0.001~1 A','0.001 A','초과 / 미달'),@('제한소자 온도 a','25~150 ℃','25 ℃','절대 / 상승량'),@('제한소자 온도 b','25~150 ℃','25 ℃','절대 / 상승량'),@('제한소자 온도 c','25~150 ℃','25 ℃','절대 / 상승량'),@('상대습도','20~90%','60%','초과 / 미달'),@('외기온도','−20~80 ℃','비교값','온도 기준'),@('입력전압 AC','0~1500','사용전압 비교','단위 / 정격'),@('번개센서','H/L','H=1, L=0','정답 의미'))
 [void](Table $s $rows @(220,200,210,210) 54 112 840 348 17)
 [void](Text $s '센싱 범위 · 위험 규칙 · 정답 · AI 임계값을 따로 관리' 54 470 840 24 17 $blue $true);Notes $s
 $s=Slide '확대 데이터 구성' '합성 소프트웨어 시험. 겹치는 입력 창을 독립적인 사건 수로 해석하지 않음'
 [void](Text $s '42,000행 + 별도 2시간 정상 입력' 54 113 850 50 31 $blue $true)
 $rows=@(@('학습·평가 원본','오류 검증 원본','정상 연속 시험'),@('36,000행 / 60세션','6,000행 / 10세션','72,000행 / 2시간'))
 [void](Table $s $rows @(280,280,280) 54 185 840 105 21)
 $rows=@(@('Train','Validation','Test'),@('4,860개 창','1,620개 창','1,620개 창'))
 [void](Table $s $rows @(280,280,280) 54 315 840 102 22)
 [void](Text $s '정상 잡음 · 경계 값 · 단일/복합 변화 · 위험/회복' 54 447 840 35 22 $muted);Notes $s
 $s=Slide '링 버퍼와 이벤트 기록' '최근 특징은 고정 배열에 저장. 원본 관측은 별도 제한된 기록에 보존'
 [void](Text $s '114개 보관 → 최신 64개로 추론' 54 113 850 52 31 $blue $true)
 $rows=@(@('동작 예시','새 입력 전','새 입력 후'),@('버퍼 보관','1~114','2~115'),@('모델 입력 64개','51~114','52~115'))
 [void](Table $s $rows @(320,260,260) 54 186 840 163 23)
 [void](Text $s '경보 전 5초 + 경보 후 2초 자동 기록' 54 379 840 39 26 $teal $true)
 [void](Text $s '입력 유효성 검사 · 별도 writer · 큐/파일 수 제한' 54 443 840 34 22 $muted);Notes $s
 $s=Slide '실제 재생 타임라인' '합성 Test 세션. 데이터 시각 기준이며 실제 센서 전송 지연·MCU 시간과 다름'
 [void](Text $s '대지전위 a (V)' 54 115 165 30 18 $blue $true)
 [void](Text $s '점선: 자료 기준 2 V (자동 위험 규칙 미적용)' 360 105 530 26 16 $muted)
 $ymax=[Math]::Max(3,1.15*($data.timeline.sensor[0].y | Measure-Object -Maximum).Maximum)
 Curve $s $data.timeline.sensor '' '시간 (초)' 'V' 185 132 730 116 60 $ymax $true
 [void](Text $s '모델 점수' 54 269 155 30 18 $blue $true)
 [void](Text $s ('점선: AI 임계값 {0:F3}, 연속 {1}회 확인' -f $data.policy.on,$data.policy.consecutive) 360 252 530 26 16 $muted)
 Curve $s $data.timeline.score '' '시간 (초)' 'Score' 185 278 730 125 60 1.05 $true
 Strip $s '합성 정답 위험' $data.timeline.truth_spans 416 $teal
 Strip $s '프로그램 경보' $data.timeline.alarm_spans 441 $blue
 Strip $s '판정 불가' $data.timeline.unavailable_spans 466 $red
 [void](Text $s '시간 (초)' 823 396 87 22 13 $muted);Notes $s
 $s=Slide '모델 후보 비교' 'Hidden·seed·특징 후보 5개를 학습하고 validation만으로 선택'
 $rows=@(@('후보','특징','Validation Recall','Validation F1'))
 foreach($c in $data.comparison.candidates){$features=$(if($c.name -eq 'lstm16-fast-only'){15}else{30});$label=switch($c.name){'lstm16'{'Hidden 16'} 'lstm32'{'Hidden 32'} 'lstm64'{'Hidden 64'} 'lstm16-seed43'{'Hidden 16 / seed43'} default{'Hidden 16 / 빠른 센서'}};$rows+=,@($label,[string]$features,('{0:F3}' -f $c.validation.recall),('{0:F3}' -f $c.validation.f1))}
 [void](Table $s $rows @(315,95,215,215) 54 117 840 283 20)
 [void](Text $s '선택: 64개 시점 × 15개 특징 · 2,065 파라미터' 54 431 840 37 25 $teal $true);Notes $s
 $s=Slide '학습 곡선과 PR 곡선' '선택 모델: 최대 50회 → 32회 조기 종료, 24회차 가중치 사용'
 Curve $s $data.loss '학습 손실' 'Epoch' 'Loss' 54 122 408 320 32 0.6
 Curve $s $data.pr 'Test PR 곡선' 'Recall' 'Precision' 500 122 408 320 1 1.05
 [void](Text $s '검증 손실이 정체·증가하면 조기 종료' 54 456 840 33 21 $muted);Notes $s
 $s=Slide '테스트 분류 결과' '별도 Test 1,620개. 임계값과 후보 선택은 validation에서 수행'
 $rows=@(@('실제 / 예측','정상','위험'),@('정상','1,437','18'),@('위험','1','164'))
 [void](Table $s $rows @(155,120,120) 54 136 395 216 24)
 [void](Text $s '미탐지 FN 1 · 오경보 입력 FP 18' 492 128 415 45 26 $blue $true)
 $m=$data.report.models.lstm.test
 [void](Text $s ('Precision {0:F3}' -f $m.precision) 492 209 415 34 24 $ink)
 [void](Text $s ('Recall      {0:F3}' -f $m.recall) 492 252 415 34 24 $ink)
 [void](Text $s ('F1            {0:F3}' -f $m.f1) 492 295 415 34 24 $ink)
 [void](Text $s 'Logistic: FN 13 / FP 8' 54 405 840 33 23 $teal $true)
 [void](Text $s '이번 조건에서 LSTM은 미탐지가 적고 오경보 입력이 많음' 54 454 840 31 21 $muted);Notes $s
 $s=Slide '오경보와 시간 평가' '오경보 에피소드: 유효한 정상 시각에 새 경보(ENTER)가 시작한 횟수'
 $rows=@(@('평가 관점','혼합 Test 재생'),@('오경보 입력 창','18개'),@('정상에서 시작한 새 경보','0회'),@('정상 구간 경보 유지 시간','7.5초 / 유효 정상 579.1초'),@('합성 위험 구간 감지','8 / 8구간, 지연 중앙값 0.5초'))
 [void](Table $s $rows @(405,435) 54 115 840 265 21)
 [void](Text $s '별도 2시간 정상 시험: 경보 0회' 54 412 840 41 28 $teal $true)
 [void](Text $s '정상 경보 시간도 집계. 실제 현장 오경보율 보장은 아님' 54 466 840 25 18 $muted);Notes $s
 $s=Slide '모델 변환과 임베디드 준비' 'PC 변환·host C++ 검증 완료. 실제 MCU kernel·arena·firmware 검증 필요'
 $rows=@(@('변환 형식','파일 bytes','Test 판정 변화','Test FP / FN'))
 foreach($k in @('float32','float16','int8')){$item=$data.exports.formats.$k;$rows+=,@($k,('{0:N0}' -f $item.bytes),[string]$item.classification_changes,([string]$item.test.false_positives+' / '+[string]$item.test.false_negatives))}
 [void](Table $s $rows @(230,210,200,200) 54 118 840 195 22)
 [void](Text $s 'INT8: 반복 그래프가 펼쳐져 파일이 더 커짐' 54 335 840 36 23 $muted)
 [void](Text $s ('C++ 기준 입력 140개 일치 · 자동 테스트 {0}개 통과' -f $data.test_count) 54 390 840 40 25 $blue $true)
 [void](Text $s 'RAM 확인 하한 12,282B · 전체 자원/탑재 가능성 UNKNOWN' 54 453 840 33 21 $muted);Notes $s
 $s=Slide '남은 확인과 개발' 'PC 기능 완료. 실제 기준·실측 데이터·통신 규격·목표 보드 확보 후 검증'
 [void](Text $s '1  판정 기준과 운용 요구 확정' 54 124 840 44 29 $blue $true)
 [void](Text $s '초과/미달 · 온도 기준 · 허용 오경보/미탐지/지연' 93 181 800 38 22 $muted)
 [void](Text $s '2  실측 데이터 재학습과 테스트 확대' 54 247 840 44 29 $blue $true)
 [void](Text $s '독립 정답 · 다른 장치/환경 · 장시간·장애 사례' 93 304 800 38 22 $muted)
 [void](Text $s '3  실제 통신·MCU 연결과 자원 측정' 54 370 840 44 29 $blue $true)
 [void](Text $s '패킷 adapter · TFLM 연산자/arena · 최악 처리시간' 93 427 800 38 22 $muted);Notes $s
 if($deck.Slides.Count -ne 11){throw 'Unexpected slide count'}
 $deck.Save();$deck.Close();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck);$deck=$null
 $deck=$app.Presentations.Open($candidate,-1,0,0)
 $preview=Join-Path $build 'preview';[void](New-Item -ItemType Directory -Path $preview -Force);$deck.Export($preview,'PNG',1600,900)
 if((Get-FileHash -LiteralPath $source).Hash -ne $sourceHash){throw 'Source changed'}
 Write-Output "Saved, reopened and rendered $($deck.Slides.Count) slides: $candidate"
}catch{
 Write-Output $_.ScriptStackTrace
 throw
}finally{
 if($null -ne $deck){try{$deck.Close()}catch{};[void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck)}
 if(-not $hadPowerPoint){try{$app.Quit()}catch{}};[void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
 try{[void]$keepAliveWorkbook.Close($false)}catch{}
 if(-not $hadExcel){try{$excelApp.Quit()}catch{}};[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excelApp)
}
