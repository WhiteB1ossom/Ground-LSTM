$ErrorActionPreference='Stop'
$root=(Resolve-Path '.').Path
$build=Join-Path $root 'artifacts/presentation4-build'
$test=Join-Path $build 'chart-edit-test-v3.pptx'
if(Test-Path -LiteralPath $test){throw 'Test copy already exists'}
$source=Join-Path $root 'output/presentations/그라운드_4회차_LSTM_학습평가_방경식.pptx'
$hash=(Get-FileHash -LiteralPath $source).Hash
Copy-Item -LiteralPath $source -Destination $test
$hadPowerPoint=@(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app=New-Object -ComObject PowerPoint.Application
$deck=$null;$book=$null
try {
    $app.Visible=-1
    $deck=$app.Presentations.Open($test,0,0,-1)
    $shape=@($deck.Slides.Item(5).Shapes | Where-Object {$_.HasChart -eq -1})[0]
    $width=$shape.Width;$shape.Width=$width+12
    $shape.Chart.ChartData.Activate()
    $book=$shape.Chart.ChartData.Workbook
    $sheet=$book.Worksheets.Item(1)
    $original=[double]$sheet.Range('B2').Value2
    $sheet.Range('B2').Value2=$original+0.01
    $shape.Chart.SeriesCollection(1).Values='=Data!$B$2:$B$51'
    $shape.Chart.Refresh()
    $book.Close($true);$book=$null
    $deck.Save();$deck.Close();$deck=$null
    $deck=$app.Presentations.Open($test,-1,0,0)
    $shape=@($deck.Slides.Item(5).Shapes | Where-Object {$_.HasChart -eq -1})[0]
    if([Math]::Abs($shape.Width-($width+12)) -gt 0.1){throw 'Chart resize did not persist'}
    $values=$shape.Chart.SeriesCollection(1).Values
    $first=[double]$values.GetValue($values.GetLowerBound(0))
    if([Math]::Abs($first-($original+0.01)) -gt 0.000001){throw 'Chart data edit did not persist'}
    if((Get-FileHash -LiteralPath $source).Hash -ne $hash){throw 'Final file changed'}
    Write-Output 'Native chart data editing, resizing, saving and reopening passed in private test copy.'
} finally {
    if($null -ne $book){$book.Close($false)}
    if($null -ne $deck){$deck.Close()}
    if(-not $hadPowerPoint){$app.Quit()}
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
