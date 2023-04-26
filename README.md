# ThemerrDB

ThemerrDB is a database for movie and video game theme songs.

The database is created using codeless contributions.

See further documentation [here](https://docs.lizardbyte.dev/projects/themerr-plex/en/latest/).

## Database Growth
![Movies](https://app.lizardbyte.dev/ThemerrDB/movies/movies_plot.svg)
![Games](https://app.lizardbyte.dev/ThemerrDB/games/games_plot.svg)

## Contributing

### Adding/Updating Theme Song

1. Create a new [Issue](https://github.com/LizardByte/ThemerrDB/issues/new/choose) selecting either template.

   - [Game](https://github.com/LizardByte/ThemerrDB/issues/new?assignees=&labels=request-game&template=game-theme.yml&title=%5BGAME%5D%3A+)
   - [Movie](https://github.com/LizardByte/ThemerrDB/issues/new?assignees=&labels=request-movie&template=movie-theme.yml&title=%5BMOVIE%5D%3A+)

2. Add the requested URLs to the issue.
3. Submit the issue.

A label will be added to the request. i.e. `request-game` or `request-movie`

A workflow will run. If necessary the title of the issue will be updated. Additionally, a comment will be added to the
issue. If there are any issues with the YouTube URL, the comment will contain the error message in the first section.
The remaining information in the comment is to assist with the review process.

### Content Review

Submitted "issues" will be reviewed by a developer/moderator. Once approved we will add a label, i.e. `add-game` or
`add-movie`. At this point, the workflow will run and attempt to update the database in the
[database](https://github.com/LizardByte/ThemerrDB/tree/database) branch.

## Daily updates

The database will be pushed to the [gh-pages](https://github.com/LizardByte/ThemerrDB/tree/gh-pages) branch, once daily
at UTC 12:00. Theme songs will not be available until they are published.

## How to use the database in your own project

1. Determine the type of content. i.e. `game` or `movie`
2. Determine the id of the item from the main database.

    - Games
      - [igdb](https://www.igdb.com/)
    - Movies
      - [imdb](https://www.imdb.com/)
      - [themoviedb](https://www.themoviedb.org/)

3. Access the item on ThemerrDB at the following url:

    `https://app.lizardbyte.dev/ThemerrDB/<media_type>/<database>/<item_id>.json`

    Where:
  
    - `media_type` is `games` or `movies`
    - `database` is `igdb`, `imdb`, or `themoviedb`
    - `item_id` is the id number from the specified database

    :warning: Not all movies will be available in the `imdb` database directory. This is due to the fact that the `imdb_id`
    is missing from the item's entry in `themoviedb`.

4. Within the downloaded `json` file there is a key named `youtube_theme_url` that contains the YouTube video URL to 
the theme song.
5. Extract the audio from the YouTube video using your preferred method. Some suggestions are listed in the table below.
  
| language   | library                                                    |
|------------|------------------------------------------------------------|
| C#         | [YoutubeExplode](https://github.com/Tyrrrz/YoutubeExplode) |
| JavaScript | [ytdl-core](https://www.npmjs.com/package/ytdl-core)       |
| Python     | [youtube_dl](https://github.com/ytdl-org/youtube-dl)       |

## Projects using ThemerrDB

- [Themerr-plex](https://github.com/LizardByte/Themerr-plex)
- [Themerr-jellyfin](https://github.com/LizardByte/Themerr-jellyfin)

Something missing? Let us know by opening a PR to update the README.
