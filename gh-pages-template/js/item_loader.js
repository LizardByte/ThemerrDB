let org_name = "LizardByte"
let base_url = `https://app.${org_name.toLowerCase()}.dev`
let themerr_database = "ThemerrDB"
// for local testing in a JetBrains IDE
// base_url = `http://localhost:63342/ThemerrDB/`
// themerr_database = "database"


// load external js scripts
$.getScript('https://app.lizardbyte.dev/js/levenshtein_distance.js')
$.getScript('https://app.lizardbyte.dev/js/ranking_sorter.js')


$(document).ready(function(){
    // Set cache = false for all jquery ajax requests.
    $.ajaxSetup({
        cache: false,
    })
})


// create item cards
let types_dict = {
    "games": {
        "base_url": `${base_url}/${themerr_database}/games/`,
        "container": document.getElementById("games-container"),
        "database": "igdb",
        "database-logo": "https://pbs.twimg.com/profile_images/1186326995254288385/_LV6aKaA_400x400.jpg",
        "all_search_items": [],
    },
    "game_collections": {
        "base_url": `${base_url}/${themerr_database}/game_collections/`,
        "container": document.getElementById("game-collections-container"),
        "database": "igdb",
        "database-logo": "https://pbs.twimg.com/profile_images/1186326995254288385/_LV6aKaA_400x400.jpg",
        "all_search_items": [],
    },
    "game_franchises": {
        "base_url": `${base_url}/${themerr_database}/game_franchises/`,
        "container": document.getElementById("game-franchises-container"),
        "database": "igdb",
        "database-logo": "https://pbs.twimg.com/profile_images/1186326995254288385/_LV6aKaA_400x400.jpg",
        "all_search_items": [],
    },
    "movies": {
        "base_url": `${base_url}/${themerr_database}/movies/`,
        "container": document.getElementById("movies-container"),
        "database": "themoviedb",
        "database-logo": "https://www.themoviedb.org/assets/2/v4/logos/v2/blue_square_2-d537fb228cf3ded904ef09b136fe3fec72548ebc1fea3fbbd1ad9e36364db38b.svg",
        "all_search_items": [],
    },
    "movie_collections": {
        "base_url": `${base_url}/${themerr_database}/movie_collections/`,
        "container": document.getElementById("movie-collections-container"),
        "database": "themoviedb",
        "database-logo": "https://www.themoviedb.org/assets/2/v4/logos/v2/blue_square_2-d537fb228cf3ded904ef09b136fe3fec72548ebc1fea3fbbd1ad9e36364db38b.svg",
        "all_search_items": [],
    }
}


$(document).ready(function(){
    for (let type in types_dict) {
        let page = 1
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

        let item_type_container = document.createElement("div")
        types_dict[type]['container'].appendChild(item_type_container)

        let load_more_button_container = document.createElement("div")
        load_more_button_container.className = "d-flex justify-content-center"
        types_dict[type]['container'].appendChild(load_more_button_container)

        let load_more_button = document.createElement("button")
        load_more_button.innerHTML = "Load More"
        load_more_button.className = "btn btn-warning rounded-0"
        load_more_button_container.appendChild(load_more_button)

        // checking if the load_more_button is in the view port
        let load_more_button_clicked = false
        window.addEventListener("scroll", function() {
            let load_more_button_rect = load_more_button.getBoundingClientRect()
            console.log(`${load_more_button_rect.bottom}, ${load_more_button_rect.top}`)
            // if the top of the button is in the view port and the button has not been clicked
            if (!load_more_button_clicked && load_more_button_rect.top < window.innerHeight) {
                load_more_button_clicked = true
                load_more_button.click()

                // allow the button to be clicked again after 0.1 second
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

                // increase page number
                page += 1
            }
            if (page > total_pages) {
                // hide and disable the button if there are no more pages
                load_more_button.classList.add("d-none")
                load_more_button.disabled = true
            }
        })

        // click the button once to load the first page automatically
        load_more_button.click()
    }
})


let populate_results = function (type, result, item_type_container) {
    for (let item in result) {
        // create the container here, so that they are ordered properly
        // ajax requests are async (by default), so the order is not guaranteed
        let item_container = document.createElement("div")
        item_container.className = "container mb-5 shadow border-0 bg-dark rounded-0 px-0"
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
                    edit_link = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-theme&template=theme.yml&title=${encodeURIComponent('[GAME]: ')}${encodeURIComponent(title)}&databause_url=${encodeURIComponent(database_link_src)}`
                } else if (type === "game_collections" || type === "game_franchises") {
                    year = null
                    poster_src = null
                    title = themerr_data['name']
                    summary = null
                    database_link_src = themerr_data['url']
                    edit_link = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-theme&template=theme.yml&title=${encodeURIComponent('[GAME COLLECTION]: ')}${encodeURIComponent(title)}&databause_url=${encodeURIComponent(database_link_src)}`
                } else if (type === "movies") {
                    year = themerr_data['release_date'].split("-")[0]
                    poster_src = `https://image.tmdb.org/t/p/w185${themerr_data['poster_path']}`
                    title = themerr_data['title']
                    summary = themerr_data['overview']
                    database_link_src = `https://www.themoviedb.org/movie/${themerr_data['id']}`
                    edit_link = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-theme&template=theme.yml&title=${encodeURIComponent('[MOVIE]: ')}${encodeURIComponent(title)}&database_url=${encodeURIComponent(database_link_src)}`
                } else if (type === "movie_collections") {
                    year = null
                    poster_src = `https://image.tmdb.org/t/p/w185${themerr_data['poster_path']}`
                    title = themerr_data['name']
                    summary = themerr_data['overview']
                    database_link_src = `https://www.themoviedb.org/collection/${themerr_data['id']}`
                    edit_link = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-theme&template=theme.yml&title=${encodeURIComponent('[MOVIE COLLECTION]: ')}${encodeURIComponent(title)}&database_url=${encodeURIComponent(database_link_src)}`
                }

                let inner_container = document.createElement("div")
                inner_container.className = "container py-4 px-1"
                item_container.appendChild(inner_container)

                let table_row = document.createElement("div")
                table_row.className = "d-flex g-0 text-white"
                inner_container.appendChild(table_row)

                let poster = document.createElement("img")
                poster.className = "d-flex flex-column px-3 rounded-0 mx-auto"
                poster.src = poster_src
                poster.alt = ""
                poster.height = 200
                table_row.appendChild(poster)

                let data_column = document.createElement("div")
                data_column.className = "d-flex flex-column border-white px-3 border-start w-100"
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
                edit_button.className = "btn-danger btn-outline-light rounded-0 btn"
                edit_button.type = "button"
                edit_button.textContent = "Edit"
                edit_button_link.appendChild(edit_button)
            }
        })
    }
}


let run_search = function () {
    // get the search container
    let search_container = document.getElementById("search-container")
    search_container.innerHTML = ""

    // create FormData object
    let data = new FormData()

    // append field and values to FormData object
    let all = document.querySelectorAll("#searchForm input, #searchForm textarea, #searchForm select")
    for (let field of all) {
        // exclude submit and buttons
        if (field.type !== "submit" && field.type !== "button") {
            // checkbox fields
            if (field.type === "checkbox") {
                data.append(field.id, field.checked)
            }
            // radio fields... must be checked
            else if (field.type === "radio") {
                if (field.checked) {
                    data.append(field.id, field.value)
                }
            }
            // other fields
            else {
                data.append(field.id, field.value)
            }
        }
    }

    // extract the search values from the data object
    let search_type = data.get("search_type")
    let search_term = data.get("search_term")

    // if the search term is empty, don't do anything
    if (search_term === "") {
        return
    }

    // hide the existing content
    document.getElementById("Games").classList.add("d-none")
    document.getElementById("Game Collections").classList.add("d-none")
    document.getElementById("Game Franchises").classList.add("d-none")
    document.getElementById("Movies").classList.add("d-none")
    document.getElementById("Movie Collections").classList.add("d-none")

    // get the item type
    let type = Object.keys(types_dict)[search_type]

    // check if the all_search_items array is empty
    if (types_dict[type]['all_search_items'].length === 0) {
        // reset page count
        let page = 1
        let total_pages = 1

        // get total number of pages
        $.ajax({
            async: false,
            url: `${types_dict[type]['base_url']}pages.json`,
            type: "GET",
            dataType: "json",
            success: function (result) {
                total_pages = result['pages']
            }
        })

        // loop through all pages
        while (page <= total_pages) {
            $.ajax({
                async: false,
                url: `${types_dict[type]['base_url']}all_page_${page}.json`,
                type: "GET",
                dataType: "json",
                success: function (result) {
                    // loop through all items in the page
                    for (let item of result) {
                        types_dict[type]['all_search_items'].push(item)
                    }
                }
            })
            page += 1
        }
    }

    // results list
    let result = []

    // loop through all search items
    for (let item of types_dict[type]['all_search_items']) {
        // search using levenshtein distance
        item['score'] = levenshteinDistance.get(search_term.toLowerCase(), item['title'].toLowerCase())
        if (item['score'] >= 40) {
            result.push(item)
        }
    }

    // add a clear results button
    let clear_results_button = document.createElement("button")
    clear_results_button.className = "btn btn-danger rounded-0 mb-5"
    clear_results_button.textContent = "Clear Results"
    search_container.appendChild(clear_results_button)
    clear_results_button.onclick = function () {
        search_container.innerHTML = ""
        document.getElementById("Games").classList.remove("d-none")
        document.getElementById("Game Collections").classList.remove("d-none")
        document.getElementById("Game Franchises").classList.remove("d-none")
        document.getElementById("Movies").classList.remove("d-none")
        document.getElementById("Movie Collections").classList.remove("d-none")
    }

    let item_type_container = document.createElement("div")
    search_container.appendChild(item_type_container)

    let sorted = result.sort(rankingSorter('score', 'title'))

    populate_results(type, sorted, item_type_container)
}

$(document).ready(function() {
    // replace default function of enter key in search form
    document.getElementById("searchForm").addEventListener("keypress", function (e) {
        if (e.key === "Enter") {
            e.preventDefault()
            run_search()
        }
    })
})
