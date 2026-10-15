$ErrorActionPreference='Stop'
$root=(Resolve-Path '.').Path
$build=Join-Path $root 'artifacts/presentation4-build'
$candidate=Join-Path $build 'candidate-v6.pptx'
if(Test-Path -LiteralPath $candidate){throw 'Candidate already exists'}
$data=Get-Content -LiteralPath (Join-Path $build 'chart-data.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$hadPowerPoint=@(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$hadExcel=@(Get-Process EXCEL -ErrorAction SilentlyContinue).Count -gt 0
$app=New-Object -ComObject PowerPoint.Application
$deck=$null
function RGB([string]$hex){return [Convert]::ToInt32($hex.Substring(0,2),16)+256*[Convert]::ToInt32($hex.Substring(2,2),16)+65536*[Convert]::ToInt32($hex.Substring(4,2),16)}
$navy=RGB '11263E';$ink=RGB '142B40';$white=RGB 'FFFFFF';$blue=RGB '1766AE';$teal=RGB '087E7D'
function AddCurve($slide,$series,[string]$title,[string]$xlabel,[string]$ylabel,[double]$left,[double]$xmax,[double]$ymax){
    $shape=$slide.Shapes.AddChart2(-1,75,$left,122,408,320,$false)
    $chart=$shape.Chart
    $chart.ChartData.Activate()
    $book=$chart.ChartData.Workbook
    try {
        if(-not $hadExcel){$book.Application.Visible=$false}
        $sheet=$book.Worksheets.Item(1);$sheet.Name='Data';[void]$sheet.Cells.Clear()
        $rowCount=1+($series | ForEach-Object {$_.x.Count} | Measure-Object -Maximum).Maximum
        $matrix=New-Object 'object[,]' $rowCount,4
        for($j=0;$j -lt 2;$j++){
            $matrix[0,(2*$j)]=$xlabel
            $matrix[0,(2*$j+1)]=$series[$j].name
            for($i=0;$i -lt $series[$j].x.Count;$i++){
                $matrix[($i+1),(2*$j)]=[double]$series[$j].x[$i]
                $matrix[($i+1),(2*$j+1)]=[double]$series[$j].y[$i]
            }
        }
        $sheet.Range('A1:D'+$rowCount).Value2=$matrix
        while($chart.SeriesCollection().Count -gt 0){$chart.SeriesCollection(1).Delete()}
        for($j=0;$j -lt 2;$j++){
            $s=$chart.SeriesCollection().NewSeries()
            $xcol=@('A','C')[$j];$ycol=@('B','D')[$j];$last=$series[$j].x.Count+1
            $s.Name=('=Data!$'+$ycol+'$1')
            $s.XValues=('=Data!$'+$xcol+'$2:$'+$xcol+'$'+$last)
            $s.Values=('=Data!$'+$ycol+'$2:$'+$ycol+'$'+$last)
            $s.Format.Line.ForeColor.RGB=$(if($j -eq 0){$blue}else{$teal})
            $s.Format.Line.Weight=2
            $s.MarkerStyle=-4142
        }
        $chart.HasTitle=$true;$chart.ChartTitle.Text=$title
        $chart.ChartTitle.Format.TextFrame2.TextRange.Font.Name='맑은 고딕'
        $chart.ChartTitle.Format.TextFrame2.TextRange.Font.Size=21
        $chart.ChartTitle.Format.TextFrame2.TextRange.Font.Fill.ForeColor.RGB=$navy
        $chart.HasLegend=$true;$chart.Legend.Position=-4107
        $chart.Legend.Font.Name='맑은 고딕';$chart.Legend.Font.Size=16
        $chart.ChartArea.Font.Name='맑은 고딕';$chart.ChartArea.Font.Size=16
        $chart.ChartArea.Format.Line.Visible=0
        $chart.ChartArea.Format.Fill.ForeColor.RGB=$white
        foreach($axisType in @(1,2)){
            $axis=$chart.Axes($axisType,1)
            $axis.MinimumScale=0;$axis.MaximumScale=$(if($axisType -eq 1){$xmax}else{$ymax})
            $axis.HasTitle=$true;$axis.AxisTitle.Text=$(if($axisType -eq 1){$xlabel}else{$ylabel})
            $axis.AxisTitle.Font.Name='맑은 고딕';$axis.AxisTitle.Font.Size=17
            $axis.TickLabels.Font.Name='맑은 고딕';$axis.TickLabels.Font.Size=15
            $axis.TickLabels.NumberFormat=$(if($xmax -eq 50 -and $axisType -eq 1){'0'}else{'0.0'})
        }
        $chart.Axes(2,1).HasMajorGridlines=$true
        $chart.Axes(2,1).MajorGridlines.Format.Line.ForeColor.RGB=RGB 'E1E8EF'
        $book.Close($true)
        $book=$null
    } finally {if($null -ne $book){$book.Close($true);$book=$null}}
}
function Matrix($slide,$rows,[double]$x,[double]$y,[double]$w,[double]$h){
    $shape=$slide.Shapes.AddTable(3,3,$x,$y,$w,$h)
    $table=$shape.Table
    for($r=1;$r -le 3;$r++){
        for($c=1;$c -le 3;$c++){
            $cell=$table.Cell($r,$c).Shape
            $cell.TextFrame.MarginLeft=7;$cell.TextFrame.MarginRight=7
            $cell.TextFrame.MarginTop=5;$cell.TextFrame.MarginBottom=5
            $cell.TextFrame.VerticalAnchor=3
            $range=$cell.TextFrame.TextRange;$range.Text=$rows[$r-1][$c-1]
            $range.Font.Name='맑은 고딕';$range.Font.NameFarEast='맑은 고딕'
            $range.Font.Size=$(if($r -eq 1 -or $c -eq 1){19}else{32})
            $range.Font.Bold=-1;$range.ParagraphFormat.Alignment=2
            $range.Font.Color.RGB=$(if($r -eq 1){$white}else{$ink})
            $cell.Fill.Solid();$cell.Fill.ForeColor.RGB=$(if($r -eq 1){$navy}elseif($c -eq 1){RGB 'EEF4F8'}else{$white})
        }
    }
}
function SetSource($slide,[string]$source){
    foreach($shape in $slide.NotesPage.Shapes){
        if($shape.Type -eq 14 -and $shape.PlaceholderFormat.Type -eq 2){
            $script=$shape.TextFrame.TextRange.Text.Split(@('자료:'),[StringSplitOptions]::None)[0].TrimEnd()
            $shape.TextFrame.TextRange.Text=$script+"`r`r자료: "+$source
        }
    }
}
try {
    $app.Visible=-1
    $deck=$app.Presentations.Open((Join-Path $build 'candidate.pptx'),0,0,-1)
    $deck.SaveAs($candidate,24)
    $s=$deck.Slides.Item(5)
    for($i=$s.Shapes.Count;$i -ge 1;$i--){if($s.Shapes.Item($i).Type -eq 13){$s.Shapes.Item($i).Delete()}}
    AddCurve $s $data.loss '학습 손실' 'Epoch' 'Loss' 54 50 0.7
    AddCurve $s $data.pr 'Test PR 곡선' 'Recall' 'Precision' 500 1 1.05
    foreach($shape in $s.Shapes){
        if($shape.HasTextFrame -eq -1 -and $shape.TextFrame.HasText -eq -1){
            $t=$shape.TextFrame.TextRange.Text
            if($t.StartsWith('최종 Train')){$shape.TextFrame.TextRange.Text='Train loss  0.021';$shape.Left=66;$shape.Width=396}
            if($t.StartsWith('최종 Validation')){$shape.TextFrame.TextRange.Text='Validation loss  0.019';$shape.Left=512;$shape.Width=396}
        }
    }
    SetSource $s 'artifacts/models/demo-20261005-233045/history.json, test-predictions.npz, report.json. 저장된 원본 수치로 그린 합성 데이터 실험 결과. PR 곡선은 sklearn precision_recall_curve 사용.'
    foreach($number in @(6,7)){
        $s=$deck.Slides.Item($number)
        for($i=$s.Shapes.Count;$i -ge 1;$i--){if($s.Shapes.Item($i).Type -eq 13){$s.Shapes.Item($i).Delete()}}
        $rows=$(if($number -eq 6){@(@('실제 / 예측','정상','위험'),@('정상','158','46'),@('위험','0','90'))}else{@(@('실제 / 예측','정상','위험'),@('정상','204','0'),@('위험','0','90'))})
        Matrix $s $rows 54 146 $(if($number -eq 6){402}else{365}) 282
        SetSource $s ('artifacts/models/demo-20261005-233045/report.json models.'+$(if($number -eq 6){'lstm'}else{'logistic'})+'.test.confusion_matrix. 행은 실제 클래스, 열은 예측 클래스.')
    }
    $deck.Save();$deck.Close();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck);$deck=$null
    $deck=$app.Presentations.Open($candidate,-1,0,0)
    $preview=Join-Path $build 'preview-v6';[void](New-Item -ItemType Directory -Path $preview -Force)
    $deck.Export($preview,'PNG',1600,900)
    Write-Output "Saved, reopened and rendered $($deck.Slides.Count) slides: $candidate"
} finally {
    if($null -ne $deck){$deck.Close();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck)}
    if(-not $hadPowerPoint){$app.Quit()}
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
