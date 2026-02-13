param(
  [Parameter(Mandatory=$true)][string]$Manifest,
  [Parameter(Mandatory=$true)][string]$OutputRoot,
  [string]$GroundTruth = "",
  [string]$DetectorConfig = "ml/configs/train.detector.yaml"
)

$strictValidation = Join-Path $OutputRoot "dataset_validation.json"
$splitDir = Join-Path $OutputRoot "splits"
$trainName = "detector_run"
$trainProject = $OutputRoot
$predCsv = Join-Path $OutputRoot "predictions_val.csv"
$calibJson = Join-Path $OutputRoot "calibration.json"
$releaseMetrics = Join-Path $OutputRoot "release_metrics.json"

.\.venv\Scripts\python ml\scripts\validate_dataset.py --manifest $Manifest --output $strictValidation --strict
.\.venv\Scripts\python ml\scripts\build_splits.py --manifest $Manifest --outdir $splitDir

$overrideData = Join-Path $splitDir "data.yaml"
.\.venv\Scripts\python ml\scripts\train_detector.py --config $DetectorConfig --override-data $overrideData

$bestModel = Join-Path $trainProject "$trainName\weights\best.pt"
if (!(Test-Path $bestModel)) {
  Write-Error "best.pt not found at $bestModel"
  exit 1
}

.\.venv\Scripts\python ml\scripts\export_detections.py --manifest $Manifest --model $bestModel --output $predCsv
.\.venv\Scripts\python ml\scripts\calibrate_confidence.py --predictions-csv $predCsv --output $calibJson

if ($GroundTruth -ne "") {
  .\.venv\Scripts\python -m app.eval.run --ground-truth $GroundTruth --predictions (Split-Path $OutputRoot -Parent) --outdir (Join-Path (Split-Path $OutputRoot -Parent) "eval_reports")
  $latestEval = Get-ChildItem -Directory (Join-Path (Split-Path $OutputRoot -Parent) "eval_reports") | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $evalJson = Join-Path $latestEval.FullName "evaluation.json"
  .\.venv\Scripts\python ml\scripts\prepare_release_metrics.py --evaluation-json $evalJson --calibration-json $calibJson --output $releaseMetrics
  .\.venv\Scripts\python ml\scripts\check_acceptance.py --metrics-json $releaseMetrics --gates-yaml ml\configs\acceptance_gates.yaml
} else {
  Write-Host "GroundTruth not provided: skipping acceptance gate check"
}

Write-Host "Pipeline complete. Output root: $OutputRoot"
