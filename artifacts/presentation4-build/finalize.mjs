import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const workspaceDir = process.cwd();
const skillDir = 'C:/Users/bloss/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations';
const buildDir = path.join(workspaceDir, 'artifacts/presentation4-build');
const outputDir = path.join(workspaceDir, 'output/presentations');
await fs.mkdir(outputDir, { recursive: true });
const { finalizePresentation } = await import(pathToFileURL(path.join(skillDir, 'container_tools/artifact_tool_utils.mjs')).href);
const result = await finalizePresentation({
  workspaceDir,
  candidatePath: path.join(buildDir, 'candidate-v6.pptx'),
  finalPath: path.join(outputDir, '그라운드_4회차_LSTM_학습평가_방경식.pptx'),
  pythonExecutable: path.join(workspaceDir, '.venv-ml/Scripts/python.exe'),
  integrityValidatorPath: path.join(skillDir, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(skillDir, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: [
    '--expected-aspect', '16:9', '--expected-slide-count', '9', '--cover-role', 'cover',
    '--validate-heading-fit', '--validate-heading-punctuation',
    ...[2, 3, 6, 7].flatMap(n => ['--require-native-table-slide', String(n)]),
  ],
  requiredNativeTableOwnerSlides: [2, 3, 6, 7],
  requiredNativeChartOwnerSlides: [5],
  requiredEmbeddedWorkbookChartOwnerSlides: [5],
  nativeChartTargetApplication: 'portable',
  fontPolicy: { basis: 'design', families: ['맑은 고딕'] },
  verifyArtifactToolImport: false,
  receiptPath: path.join(buildDir, 'final-validation.json'),
});
const receipt = JSON.parse(await fs.readFile(result.receiptPath, 'utf8'));
receipt.authoringRuntime = 'Installed native PowerPoint COM';
receipt.unavailableValidation = 'Artifact Tool import: package is unavailable in the current runtime. Native PowerPoint reopening and rendering used instead.';
await fs.writeFile(result.receiptPath, JSON.stringify(receipt, null, 2), 'utf8');
console.log(JSON.stringify({ finalPath: result.finalPath, receiptPath: result.receiptPath }));
