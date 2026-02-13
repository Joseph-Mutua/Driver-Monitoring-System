param(
  [Parameter(Mandatory=$true)][string]$GroundTruth,
  [Parameter(Mandatory=$true)][string]$Predictions,
  [string]$OutDir = "eval_reports",
  [double]$IouThreshold = 0.30,
  [int]$ToleranceMs = 1200,
  [int]$Bins = 10
)

.\.venv\Scripts\python -m app.eval.run `
  --ground-truth $GroundTruth `
  --predictions $Predictions `
  --outdir $OutDir `
  --iou-threshold $IouThreshold `
  --tolerance-ms $ToleranceMs `
  --bins $Bins
