# Documentation index

Last reviewed: 16 August 2026 (Asia/Kolkata)

This index identifies the source of truth for each part of CYPHER. When a
historical milestone record conflicts with a current guide, follow the current
guide, the checked-in configuration, and the code in that order.

## Start here

| Document | Use it for |
| --- | --- |
| [README](../README.md) | Project summary, current application, repository layout, and workflow |
| [Project guide](PROJECT_GUIDE.md) | Plain-language end-to-end handover |
| [Simplified application guide](SIMPLIFIED_APPLICATION_GUIDE.md) | Current one-page CYPHER workflow and output contract |
| [Integration setup](INTEGRATION_SETUP.md) | Supabase, Render, R2, Cloudflare Pages, local setup, and release commands |
| [Deployment architecture](DEPLOYMENT_ARCHITECTURE.md) | Current runtime boundaries and data flow |

## Current ML and data references

| Document | Status and purpose |
| --- | --- |
| [Class imbalance and leakage](CLASS_IMBALANCE_AND_DATA_LEAKAGE.md) | Current training safeguards and evaluation rules |
| [Feature engineering guide](FEATURE_ENGINEERING_GUIDE.md) | Current V1/V2 transformations and model-specific preprocessing |
| [Data dictionary](DATA_DICTIONARY.md) | Generated 434-input-column training reference; anonymized fields are not reinterpreted |
| [EDA report](EDA_REPORT.md) | Generated labelled-training-data analysis snapshot |
| [Final model selection](FINAL_MODEL_SELECTION.md) | Frozen approved runs and champion rationale |
| [Model artifact contract](MODEL_ARTIFACT_CONTRACT.md) | Required files, identifiers, thresholds, and adapter boundary |
| [Model verification gate](MODEL_VERIFICATION_GATE.md) | Eight-pipeline acceptance checks before integration |
| [Project asset inventory](PROJECT_ASSET_INVENTORY.md) | Location and Git policy for datasets, models, samples, and deployment contracts |
| [Kaggle inference sample](KAGGLE_INFERENCE_SAMPLE.md) | Current 100-row, 433-column, unlabelled input sample |

## Training runbooks and design records

| Document | Status and purpose |
| --- | --- |
| [Four-model experiment plan](FOUR_MODEL_EXPERIMENT_PLAN.md) | Original V1 experiment design; final outcomes are in Final Model Selection |
| [Lightning training guide](LIGHTNING_TRAINING_GUIDE.md) | Reproducible V1 training runbook |
| [Version 2 training guide](VERSION_2_TRAINING_GUIDE.md) | Reproducible V2 training runbook and validation-first selection rule |
| [Teammate training guide](TEAMMATE_TRAINING_GUIDE.md) | Short operational handover for model owners |
| [YData profiling guide](YDATA_PROFILING_GUIDE.md) | Rebuilding the ignored interactive profiling report |
| [Hackathon evaluation checklist](HACKATHON_EVALUATION_CHECKLIST.md) | Evaluation and presentation checklist; product scope is defined by the simplified guide |
| [Notebook index](../notebooks/README.md) | Entry point for V1 and V2 notebook folders |
| [V1 notebook runbook](../notebooks/lightning_ai/README.md) | V1 notebook order, ownership, hardware, and secret handling |
| [V2 notebook runbook](../notebooks/lightning_ai/v2/README.md) | V2 notebook order and deferred consensus status |
| [EDA report folder](../reports/eda/README.md) | Location and regeneration command for the ignored HTML report |

## Milestone records

These files explain how the system evolved. They are useful engineering records,
but later product decisions can supersede their UI or dataset descriptions.

| Document | Record |
| --- | --- |
| [Milestone 1](MILESTONE_1_INFERENCE_REPORT.md) | Trusted local eight-pipeline inference foundation |
| [Milestone 2](MILESTONE_2_API_GUIDE.md) | FastAPI manual and batch foundation, including current explanation additions |
| [Milestone 3](MILESTONE_3_STREAMING_GUIDE.md) | Labelled Supabase FIFO implementation; current UI instead uses the 100-row unlabelled sample |
| [Milestone 4](MILESTONE_4_FRONTEND_GUIDE.md) | Historical six-page analyst console, replaced publicly by the one-page CYPHER UI |
| [Milestone 5](MILESTONE_5_CLOUD_DEPLOYMENT.md) | Current R2, Render, Supabase, and Cloudflare deployment contract |

## Current product facts

- Product name: **CYPHER**.
- Input modes: **Single JSON**, **CSV Upload**, and **Real-time**.
- Models: Logistic Regression, LightGBM, CatBoost, and Neural Network in V1 and
  V2, for eight selectable pipelines.
- Default selection: no models are selected until the user chooses them.
- Output: one row per transaction and selected model with Fraud/Not Fraud,
  fraud-risk score, and saved model-specific threshold.
- Row detail: non-null transaction inputs plus up to five on-demand local model
  contributions.
- Current Real-time data: 100 official unlabelled Kaggle test rows in strict
  chronological FIFO order.
- Cloudflare Pages: Direct Upload via Wrangler; Git push alone does not publish.
- Backend limitation: the configured Render free service is not reliable for
  the largest models; local FastAPI is the full-inference development path.
