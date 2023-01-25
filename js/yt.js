/* 
 YouTube Audio Embed 
 --------------------
 
 Original Author: Amit Agarwal
 Web: http://www.labnol.org/?p=26740 
*/

function onYouTubeIframeAPIReady(elementId, youtubeId) {
    let container = document.getElementById(elementId);
    let icon = document.createElement("i");
    icon.className = "fa-solid fa-2x fa-spinner fa-spin align-middle";
    icon.setAttribute("id", `youtube-icon-${elementId}`);
    icon.style.cssText = "cursor:pointer;cursor:hand";
    container.appendChild(icon);

    let playerWrapper = document.createElement("div");
    playerWrapper.setAttribute("id", `youtube-player-${elementId}`);
    container.appendChild(playerWrapper);

    let toggleIcon = function (isPlaying) {
        if (isPlaying) {
            icon.className = "fa-regular fa-2x fa-circle-pause align-middle";
        }
        else {
            icon.className = "fa-regular fa-2x fa-circle-play align-middle";
        }
    };
    container.onclick = function () {
        player.getPlayerState() === YT.PlayerState.PLAYING || player.getPlayerState() === YT.PlayerState.BUFFERING ? (player.pauseVideo(), toggleIcon(false)) : (player.playVideo(), toggleIcon(true));
    };
    let player = new YT.Player(`youtube-player-${elementId}`, {
        height: "0",
        width: "0",
        videoId: youtubeId,
        playerVars: { autoplay: container.dataset.autoplay, loop: container.dataset.loop },
        events: {
            onReady: function (e) {
                player.setPlaybackQuality("small");
                toggleIcon(player.getPlayerState() !== YT.PlayerState.CUED);
            },
            onStateChange: function (e) {
                e.data === YT.PlayerState.ENDED && toggleIcon(false);
            },
        },
    });
}
