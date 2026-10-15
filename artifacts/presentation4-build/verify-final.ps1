$ErrorActionPreference='Stop'
$root=(Resolve-Path '.').Path
$final=Join-Path $root 'output/presentations/그라운드_4회차_LSTM_학습평가_방경식.pptx'
$build=Join-Path $root 'artifacts/presentation4-build'
$preview=Join-Path $build 'final-preview'
[void](New-Item -ItemType Directory -Path $preview -Force)
$before=(Get-FileHash -LiteralPath $final -Algorithm SHA256).Hash
$hadPowerPoint=@(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app=New-Object -ComObject PowerPoint.Application
$deck=$null
try {
    $deck=$app.Presentations.Open($final,-1,0,0)
    if($deck.Slides.Count -ne 9){throw 'Slide count mismatch'}
    $notes=0;$charts=0;$tables=0
    foreach($slide in $deck.Slides){
        foreach($shape in $slide.NotesPage.Shapes){
            if($shape.Type -eq 14 -and $shape.PlaceholderFormat.Type -eq 2 -and $shape.TextFrame.TextRange.Text.Length -gt 30){$notes++}
        }
        foreach($shape in $slide.Shapes){if($shape.HasChart -eq -1){$charts++};if($shape.HasTable -eq -1){$tables++}}
    }
    if($notes -ne 9 -or $charts -ne 2 -or $tables -ne 6){throw 'Editable content or notes mismatch'}
    $deck.Export($preview,'PNG',1600,900)
    $deck.Close();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck);$deck=$null
    if((Get-FileHash -LiteralPath $final -Algorithm SHA256).Hash -ne $before){throw 'Final file changed'}
    $candidate=Join-Path $build 'candidate-v6.pptx'
    if((Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash -ne $before){throw 'Final bytes differ from inspected candidate'}
    $images=@(Get-ChildItem -LiteralPath $preview -Filter '*.PNG')
    if($images.Count -ne 9){throw 'Missing final renders'}
    foreach($img in $images){
        $draft=Join-Path (Join-Path $build 'preview-v6') $img.Name
        if((Get-FileHash -LiteralPath $draft).Hash -ne (Get-FileHash -LiteralPath $img.FullName).Hash){throw ('Rendered slide changed: '+$img.Name)}
    }
    Write-Output "Final opened in PowerPoint: 9 slides, 9 notes, 2 editable charts, 6 editable tables"
    Write-Output "All 9 final renders match the inspected draft"
} finally {
    if($null -ne $deck){$deck.Close();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck)}
    if(-not $hadPowerPoint){$app.Quit()}
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
