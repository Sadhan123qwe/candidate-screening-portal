# Decisions

Every non-obvious choice and the reason for it. Newest thinking is grouped by topic, not by date.

## Project setup

- **Source files were named `README.md.txt` and `data_dictionary.md.txt`** on disk. They are stored in
  `backend/data/` as `README.md` and `data_dictionary.md`, the names the brief uses. Content is unchanged.
- **Dependencies are pinned to exact versions.** `model.joblib` is only safe to load with the scikit-learn
  version that trained it, and the commit-before-response guarantee relies on a specific FastAPI feature.
