# 🧠 GitHub Analyzer

GitHub Analyzer is a Flask-based web application that analyzes any GitHub user's public profile and generates detailed insights, statistics, and a **profile score** based on their activity and contributions.

## 🚀 Features

- 🔍 Fetches detailed GitHub profile data:
  - Public repositories, commits, issues, pull requests
  - Followers, following, organizations
  - Gists, pinned repositories, project boards
  - Recent contributions & activity
- 🧠 Calculates a **profile score** based on various GitHub metrics
- 🌐 Provides both Web UI and REST API endpoints
- 📊 Language breakdown and repository-level details
- ⚙️ Uses both REST and GraphQL GitHub APIs

---

## 📸 Screenshot

> *(Add a screenshot of the web UI here, if applicable)*

---

## 🛠️ Tech Stack

- [Python](https://www.python.org/)
- [Flask](https://flask.palletsprojects.com/)
- [GitHub REST API](https://docs.github.com/en/rest)
- [GitHub GraphQL API](https://docs.github.com/en/graphql)

---

## 🔧 Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/developersayandutta/github_analyzer.git
cd github_analyzer
```
### 2. Install dependencies
> *Make sure you have Python 3.7+ and pip installed.

```
pip install -r requirements.txt
```
### 3. Set up your GitHub Token (for higher API rate limits)
Create a .env file or export directly:

```
export GITHUB_TOKEN=your_personal_github_token
```
Or in Windows PowerShell:
```
$env:GITHUB_TOKEN="your_personal_github_token"
```
### 🖥️ Run the App
```
python app.py
```
> The app will run at: 📍 http://localhost:3000

### 📈 Profile Score Logic
The profile score is calculated using a weighted formula based on:
- Repositories
- Commits
- Issues and PRs
- Followers and following
- Languages used
- Pinned repositories
- Organizations
> Score is capped at 100 for normalization.
