# ThemerrDB

ThemerrDB is a database for movie and video game theme songs.

The database is created using codeless contributions.

## Adding/Updating Theme Song

1. Create a new [Issue](https://github.com/LizardByte/ThemerrDB/issues/new/choose) selecting either template.

   - [Game](https://github.com/LizardByte/ThemerrDB/issues/new?assignees=&labels=request-game&template=add-game-theme.yml&title=%5BGAME%5D%3A+)
   - [Movie](https://github.com/LizardByte/ThemerrDB/issues/new?assignees=&labels=request-movie&template=add-movie-theme.yml&title=%5BMOVIE%5D%3A+)

2. Please append the game/movie name to the end of the issue title.
3. Fill the requested information.
4. Submit the issue.

A label will be added to the request. i.e. `request-game` or `request-movie`

## Content Review

Submitted "issues" will be reviewed by a developer/moderator. Once approved we will add a label, i.e. `add-game` or
`add-movie`. At this point, the workflow will run and attempt to update the database in the
[database](https://github.com/LizardByte/ThemerrDB/tree/database) branch.

## Publish to gh-pages

The database will be pushed to the [gh-pages](https://github.com/LizardByte/ThemerrDB/tree/gh-pages) branch, once daily
at UTC 00:00.

## How to use the database

1. Determine the type of content. i.e `game` or `movie`
2. Determine the id of the item from the main database.

    - Games
      - [igdb](https://www.igdb.com/)
    - Movies
      - [imdb](https://www.imdb.com/)
      - [themoviedb](https://www.themoviedb.org/)
      - [thetvdb](https://thetvdb.com/)

3. Access the item on ThemerrDB at the following url:

    `https://app.lizardbyte.dev/ThemerrDB/<media_type>/<database>/<item_id>.json`

    Where:
  
    - `media_type` is `games` or `movies`
    - `database` is `igdb`, `imdb`, `themoviedb` or `thetvdb`
    - `item_id` is the id number from the specified database

4. Within the downloaded `json` file there is a key named `youtube_theme_url` that contains the YouTube video URL to 
the theme song.
5. Use [youtube_dl](https://github.com/ytdl-org/youtube-dl), or some other method to extract the audio from the YouTube video.

## Projects using ThemerrDB

- [Themerr-plex](https://github.com/LizardByte/Themerr-plex)
