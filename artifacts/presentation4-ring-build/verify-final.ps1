$ErrorActionPreference='Stop'
$root=(Resolve-Path '.').Path
$build=Join-Path $root 'artifacts/presentation4-ring-build'
$final=Join-Path $root 'output/presentations/그라운드_4회차_LSTM_링버퍼_추가_방경식.pptx'
$candidate=Join-Path $build 'candidate.pptx'
$source=Join-Path $root 'output/presentations/그라운드_4회차_LSTM_학습평가_방경식.pptx'
$preview=Join-Path $build 'final-preview'
[void](New-Item -ItemType Directory -Path $preview -Force)
$receipt=Get-Content -LiteralPath (Join-Path $build 'final-validation.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$finalHash=(Get-FileHash -LiteralPath $final).Hash
if($finalHash -ne (Get-FileHash -LiteralPath $candidate).Hash){throw 'Final differs from inspected candidate'}
if((Get-FileHash -LiteralPath $source).Hash -ne $receipt.sourcePreservedSha256){throw 'Source changed'}
$hadPowerPoint=@(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app=New-Object -ComObject PowerPoint.Application
$deck=$null
try {
    $deck=$app.Presentations.Open($final,-1,0,0)
    if($deck.Slides.Count -ne 11){throw 'Slide count mismatch'}
    $notes=0;$charts=0;$tables=0
    foreach($slide in $deck.Slides){
        foreach($shape in $slide.NotesPage.Shapes){
            if($shape.Type -eq 14 -and $shape.PlaceholderFormat.Type -eq 2 -and $shape.TextFrame.TextRange.Text.Length -gt 30){$notes++}
        }
        foreach($shape in $slide.Shapes){
            if($shape.HasChart -eq -1){$charts++}
            if($shape.HasTable -eq -1){$tables++}
            if($slide.SlideIndex -gt 1 -and $shape.HasTextFrame -eq -1 -and $shape.Left -ge 880 -and $shape.Top -ge 495 -and $shape.Width -le 45){
                if($shape.TextFrame.TextRange.Text -ne ('{0:D2}' -f $slide.SlideIndex)){throw 'Page number mismatch'}
            }
        }
    }
    if($notes -ne 11 -or $charts -ne 2 -or $tables -ne 8){throw 'Native content or notes missing'}
    $deck.Export($preview,'PNG',1600,900)
    $deck.Close();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck);$deck=$null
    $images=@(Get-ChildItem -LiteralPath $preview -Filter '*.PNG')
    if($images.Count -ne 11){throw 'Final render count mismatch'}
    foreach($img in $images){
        $draft=Join-Path (Join-Path $build 'preview') $img.Name
        if((Get-FileHash -LiteralPath $draft).Hash -ne (Get-FileHash -LiteralPath $img.FullName).Hash){throw ('Final render changed: '+$img.Name)}
    }
    if((Get-FileHash -LiteralPath $final).Hash -ne $finalHash){throw 'Final file changed'}
    Write-Output 'Final opened and rendered in PowerPoint: 11 slides, 11 notes, 2 charts, 8 tables. All renders match reviewed candidate.'
} finally {
    if($null -ne $deck){$deck.Close();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck)}
    if(-not $hadPowerPoint){$app.Quit()}
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
