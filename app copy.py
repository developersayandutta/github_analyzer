from flask import Flask, render_template, request
import requests
import os

app = Flask(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def calculate_score(profile):
    score = 0

    # Public repos weight (max 20 points)
    score += min(profile.get('public_repos', 0), 20)

    # Commits weight (max 30 points)
    commits = profile.get('total_commits', 0)
    if commits > 100:
        score += 30
    else:
        score += commits * 0.3

    # Issues weight (max 10 points)
    score += min(profile.get('total_issues', 0), 10)

    # PRs weight (max 10 points)
    score += min(profile.get('total_prs', 0), 10)

    # Followers weight (max 20 points)
    followers = profile.get('followers', 0)
    if followers > 50:
        score += 20
    else:
        score += followers * 0.4

    # Bonus for bio presence (5 points)
    if profile.get('bio'):
        score += 5

    return round(min(score, 100), 2)

def fetch_github_data(username):
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        # Get user profile info
        user_url = f"https://api.github.com/users/{username}"
        user_resp = requests.get(user_url, headers=headers).json()
        if "message" in user_resp:
            return {"error": user_resp["message"]}

        # Extract profile details
        profile = {
            "login": user_resp.get("login"),
            "full_name": user_resp.get("name"),
            "email": user_resp.get("email"),
            "public_repos": user_resp.get("public_repos"),
            "followers": user_resp.get("followers"),
            "following": user_resp.get("following"),
            "bio": user_resp.get("bio"),
            "location": user_resp.get("location"),
            "blog": user_resp.get("blog"),
            "created_at": user_resp.get("created_at"),
            "updated_at": user_resp.get("updated_at"),
            "avatar_url": user_resp.get("avatar_url"),
        }

        # Fetch repos (max 100 by default)
        repos_url = f"https://api.github.com/users/{username}/repos?per_page=100"
        repos = requests.get(repos_url, headers=headers).json()

        # Calculate total commits across all repos
        total_commits = 0
        for repo in repos:
            repo_name = repo['name']
            commits_url = f"https://api.github.com/repos/{username}/{repo_name}/commits?author={username}&per_page=100"
            commits = requests.get(commits_url, headers=headers).json()
            if isinstance(commits, list):
                total_commits += len(commits)

        # Total issues created by user
        issues_url = f"https://api.github.com/search/issues?q=author:{username}+type:issue"
        issues_resp = requests.get(issues_url, headers=headers).json()
        total_issues = issues_resp.get('total_count', 0)

        # Total PRs created by user
        prs_url = f"https://api.github.com/search/issues?q=author:{username}+type:pr"
        prs_resp = requests.get(prs_url, headers=headers).json()
        total_prs = prs_resp.get('total_count', 0)

        # Recent contributions/events
        events_url = f"https://api.github.com/users/{username}/events/public"
        events = requests.get(events_url, headers=headers).json()
        recent_contributions = []
        for e in events[:10]:  # top 10 recent events
            event_type = e.get("type", "UnknownEvent")
            repo_name = e.get("repo", {}).get("name", "UnknownRepo")
            recent_contributions.append(f"{event_type} in {repo_name}")

        profile.update({
            "total_commits": total_commits,
            "total_issues": total_issues,
            "total_prs": total_prs,
            "recent_contributions": recent_contributions
        })

        # Calculate and add score
        profile['score'] = calculate_score(profile)

        return profile

    except Exception as e:
        return {"error": str(e)}


@app.route('/', methods=['GET', 'POST'])
def home():
    data = None
    error = None
    if request.method == 'POST':
        username = request.form['username']
        data = fetch_github_data(username)
        if "error" in data:
            error = data["error"]
            data = None
    return render_template('index.html', data=data, error=error)


if __name__ == '__main__':
    app.run(debug=True)
