# Step 1: Set up the project and preserve the source

**Goal:** Have one organized local project folder and a GitHub repository that explains what you are building. Estimated learner time: 15-25 minutes.

No Python code or SQL is required in this step.

## A. Put the project in one place

1. Download the starter ZIP from the conversation.
2. In Windows File Explorer, right-click it and choose **Extract All**.
3. Move the extracted `personal-finance-analytics` folder into a `Projects` folder under Documents. Create `Projects` if needed.
4. In VS Code, select **File > Open Folder** and choose `personal-finance-analytics`.

The project root is the folder that directly contains `README.md` and `docs`. If you see another folder with the same project name inside it, open the inner folder that contains those files.

The suggested location is `Documents\Projects\personal-finance-analytics`. Windows may place Documents under OneDrive; use the actual Documents location shown on your computer.

## B. Confirm the source file exists

In the VS Code Explorer panel, expand `data`, then `raw`, then `artha`. Confirm the file `artha_users_v2.json` exists. It is about 47 MiB, so you do not need to open the whole file yet.

Open `docs/source_inspection.md` for a short description of its structure. JSON is nested text data; it is not an Excel workbook. In the next lesson, we will read it with Python and start with one user.

Keep this file unchanged. The `raw` folder means original source data. Later, cleaned tables will be written into a separate folder so we can trace every result back to the original.

## C. Read the project introduction

Open `README.md`. In VS Code, use **Ctrl+Shift+V** to preview the formatted Markdown.

Markdown (`.md`) is a plain-text format used for GitHub documentation. This README is the front page a recruiter will see. It explains the business question, the current stage, and what is planned.

## GitHub mini-step

A repository is the online home for your project's files and version history. A commit is a named checkpoint of changes.

1. Sign in at [GitHub](https://github.com) and open [New repository](https://github.com/new).
2. Use the name `personal-finance-analytics`. Suggested description: `Work-in-progress personal finance analytics project using Python, SQL, and Power BI.` Choose **Public** if you want recruiters to be able to view it. Leave the README, gitignore, and license initialization options off because the starter already supplies the first two.
3. Click **Create repository**. On the empty repository page, click **uploading an existing file**. If you initialized a README anyway, use **Add file > Upload files**.
4. From inside your local project folder, drag only `README.md`, `.gitignore`, and the entire `docs` folder into the upload page. The `docs` folder should remain a folder on GitHub. Do not upload the ZIP, the outer project folder, or `data/raw/`.
5. Use the commit message `docs: define project scope and record data sources`, then commit the files. On a personal repository, committing this initial setup to `main` is fine.
6. Return to the repository's main page. Confirm `README.md` is at the top level, `docs/data_sources.md` exists, and the README renders below the files.

The full raw JSON is excluded to keep the repository lightweight; source links and its checksum make it reproducible. The `.gitignore` supplies rules for later Git commits. When manually uploading in a browser, choose the files yourself; do not rely on ignore rules to filter your selection.

The README says **work in progress** because the analysis and dashboard are not finished. Recruiter-facing claims will be updated only as each feature is built and verified.

GitHub references: [creating a repository](https://docs.github.com/en/get-started/start-your-journey/creating-a-repository-for-your-project-on-github), [uploading files](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository).

## Completion check

- [ ] The project folder opens in VS Code.
- [ ] The raw JSON exists in `data/raw/artha/` and remains unchanged.
- [ ] You have read the README and can explain the first business question.
- [ ] GitHub displays the README and source documentation.
- [ ] The raw JSON and ZIP have not been uploaded to GitHub.

Stop here. Share the repository link or say `Step 1 done` when ready. Step 2 will set up Python and read a small part of the data, with each command and line explained.
