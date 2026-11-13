# Final Crowd-Counting Benchmark Summary

## Experimental setup

- 50 ShanghaiTech test images were evaluated.
- 25 images were selected from Part A and 25 from Part B.
- Each image was run three times per model for timing.
- Model loading and one warm-up inference were excluded from inference timing.
- MAE and RMSE are the primary accuracy metrics.

## Main findings

- **Best overall accuracy:** Bayesian (MAE 39.55, RMSE 61.65).
- **Fastest average inference:** CSRNet (0.8908 seconds/image).
- **Best on dense Part A images:** Bayesian (MAE 49.44).
- **Best on Part B street scenes:** SFANet (MAE 14.51).

## Overall results

| Model | MAE | RMSE | MAPE (%) | Avg inference (s) |
|---|---:|---:|---:|---:|
| Bayesian | 39.55 | 61.65 | 18.02 | 0.9317 |
| DM-Count | 42.79 | 72.47 | 18.43 | 0.9014 |
| CSRNet | 56.99 | 84.42 | 39.81 | 0.8908 |
| SFANet | 80.44 | 187.95 | 18.44 | 1.1332 |

## Interpretation

The Bayesian model provides the strongest overall accuracy and performs best on the dense ShanghaiTech Part A subset. SFANet performs best on Part B, indicating stronger suitability for lower-density street scenes and perspective variation. CSRNet provides the fastest average inference, while DM-Count offers a competitive balance between accuracy and speed.

## Important limitation

CSRNet, Bayesian, and DM-Count use SHA weights, whereas SFANet uses SHB weights. Therefore, the experiment compares both model architecture and training-domain effects. The results support selecting a model for a specific image domain, but they are not a perfectly controlled comparison of architecture alone.

## Generated charts

- `charts/01_overall_mae.png`
- `charts/02_overall_rmse.png`
- `charts/03_average_inference_time.png`
- `charts/04_mae_by_part.png`
- `charts/05_predictions_vs_ground_truth.png`
- `charts/06_absolute_error_by_count.png`
