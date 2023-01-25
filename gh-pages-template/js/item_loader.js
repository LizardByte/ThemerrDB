let org_name = "LizardByte"
let base_url = `https://app.${org_name.toLowerCase()}.dev`
let themerr_database = "ThemerrDB"

// sort items
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

$(document).ready(function(){
    // Set cache = false for all jquery ajax requests.
    $.ajaxSetup({
        cache: false,
    });
});

// create item cards
let types_dict = {
    "games": {
        "base_url": `${base_url}/${themerr_database}/games/igdb/`,
        "container": document.getElementById("games-container"),
        "database": "igdb",
        "database-logo": "https://pbs.twimg.com/profile_images/1186326995254288385/_LV6aKaA_400x400.jpg",
        "sorter": rankingSorter("name", "id")
    },
    "movies": {
        "base_url": `${base_url}/${themerr_database}/movies/themoviedb/`,
        "container": document.getElementById("movies-container"),
        "database": "tmdb",
        "database-logo": "https://www.themoviedb.org/assets/2/v4/logos/v2/blue_square_2-d537fb228cf3ded904ef09b136fe3fec72548ebc1fea3fbbd1ad9e36364db38b.svg",
        "sorter": rankingSorter("title", "id")
    }
}

$(document).ready(function(){
    for (let type in types_dict) {
        $.ajax({
            url: `${types_dict[type]['base_url']}all.json`,
            type: "GET",
            dataType: "json",
            success: function (result) {
                let sorted = result.sort(types_dict[type]['sorter']).reverse();

                for (let item in sorted) {
                    $.ajax({
                        url: `${types_dict[type]['base_url']}/${sorted[item]['id']}.json`,
                        type: "GET",
                        dataType: "json",
                        success: function (themerr_data) {
                            let year = null;
                            let poster_src = null;
                            let title = null;
                            let summary = null;
                            let edit_link = null;

                            if (type === "games") {
                                // get the lowest year from release dates
                                for (let release in themerr_data['release_dates']) {
                                    if (year == null || themerr_data['release_dates'][release]['y'] < year) {
                                        year = themerr_data['release_dates'][release]['y'];
                                    }
                                }
                                poster_src = themerr_data['cover']['url'].replace('/t_thumb/', '/t_cover_big/');
                                title = themerr_data['name'];
                                summary = themerr_data['summary'];
                                edit_link = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-game&template=add-game-theme.yml&title=${encodeURIComponent('[GAME]: ')}${encodeURIComponent(themerr_data['name'])}&igdb_url=${encodeURIComponent(themerr_data['url'])}`;
                            } else if (type === "movies") {
                                year = themerr_data['release_date'].split("-")[0];
                                poster_src = `https://image.tmdb.org/t/p/w185${themerr_data['poster_path']}`;
                                title = themerr_data['title'];
                                summary = themerr_data['overview'];
                                edit_link = `https://github.com/${org_name}/${themerr_database}/issues/new?assignees=&labels=request-movie&template=add-movie-theme.yml&title=${encodeURIComponent('[MOVIE]: ')}${encodeURIComponent(themerr_data['title'])}&themoviedb_url=${encodeURIComponent("https://www.themoviedb.org/movie/")}${encodeURIComponent(themerr_data['id'])}`;
                            }

                            let item_container = document.createElement("div")
                            item_container.className = "container mb-5 shadow border-0 bg-dark rounded-0 px-0"
                            types_dict[type]['container'].appendChild(item_container)

                            let inner_container = document.createElement("div")
                            inner_container.className = "container py-4 px-1"
                            item_container.appendChild(inner_container)

                            let table_row = document.createElement("div")
                            table_row.className = "d-table-row g-0 text-white"
                            inner_container.appendChild(table_row)

                            let poster = document.createElement("img")
                            poster.className = "d-table-cell px-3 rounded-0 mx-auto"
                            poster.src = poster_src
                            poster.alt = ""
                            poster.height = 200
                            table_row.appendChild(poster)

                            let data_column = document.createElement("div")
                            data_column.className = "d-table-cell align-top border-white my-3 px-3 border-start"
                            table_row.appendChild(data_column)

                            let item_title = document.createElement("h4")
                            item_title.className = "card-title mb-3 fw-bolder ms-0 mx-5"
                            item_title.textContent = `${title} (${year})`
                            data_column.appendChild(item_title)

                            let item_summary = document.createElement("p")
                            item_summary.className = "card-text ms-0 mx-5"
                            item_summary.textContent = summary
                            data_column.appendChild(item_summary)

                            let database_link = document.createElement("a")
                            database_link.href = themerr_data['url']
                            database_link.target = "_blank"

                            let database_logo = document.createElement("img")
                            database_logo.className = "m-3"
                            database_logo.src = types_dict[type]['database-logo']
                            database_logo.width = 40
                            database_link.appendChild(database_logo)

                            let player_logo = document.createElement("i");
                            let youtube_id = themerr_data['youtube_theme_url'].split("v=")[1]
                            player_logo.className = "fa-regular fa-play-circle fa-2x align-middle";
                            player_logo.style.cssText = "cursor:pointer;cursor:hand";
                            player_logo.onclick = function() {
                                changeVideo(youtube_id)
                            }

                            let card_footer = document.createElement("div");
                            data_column.appendChild(card_footer);
                            card_footer.appendChild(database_link);
                            card_footer.appendChild(player_logo);

                            let edit_column = document.createElement("div")
                            edit_column.className = "d-table-cell align-top mx-3"
                            edit_column.style.position = "absolute";
                            edit_column.style.right = "0";
                            table_row.appendChild(edit_column)

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
                    });
                }
            }
        });
    }
});
