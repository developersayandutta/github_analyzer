from flask import Flask, render_template, request
from flask import jsonify
import requests
import os

app = Flask(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Helper to make REST API GET requests with auth headers
def github_get(url, params=None):
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        return None
    return resp.json()

# Helper to run GraphQL queries
def github_graphql(query, variables=None):
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"bearer {GITHUB_TOKEN}"}
    json_data = {"query": query}
    if variables:
        json_data["variables"] = variables
    resp = requests.post(url, json=json_data, headers=headers)
    if resp.status_code != 200:
        return None
    return resp.json()

def calculate_profile_score(profile):
    score = 0

    # Weights - adjust if needed
    weights = {
        "public_repos": 0.5,
        "total_commits": 0.05,
        "total_issues": 0.5,
        "total_prs": 0.5,
        "followers_count": 1,
        "following_count": 0.1,
        "languages_count": 1,
        "pinned_repos_count": 2,
        "organizations_count": 1,
    }

    score += profile.get("public_repos", 0) * weights["public_repos"]
    score += profile.get("total_commits", 0) * weights["total_commits"]
    score += profile.get("total_issues", 0) * weights["total_issues"]
    score += profile.get("total_prs", 0) * weights["total_prs"]
    score += profile.get("followers_count", 0) * weights["followers_count"]
    score += profile.get("following_count", 0) * weights["following_count"]

    languages_count = len(profile.get("aggregate_languages", {}))
    score += languages_count * weights["languages_count"]

    pinned_count = len(profile.get("pinned_repos", []))
    score += pinned_count * weights["pinned_repos_count"]

    org_count = len(profile.get("organizations", []))
    score += org_count * weights["organizations_count"]

    # Optional: Cap the score at 100
    if score > 100:
        score = 100

    return round(score, 2)


def fetch_github_data(username):
    try:
        # 1. User profile info
        user_url = f"https://api.github.com/users/{username}"
        user_resp = github_get(user_url)
        if not user_resp or "message" in user_resp:
            return {"error": user_resp.get("message", "User not found")}

        profile = {
            "login": user_resp.get("login"),
            "full_name": user_resp.get("name"),
            "email": user_resp.get("email"),
            "public_repos": user_resp.get("public_repos"),
            "followers_count": user_resp.get("followers"),
            "following_count": user_resp.get("following"),
            "bio": user_resp.get("bio"),
            "location": user_resp.get("location"),
            "blog": user_resp.get("blog"),
            "created_at": user_resp.get("created_at"),
            "updated_at": user_resp.get("updated_at"),
            "avatar_url": user_resp.get("avatar_url"),
        }

        # 2. Repositories + languages + stars + forks + description + last updated
        repos_url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated"
        repos = github_get(repos_url) or []

        repo_list = []
        aggregate_languages = {}

        total_commits = 0
        for repo in repos:
            repo_name = repo["name"]

            # Fetch repo languages
            lang_url = f"https://api.github.com/repos/{username}/{repo_name}/languages"
            languages = github_get(lang_url) or {}

            # Aggregate languages for user
            for lang, bytes_count in languages.items():
                aggregate_languages[lang] = aggregate_languages.get(lang, 0) + bytes_count

            # Count commits authored by user in repo (only first 100 commits)
            commits_url = f"https://api.github.com/repos/{username}/{repo_name}/commits"
            commits_params = {"author": username, "per_page": 100}
            commits = github_get(commits_url, params=commits_params)
            if isinstance(commits, list):
                total_commits += len(commits)

            repo_list.append({
                "name": repo_name,
                "html_url": repo.get("html_url"),
                "description": repo.get("description"),
                "stargazers_count": repo.get("stargazers_count"),
                "forks_count": repo.get("forks_count"),
                "languages": languages,
                "updated_at": repo.get("updated_at"),
                "private": repo.get("private"),
            })

        profile["repos"] = repo_list
        profile["aggregate_languages"] = aggregate_languages
        profile["total_commits"] = total_commits

        # 3. Total issues and PRs created by user
        issues_url = f"https://api.github.com/search/issues?q=author:{username}+type:issue"
        issues_resp = github_get(issues_url)
        profile["total_issues"] = issues_resp.get("total_count", 0) if issues_resp else 0

        prs_url = f"https://api.github.com/search/issues?q=author:{username}+type:pr"
        prs_resp = github_get(prs_url)
        profile["total_prs"] = prs_resp.get("total_count", 0) if prs_resp else 0

        # 4. Followers list (up to 100)
        followers_url = f"https://api.github.com/users/{username}/followers?per_page=100"
        followers = github_get(followers_url) or []
        profile["followers"] = [{"login": f.get("login"), "html_url": f.get("html_url")} for f in followers]

        # 5. Following list (up to 100)
        following_url = f"https://api.github.com/users/{username}/following?per_page=100"
        following = github_get(following_url) or []
        profile["following"] = [{"login": f.get("login"), "html_url": f.get("html_url")} for f in following]

        # 6. Public gists (up to 100)
        gists_url = f"https://api.github.com/users/{username}/gists?per_page=100"
        gists = github_get(gists_url) or []
        profile["gists"] = [{"html_url": g.get("html_url"), "description": g.get("description")} for g in gists]

        # 7. Organizations
        orgs_url = f"https://api.github.com/users/{username}/orgs"
        orgs = github_get(orgs_url) or []
        profile["organizations"] = [{"login": o.get("login"), "html_url": o.get("html_url")} for o in orgs]

        # 8. Recent public events
        events_url = f"https://api.github.com/users/{username}/events/public?per_page=10"
        events = github_get(events_url) or []
        recent_contributions = []
        for e in events:
            event_type = e.get("type", "UnknownEvent")
            repo_name = e.get("repo", {}).get("name", "UnknownRepo")
            recent_contributions.append(f"{event_type} in {repo_name}")
        profile["recent_contributions"] = recent_contributions

        # 9. Pinned repos via GraphQL (requires token)
        profile["pinned_repos"] = []
        if GITHUB_TOKEN:
            query = """
            query($login:String!) {
              user(login:$login) {
                pinnedItems(first:6, types:REPOSITORY) {
                  nodes {
                    ... on Repository {
                      name
                      description
                      stargazerCount
                      forkCount
                      url
                      primaryLanguage {
                        name
                        color
                      }
                    }
                  }
                }
              }
            }
            """
            variables = {"login": username}
            result = github_graphql(query, variables)
            pinned_nodes = result.get("data", {}).get("user", {}).get("pinnedItems", {}).get("nodes", [])
            for pr in pinned_nodes:
                profile["pinned_repos"].append({
                    "name": pr.get("name"),
                    "description": pr.get("description"),
                    "stars": pr.get("stargazerCount"),
                    "forks": pr.get("forkCount"),
                    "url": pr.get("url"),
                    "language": pr.get("primaryLanguage", {}).get("name"),
                    "language_color": pr.get("primaryLanguage", {}).get("color"),
                })

        # 10. Project boards (public)
        profile["project_boards"] = []
        if GITHUB_TOKEN:
            query_projects = """
            query($login: String!) {
              user(login: $login) {
                projectsV2(first: 10, orderBy: {field: CREATED_AT, direction: DESC}) {
                  nodes {
                    title
                    url
                    number
                    closed
                    createdAt
                  }
                }
              }
            }
            """
            variables = {"login": username}
            projects_result = github_graphql(query_projects, variables)
            projects_nodes = projects_result.get("data", {}).get("user", {}).get("projectsV2", {}).get("nodes", [])
            for p in projects_nodes:
                profile["project_boards"].append({
                    "title": p.get("title"),
                    "url": p.get("url"),
                    "number": p.get("number"),
                    "closed": p.get("closed"),
                    "created_at": p.get("createdAt"),
                })

        # Calculate profile score before returning
        profile["profile_score"] = calculate_profile_score(profile)

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

@app.route('/api/github/<username>', methods=['GET'])
def api_github_profile(username):
    data = fetch_github_data(username)
    if "error" in data:
        return jsonify({"error": data["error"]}), 404
    return jsonify(data)
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
