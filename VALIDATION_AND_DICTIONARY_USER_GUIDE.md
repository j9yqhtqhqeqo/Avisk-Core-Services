# Validation and Dictionary Terms User Guide

This guide explains how to use the `Validation` page and the `Process Dictionary Terms` page in Avisk Core Services.

## Audience

Use this guide if you are responsible for:
- running keyword validations
- managing validation queues
- reviewing dictionary terms
- classifying new terms into include or exclude lists
- processing updated dictionary files

## Access Requirements

Both pages require login with one of these roles:
- `admin`
- `validator`

## Pages Covered

Client navigation pages:
- `Clients/Pages/3Validation.py`
- `Clients/Pages/4Process Dictionary Terms.py`

Equivalent page also exists in:
- `pages/3Validation.py`

## Before You Start

Make sure the following are true:
- the application is running and reachable
- the database connection is available
- the dictionary files are accessible on the current environment
- you understand whether you are working in development or production data

Operational note:
- the Validation page reads live database status from `t_document`
- the Process Dictionary Terms page reads and writes local dictionary staging files before processing them into the active dictionaries

## Validation Page

The Validation page contains three tabs:
- `Run Validations`
- `Manage Validation List`
- `Dictionary Terms`

### 1. Run Validations

Purpose:
- start validation runs for one or more keyword categories

How it works:
- select one or more categories:
  - `Exposure Pathway`
  - `Internalization`
  - `Mitigation`
- click `Run Validations`
- the page runs the selected validation jobs and then sends include/exclude dictionary files for validation processing

What you will see:
- progress messages by step
- success messages for each category completed
- a final success message when the full validation flow finishes

Background Validation Status panel:
- shows how many documents are currently `running` and `pending` for each category
- refreshes automatically every 5 seconds when validations are in progress
- warns when documents are pending but no validation job is currently running

Status meaning on this page:
- `running`: validation flag is currently in in-progress state
- `pending`: validation-ready document is waiting to run
- `not ready`: handled in the `Manage Validation List` tab

Recommended usage:
- use this tab when documents are already ready for validation and you want to execute the workflow
- do not use this tab to fix `not ready` items; use `Manage Validation List` first

### 2. Manage Validation List

Purpose:
- review documents whose validation status is `-1` (`Not Ready`)
- move selected company/year combinations back to `0` (`Pending`)

How it works:
- select the validation category:
  - `Exposure Pathway`
  - `Internalization`
  - `Mitigation`
- the page shows grouped rows from `t_document` where the category validation flag is `-1`
- each row is grouped by:
  - `company_name`
  - `year`
  - document count
- choose one or more company/year combinations from the multi-select list
- click `Update selected combinations to Pending`

What happens after update:
- all matching rows for the selected category, company, and year are updated from `-1` to `0`
- `modify_dt` is updated in the database
- the page reruns and refreshes the list

Use this tab when:
- validation items are blocked as `Not Ready`
- you need to re-queue a subset of records for reprocessing
- you want to re-open validation for multiple companies and years at once

Recommended workflow:
1. Open `Manage Validation List`
2. Choose the category
3. Select the company/year combinations to re-queue
4. Update them to `Pending`
5. Move to `Run Validations`
6. Run the category validation job

### 3. Dictionary Terms

Purpose:
- browse the current database-backed dictionary terms used by validation

This tab contains sub-tabs for:
- `Exposure Pathway`
- `Internalization`
- `Mitigation`

Displayed columns:

Exposure Pathway:
- `esg_category_name`
- `impact_category_name`
- `exposure_path_name`
- `keywords`

Internalization:
- `esg_category_name`
- `impact_category_name`
- `exposure_path_name`
- `internalization_name`
- `keywords`

Mitigation:
- `class_name`
- `sub_class_name`
- `keywords`

Use this tab when:
- you want to review what terms are already configured
- you need to confirm category mapping before changing validation status
- you want to verify dictionary structure before processing new terms

## Process Dictionary Terms Page

Purpose:
- review newly collected keyword candidates
- decide whether each term should be included or excluded
- save those decisions to staging files
- process the files into the active dictionaries

### What the page does

This page works with staging files for new terms, not directly with the validation database tables.

It reads from:
- `new_include_list.txt`
- `new_exclude_list.txt`

It writes back to those same staging files after user edits.

It then calls dictionary processing logic to update the active inclusion and exclusion dictionaries.

### Main Sections

#### 1. Load/Reload Terms from Files

Button:
- `Load/Reload Terms from Files`

What it does:
- loads term pairs from the include staging file
- loads term pairs from the exclude staging file
- combines them into a single editable grid with an `Action` column

Grid columns:
- `Keyword`
- `Related Term`
- `Action`

Action values:
- `Include`
- `Exclude`

Use this when:
- new validation results have produced candidate terms
- you want to review the current staging set before processing

#### 2. Dictionary Terms Management Grid

Purpose:
- review each keyword-related-term pair
- assign each pair to Include or Exclude

How to use it:
- inspect each row
- choose the desired `Action`
- keep the same term in only one action path

Important rule:
- a keyword-related-term pair should not remain duplicated across both include and exclude processing paths

#### 3. Save Changes

Button:
- `Save Changes`

What it does:
- writes all current `Include` rows back to the include staging file
- writes all current `Exclude` rows back to the exclude staging file
- updates the in-memory grid state

Use this before processing dictionary terms.

#### 4. Clear All

Button:
- `Clear All`

What it does:
- clears the currently loaded grid from session state
- does not itself process dictionary changes

Use this when:
- you want to discard the loaded session view and reload from files

#### 5. Auto-Recommend Include / Exclude

Buttons:
- `Recommend for All Terms`
- `Recommend Unclassified Only`

What it does:
- uses the recommendation engine to compare current candidates against historical include and exclude dictionary entries
- calculates a recommendation and confidence score
- shows closest matching include and exclude terms

Displayed recommendation fields include:
- keyword
- related term
- recommendation action
- confidence
- closest include term
- closest exclude term
- similarity scores
- reason

Apply button:
- `Apply Recommendations to Grid`

What it does:
- copies recommendation actions into the grid’s `Action` column
- does not save to files until you click `Save Changes`

Recommended usage:
1. Load terms
2. Run recommendations
3. Review recommendations manually
4. Apply recommendations if appropriate
5. Adjust any edge cases
6. Save changes

#### 6. Process Dictionary Terms

Button:
- `Process Dictionary Terms`

What it does:
- calls the dictionary manager to update the active dictionaries
- updates validation-completed status after successful processing

Success result:
- active dictionary files are updated
- validation state is updated for downstream processing

Error handling:
- if duplicate terms are found in both include and exclude paths, the page raises a duplicate-term error
- duplicate keywords are shown to the operator for correction

If duplicates are reported:
1. review the duplicate keywords shown on screen
2. decide whether each belongs in Include or Exclude
3. remove duplicates from one side
4. save changes
5. run `Process Dictionary Terms` again

## Recommended End-to-End Workflow

### Scenario A: Re-queue Not Ready validation items

1. Open `Validation`
2. Go to `Manage Validation List`
3. Select the validation category
4. Select one or more company/year combinations
5. Update them to `Pending`
6. Go to `Run Validations`
7. Run the validation job for the same category

### Scenario B: Review current dictionary coverage

1. Open `Validation`
2. Go to `Dictionary Terms`
3. Review the relevant category tab
4. Confirm the existing terms and category mapping
5. If new terms are needed, go to `Process Dictionary Terms`

### Scenario C: Process new candidate dictionary terms

1. Open `Process Dictionary Terms`
2. Click `Load/Reload Terms from Files`
3. Review the term grid
4. Use recommendation tools if helpful
5. Set each term to `Include` or `Exclude`
6. Click `Save Changes`
7. Click `Process Dictionary Terms`
8. Return to `Validation` to review dictionary terms or run validations

## Troubleshooting

### Validation status unavailable

Possible causes:
- database connection not configured
- database unavailable
- environment configuration issue

What to do:
- verify the app has database connectivity
- confirm environment variables and secrets are loaded
- retry after database availability is restored

### Dictionary terms unavailable

Possible causes:
- database query failure
- missing lookup tables
- broken connection to the production database

What to do:
- verify database connectivity
- confirm the relevant tables exist and are populated

### No new terms found in Process Dictionary Terms

Possible causes:
- no new validation term files were generated
- staging files are empty
- wrong environment or data path

What to do:
- verify validation output has produced new staging files
- confirm file paths for the current environment
- reload terms again

### Duplicate dictionary terms error

Cause:
- the same term appears in both Include and Exclude flows

Resolution:
- keep the term in only one classification
- save the corrected staging files
- rerun processing

## Operator Tips

- Use `Dictionary Terms` before running validations if you need to confirm category mappings.
- Use `Manage Validation List` for queue correction, not `Run Validations`.
- Save dictionary file edits before clicking `Process Dictionary Terms`.
- Treat auto-recommendations as decision support, not as a final answer.
- When re-queuing validations, select only the company/year combinations you actually want to rerun.

## File References

Validation page:
- `Clients/Pages/3Validation.py`
- `pages/3Validation.py`

Process Dictionary Terms page:
- `Clients/Pages/4Process Dictionary Terms.py`

Dictionary staging path logic:
- `Utilities/PathConfiguration.py`

Dictionary processing logic:
- `Dictionary/DictionaryManager.py`
