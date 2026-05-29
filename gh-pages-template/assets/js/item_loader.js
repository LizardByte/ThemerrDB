/* global $, changeVideo, document, window */
/**
 * @file Loads ThemerrDB static site item cards and search results.
 */

/**
 * GitHub organization that owns the database repository.
 *
 * @type {string}
 */
let org_name = "LizardByte"

/**
 * Base URL for published database assets.
 *
 * @type {string}
 */
let base_url = `https://app.${org_name.toLowerCase()}.dev`

/**
 * Repository or local folder that contains database assets.
 *
 * @type {string}
 */
let themerr_database = "ThemerrDB"
// for local testing in a JetBrains IDE
// base_url = `http://localhost:63342/ThemerrDB/`
// themerr_database = "database"

/**
 * Disable Ajax caching so generated JSON updates are fetched fresh.
 *
 * @returns {void}
 */
$(document).ready(function(){
    // Set cache = false for all jquery ajax requests.
    $.ajaxSetup({
        cache: false,
    })
})


/**
 * Display configuration for each database category.
 *
 * @type {Object.<string, {
 *   all_search_items: Object[],
 *   base_url: string,
 *   container: HTMLElement,
 *   database: string,
 *   database-logo: string,
 *   initialized: boolean,
 *   section_id: string,
 *   title: string
 * }>}
 */
let types_dict = {
    "games": {
        "all_search_items": [],
        "base_url": `${base_url}/${themerr_database}/games/`,
        "container": document.getElementById("games-container"),
        "database": "igdb",
        "database-logo": "https://pbs.twimg.com/profile_images/1186326995254288385/_LV6aKaA_400x400.jpg",
        "initialized": false,
        "section_id": "Games",
        "title": "Games",
    },
    "game_collections": {
        "all_search_items": [],
        "base_url": `${base_url}/${themerr_database}/game_collections/`,
        "container": document.getElementById("game-collections-container"),
        "database": "igdb",
        "database-logo": "https://pbs.twimg.com/profile_images/1186326995254288385/_LV6aKaA_400x400.jpg",
        "initialized": false,
        "section_id": "Game Collections",
        "title": "Game Collections",
    },
    "game_franchises": {
        "all_search_items": [],
        "base_url": `${base_url}/${themerr_database}/game_franchises/`,
        "container": document.getElementById("game-franchises-container"),
        "database": "igdb",
        "database-logo": "https://pbs.twimg.com/profile_images/1186326995254288385/_LV6aKaA_400x400.jpg",
        "initialized": false,
        "section_id": "Game Franchises",
        "title": "Game Franchises",
    },
    "movies": {
        "all_search_items": [],
        "base_url": `${base_url}/${themerr_database}/movies/`,
        "container": document.getElementById("movies-container"),
        "database": "themoviedb",
        "database-logo": "https://www.themoviedb.org/assets/2/v4/logos/v2/blue_square_2-d537fb228cf3ded904ef09b136fe3fec72548ebc1fea3fbbd1ad9e36364db38b.svg",
        "initialized": false,
        "section_id": "Movies",
        "title": "Movies",
    },
    "movie_collections": {
        "all_search_items": [],
        "base_url": `${base_url}/${themerr_database}/movie_collections/`,
        "container": document.getElementById("movie-collections-container"),
        "database": "themoviedb",
        "database-logo": "https://www.themoviedb.org/assets/2/v4/logos/v2/blue_square_2-d537fb228cf3ded904ef09b136fe3fec72548ebc1fea3fbbd1ad9e36364db38b.svg",
        "initialized": false,
        "section_id": "Movie Collections",
        "title": "Movie Collections",
    },
    "tv_shows": {
        "all_search_items": [],
        "base_url": `${base_url}/${themerr_database}/tv_shows/`,
        "container": document.getElementById("tv-shows-container"),
        "database": "themoviedb",
        "database-logo": "https://www.themoviedb.org/assets/2/v4/logos/v2/blue_square_2-d537fb228cf3ded904ef09b136fe3fec72548ebc1fea3fbbd1ad9e36364db38b.svg",
        "initialized": false,
        "section_id": "TV Shows",
        "title": "TV Shows",
    }
}


/**
 * Top-level content sections hidden while search results are visible.
 *
 * @type {string[]}
 */
let content_section_ids = Object.values(types_dict).map(type_config => type_config['section_id'])

/**
 * Currently selected theme category.
 *
 * @type {string|null}
 */
let active_type = null


/**
 * Return the currently selected theme category.
 *
 * @returns {string|null} Active theme category key.
 */
let get_active_type = function () {
    return active_type
}


/**
 * Return the section element for a category.
 *
 * @param {string} type Database category key from `types_dict`.
 * @returns {HTMLElement|null} Matching section element.
 */
let get_type_section = function (type) {
    return document.getElementById(types_dict[type]['section_id'])
}


/**
 * Normalize a category label for hash comparisons.
 *
 * @param {string} value Category label or hash value.
 * @returns {string} Normalized category token.
 */
let normalize_theme_type = function (value) {
    return value.toLowerCase().replaceAll(/[\s-]+/g, "_")
}


/**
 * Return the category key represented by a URL hash.
 *
 * @param {string} hash Current location hash.
 * @returns {string|null} Matching category key.
 */
let get_type_from_hash = function (hash) {
    let normalized_hash = normalize_theme_type(decodeURIComponent(hash.replace(/^#/, "")))
    for (let type in types_dict) {
        let type_config = types_dict[type]
        if (
            normalized_hash === normalize_theme_type(type) ||
            normalized_hash === normalize_theme_type(type_config['section_id']) ||
            normalized_hash === normalize_theme_type(type_config['title'])
        ) {
            return type
        }
    }

    return null
}


/**
 * Show or hide the theme type card picker.
 *
 * @param {boolean} hidden Whether the picker should be hidden.
 * @returns {void}
 */
let set_theme_type_picker_hidden = function (hidden) {
    document.getElementById("Theme Types").classList.toggle("d-none", hidden)
}


/**
 * Update the selected visual state of theme type cards.
 *
 * @param {string|null} type Selected database category key.
 * @returns {void}
 */
let set_theme_type_card_selected = function (type) {
    for (let card of document.querySelectorAll(".theme-type-card")) {
        let selected = card.dataset.themeType === type
        card.classList.toggle("border", selected)
        card.classList.toggle("border-0", !selected)
        card.classList.toggle("border-warning", selected)
        card.classList.toggle("border-3", selected)
        card.setAttribute("aria-pressed", selected ? "true" : "false")
    }
}


/**
 * Show or hide the normal content sections.
 *
 * @param {boolean} hidden Whether the sections should be hidden.
 * @returns {void}
 */
let set_content_sections_hidden = function (hidden) {
    for (let section_id of content_section_ids) {
        let section = document.getElementById(section_id)
        let visible = !hidden && active_type !== null && section_id === types_dict[active_type]['section_id']
        section.classList.toggle("d-none", !visible)
    }
}


/**
 * Fetch the page count for a database category.
 *
 * @param {string} type Database category key from `types_dict`.
 * @returns {number} Total available pages.
 */
let load_total_pages = function (type) {
    let total_pages = 1
    $.ajax({
        async: false,
        url: `${types_dict[type]['base_url']}pages.json`,
        type: "GET",
        dataType: "json",
        success: function (result) {
            total_pages = result['pages']
        }
    })

    return total_pages
}


/**
 * Append the load-more controls for a category.
 *
 * @param {string} type Database category key from `types_dict`.
 * @param {HTMLElement} item_type_container Container that receives item cards.
 * @param {number} total_pages Total available pages.
 * @returns {void}
 */
let append_load_more_controls = function (type, item_type_container, total_pages) {
    let page = 1

    let load_more_button_container = document.createElement("div")
    load_more_button_container.className = "d-flex justify-content-center"
    types_dict[type]['container'].appendChild(load_more_button_container)

    let load_more_button = document.createElement("button")
    load_more_button.innerHTML = "Load More"
    load_more_button.className = "btn btn-warning rounded-0"
    load_more_button_container.appendChild(load_more_button)

    let load_more_button_clicked = false
    window.addEventListener("scroll", function() {
        if (active_type !== type) {
            return
        }

        let load_more_button_rect = load_more_button.getBoundingClientRect()
        if (!load_more_button_clicked && load_more_button_rect.top < window.innerHeight) {
            load_more_button_clicked = true
            load_more_button.click()

            setTimeout(function() {
                load_more_button_clicked = false
            }, 100)
        }
    })

    load_more_button.addEventListener("click", function() {
        if (page <= total_pages) {
            $.ajax({
                url: `${types_dict[type]['base_url']}all_page_${page}.json`,
                type: "GET",
                dataType: "json",
                success: function (result) {
                    populate_results(type, result, item_type_container)
                },
            })

            page += 1
        }
        if (page > total_pages) {
            load_more_button.classList.add("d-none")
            load_more_button.disabled = true
        }
    })

    load_more_button.click()
}


/**
 * Initialize paginated item loading for one database category.
 *
 * @param {string} type Database category key from `types_dict`.
 * @returns {void}
 */
let initialize_type_loader = function (type) {
    if (types_dict[type]['initialized']) {
        return
    }

    types_dict[type]['initialized'] = true

    let total_pages = load_total_pages(type)
    let item_type_container = document.createElement("div")
    types_dict[type]['container'].appendChild(item_type_container)

    append_load_more_controls(type, item_type_container, total_pages)
}


/**
 * Select a theme category and load its items.
 *
 * @param {string} type Database category key from `types_dict`.
 * @param {boolean} scroll_to_section Whether to scroll to the selected section.
 * @returns {void}
 */
let show_theme_type = function (type, scroll_to_section = false) {
    if (!types_dict[type]) {
        return
    }

    active_type = type
    globalThis.history.replaceState(null, "", `#${encodeURIComponent(types_dict[type]['section_id'])}`)
    set_theme_type_card_selected(type)
    set_content_sections_hidden(false)
    initialize_type_loader(type)

    let section = get_type_section(type)
    if (scroll_to_section && typeof section.scrollIntoView === "function") {
        section.scrollIntoView({behavior: "smooth", block: "start"})
    }
}


/**
 * Attach category card click handlers and open direct hash links.
 *
 * @returns {void}
 */
let initialize_theme_type_cards = function () {
    for (let card of document.querySelectorAll(".theme-type-card")) {
        card.addEventListener("click", function () {
            show_theme_type(card.dataset.themeType, true)
        })
    }

    let hash_type = get_type_from_hash(globalThis.location.hash)
    if (hash_type !== null) {
        show_theme_type(hash_type)
    }
}


/**
 * Render item cards into a category container.
 *
 * @param {string} type Database category key from `types_dict`.
 * @param {Object[]} result Items to render.
 * @param {HTMLElement} item_type_container Container that receives item cards.
 * @returns {void}
 */
let populate_results = function (type, result, item_type_container) {
    for (let item in result) {
        // create the container here, so that they are ordered properly
        // ajax requests are async (by default), so the order is not guaranteed
        let item_container = document.createElement("div")
        item_container.className = "container mb-5 shadow border-0 card-body rounded-0 px-0"
        item_type_container.appendChild(item_container)

        $.ajax({
            url: `${types_dict[type]['base_url']}/${types_dict[type]['database']}/${result[item]['id']}.json`,
            type: "GET",
            dataType: "json",
            success: function (themerr_data) {
                let year = null
                let poster_src = null
                let title = null
                let summary = null
                let database_link_src = null
                let edit_link = null

                if (type === "games") {
                    // get the lowest year from release dates
                    for (let release in themerr_data['release_dates']) {
                        if (year == null || themerr_data['release_dates'][release]['y'] < year) {
                            year = themerr_data['release_dates'][release]['y']
                        }
                    }
                    poster_src = themerr_data['cover']['url'].replace('/t_thumb/', '/t_cover_big/')
                    title = themerr_data['name']
                    summary = themerr_data['summary']
                    database_link_src = themerr_data['url']
                    edit_link = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-theme&template=theme.yml&title=${encodeURIComponent('[GAME]: ')}${encodeURIComponent(title)}&database_url=${encodeURIComponent(database_link_src)}`
                } else if (type === "game_collections" || type === "game_franchises") {
                    title = themerr_data['name']
                    database_link_src = themerr_data['url']
                    let issue_type = type === "game_franchises" ? "GAME FRANCHISE" : "GAME COLLECTION"
                    let issue_title = encodeURIComponent(`[${issue_type}]: `)
                    edit_link = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-theme&template=theme.yml&title=${issue_title}${encodeURIComponent(title)}&database_url=${encodeURIComponent(database_link_src)}`
                } else if (type === "movies") {
                    year = themerr_data['release_date'].split("-")[0]
                    poster_src = `https://image.tmdb.org/t/p/w185${themerr_data['poster_path']}`
                    title = themerr_data['title']
                    summary = themerr_data['overview']
                    database_link_src = `https://www.themoviedb.org/movie/${themerr_data['id']}`
                    edit_link = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-theme&template=theme.yml&title=${encodeURIComponent('[MOVIE]: ')}${encodeURIComponent(title)}&database_url=${encodeURIComponent(database_link_src)}`
                } else if (type === "movie_collections") {
                    poster_src = `https://image.tmdb.org/t/p/w185${themerr_data['poster_path']}`
                    title = themerr_data['name']
                    summary = themerr_data['overview']
                    database_link_src = `https://www.themoviedb.org/collection/${themerr_data['id']}`
                    edit_link = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-theme&template=theme.yml&title=${encodeURIComponent('[MOVIE COLLECTION]: ')}${encodeURIComponent(title)}&database_url=${encodeURIComponent(database_link_src)}`
                } else if (type === "tv_shows") {
                    year = themerr_data['first_air_date'].split("-")[0]
                    poster_src = `https://image.tmdb.org/t/p/w185${themerr_data['poster_path']}`
                    title = themerr_data['name']
                    summary = themerr_data['overview']
                    database_link_src = `https://www.themoviedb.org/tv/${themerr_data['id']}`
                    edit_link = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-theme&template=theme.yml&title=${encodeURIComponent('[TV SHOW]: ')}${encodeURIComponent(title)}&database_url=${encodeURIComponent(database_link_src)}`
                }

                let inner_container = document.createElement("div")
                inner_container.className = "container py-4 px-1"
                item_container.appendChild(inner_container)

                let table_row = document.createElement("div")
                table_row.className = "d-flex g-0"
                inner_container.appendChild(table_row)

                let poster = document.createElement("img")
                poster.className = "d-flex flex-column px-3 rounded-0 mx-auto"
                poster.src = poster_src
                poster.alt = ""
                poster.height = 200
                table_row.appendChild(poster)

                let data_column = document.createElement("div")
                // Border utilities like .border-* that generated from bootstrap original $theme-colors Sass map don’t
                // yet respond to color modes, however, any .border-*-subtle utility will. This will be resolved in v6.
                // https://getbootstrap.com/docs/5.3/utilities/borders/#color
                // border-dark-subtle is a decent compromise for now
                data_column.className = "d-flex flex-column border-dark-subtle px-3 border-start w-100"
                table_row.appendChild(data_column)

                let text_container = document.createElement("div")
                data_column.appendChild(text_container)

                let item_title = document.createElement("h4")
                item_title.className = "card-title mb-3 fw-bolder ms-0 mx-2"
                item_title.textContent = `${title} (${year})`
                text_container.appendChild(item_title)

                let item_summary = document.createElement("p")
                item_summary.className = "card-text ms-0 mx-2"
                item_summary.textContent = summary
                text_container.appendChild(item_summary)

                let card_footer = document.createElement("div")
                // move to bottom of data_column
                card_footer.className = "row w-100 mt-auto pt-4"
                data_column.appendChild(card_footer)

                let database_column = document.createElement("div")
                database_column.className = "col-auto align-self-center me-1"
                card_footer.appendChild(database_column)

                let database_link = document.createElement("a")
                database_link.href = database_link_src
                database_link.target = "_blank"
                database_column.appendChild(database_link)

                let database_logo = document.createElement("img")
                database_logo.src = types_dict[type]['database-logo']
                database_logo.width = 40
                database_link.appendChild(database_logo)

                let player_column = document.createElement("div")
                player_column.className = "col-auto align-self-center me-1"
                card_footer.appendChild(player_column)

                let player_logo = document.createElement("i")
                let youtube_id = themerr_data['youtube_theme_url'].split("v=")[1]
                player_logo.className = "fa-regular fa-play-circle fa-2x align-middle"
                player_logo.style.cssText = "cursor:pointer;cursor:hand"
                player_logo.onclick = function () {
                    changeVideo(youtube_id)
                }
                player_column.appendChild(player_logo)

                let edit_column = document.createElement("div")
                // right align with ms-auto
                edit_column.className = "col-auto align-self-center ms-auto"
                card_footer.appendChild(edit_column)

                let edit_button_link = document.createElement("a")
                edit_button_link.href = edit_link
                edit_button_link.target = "_blank"
                edit_column.appendChild(edit_button_link)

                let edit_button = document.createElement("button")
                edit_button.className = "btn btn-danger rounded-0"
                edit_button.type = "button"
                edit_button.textContent = "Edit"
                edit_button_link.appendChild(edit_button)
            }
        })
    }
}


/**
 * Append a supported search form field to a FormData payload.
 *
 * @param {FormData} data Search form payload.
 * @param {HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement} field Search form field.
 * @returns {void}
 */
let append_search_field = function (data, field) {
    if (field.type === "submit" || field.type === "button") {
        return
    }

    if (field.type === "checkbox") {
        data.append(field.id, field.checked)
        return
    }

    if (field.type === "radio") {
        if (field.checked) {
            data.append(field.id, field.value)
        }
        return
    }

    data.append(field.id, field.value)
}


/**
 * Collect search form values.
 *
 * @returns {FormData} Search form payload.
 */
let get_search_form_data = function () {
    let data = new FormData()
    let all = document.querySelectorAll("#searchForm input, #searchForm textarea, #searchForm select")
    for (let field of all) {
        append_search_field(data, field)
    }

    return data
}


/**
 * Load and cache all searchable items for a database category.
 *
 * @param {string} type Database category key from `types_dict`.
 * @returns {void}
 */
let load_search_items = function (type) {
    if (types_dict[type]['all_search_items'].length !== 0) {
        return
    }

    let page = 1
    let total_pages = load_total_pages(type)

    while (page <= total_pages) {
        $.ajax({
            async: false,
            url: `${types_dict[type]['base_url']}all_page_${page}.json`,
            type: "GET",
            dataType: "json",
            success: function (result) {
                for (let item of result) {
                    types_dict[type]['all_search_items'].push(item)
                }
            }
        })
        page += 1
    }
}


/**
 * Score cached items against a search term.
 *
 * @param {string} type Database category key from `types_dict`.
 * @param {string} search_term Search text.
 * @returns {Object[]} Items with scores at or above the display threshold.
 */
let get_search_results = function (type, search_term) {
    let result = []
    let normalized_search_term = search_term.toLowerCase()
    for (let item of types_dict[type]['all_search_items']) {
        item['score'] = globalThis.levenshteinDistance(normalized_search_term, item['title'].toLowerCase())
        if (item['score'] >= 40) {
            result.push(item)
        }
    }

    return result
}


/**
 * Add the clear-results button and restore normal content when it is clicked.
 *
 * @param {HTMLElement} search_container Search results container.
 * @returns {void}
 */
let add_clear_results_button = function (search_container) {
    let clear_results_button = document.createElement("button")
    clear_results_button.className = "btn btn-danger rounded-0 mb-5"
    clear_results_button.textContent = "Clear Results"
    search_container.appendChild(clear_results_button)
    clear_results_button.onclick = function () {
        search_container.innerHTML = ""
        set_theme_type_picker_hidden(false)
        set_content_sections_hidden(false)
    }
}


/**
 * Run the search form and render matching item cards.
 *
 * @returns {void}
 */
let run_search = function () {
    // get the search container
    let search_container = document.getElementById("search-container")
    search_container.innerHTML = ""

    let data = get_search_form_data()

    // extract the search values from the data object
    let search_type = data.get("search_type")
    let search_term = data.get("search_term")

    // if the search term is empty, don't do anything
    if (search_term === "") {
        return
    }

    // hide the existing content
    set_theme_type_picker_hidden(true)
    set_content_sections_hidden(true)

    // get the item type
    let type = Object.keys(types_dict)[search_type]

    load_search_items(type)
    let result = get_search_results(type, search_term)

    // add a clear results button
    add_clear_results_button(search_container)

    let item_type_container = document.createElement("div")
    search_container.appendChild(item_type_container)

    let sorted = result.toSorted(globalThis.rankingSorter('score', 'title'))

    populate_results(type, sorted, item_type_container)
}

globalThis.run_search = run_search
globalThis.themerrItemLoader = {
    add_clear_results_button,
    append_load_more_controls,
    append_search_field,
    content_section_ids,
    get_active_type,
    get_search_form_data,
    get_search_results,
    get_type_from_hash,
    get_type_section,
    initialize_theme_type_cards,
    initialize_type_loader,
    load_search_items,
    load_total_pages,
    normalize_theme_type,
    populate_results,
    run_search,
    set_content_sections_hidden,
    set_theme_type_card_selected,
    set_theme_type_picker_hidden,
    show_theme_type,
    types_dict,
}

/**
 * Hook Enter key submission into the custom search renderer.
 *
 * @returns {void}
 */
$(document).ready(function() {
    initialize_theme_type_cards()

    // replace default function of enter key in search form
    document.getElementById("searchForm").addEventListener("keypress", function (e) {
        if (e.key === "Enter") {
            e.preventDefault()
            run_search()
        }
    })
})
