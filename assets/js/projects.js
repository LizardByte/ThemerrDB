// projects section script

// get project container
let container
let org_name = "LizardByte"
let base_url = `https://app.${org_name.toLowerCase()}.dev`
let cache_repo = "dashboard"
const organizations_url = "https://raw.githubusercontent.com/LizardByte/.github/master/organizations.json"
let shared_web_url = "https://cdn.jsdelivr.net/npm/@lizardbyte/shared-web@2026.1107.31840"


function onDocumentReady(callback) {
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", callback)
        return
    }

    callback()
}

function fetchWithNoCache(url, options = {}) {
    return fetch(url, {
        ...options,
        cache: "no-store",
    })
}

function fetchJson(url) {
    return fetchWithNoCache(url)
        .then(function (response) {
            if (!response.ok) {
                throw new Error(`Request failed for ${url}: ${response.status}`)
            }

            return response.json()
        })
}

function shouldProcessRepo(repo) {
    if (repo['private'] === true) return false;
    if (repo['archived'] === true) return false;
    if (repo['description'] === null) return false;
    return !(repo['fork'] === true && !repo['topics'].includes("featured-fork"));
}

function projectUrl(repo) {
    try {
        const homepage = new URL(repo.homepage)
        if (["https:", "http:"].includes(homepage.protocol)) return homepage.href
    } catch {
        // Repositories without a valid homepage link to GitHub.
    }
    return repo.html_url
}

function githubIdentity(value) {
    try {
        const url = new URL(value.replace(/^git@github\.com:/i, "https://github.com/"))
        const parts = url.pathname.split("/").filter(Boolean)
        if (url.hostname !== "github.com" || parts.length !== 2) return null
        return parts.join("/").replace(/\.git$/i, "").toLowerCase()
    } catch {
        return null
    }
}

function createBannerElement(repo) {
    let banner_div = document.createElement("div")
    banner_div.className = "hover-zoom"

    let banner_link = document.createElement("a")
    banner_link.className = "crowdin-ignore"
    banner_link.href = projectUrl(repo)
    banner_link.target = "_blank"
    banner_link.rel = "noopener noreferrer"
    banner_div.append(banner_link)

    let banner = document.createElement("img")
    banner.className = "card-img-top rounded-0"
    banner.src = `${base_url}/${cache_repo}/${repo.dashboard_paths.banner_small}`
    banner.alt = ""
    banner_link.append(banner)

    return banner_div
}

function createCardBody(repo) {
    let card_body = document.createElement("div")
    card_body.className = "card-body p-4 rounded-0"

    let card_title_link = document.createElement("a")
    card_title_link.className = "text-decoration-none project-card-link crowdin-ignore"
    card_title_link.href = projectUrl(repo)
    card_title_link.target = "_blank"
    card_title_link.rel = "noopener noreferrer"
    card_body.appendChild(card_title_link)

    let card_title_text = document.createElement("h5")
    card_title_text.className = "card-title mb-3 fw-bolder crowdin-ignore"
    card_title_text.textContent = repo['name']

    if (repo['fork'] === true && repo['topics'].includes("featured-fork")) {
        let fork_badge = document.createElement("span")
        fork_badge.className = "badge bg-info ms-2"
        fork_badge.textContent = "Fork"
        card_title_text.appendChild(fork_badge)
    }

    card_title_link.appendChild(card_title_text)

    const organization = document.createElement("p")
    organization.className = "project-organization small text-muted crowdin-ignore"
    organization.textContent = repo.owner.login
    card_body.appendChild(organization)

    let card_paragraph = document.createElement("p")
    card_paragraph.className = "card-text mb-0"
    card_paragraph.textContent = repo['description']
    card_body.appendChild(card_paragraph)

    return card_body
}

function loadCommitActivity(repo, card_footer) {
    fetchJson(`${base_url}/${cache_repo}/github/commitActivity/${repo.dashboard_key}.json`)
        .then(function (commitActivity) {
            let activity_container = document.createElement("div")
            activity_container.className = "commit-activity-graph mt-2 mb-2 mx-3"
            activity_container.style.cssText = "display: flex; gap: 2px; height: 32px; align-items: flex-end;"

            let maxCommits = Math.max(...commitActivity.map(week => week.total), 0)

            for (let week of commitActivity) {
                let bar = document.createElement("div")
                let height = maxCommits > 0 ? (week.total / maxCommits) * 100 : 0
                let intensity = 0.3 + (height / 100) * 0.7

                bar.className = week.total === 0 ? 'commit-bar-empty crowdin-ignore' : 'commit-bar-active crowdin-ignore'
                bar.style.cssText = `
                    flex: 1;
                    min-width: 2px;
                    height: ${Math.max(height, 10)}%;
                    border-radius: 1px;
                    transition: all 0.2s ease;
                    --commit-bar-opacity: ${intensity};
                `
                bar.title = `${week.total} commits this week`
                activity_container.appendChild(bar)
            }

            card_footer.insertBefore(activity_container, card_footer.firstChild)
        })
        .catch(function () {
            console.log(`No commit activity data available for ${repo['name']}`)
        })
}

function createRepoDataRow(repo, card_footer) {
    let repo_data_row = document.createElement("div")
    repo_data_row.className = "d-flex align-items-center"
    card_footer.appendChild(repo_data_row)

    let github_link = document.createElement("a")
    github_link.className = "nav-link project-nav-link ms-3"
    github_link.href = repo['html_url']
    github_link.target = "_blank"
    repo_data_row.appendChild(github_link)

    let github_link_image = document.createElement("i")
    github_link_image.className = "fa-fw fa-brands fa-github"
    github_link.prepend(github_link_image)

    let star_link = document.createElement("a")
    star_link.className = "nav-link nav-link-sm project-nav-link ms-3 crowdin-ignore"
    star_link.href = `https://star-history.com/#${repo['full_name']}`
    star_link.target = "_blank"
    star_link.textContent = globalThis.formatNumber(repo['stargazers_count'])
    repo_data_row.appendChild(star_link)

    let star_link_image = document.createElement("i")
    star_link_image.className = "fa-fw fa-solid fa-star"
    star_link.prepend(star_link_image)

    let fork_link = document.createElement("a")
    fork_link.className = "nav-link nav-link-sm project-nav-link ms-3 crowdin-ignore"
    fork_link.href = `https://github.com/${repo['full_name']}/network/members`
    fork_link.target = "_blank"
    fork_link.textContent = globalThis.formatNumber(repo['forks'])
    repo_data_row.appendChild(fork_link)

    let fork_link_image = document.createElement("i")
    fork_link_image.className = "fa-fw fa-solid fa-code-fork"
    fork_link.prepend(fork_link_image)

    return repo_data_row
}

function addDocsLink(repo, readthedocs, repo_data_row) {
    for (let docs in readthedocs) {
        const docs_repo = githubIdentity(readthedocs[docs]['repository']['url']);
        if (!repo.dashboard_aliases.some(alias => alias.toLowerCase() === docs_repo)) continue;

        let docs_url = readthedocs[docs]['urls']['documentation']
        try {
            let parsedUrl = new URL(docs_url);
            if (parsedUrl.host !== "docs.lizardbyte.dev") continue;
        } catch (e) {
            console.error("Invalid URL:", docs_url, e);
            continue;
        }

        let docs_link = document.createElement("a")
        docs_link.className = "nav-link ms-3"
        docs_link.href = docs_url
        docs_link.target = "_blank"
        repo_data_row.appendChild(docs_link)

        let docs_link_image = document.createElement("img")
        docs_link_image.className = "readthedocs-icon"
        docs_link_image.src = "https://cdn.jsdelivr.net/npm/simple-icons@16/icons/readthedocs.svg"
        docs_link_image.alt = "ReadTheDocs"
        docs_link_image.title = "ReadTheDocs"
        docs_link_image.style.width = "24px"
        docs_link_image.style.height = "24px"
        docs_link.prepend(docs_link_image)
    }
}

function loadLanguageIcons(repo, card_footer) {
    fetchJson(`${base_url}/${cache_repo}/github/languages/${repo.dashboard_key}.json`)
        .then(function (languages) {
            let language_data_row = document.createElement("div")
            language_data_row.className = "card-group p-3 align-items-center"
            card_footer.appendChild(language_data_row)

            for (let language in languages) {
                let language_file = encodeURIComponent(`${language}.svg`)
                let language_icon = document.createElement("img")
                language_icon.className = "language-logo crowdin-ignore"
                language_icon.src = `${shared_web_url}/dist/language-icons/${language_file}`
                language_icon.alt = language
                language_icon.title = language
                language_data_row.append(language_icon)
            }
        })
        .catch(function () {})
}

function buildRepoCard(repo, readthedocs) {
    let column = document.createElement("div")
    column.className = "col-lg-4 mb-5"
    container.appendChild(column)

    let card = document.createElement("div")
    card.className = "card h-100 shadow border-0 rounded-0"
    column.appendChild(card)

    card.append(createBannerElement(repo))

    card.appendChild(createCardBody(repo))

    let card_footer = document.createElement("div")
    card_footer.className = "card-footer p-2 pt-0 border-0 rounded-0"
    card.appendChild(card_footer)

    loadCommitActivity(repo, card_footer)

    let repo_data_row = createRepoDataRow(repo, card_footer)
    addDocsLink(repo, readthedocs, repo_data_row)
    loadLanguageIcons(repo, card_footer)
    return column
}

function updateProjectFilters(cards, organizations) {
    const organization = document.getElementById("project-organization").value
    const terms = document.getElementById("project-search").value.toLowerCase().trim().split(/\s+/).filter(Boolean)
    let count = 0
    for (const { repo, column } of cards) {
        const text = `${repo.full_name} ${repo.description}`.toLowerCase()
        const matches = (!organization || repo.owner.login.toLowerCase() === organization.toLowerCase())
            && terms.every(term => text.includes(term))
        column.hidden = !matches
        if (matches) count += 1
    }
    const noun = count === 1 ? "project" : "projects"
    document.getElementById("project-status").textContent = count
        ? `${count} ${noun}` : "No projects match your search."

    const scope = organization ? [organization] : organizations
    const query = [...scope.map(name => `org:${name}`), "archived:true"].join(" ")
    const archive = document.getElementById("archived-projects-link")
    archive.href = `https://github.com/search?${new URLSearchParams({ q: query, type: "repositories" })}`
    archive.classList.remove("disabled")
    archive.removeAttribute("aria-disabled")
}

function createProjectBrowser(repos, readthedocs, organizations) {
    if (!Array.isArray(organizations) || !organizations.length
        || organizations.some(name => typeof name !== "string" || !/^[a-z\d][a-z\d-]*$/i.test(name))) {
        throw new Error("Invalid organization registry")
    }
    const organization = document.getElementById("project-organization")
    organizations.sort((left, right) => left.localeCompare(right))
    for (const name of organizations) {
        organization.add(new Option(name, name))
    }
    const registered = new Set(organizations.map(name => name.toLowerCase()))
    const sorted = repos.filter(repo => registered.has(repo.owner.login.toLowerCase()) && shouldProcessRepo(repo))
        .sort(globalThis.rankingSorter("stargazers_count", "full_name"))
    // Build each card once so filtering does not fetch its assets again.
    const cards = sorted.map(repo => ({ repo, column: buildRepoCard(repo, readthedocs) }))
    const update = () => updateProjectFilters(cards, organizations)
    const search = document.getElementById("project-search")
    organization.disabled = false
    search.disabled = false
    organization.addEventListener("change", update)
    search.addEventListener("input", update)
    update()
}


// create project cards
onDocumentReady(function () {
    container = document.getElementById("project-container")
    if (!container) return

    let readthedocsRequest = fetchJson(`${base_url}/${cache_repo}/readthedocs/projects.json`)
        .then(function (data) {
            return Object.values(data)
        })
        .catch(function (error) {
            console.log("No ReadTheDocs project data available", error)
            return []
        })

    let reposRequest = fetchJson(`${base_url}/${cache_repo}/github/repos.json`)
    let organizationsRequest = fetchJson(organizations_url)

    Promise.all([readthedocsRequest, reposRequest, organizationsRequest])
        .then(function ([readthedocs, result, organizations]) {
            createProjectBrowser(result, readthedocs, organizations)
        })
        .catch(function (error) {
            document.getElementById("project-status").textContent = "Projects could not be loaded. Please try again later."
            console.error("Error loading project data:", error)
        })
})
