# Hackathon Evaluation Checklist

> Status: Evaluation and presentation checklist. The current product deliberately
> uses the focused one-page scope in
> [SIMPLIFIED_APPLICATION_GUIDE.md](SIMPLIFIED_APPLICATION_GUIDE.md); analyst
> case management is no longer part of the public demonstration.

This checklist captures the stated evaluation expectations for the NPN hackathon. Use it before finalizing any milestone, demo, or presentation.

## What the final solution must visibly include

- **Architecture and source code:** a clear end-to-end architecture, readable source code, documented design decisions, and a reproducible repository.
- **User interface:** a polished analyst-facing interface that is easy to navigate and visually clear.
- **Documentation and video:** setup/run instructions, technical documentation, and a short demo video showing the working flow.
- **Development roadmap:** a clear MVP-to-future-state roadmap, with realistic next enhancements.
- **Presentation:** an organized narrative that explains and justifies technical choices.

## Evaluation criteria mapped to this project

| Criterion | What our fraud solution will demonstrate |
| --- | --- |
| Use-case understanding | A clear ML inference workflow: classify one transaction, a CSV batch, or a chronological stream and inspect the model evidence. |
| Solution architecture | Kaggle data → preparation/features → validated model → model artifact → FastAPI → dashboard → cloud deployment/monitoring. |
| Innovation and creativity | Device/identity enrichment, eight V1/V2 pipelines, local explanation signals, and strict-FIFO real-time scoring. |
| UI and UX | Clear red/green decisions, spreadsheet-style output, version/model filters, row details, and consistent manual/batch/stream modes. |
| Code quality | Modular code, common feature pipeline, tests, environment examples, Git branching discipline, and plain-language docs. |
| Model performance | Fair comparison of Logistic Regression, LightGBM, CatBoost, and Neural Network using chronological validation and imbalance-aware metrics. |
| Deployment and integration | Cloud-deployed API/dashboard, health check, documented configuration, model versioning, and a deployment plan. |
| Presentation and communication | Problem → data → design → model comparison → working demo → impact → roadmap, with evidence for each choice. |
| Collaboration and teamwork | Clear ownership, frequent Git updates, documented changes, merged milestones, and mentor feedback incorporated. |

## Post-build quality bar

Before the final submission, verify that the solution demonstrates:

- Real-time decision capability: every transaction returns a Fraud/Not Fraud
  decision, fraud-risk score, saved threshold, and latency without dropped FIFO
  events.
- Inspectability: opening a result shows its non-null inputs and strongest local
  model contributions without claiming causation.
- Performance evidence: ROC-AUC, PR-AUC, precision/recall, and an analyst-capacity metric such as recall at top 10% of alerts.
- Integration alternatives: FastAPI is consumed by the React/Cloudflare dashboard and can later be integrated with a bank/payment system through the same JSON contract.
- Reusability: preprocessing and prediction contracts are versioned; model/schema can be replaced without redesigning the UI.
- Ease of implementation: the MVP uses a small number of cloud services and documented deployment steps.

## Required final deliverables

1. GitHub repository with `main` containing a stable release.
2. Architecture diagram and project documentation.
3. Cloud URL for the dashboard and API documentation/health URL.
4. Model comparison table and evaluation charts.
5. Recorded demo video with a backup local demo path.
6. Presentation deck, roadmap, and anticipated Q&A answers.

## Working rule

Every upcoming feature should improve at least one of these criteria without
weakening the others. A strong model alone is not enough: it must be accessible
through a usable inference UI, verifiable, explainable, documented, and
presented with an honest local fallback when cloud memory is insufficient.
