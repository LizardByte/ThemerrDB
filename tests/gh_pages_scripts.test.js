/**
 * @jest-environment jsdom
 *
 * @file Tests for the static GitHub Pages JavaScript.
 */
/* global document, KeyboardEvent */

const {
  afterEach,
  beforeEach,
  describe,
  expect,
  jest,
  test
} = require('@jest/globals')

const ITEM_LOADER_PATH = '../gh-pages-template/assets/js/item_loader.js'
const YOUTUBE_PLAYER_PATH = '../gh-pages-template/assets/js/yt.js'

/**
 * Build the page nodes expected by item_loader.js.
 *
 * @returns {void}
 */
function buildItemLoaderDocument() {
  document.body.innerHTML = `
    <form id="searchForm">
      <select id="search_type">
        <option value="0">Games</option>
        <option selected value="3">Movies</option>
      </select>
      <input id="search_term" value="goldeneye">
      <input id="include_missing" type="checkbox" checked>
      <input id="checked_radio" type="radio" value="checked" checked>
      <input id="unchecked_radio" type="radio" value="unchecked">
      <textarea id="notes">note text</textarea>
      <input id="search_button" type="button" value="Search">
      <input id="submit_button" type="submit" value="Submit">
    </form>
    <div id="search-container"></div>
    <section id="Games"><div id="games-container"></div></section>
    <section id="Game Collections"><div id="game-collections-container"></div></section>
    <section id="Game Franchises"><div id="game-franchises-container"></div></section>
    <section id="Movies"><div id="movies-container"></div></section>
    <section id="Movie Collections"><div id="movie-collections-container"></div></section>
  `
}

/**
 * Build the page nodes expected by yt.js.
 *
 * @returns {void}
 */
function buildYouTubeDocument() {
  document.body.innerHTML = `
    <script id="first-script"></script>
    <nav id="player-navbar"></nav>
  `
}

/**
 * Return paginated list data for the item loader Ajax mock.
 *
 * @param {string} path Request path.
 * @returns {Object[]} Page item data.
 */
function getPageItems(path) {
  const pages = {
    '/ThemerrDB/games/all_page_1.json': [{id: 1638, title: 'GoldenEye 007'}],
    '/ThemerrDB/games/all_page_2.json': [{id: 42, title: 'Second Game'}],
    '/ThemerrDB/game_collections/all_page_1.json': [{id: 326, title: 'James Bond'}],
    '/ThemerrDB/game_franchises/all_page_1.json': [{id: 37, title: 'James Bond'}],
    '/ThemerrDB/movies/all_page_1.json': [
      {id: 710, title: 'GoldenEye'},
      {id: 999, title: 'Unrelated Movie'}
    ],
    '/ThemerrDB/movie_collections/all_page_1.json': [{id: 645, title: 'James Bond Collection'}]
  }
  return pages[path]
}

/**
 * Return item detail data for the item loader Ajax mock.
 *
 * @param {string} url Request URL.
 * @returns {Object} Item detail data.
 */
function getItemDetails(url) {
  const details = {
    '/igdb/37.json': {
      id: 37,
      name: 'James Bond',
      url: 'https://www.igdb.com/franchises/james-bond',
      youtube_theme_url: 'https://www.youtube.com/watch?v=franchise'
    },
    '/igdb/42.json': {
      cover: {url: '//images.igdb.com/igdb/image/upload/t_thumb/co2.jpg'},
      id: 42,
      name: 'Second Game',
      release_dates: [{y: 2000}],
      summary: 'Another game summary.',
      url: 'https://www.igdb.com/games/second-game',
      youtube_theme_url: 'https://www.youtube.com/watch?v=second'
    },
    '/igdb/404.json': {
      id: 404,
      youtube_theme_url: 'https://www.youtube.com/watch?v=unknown'
    },
    '/igdb/326.json': {
      id: 326,
      name: 'James Bond',
      url: 'https://www.igdb.com/collections/james-bond',
      youtube_theme_url: 'https://www.youtube.com/watch?v=collection'
    },
    '/igdb/1638.json': {
      cover: {url: '//images.igdb.com/igdb/image/upload/t_thumb/co1.jpg'},
      id: 1638,
      name: 'GoldenEye 007',
      release_dates: [{y: 1997}, {y: 1995}, {y: 1996}],
      summary: 'A game summary.',
      url: 'https://www.igdb.com/games/goldeneye-007',
      youtube_theme_url: 'https://www.youtube.com/watch?v=game'
    },
    '/themoviedb/645.json': {
      id: 645,
      name: 'James Bond Collection',
      overview: 'A collection summary.',
      poster_path: '/james-bond.jpg',
      youtube_theme_url: 'https://www.youtube.com/watch?v=tmdbcollection'
    },
    '/themoviedb/710.json': {
      id: 710,
      overview: 'A movie summary.',
      poster_path: '/goldeneye.jpg',
      release_date: '1995-11-16',
      title: 'GoldenEye',
      youtube_theme_url: 'https://www.youtube.com/watch?v=movie'
    },
    '/themoviedb/999.json': {
      id: 999,
      overview: 'Another movie summary.',
      poster_path: '/unrelated.jpg',
      release_date: '2001-01-01',
      title: 'Unrelated Movie',
      youtube_theme_url: 'https://www.youtube.com/watch?v=other'
    }
  }
  return Object.entries(details).find(([suffix]) => url.endsWith(suffix))?.[1]
}

/**
 * Install a jQuery-style mock used by the browser scripts.
 *
 * @param {Function[]} readyCallbacks Captured document-ready callbacks.
 * @returns {jest.Mock} Ajax mock.
 */
function mockJQuery(readyCallbacks) {
  const ajax = jest.fn(options => {
    const path = new URL(options.url).pathname
    if (path.endsWith('/pages.json')) {
      options.success({pages: path.includes('/games/') ? 2 : 1})
      return
    }

    const pageItems = getPageItems(path)
    if (pageItems) {
      options.success(pageItems)
      return
    }

    const itemDetails = getItemDetails(options.url)
    if (itemDetails) {
      options.success(itemDetails)
      return
    }

    throw new Error(`Unexpected ajax url: ${options.url}`)
  })
  globalThis.$ = jest.fn(() => ({
    ready: callback => readyCallbacks.push(callback)
  }))
  globalThis.$.ajax = ajax
  globalThis.$.ajaxSetup = jest.fn()
  return ajax
}

/**
 * Load item_loader.js after test globals are prepared.
 *
 * @returns {{ajax: jest.Mock, readyCallbacks: Function[], timeoutCallbacks: Function[]}} Script test state.
 */
function loadItemLoader() {
  const readyCallbacks = []
  const timeoutCallbacks = []
  const ajax = mockJQuery(readyCallbacks)
  jest.spyOn(console, 'log').mockImplementation(() => {})
  jest.spyOn(globalThis, 'setTimeout').mockImplementation(callback => {
    timeoutCallbacks.push(callback)
    return 0
  })
  globalThis.changeVideo = jest.fn()
  globalThis.levenshteinDistance = jest.fn((searchTerm, title) => (
    title.includes(searchTerm) ? 100 : 20
  ))
  globalThis.rankingSorter = jest.fn((scoreKey, titleKey) => (left, right) => (
    right[scoreKey] - left[scoreKey] || left[titleKey].localeCompare(right[titleKey])
  ))

  require(ITEM_LOADER_PATH)
  for (const callback of readyCallbacks) {
    callback()
  }

  return {ajax, readyCallbacks, timeoutCallbacks}
}

/**
 * Create a mock YouTube iframe player.
 *
 * @returns {{config: Object|null, intervalCallback: Function|null, player: Object, states: Object}} Mock player state.
 */
function mockYouTubeApi() {
  const states = {
    BUFFERING: 3,
    ENDED: 0,
    PAUSED: 2,
    PLAYING: 1,
    UNSTARTED: -1
  }
  const player = {
    getCurrentTime: jest.fn(() => 5),
    getDuration: jest.fn(() => 10),
    getPlayerState: jest.fn(() => states.PAUSED),
    loadVideoById: jest.fn(),
    pauseVideo: jest.fn(),
    playVideo: jest.fn(),
    setPlaybackQuality: jest.fn()
  }
  const mockState = {
    config: null,
    intervalCallback: null,
    player,
    states
  }
  globalThis.YT = {
    Player: jest.fn((elementId, config) => {
      mockState.config = config
      return player
    }),
    PlayerState: states
  }
  jest.spyOn(globalThis, 'setInterval').mockImplementation(callback => {
    mockState.intervalCallback = callback
    return 0
  })
  return mockState
}

describe('gh-pages item loader', () => {
  beforeEach(() => {
    jest.resetModules()
    buildItemLoaderDocument()
  })

  afterEach(() => {
    jest.restoreAllMocks()
    delete globalThis.$
    delete globalThis.changeVideo
    delete globalThis.levenshteinDistance
    delete globalThis.rankingSorter
    delete globalThis.run_search
    delete globalThis.themerrItemLoader
  })

  test('initializes paginated loaders and renders every item type', () => {
    const {ajax, timeoutCallbacks} = loadItemLoader()

    expect(globalThis.$.ajaxSetup).toHaveBeenCalledWith({cache: false})
    expect(document.getElementById('games-container').textContent).toContain('GoldenEye 007 (1995)')
    expect(document.getElementById('game-collections-container').textContent).toContain('James Bond (null)')
    expect(document.getElementById('game-franchises-container').textContent).toContain('James Bond (null)')
    expect(document.getElementById('movies-container').textContent).toContain('GoldenEye (1995)')
    expect(document.getElementById('movie-collections-container').textContent)
      .toContain('James Bond Collection (null)')

    document.querySelector('.fa-play-circle').click()

    expect(globalThis.changeVideo).toHaveBeenCalledWith('game')

    globalThis.dispatchEvent(new Event('scroll'))
    globalThis.dispatchEvent(new Event('scroll'))
    for (const callback of timeoutCallbacks) {
      callback()
    }
    const gamesLoadMoreButton = document.querySelector('#games-container .btn-warning')
    gamesLoadMoreButton.disabled = false
    gamesLoadMoreButton.click()
    Object.defineProperty(globalThis, 'innerHeight', {configurable: true, value: 1000})
    globalThis.dispatchEvent(new Event('scroll'))
    Object.defineProperty(globalThis, 'innerHeight', {configurable: true, value: -1})
    globalThis.dispatchEvent(new Event('scroll'))

    expect(ajax).toHaveBeenCalledWith(expect.objectContaining({
      url: 'https://app.lizardbyte.dev/ThemerrDB/games/all_page_2.json'
    }))

    const fallbackContainer = document.createElement('div')
    globalThis.themerrItemLoader.types_dict.unknown = {
      all_search_items: [],
      base_url: 'https://app.lizardbyte.dev/ThemerrDB/unknown/',
      container: fallbackContainer,
      database: 'igdb',
      'database-logo': 'https://example.invalid/logo.png'
    }
    globalThis.themerrItemLoader.populate_results('unknown', [{id: 404, title: 'Unknown'}], fallbackContainer)

    expect(fallbackContainer.textContent).toContain('null (null)')
  })

  test('serializes form data, searches cached items, and clears results', () => {
    const {ajax} = loadItemLoader()

    document.getElementById('searchForm').dispatchEvent(new KeyboardEvent('keypress', {
      bubbles: true,
      key: 'Space'
    }))
    document.getElementById('searchForm').dispatchEvent(new KeyboardEvent('keypress', {
      bubbles: true,
      key: 'Enter'
    }))
    globalThis.run_search()

    const formData = globalThis.themerrItemLoader.get_search_form_data()
    expect(formData.get('include_missing')).toBe('true')
    expect(formData.get('checked_radio')).toBe('checked')
    expect(formData.get('unchecked_radio')).toBeNull()
    expect(formData.get('notes')).toBe('note text')
    expect(formData.get('search_button')).toBeNull()
    expect(formData.get('submit_button')).toBeNull()
    expect(globalThis.levenshteinDistance).toHaveBeenCalledWith('goldeneye', 'goldeneye')
    expect(globalThis.levenshteinDistance).toHaveBeenCalledWith('goldeneye', 'unrelated movie')
    expect(document.getElementById('Movies').classList.contains('d-none')).toBe(true)
    expect(document.getElementById('search-container').textContent).toContain('Clear Results')
    expect(document.getElementById('search-container').textContent).toContain('GoldenEye (1995)')
    expect(document.getElementById('search-container').textContent).not.toContain('Unrelated Movie')
    expect(ajax).toHaveBeenCalledWith(expect.objectContaining({
      url: 'https://app.lizardbyte.dev/ThemerrDB/movies/all_page_1.json'
    }))

    document.querySelector('#search-container button').click()

    expect(document.getElementById('search-container').textContent).toBe('')
    expect(document.getElementById('Movies').classList.contains('d-none')).toBe(false)
  })

  test('skips empty searches', () => {
    loadItemLoader()
    document.getElementById('search_term').value = ''

    globalThis.run_search()

    expect(document.getElementById('Movies').classList.contains('d-none')).toBe(false)
    expect(document.getElementById('search-container').textContent).toBe('')
  })
})

describe('gh-pages YouTube player', () => {
  beforeEach(() => {
    jest.resetModules()
    buildYouTubeDocument()
  })

  afterEach(() => {
    jest.restoreAllMocks()
    delete globalThis.YT
    delete globalThis.changeVideo
    delete globalThis.onYouTubeIframeAPIReady
    delete globalThis.themerrYouTubePlayer
  })

  test('loads the iframe API script and identifies playing states', () => {
    const {player, states} = mockYouTubeApi()

    require(YOUTUBE_PLAYER_PATH)

    expect(document.querySelector('script[src="https://www.youtube.com/iframe_api"]')).not.toBeNull()
    player.getPlayerState.mockReturnValue(states.PLAYING)
    expect(globalThis.themerrYouTubePlayer.isPlaying(player)).toBe(true)
    player.getPlayerState.mockReturnValue(states.BUFFERING)
    expect(globalThis.themerrYouTubePlayer.isPlaying(player)).toBe(true)
    player.getPlayerState.mockReturnValue(states.PAUSED)
    expect(globalThis.themerrYouTubePlayer.isPlaying(player)).toBe(false)
    player.getPlayerState.mockReturnValue(states.ENDED)
    expect(globalThis.themerrYouTubePlayer.isPlaying(player)).toBe(false)
    player.getPlayerState.mockReturnValue(states.UNSTARTED)
    expect(globalThis.themerrYouTubePlayer.isPlaying(player)).toBe(false)
  })

  test('builds player controls and handles playback updates', () => {
    const mockState = mockYouTubeApi()
    const {player, states} = mockState

    require(YOUTUBE_PLAYER_PATH)
    globalThis.onYouTubeIframeAPIReady()

    const playerConfig = mockState.config
    const progressBar = document.getElementById('youtube-progress')
    const icon = document.getElementById('youtube-icon')

    expect(globalThis.YT.Player).toHaveBeenCalledWith('youtube-player', expect.objectContaining({
      height: '0',
      width: '0'
    }))
    expect(document.body.style.paddingBottom).toBe('50px')
    expect(document.getElementById('player-navbar').className)
      .toBe('navbar bg-dark border-1 border-top border-bottom-0 text-white')

    player.getPlayerState.mockReturnValue(states.PAUSED)
    playerConfig.events.onReady()

    expect(player.setPlaybackQuality).toHaveBeenCalledWith('small')
    expect(icon.classList.contains('fa-circle-play')).toBe(true)

    player.getPlayerState.mockReturnValue(states.PLAYING)
    playerConfig.events.onStateChange()
    expect(icon.classList.contains('fa-circle-pause')).toBe(true)
    icon.click()
    expect(player.pauseVideo).toHaveBeenCalled()

    player.getPlayerState.mockReturnValue(states.PAUSED)
    icon.click()
    expect(player.playVideo).toHaveBeenCalled()

    player.getPlayerState.mockReturnValue(states.PLAYING)
    mockState.intervalCallback()
    expect(progressBar.getAttribute('style')).toBe('width: 50%;')
    expect(progressBar.getAttribute('aria-valuemax')).toBe('10')
    expect(progressBar.getAttribute('aria-valuenow')).toBe('5')
    expect(globalThis.themerrYouTubePlayer.isPlaying()).toBe(true)

    player.getPlayerState.mockReturnValue(states.ENDED)
    mockState.intervalCallback()
    expect(progressBar.getAttribute('style')).toBe('width: 100%;')
    expect(progressBar.getAttribute('aria-valuenow')).toBe('100')

    player.getPlayerState.mockReturnValue(states.PAUSED)
    mockState.intervalCallback()

    globalThis.changeVideo('abc123')

    expect(player.loadVideoById).toHaveBeenCalledWith('abc123')
    expect(icon.classList.contains('fa-circle-pause')).toBe(true)
  })
})
