// items section script
function rankingSorter(firstKey, secondKey) {
    return function(a, b) {
        if (a[firstKey] > b[firstKey]) {
            return -1;
        } else if (a[firstKey] < b[firstKey]) {
            return 1;
        }
        else {
            if (a[secondKey] > b[secondKey]) {
                return 1;
            } else if (a[secondKey] < b[secondKey]) {
                return -1;
            } else {
                return 0;
            }
        }
    }
}

games_container = document.getElementById("games-container")
movies_container = document.getElementById("movies-container")
let org_name = "LizardByte"
let base_url = `https://app.${org_name.toLowerCase()}.dev`
let themerr_database = "ThemerrDB"

// create project cards
$(document).ready(function(){
    // Set cache = false for all jquery ajax requests.
    $.ajaxSetup({
        cache: false,
    });
});

$(document).ready(function(){
    // get all games
    $.ajax({
        url: `${base_url}/${themerr_database}/games/igdb/all.json`,
        type: "GET",
        dataType:"json",
        success: function (result) {
            let sorted = result.sort(rankingSorter("name", "id")).reverse();

            for(let item in sorted) {
                $.ajax({
                    url: `${base_url}/${themerr_database}/games/igdb/${sorted[item]['id']}.json`,
                    type: "GET",
                    dataType: "json",
                    success: function (themerr_data) {
                        // get the lowest year from release dates
                        let found_year = null;
                        for(let release in themerr_data['release_dates']) {
                            if (found_year == null || themerr_data['release_dates'][release]['y'] < found_year) {
                                found_year = themerr_data['release_dates'][release]['y'];
                            }
                        }

                        let item_container = document.createElement("div")
                        item_container.className = "container mb-5 shadow border-0 bg-dark rounded-0 px-0"
                        games_container.appendChild(item_container)

                        let inner_container = document.createElement("div")
                        inner_container.className = "container py-4 px-1"
                        item_container.appendChild(inner_container)

                        let table_row = document.createElement("div")
                        table_row.className = "d-table-row g-0 text-white"
                        inner_container.appendChild(table_row)

                        let poster = document.createElement("img")
                        poster.className = "d-table-cell px-3 rounded-0 mx-auto"
                        poster.src = themerr_data['cover']['url'].replace('/t_thumb/','/t_cover_big/')
                        poster.alt = ""
                        poster.height = 200
                        table_row.appendChild(poster)

                        let data_column = document.createElement("div")
                        data_column.className = "d-table-cell align-top border-white my-3 px-3 border-start"
                        table_row.appendChild(data_column)

                        let item_title = document.createElement("h4")
                        item_title.className = "card-title mb-3 fw-bolder ms-0 mx-5"
                        item_title.textContent = `${themerr_data['name']} (${found_year})`
                        data_column.appendChild(item_title)

                        let item_summary = document.createElement("p")
                        item_summary.className = "card-text ms-0 mx-5"
                        item_summary.textContent = themerr_data['summary']
                        data_column.appendChild(item_summary)

                        let igdb_link = document.createElement("a")
                        igdb_link.href = themerr_data['url']
                        igdb_link.target = "_blank"
                        data_column.appendChild(igdb_link)

                        let igdb_logo = document.createElement("img")
                        igdb_logo.className = "m-3"
                        igdb_logo.src = "https://pbs.twimg.com/profile_images/1186326995254288385/_LV6aKaA_400x400.jpg"
                        igdb_logo.width = 40
                        igdb_link.appendChild(igdb_logo)

                        let youtube_link = document.createElement("a")
                        youtube_link.href = themerr_data['youtube_theme_url']
                        youtube_link.target = "_blank"
                        data_column.appendChild(youtube_link)

                        let youtube_logo = document.createElement("i")
                        youtube_logo.className = "fa-2x fa-fw fab fa-youtube text-decoration-none link-light align-middle"
                        youtube_link.appendChild(youtube_logo)

                        let edit_column = document.createElement("div")
                        edit_column.className = "d-table-cell align-top mx-3"
                        edit_column.style.position = "absolute";
                        edit_column.style.right = "0";
                        table_row.appendChild(edit_column)

                        let edit_button_link = document.createElement("a")
                        edit_button_link.href = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-game&template=add-game-theme.yml&title=${encodeURIComponent('[GAME]: ')}${encodeURIComponent(themerr_data['name'])}&igdb_url=${encodeURIComponent(themerr_data['url'])}`
                        edit_button_link.target = "_blank"
                        edit_column.appendChild(edit_button_link)

                        let edit_button = document.createElement("button")
                        edit_button.className = "btn-danger btn-outline-light rounded-0 btn"
                        edit_button.type = "button"
                        edit_button.textContent = "Edit"
                        edit_button_link.appendChild(edit_button)
                    }
                });
            }
        }
    });
    // get all movies
    $.ajax({
        url: `${base_url}/${themerr_database}/movies/themoviedb/all.json`,
        type: "GET",
        dataType:"json",
        success: function (result) {
            let sorted = result.sort(rankingSorter("title", "id")).reverse();

            for(let item in sorted) {
                $.ajax({
                    url: `${base_url}/${themerr_database}/movies/themoviedb/${sorted[item]['id']}.json`,
                    type: "GET",
                    dataType: "json",
                    success: function (themerr_data) {
                        // get the lowest year from release dates
                        let year = themerr_data['release_date'].split('-')[0]

                        let item_container = document.createElement("div")
                        item_container.className = "container mb-5 shadow border-0 bg-dark rounded-0 px-0"
                        movies_container.appendChild(item_container)

                        let inner_container = document.createElement("div")
                        inner_container.className = "container py-4 px-1"
                        item_container.appendChild(inner_container)

                        let table_row = document.createElement("div")
                        table_row.className = "d-table-row g-0 text-white"
                        inner_container.appendChild(table_row)

                        let poster = document.createElement("img")
                        poster.className = "d-table-cell px-3 rounded-0 mx-auto"
                        poster.src = `https://image.tmdb.org/t/p/w185${themerr_data['poster_path']}`
                        poster.alt = ""
                        poster.height = 200
                        table_row.appendChild(poster)

                        let data_column = document.createElement("div")
                        data_column.className = "d-table-cell align-top border-white my-3 px-3 border-start"
                        table_row.appendChild(data_column)

                        let item_title = document.createElement("h4")
                        item_title.className = "card-title mb-3 fw-bolder ms-0 mx-5"
                        item_title.textContent = `${themerr_data['title']} (${year})`
                        data_column.appendChild(item_title)

                        let item_summary = document.createElement("p")
                        item_summary.className = "card-text ms-0 mx-5"
                        item_summary.textContent = themerr_data['overview']
                        data_column.appendChild(item_summary)

                        let tmdb_link = document.createElement("a")
                        tmdb_link.href = `https://www.themoviedb.org/movie/${themerr_data['id']}`
                        tmdb_link.target = "_blank"
                        data_column.appendChild(tmdb_link)

                        let tmdb_logo = document.createElement("img")
                        tmdb_logo.className = "m-3"
                        tmdb_logo.src = "https://www.themoviedb.org/assets/2/v4/logos/v2/blue_square_2-d537fb228cf3ded904ef09b136fe3fec72548ebc1fea3fbbd1ad9e36364db38b.svg"
                        tmdb_logo.width = 40
                        tmdb_link.appendChild(tmdb_logo)

                        let youtube_link = document.createElement("a")
                        youtube_link.href = themerr_data['youtube_theme_url']
                        youtube_link.target = "_blank"
                        data_column.appendChild(youtube_link)

                        let youtube_logo = document.createElement("i")
                        youtube_logo.className = "fa-2x fa-fw fab fa-youtube text-decoration-none link-light align-middle"
                        youtube_link.appendChild(youtube_logo)

                        let edit_column = document.createElement("div")
                        edit_column.className = "d-table-cell align-top mx-3"
                        edit_column.style.position = "absolute";
                        edit_column.style.right = "0";
                        table_row.appendChild(edit_column)

                        let edit_button_link = document.createElement("a")
                        edit_button_link.href = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-movie&template=add-movie-theme.yml&title=${encodeURIComponent('[MOVIE]: ')}${encodeURIComponent(themerr_data['title'])}&themoviedb_url=${encodeURIComponent("https://www.themoviedb.org/movie/")}${encodeURIComponent(themerr_data['id'])}`
                        edit_button_link.target = "_blank"
                        edit_column.appendChild(edit_button_link)

                        let edit_button = document.createElement("button")
                        edit_button.className = "btn-danger btn-outline-light rounded-0 btn"
                        edit_button.type = "button"
                        edit_button.textContent = "Edit"
                        edit_button_link.appendChild(edit_button)
                    }
                });
            }
        }
    });
});
