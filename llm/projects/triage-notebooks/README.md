# triage-notebooks

Jupyter notebooks for building a **customer-message triage** dataset and model:
pulling messages from the MySQL database, cleaning/anonymizing text, splitting by
responder, labeling, and preparing training data (used together with the
`finetune_unsloth.py` fine-tuning script that produces a `triage-gguf` model).

| Notebook | Purpose |
|----------|---------|
| `Excrat.ipynb` | Extract raw messages/tickets from the database |
| `Cleaner.ipynb` | Clean & normalize text (strip e-mails, HTML, signatures) |
| `Genel.ipynb` | General dataset assembly / filtering |
| `DatasetTrain.ipynb` | Build the labeled train/eval dataset |
| `t1.ipynb`, `t2.ipynb` | Per-responder subsets & labeling experiments |

## Notes

- **Outputs were cleared** in this consolidated copy to avoid leaking customer
  message content and personal data that was embedded in the saved cell outputs.
  Re-run the notebooks against your own database to regenerate them.
- DB credentials were replaced with placeholders — set the real ones via the
  shared `.env` (see the repository root) instead of hardcoding them in cells.
- Employee names that appear as filter values inside the code (e.g. in SQL
  `WHERE` clauses) were left intact because they are part of the logic; anonymize
  them if you plan to publish.

## Requirements

Python 3.10+, Jupyter, `pandas`, `mysql-connector-python`; fine-tuning uses
`unsloth` + `transformers` (see `../../README.md`).
