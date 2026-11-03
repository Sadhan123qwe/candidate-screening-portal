# Data dictionary

Each CSV uses UTF-8, a header row and comma-separated fields. Multi-skill values are semicolon-delimited within a field. No fields are missing in this version; zero experience is valid. Experience is measured in years.

| File | Field | Type / meaning |
|---|---|---|
| candidates | candidate_id | Unique string key; exclude from model features |
| candidates | name, email | Fictional UI fields; exclude from model features |
| candidates | skills | Canonical skill tokens separated by semicolons |
| candidates | experience_years | Nonnegative numeric years of overall project/work experience |
| candidates | profile_summary | Synthetic text restating skills; optional text input |
| jobs | job_id | Unique string key; exclude from model features |
| jobs | title, description | Fictional role text |
| jobs | required_skills | Semicolon-delimited required skill tokens |
| jobs | preferred_skills | Semicolon-delimited optional skill tokens |
| jobs | minimum_experience_years | Numeric experience requirement; 0 means none |
| applications | application_id | Unique string key; exclude from model features |
| applications | candidate_id, job_id | Foreign keys; pair must be unique |
| applications | match_label | Integer target: 1 Potential Match; 0 Needs Review |
| ml_dataset | candidate_skills | Same content as candidates.skills |
| ml_dataset | all other fields | Joined copies of application, candidate and job fields above |
| candidate_split | candidate_id | Join key to assign all applications from that candidate |
| candidate_split | split | train or test; metadata only, never a model feature |

Skills are exact canonical tokens: java and javascript would be different skills. nextjs denotes Next.js; nodejs denotes Node.js. No normalization exercise is required. Do not infer protected attributes from candidate identifiers.