param(
  [Parameter(Mandatory=$true)][string]$GroundTruth,
  [string]$DateFrom,
  [string]$DateTo,
  [double]$IouThreshold = 0.30,
  [int]$ToleranceMs = 1200,
  [int]$Bins = 10
)

.\.venv\Scripts\python -m app.eval.run_range `
  --ground-truth $GroundTruth `
  --date-from $DateFrom `
  --date-to $DateTo `
  --iou-threshold $IouThreshold `
  --tolerance-ms $ToleranceMs `
  --bins $Bins
