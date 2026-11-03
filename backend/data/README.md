# Candidate screening assignment dataset

All records are generated synthetic examples. No real candidate information is included. Email addresses use the reserved example.com domain.

## Files
- candidates.csv: 250 fictional candidates. name and email exist only for the application UI.
- jobs.csv: 10 fictional internship job openings.
- applications.csv: 500 unique candidate-job pairs and synthetic binary labels. Each candidate has two applications.
- ml_dataset.csv: the same 500 applications, already joined for ML work. This is a convenience view, not 500 additional records.
- candidate_split.csv: fixed 200-candidate training / 50-candidate test split (400 / 100 applications).
- data_dictionary.md: column definitions and handling instructions.

## ML task
Predict match_label using candidate skills, experience and job requirements. Label 1 means Potential Match; 0 means Needs Review. Labels are artificial assessment targets, not actual hiring outcomes or application statuses.

Use candidate_split.csv to join the split by candidate_id. All applications from a candidate must stay together. Use only training candidates for fitting preprocessing, feature selection and models. If tuning, use a grouped validation split within training data. Evaluate on the test set after finalizing your approach. Report precision, recall, F1 and a confusion matrix for class 1, plus a simple skill-overlap baseline. Explain the baseline threshold and select it without consulting test labels.

Exclude IDs, names, email addresses and match_label from prediction inputs. Do not use a stored prediction, recruiter status or label-derived value as a feature. Skills use canonical lowercase tokens separated by semicolons. Candidate and job IDs are relational keys only. Job text is available for optional text modelling, but job_id should not be a learned feature.

The small, synthetic dataset has incomplete coverage and intentionally uncertain labels. Do not expect 100% accuracy. Performance measures recovery of artificial patterns, not suitability for real recruitment. Unseen jobs and candidates can behave differently.

## Portal import
Import candidates and jobs first, then applications. Initialize application workflow status as Applied; do not turn match_label into Shortlisted/Rejected. Keep match_label as an offline training target, not an editable recruiter decision. Names and emails are display fields only.

Python standard-library csv or pandas.read_csv can load the files. Use str.split(';') for skill lists. The assignment is to build the solution: no model or implementation solution is supplied.