$ErrorActionPreference='Stop'
$root=(Resolve-Path '.').Path
$build=Join-Path $root 'artifacts/presentation-integration-build'
$candidate=Join-Path $root 'output/presentations/그라운드_실시간_통합개발_방경식.pptx'
$hadPowerPoint=@(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app=New-Object -ComObject PowerPoint.Application
$deck=$null
try{
 $deck=$app.Presentations.Open($candidate,-1,0,0)
 if($deck.Slides.Count -ne 11){throw 'Slide count changed'}
 $preview=Join-Path $build 'preview-final'
 [void](New-Item -ItemType Directory -Path $preview -Force)
 $deck.Export($preview,'PNG',1600,900)
 Write-Output "Reopened and rendered all 11 slides"
}finally{
 if($null -ne $deck){try{$deck.Close()}catch{}}
 if(-not $hadPowerPoint){try{$app.Quit()}catch{}}
 [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
