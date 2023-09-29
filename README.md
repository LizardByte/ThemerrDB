# ThemerrDB

[![GitHub Workflow Status (update)](https://img.shields.io/github/actions/workflow/status/LizardByte/ThemerrDB/update-pages.yml?branch=master&event=schedule&style=for-the-badge&logo=github&label=build)](https://github.com/LizardByte/ThemerrDB/actions/workflows/update-pages.yml?query=branch%3Amaster+event%3Aschedule)
[![Codecov](https://img.shields.io/codecov/c/gh/LizardByte/ThemerrDB?token=RAWCMC72RT&style=for-the-badge&logo=codecov&label=codecov)](https://app.codecov.io/gh/LizardByte/ThemerrDB)

ThemerrDB is a database for movie and video game theme songs.

The database is created using codeless contributions.

You can view the entire database at [ThemerrDB](https://app.lizardbyte.dev/ThemerrDB).

## Database Growth
[![Movies](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapp.lizardbyte.dev%2FThemerrDB%2Fmovies%2Fpages.json&query=count&style=for-the-badge&label=Movies&logo=the-movie-database)](#movies)
[![Movie Collections](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapp.lizardbyte.dev%2FThemerrDB%2Fmovie_collections%2Fpages.json&query=count&style=for-the-badge&label=Movie%20Collections&logo=the-movie-database)](#movie-collections)
[![Games](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapp.lizardbyte.dev%2FThemerrDB%2Fgames%2Fpages.json&query=count&style=for-the-badge&label=Games&logo=igdb)](#games)
[![Games](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapp.lizardbyte.dev%2FThemerrDB%2Fgame_collections%2Fpages.json&query=count&style=for-the-badge&label=Game%20Collections&logo=igdb)](#game-collections)
[![Games](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapp.lizardbyte.dev%2FThemerrDB%2Fgame_franchises%2Fpages.json&query=count&style=for-the-badge&label=Game%20Franchises&logo=igdb)](#game-franchises)

#### Movies
![Movies](https://app.lizardbyte.dev/ThemerrDB/movies/movies_plot.svg)

#### Movie Collections
![Movie Collections](https://app.lizardbyte.dev/ThemerrDB/movie_collections/movie_collections_plot.svg)

#### Games
![Games](https://app.lizardbyte.dev/ThemerrDB/games/games_plot.svg)

#### Game Collections
![Game Collections](https://app.lizardbyte.dev/ThemerrDB/game_collections/game_collections_plot.svg)

#### Game Franchises
![Game Franchises](https://app.lizardbyte.dev/ThemerrDB/game_franchises/game_franchises_plot.svg)

## Contributing

### Adding/Updating Theme Song

1. Read our [Theme Guidelines](docs/Theme_Guidelines.md).

2. Create a new [request](https://github.com/LizardByte/ThemerrDB/issues/new?assignees=&labels=request-theme&template=theme.yml&title=%5BTHEME%5D%3A+)

3. Add the requested URLs to the issue.

   > **Warning**
   > YouTube URLs should only contain the video ID parameter. i.e. `https://www.youtube.com/watch?v={VIDEO_ID}` or
   >`https://youtu.be/{VIDEO_ID}`
   
   :link: See [YouTube Share](docs/YouTube_Share.md) for further instruction.

4. Submit the issue.

A label will be added to the request. i.e. `request-theme`.

The workflow will automatically determine the type of theme to add.

A workflow will run. If necessary the title of the issue will be updated. Additionally, a comment will be added to the
issue. If there are any issues with the YouTube URL, the comment will contain the error message in the first section.
The remaining information in the comment is to assist with the review process.

### Content Review

Submitted "issues" will be reviewed by a developer/moderator. Once approved we will add a label, i.e. `approve-theme`.
At this point, the workflow will run and attempt to update the database in the
[database](https://github.com/LizardByte/ThemerrDB/tree/database) branch.

## Daily updates

The database will be pushed to the [gh-pages](https://github.com/LizardByte/ThemerrDB/tree/gh-pages) branch, once daily
at UTC 12:00. Theme songs will not be available until they are published.

## How to use the database in your own project

1. Determine the media type. Supported types are shown in the table.

   | Type              | Databases        |
   |-------------------|------------------|
   | games             | igdb             |
   | game_collections  | igdb             |
   | game_franchises   | igdb             |
   | movies            | themoviedb, imdb |
   | movie_collections | themoviedb       |

2. Determine the id of the item from the main database.

    - Games
      - [igdb](https://www.igdb.com/)
    - Movies
      - [imdb](https://www.imdb.com/)
      - [themoviedb](https://www.themoviedb.org/)

3. Access the item on ThemerrDB at the following url:

   `https://app.lizardbyte.dev/ThemerrDB/<media_type>/<database>/<item_id>.json`

   > **Note**
   > Not all movies will be available in the `imdb` database directory. This is due to the fact that the
   > `imdb_id` is missing from the item's entry in `themoviedb`.

4. Within the downloaded `json` file there is a key named `youtube_theme_url` that contains the YouTube video URL to 
   the theme song.
5. Extract the audio from the YouTube video using your preferred method. Some suggestions are listed in the table below.
  
| language    | library                                                    |
|-------------|------------------------------------------------------------|
| C#          | [YoutubeExplode](https://github.com/Tyrrrz/YoutubeExplode) |
| JavaScript  | [ytdl-core](https://www.npmjs.com/package/ytdl-core)       |
| Python 2.6+ | [youtube_dl](https://github.com/ytdl-org/youtube-dl)       |
| Python 3.7+ | [YT-DLP](https://github.com/yt-dlp/yt-dlp)                 |

## Projects using ThemerrDB

- [Themerr-plex](https://github.com/LizardByte/Themerr-plex)
- [Themerr-jellyfin](https://github.com/LizardByte/Themerr-jellyfin)

Something missing? Let us know by opening a PR to update the README.
