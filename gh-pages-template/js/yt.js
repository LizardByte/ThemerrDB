/* 
 YouTube Audio Player
 --------------------

 API Docs: https://developers.google.com/youtube/iframe_api_reference
*/
let tag = document.createElement('script');

tag.src = "https://www.youtube.com/iframe_api";
let firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

let player;
function onYouTubeIframeAPIReady() {
    // get the nav container from the index
    let nav_container = document.getElementById('player-navbar');
    nav_container.className = "navbar sticky-bottom bg-dark border-1 border-top border-bottom-0 text-white";
    nav_container.style.cssText = "min-height: 50px;";

    // create the player wrapper
    let playerWrapper = document.createElement("div");
    playerWrapper.setAttribute("id", 'youtube-player');
    nav_container.appendChild(playerWrapper);

    // create the player
    let inner_container = document.createElement("div");
    inner_container.id = "youtube-audio";
    inner_container.className = "container";
    nav_container.appendChild(inner_container);

    // create the playback control icon
    let icon_column = document.createElement("div");
    icon_column.className = "col-auto ms-5";
    inner_container.appendChild(icon_column);
    let icon = document.createElement("i");
    icon.className = "fa-solid fa-2x fa-spinner fa-spin align-middle";
    icon.setAttribute("id", 'youtube-icon');
    icon.style.cssText = "cursor:pointer;cursor:hand";
    icon_column.appendChild(icon);

    // create the progress bar
    let progress_column = document.createElement("div");
    progress_column.className = "col mx-5";
    inner_container.appendChild(progress_column);
    let progressContainer = document.createElement("div");
    progressContainer.className = "progress rounded-0 align-middle";
    progressContainer.style.cssText = "height: 7px;";
    progress_column.appendChild(progressContainer)
    let progressBar = document.createElement("div");
    progressBar.className = "progress-bar bg-danger";
    progressBar.id = 'youtube-progress';
    progressBar.setAttribute("role", "progressbar");
    progressBar.setAttribute("style", "width: 0%;");
    progressBar.setAttribute("aria-valuenow", "0");
    progressBar.setAttribute("aria-valuemin", "0");
    progressBar.setAttribute("aria-valuemax", "1000");
    progressContainer.appendChild(progressBar);

    // get isPlaying state
    let isPlaying = function() {
        let player_state = player.getPlayerState();
        if (player_state === YT.PlayerState.PLAYING || player_state === YT.PlayerState.BUFFERING) {
            return true;
        } else if (player_state === YT.PlayerState.PAUSED || player_state === YT.PlayerState.ENDED) {
            return false;
        } else {
            return false;
        }
    };

    // update the progress bar
    let updateProgressBar = function() {
        let current_time;
        let duration;
        let percent_complete;
        if (isPlaying(player)) {
            // get playback times
            current_time = player.getCurrentTime();
            duration = player.getDuration();
            percent_complete = (current_time / duration) * 100;
            progressBar.setAttribute("aria-valuemax", duration);

            progressBar.setAttribute("style", `width: ${percent_complete}%;`);
            progressBar.setAttribute("aria-valuenow", current_time);
        } else if (player.getPlayerState() === YT.PlayerState.ENDED) {
            progressBar.setAttribute("style", "width: 100%;");
            progressBar.setAttribute("aria-valuenow", "100");
        }
    }

    // toggle the icon
    let toggleIcon = function () {
        if (isPlaying()) {
            icon.classList.remove("fa-circle-play");
            icon.classList.add("fa-circle-pause");
        }
        else {
            icon.classList.remove("fa-circle-pause");
            icon.classList.add("fa-circle-play");
        }
    };

    // icon onclick event
    icon.onclick = function () {
        if (isPlaying(player)) {
            player.pauseVideo();
        } else {
            player.playVideo();
        }
    };

    // create the player object
    player = new YT.Player('youtube-player', {
        height: "0",
        width: "0",
        videoId: "dQw4w9WgXcQ",  // Rick Astley - Never Gonna Give You Up (Video)
        playerVars: {
            autoplay: 0,
            controls: 2,
            loop: 0
        },
        events: {
            onReady: function () {
                player.setPlaybackQuality("small");
                icon.classList.remove("fa-solid", "fa-spinner", "fa-spin");
                icon.classList.add("fa-regular", "fa-circle-pause");
                toggleIcon();
            },
            onStateChange: function () {
                toggleIcon();
            },
        },
    });

    // update the progress bar on an interval
    setInterval(updateProgressBar,50);
}

function changeVideo(videoId) {
    player.loadVideoById(videoId);  // this will automatically play the "video"
    // change the player icon to pause
    let player_icon = document.getElementById('youtube-icon');
    player_icon.addClass("fa-circle-pause");
    // todo - change the original icon to pause and allow it to control the player
    // todo - change all the other icons to play
}
