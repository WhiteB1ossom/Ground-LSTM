import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';

const workspaceDir=process.cwd();
const skillDir='C:/Users/bloss/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations';
const buildDir=path.join(workspaceDir,'artifacts/presentation4-ring-build');
const sourcePath=path.join(workspaceDir,'output/presentations/그라운드_4회차_LSTM_학습평가_방경식.pptx');
const sourceHash=createHash('sha256').update(await fs.readFile(sourcePath)).digest('hex');
const { finalizePresentation }=await import(pathToFileURL(path.join(skillDir,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({
  workspaceDir,
  candidatePath:path.join(buildDir,'candidate.pptx'),
  finalPath:path.join(workspaceDir,'output/presentations/그라운드_4회차_LSTM_링버퍼_추가_방경식.pptx'),
  pythonExecutable:path.join(workspaceDir,'.venv-ml/Scripts/python.exe'),
  integrityValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:[
    '--expected-aspect','16:9','--expected-slide-count','11','--cover-role','cover',
    '--validate-heading-fit','--validate-heading-punctuation',
    ...[2,3,4,5,8,9].flatMap(n=>['--require-native-table-slide',String(n)]),
  ],
  requiredNativeTableOwnerSlides:[2,3,4,5,8,9],
  requiredNativeChartOwnerSlides:[7],
  requiredEmbeddedWorkbookChartOwnerSlides:[7],
  nativeChartTargetApplication:'portable',
  fontPolicy:{basis:'reference',families:['맑은 고딕'],referencePath:sourcePath,referenceSha256:sourceHash},
  verifyArtifactToolImport:false,
  receiptPath:path.join(buildDir,'final-validation.json'),
});
const receipt=JSON.parse(await fs.readFile(result.receiptPath,'utf8'));
receipt.authoringRuntime='Installed native PowerPoint COM';
receipt.unavailableValidation='Artifact Tool package unavailable in this runtime; native PowerPoint reopening and rendering used instead.';
receipt.sourcePreservedSha256=sourceHash;
await fs.writeFile(result.receiptPath,JSON.stringify(receipt,null,2),'utf8');
console.log(JSON.stringify({finalPath:result.finalPath,receiptPath:result.receiptPath}));
