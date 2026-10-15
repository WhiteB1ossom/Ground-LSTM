$ErrorActionPreference='Stop'
$root=(Resolve-Path '.').Path
$build=Join-Path $root 'artifacts/presentation-integration-build'
$data=Get-Content (Join-Path $build 'content.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$target=Join-Path $build 'candidate-v7.pptx'
if(Test-Path -LiteralPath $target){throw 'Target exists'}
$hadPowerPoint=@(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app=New-Object -ComObject PowerPoint.Application
$deck=$null;$timelineBook=$null
try{
 $app.Visible=-1;$deck=$app.Presentations.Open((Join-Path $build 'candidate-v6.pptx'),-1,0,-1);$deck.SaveAs($target,24)
 $chartShape=$deck.Slides.Item(5).Shapes | Where-Object {$_.HasChart -eq -1 -and $_.Top -lt 200} | Select-Object -First 1
 $chart=$chartShape.Chart;[void]$chart.ChartData.Activate()
 for($attempt=0;$attempt -lt 20;$attempt++){$timelineBook=$chart.ChartData.Workbook;if($null -ne $timelineBook -and $null -ne $timelineBook.Worksheets){break};Start-Sleep -Milliseconds 250}
 $timelineSheet=$timelineBook.Worksheets.Item(1);$timelineSheet.Name='Data';[void]$timelineSheet.Cells.Clear()
 $series=$data.timeline.sensor;$n=$series[0].x.Count+1;$matrix=New-Object 'object[,]' $n,4
 for($j=0;$j -lt 2;$j++){$matrix[0,(2*$j)]='Time';$matrix[0,(2*$j+1)]=$series[$j].name
  for($i=0;$i -lt $series[$j].x.Count;$i++){$matrix[($i+1),(2*$j)]=[double]$series[$j].x[$i];$matrix[($i+1),(2*$j+1)]=[double]$series[$j].y[$i]}}
 $timelineSheet.Range('A1:D'+$n).Value2=$matrix
 [void]$timelineBook.Save();[void]$chart.Refresh();[void]$timelineBook.Close($true);$timelineBook=$null
 $deck.Save();Write-Output 'Persisted actual timeline sensor worksheet'
}finally{
 if($null -ne $timelineBook){try{[void]$timelineBook.Close($true)}catch{}}
 if($null -ne $deck){try{$deck.Close()}catch{}}
 if(-not $hadPowerPoint){try{$app.Quit()}catch{}}
 [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
