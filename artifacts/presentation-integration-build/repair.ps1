$ErrorActionPreference='Stop'
$root=(Resolve-Path '.').Path
$build=Join-Path $root 'artifacts/presentation-integration-build'
$source=Join-Path $build 'candidate-v5.pptx'
$target=Join-Path $build 'candidate-v6.pptx'
if(Test-Path -LiteralPath $target){throw 'Target exists'}
$data=Get-Content (Join-Path $build 'content.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$hadPowerPoint=@(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app=New-Object -ComObject PowerPoint.Application
$deck=$null
function RGB([string]$hex){return [Convert]::ToInt32($hex.Substring(0,2),16)+256*[Convert]::ToInt32($hex.Substring(2,2),16)+65536*[Convert]::ToInt32($hex.Substring(4,2),16)}
function Table($s,$rows,$widths,[double]$y,[double]$h,[double]$font){
 for($i=$s.Shapes.Count;$i -ge 1;$i--){if($s.Shapes.Item($i).HasTable -eq -1){$s.Shapes.Item($i).Delete()}}
 $sh=$s.Shapes.AddTable($rows.Count,$widths.Count,54,$y,840,$h);$t=$sh.Table
 for($c=1;$c -le $widths.Count;$c++){$t.Columns.Item($c).Width=$widths[$c-1]}
 for($r=1;$r -le $rows.Count;$r++){for($c=1;$c -le $widths.Count;$c++){
  $cell=$t.Cell($r,$c).Shape;$cell.TextFrame.MarginLeft=12;$cell.TextFrame.MarginRight=8;$cell.TextFrame.MarginTop=5;$cell.TextFrame.MarginBottom=4;$cell.TextFrame.VerticalAnchor=3
  $txt=$cell.TextFrame.TextRange;$txt.Text=[string]$rows[$r-1][$c-1];$txt.Font.Name='맑은 고딕';$txt.Font.NameFarEast='맑은 고딕';$txt.Font.Size=$font;$txt.Font.Color.RGB=$(if($r -eq 1){RGB 'FFFFFF'}else{RGB '142B40'});$txt.Font.Bold=$(if($r -eq 1){-1}else{0})
  $cell.Fill.Solid();$cell.Fill.ForeColor.RGB=$(if($r -eq 1){RGB '11263E'}elseif($r%2 -eq 0){RGB 'EEF4F8'}else{RGB 'FFFFFF'})
 }}
}
try{
 $deck=$app.Presentations.Open($source,-1,0,0);$deck.SaveAs($target,24)
 $rows=,@('후보','특징','Validation Recall','Validation F1')
 foreach($c in $data.comparison.candidates){$features=$(if($c.name -eq 'lstm16-fast-only'){15}else{30});$label=switch($c.name){'lstm16'{'Hidden 16'} 'lstm32'{'Hidden 32'} 'lstm64'{'Hidden 64'} 'lstm16-seed43'{'Hidden 16 / seed43'} default{'Hidden 16 / 빠른 센서'}};$rows+=,@($label,[string]$features,('{0:F3}' -f $c.validation.recall),('{0:F3}' -f $c.validation.f1))}
 Table $deck.Slides.Item(6) $rows @(315,95,215,215) 117 283 20
 $rows=,@('변환 형식','파일 bytes','Test 판정 변화','Test FP / FN')
 foreach($k in @('float32','float16','int8')){$item=$data.exports.formats.$k;$rows+=,@($k,('{0:N0}' -f $item.bytes),[string]$item.classification_changes,([string]$item.test.false_positives+' / '+[string]$item.test.false_negatives))}
 Table $deck.Slides.Item(10) $rows @(230,210,200,200) 118 195 22
 foreach($sh in $deck.Slides.Item(8).Shapes){if($sh.HasTextFrame -eq -1 -and $sh.TextFrame.HasText -eq -1 -and $sh.TextFrame.TextRange.Text.StartsWith('미탐지 FN')){$sh.TextFrame.TextRange.Text="미탐지 FN 1`r오경보 입력 FP 18";$sh.TextFrame.TextRange.Font.Size=25;$sh.Height=72}}
 $s=$deck.Slides.Item(5)
 $chartShape=$s.Shapes | Where-Object {$_.HasChart -eq -1 -and $_.Top -gt 260} | Select-Object -First 1
 $plotLeft=$chartShape.Left+$chartShape.Chart.PlotArea.InsideLeft
 $plotWidth=$chartShape.Chart.PlotArea.InsideWidth
 if($plotWidth -le 0){throw 'Invalid timeline plot size'}
 foreach($sh in $s.Shapes){if($sh.Type -eq 1 -and $sh.Top -ge 416 -and $sh.Top -le 484 -and $sh.Left -ge 227){$sh.Left=$plotLeft+($sh.Left-228)*$plotWidth/659;$sh.Width=$sh.Width*$plotWidth/659}}
 $deck.Save()
 Write-Output ('Timeline plot x={0:F2}, width={1:F2}; repaired two tables' -f $plotLeft,$plotWidth)
}finally{
 if($null -ne $deck){try{$deck.Close()}catch{}}
 if(-not $hadPowerPoint){try{$app.Quit()}catch{}}
 [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
