# Version 2 training notebooks

> Status: All four standalone V2 models are complete. The optional LightGBM +
> CatBoost consensus was deferred and is not part of the eight-pipeline CYPHER
> application.

Version 2 is an additional experiment. It does not replace or modify the Version 1
notebooks, processed data, or model runs.

## Run order

1. Clone or pull the repository and open it in Jupyter, Colab, or another notebook environment.
2. One teammate runs `10_v2_behavioral_data_preparation.ipynb` once.
3. Share `data/processed/v2/` privately with the other model owners, or let every owner run notebook 10.
4. Each model team runs its assigned notebook from top to bottom.
5. Do not run notebook 15 unless the team explicitly reopens the deferred
   consensus experiment.

| Notebook | Owners | Output folder |
| --- | --- | --- |
| `11_v2_lightgbm_saravana_nebal.ipynb` | Saravana / Nebal | `artifacts/v2/lightgbm/<run-id>/` |
| `12_v2_catboost_midhun_ajmeer.ipynb` | Midhun / Ajmeer | `artifacts/v2/catboost/<run-id>/` |
| `13_v2_logistic_regression_nanda_khishan.ipynb` | Nanda / Khishan | `artifacts/v2/logistic_regression/<run-id>/` |
| `14_v2_tabular_neural_network_mirdula_hashvitha.ipynb` | Mirdula / Hashvitha | `artifacts/v2/neural_network/<run-id>/` |
| `15_v2_lightgbm_catboost_consensus.ipynb` | Deferred optional experiment | `artifacts/v2/consensus/<run-id>/` |

Keep `FAST_RUN = False` for accepted results. Each model notebook automatically:

- saves the model and fitted preprocessor;
- saves validation and test probabilities, metrics, threshold, schema, and settings;
- reloads the saved model and checks its predictions; and
- creates a shareable `.tar.gz` file next to the run folder.

Send Midhun the generated `.tar.gz` file. Do not send only the model file because
inference also needs its preprocessor, schema, and threshold.

## Hardware guidance

- LightGBM: CPU or NVIDIA GPU; CPU is normally fast enough.
- CatBoost: NVIDIA GPU is recommended; CPU works but takes longer.
- Logistic Regression: CPU and at least 16 GB RAM; close other heavy programs.
- Neural network: NVIDIA GPU is strongly recommended. A 6 GB RTX 4060 can run the
  configured batch size; reduce `BATCH_SIZE` from 4096 to 2048 if memory is exhausted.

Notebook 10 is the memory-heavy step. Run it on a machine with at least 16 GB RAM and
avoid keeping duplicate copies of the joined dataframe open in other notebooks.
