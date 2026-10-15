import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const workspaceDir=process.cwd();
const skillDir='C:/Users/bloss/.codex/plugins/cache/openai-primary-runtime/presentations/26.1009.11318/skills/presentations';
const buildDir=path.join(workspaceDir,'artifacts/presentation-integration-build');
const sourcePath=path.join(workspaceDir,'output/presentations/그라운드_4회차_LSTM_링버퍼_추가_방경식.pptx');
const sourceHash=createHash('sha256').update(await fs.readFile(sourcePath)).digest('hex');
const {finalizePresentation}=await import(pathToFileURL(path.join(skillDir,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({
 workspaceDir,candidatePath:path.join(buildDir,'candidate-v10.pptx'),
 finalPath:path.join(workspaceDir,'output/presentations/그라운드_실시간_통합개발_방경식.pptx'),
 pythonExecutable:path.join(workspaceDir,'.venv-ml/Scripts/python.exe'),
 integrityValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--expected-slide-count','11','--cover-role','cover',
 '--validate-heading-fit','--validate-heading-punctuation',...[2,3,4,6,8,9,10].flatMap(n=>['--require-native-table-slide',String(n)])],
 requiredNativeTableOwnerSlides:[2,3,4,6,8,9,10],requiredNativeChartOwnerSlides:[5,7],
 requiredEmbeddedWorkbookChartOwnerSlides:[5,7],nativeChartTargetApplication:'portable',
 fontPolicy:{basis:'reference',families:['맑은 고딕'],referencePath:sourcePath,referenceSha256:sourceHash},
 verifyArtifactToolImport:false,receiptPath:path.join(buildDir,'final-validation-v10.json'),
});
const receipt=JSON.parse(await fs.readFile(result.receiptPath,'utf8'));
receipt.authoringRuntime='Installed native PowerPoint COM';
receipt.unavailableValidation='Artifact Tool package and Artifact Sessions unavailable; native PowerPoint reopening, rendering and workbook checks used.';
receipt.sourceReferenceSha256=sourceHash;
await fs.writeFile(result.receiptPath,JSON.stringify(receipt,null,2),'utf8');
console.log(JSON.stringify({finalPath:result.finalPath,receiptPath:result.receiptPath}));
