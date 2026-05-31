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
const TEST_URL_BASE = 'https://preview.example'

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
        <option value="1">Game Collections</option>
        <option value="2">Game Franchises</option>
        <option selected value="3">Movies</option>
        <option value="4">Movie Collections</option>
        <option value="5">TV Shows</option>
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
    <section id="Theme Types">
      <button type="button" class="theme-type-card border-0" data-theme-type="games" aria-pressed="false">Games</button>
      <button type="button" class="theme-type-card border-0" data-theme-type="game_collections" aria-pressed="false">
        Game Collections
      </button>
      <button type="button" class="theme-type-card border-0" data-theme-type="game_franchises" aria-pressed="false">
        Game Franchises
      </button>
      <button type="button" class="theme-type-card border-0" data-theme-type="movies" aria-pressed="false">Movies</button>
      <button type="button" class="theme-type-card border-0" data-theme-type="movie_collections" aria-pressed="false">
        Movie Collections
      </button>
      <button type="button" class="theme-type-card border-0" data-theme-type="tv_shows" aria-pressed="false">TV Shows</button>
    </section>
    <section id="Games" class="d-none"><div id="games-container"></div></section>
    <section id="Game Collections" class="d-none"><div id="game-collections-container"></div></section>
    <section id="Game Franchises" class="d-none"><div id="game-franchises-container"></div></section>
    <section id="Movies" class="d-none"><div id="movies-container"></div></section>
    <section id="Movie Collections" class="d-none"><div id="movie-collections-container"></div></section>
    <section id="TV Shows" class="d-none"><div id="tv-shows-container"></div></section>
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
 * Return paginated list data for the item loader JSON request mock.
 *
 * @param {string} path Request path.
 * @returns {Object[]} Page item data.
 */
function getPageItems(path) {
  const fixturePath = path.replace(/^\/6732\//, '/ThemerrDB/')
  const pages = {
    '/ThemerrDB/games/all_page_1.json': [{id: 1638, title: 'GoldenEye 007'}],
    '/ThemerrDB/games/all_page_2.json': [{id: 42, title: 'Second Game'}],
    '/ThemerrDB/game_collections/all_page_1.json': [{id: 326, title: 'James Bond'}],
    '/ThemerrDB/game_franchises/all_page_1.json': [{id: 37, title: 'James Bond'}],
    '/ThemerrDB/movies/all_page_1.json': [
      {id: 710, title: 'GoldenEye'},
      {id: 999, title: 'Unrelated Movie'}
    ],
    '/ThemerrDB/movie_collections/all_page_1.json': [{id: 645, title: 'James Bond Collection'}],
    '/ThemerrDB/tv_shows/all_page_1.json': [{id: 1930, title: 'The Beverly Hillbillies'}]
  }
  return pages[fixturePath]
}

/**
 * Return item detail data for the item loader JSON request mock.
 *
 * @param {string} url Request URL.
 * @returns {Object} Item detail data.
 */
function getItemDetails(url) {
  const path = new URL(url, TEST_URL_BASE).pathname
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
    },
    '/themoviedb/1930.json': {
      first_air_date: '1962-09-26',
      id: 1930,
      name: 'The Beverly Hillbillies',
      overview: 'A TV show summary.',
      poster_path: '/beverly-hillbillies.jpg',
      youtube_theme_url: 'https://www.youtube.com/watch?v=tvshow'
    }
  }
  return Object.entries(details).find(([suffix]) => path.endsWith(suffix))?.[1]
}

/**
 * Return a JSON response fixture for an item loader request.
 *
 * @param {string} url Request URL.
 * @returns {{body: Object|Object[], status: number}} Mock response.
 */
function getJsonFixture(url) {
  const path = new URL(url, TEST_URL_BASE).pathname
  if (path.endsWith('/pages.json')) {
    return {body: {pages: path.includes('/games/') ? 2 : 1}, status: 200}
  }

  const pageItems = getPageItems(path)
  if (pageItems) {
    return {body: pageItems, status: 200}
  }

  const itemDetails = getItemDetails(url)
  if (itemDetails) {
    return {body: itemDetails, status: 200}
  }

  return {body: {error: `Unexpected JSON url: ${url}`}, status: 404}
}

/**
 * Install a raw XMLHttpRequest mock used by the browser scripts.
 *
 * @returns {{requests: Object[], xhr: jest.Mock}} Request mock state.
 */
function mockJsonRequests() {
  const requests = []

  class MockXMLHttpRequest {
    async = true
    listeners = {}
    method = null
    responseText = ''
    responseURL = ''
    status = 0
    url = ''

    constructor() {
      requests.push(this)
    }

    addEventListener(eventName, callback) {
      this.listeners[eventName] = callback
    }

    open(method, url, async = true) {
      this.async = async
      this.method = method
      this.responseURL = url
      this.url = url
    }

    send() {
      const response = getJsonFixture(this.url)
      this.responseText = JSON.stringify(response.body)
      this.status = response.status

      if (this.async && this.listeners.load) {
        this.listeners.load()
      }
    }
  }

  globalThis.XMLHttpRequest = jest.fn(() => new MockXMLHttpRequest())

  return {requests, xhr: globalThis.XMLHttpRequest}
}

/**
 * Load item_loader.js after test globals are prepared.
 *
 * @param {{readyState?: string}} options Loader options.
 * @returns {{requests: Object[], timeoutCallbacks: Function[], xhr: jest.Mock}} Script test state.
 */
function loadItemLoader(options = {}) {
  const readyState = options.readyState || 'loading'
  const timeoutCallbacks = []
  const {requests, xhr} = mockJsonRequests()

  if (Object.hasOwn(options, 'basePath')) {
    globalThis.THEMERRDB_CONFIG = {base_path: options.basePath}
  } else {
    delete globalThis.THEMERRDB_CONFIG
  }

  Object.defineProperty(document, 'readyState', {
    configurable: true,
    value: readyState
  })

  jest.spyOn(Date, 'now').mockReturnValue(123456789)
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
  if (readyState === 'loading') {
    document.dispatchEvent(new Event('DOMContentLoaded'))
  }

  return {requests, timeoutCallbacks, xhr}
}

/**
 * Find a captured request by pathname.
 *
 * @param {Object[]} requests Captured requests.
 * @param {string} pathname Expected URL pathname.
 * @returns {Object|undefined} Matching request.
 */
function findRequest(requests, pathname) {
  return requests.find(request => new URL(request.url, TEST_URL_BASE).pathname === pathname)
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
    globalThis.history.replaceState(null, '', '/')
    buildItemLoaderDocument()
  })

  afterEach(() => {
    jest.restoreAllMocks()
    delete globalThis.changeVideo
    delete globalThis.levenshteinDistance
    delete globalThis.rankingSorter
    delete globalThis.run_search
    delete globalThis.THEMERRDB_CONFIG
    delete globalThis.themerrItemLoader
    delete globalThis.XMLHttpRequest
  })

  test('selects theme categories and lazy-loads every item type', () => {
    const {requests, timeoutCallbacks, xhr} = loadItemLoader()

    expect(globalThis.$).toBeUndefined()
    expect(xhr).not.toHaveBeenCalled()
    expect(globalThis.themerrItemLoader.get_active_type()).toBeNull()
    expect(document.getElementById('games-container').textContent).toBe('')
    expect(globalThis.themerrItemLoader.content_section_ids).toEqual([
      'Games',
      'Game Collections',
      'Game Franchises',
      'Movies',
      'Movie Collections',
      'TV Shows'
    ])
    expect(globalThis.themerrItemLoader.normalize_theme_type('TV Shows')).toBe('tv_shows')
    expect(globalThis.themerrItemLoader.get_type_from_hash('#Movie%20Collections')).toBe('movie_collections')
    expect(globalThis.themerrItemLoader.get_type_from_hash('#game-franchises')).toBe('game_franchises')
    expect(globalThis.themerrItemLoader.get_type_from_hash('#missing')).toBeNull()
    expect(globalThis.themerrItemLoader.types_dict.games.base_url).toBe('/ThemerrDB/games/')

    document.querySelector('[data-theme-type="games"]').click()

    expect(findRequest(requests, '/ThemerrDB/games/pages.json').async).toBe(false)
    expect(findRequest(requests, '/ThemerrDB/games/pages.json').url).toBe('/ThemerrDB/games/pages.json?_=123456789')
    expect(findRequest(requests, '/ThemerrDB/games/all_page_1.json').method).toBe('GET')
    expect(requests.every(request => new URL(request.url, TEST_URL_BASE).searchParams.get('_') === '123456789'))
      .toBe(true)
    expect(globalThis.themerrItemLoader.get_active_type()).toBe('games')
    expect(globalThis.location.hash).toBe('#Games')
    expect(globalThis.themerrItemLoader.get_type_section('games')).toBe(document.getElementById('Games'))
    expect(document.querySelector('[data-theme-type="games"]').getAttribute('aria-pressed')).toBe('true')
    expect(document.querySelector('[data-theme-type="movies"]').getAttribute('aria-pressed')).toBe('false')
    expect(document.querySelector('[data-theme-type="games"]').classList.contains('border-0')).toBe(false)
    expect(document.querySelector('[data-theme-type="movies"]').classList.contains('border-0')).toBe(true)
    expect(document.getElementById('Games').classList.contains('d-none')).toBe(false)
    expect(document.getElementById('Movies').classList.contains('d-none')).toBe(true)
    expect(document.getElementById('games-container').textContent).toContain('GoldenEye 007 (1995)')

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

    expect(findRequest(requests, '/ThemerrDB/games/all_page_2.json')).toBeDefined()

    globalThis.themerrItemLoader.show_theme_type('games')
    globalThis.themerrItemLoader.show_theme_type('game_collections')

    expect(document.getElementById('Games').classList.contains('d-none')).toBe(true)
    expect(document.getElementById('game-collections-container').textContent).toContain('James Bond (null)')

    globalThis.themerrItemLoader.show_theme_type('game_franchises')

    expect(document.getElementById('game-franchises-container').textContent).toContain('James Bond (null)')
    expect(document.getElementById('game-franchises-container').querySelector('a[href*="GAME%20FRANCHISE"]'))
      .not.toBeNull()

    document.getElementById('Movies').scrollIntoView = jest.fn()
    globalThis.themerrItemLoader.show_theme_type('movies', true)

    expect(document.getElementById('Movies').scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'start'
    })
    expect(document.getElementById('movies-container').textContent).toContain('GoldenEye (1995)')

    globalThis.themerrItemLoader.show_theme_type('movie_collections')

    expect(document.getElementById('movie-collections-container').textContent)
      .toContain('James Bond Collection (null)')

    globalThis.themerrItemLoader.show_theme_type('tv_shows')
    globalThis.dispatchEvent(new Event('scroll'))

    expect(document.getElementById('tv-shows-container').textContent).toContain('The Beverly Hillbillies (1962)')

    globalThis.themerrItemLoader.show_theme_type('unknown')

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
    const {requests} = loadItemLoader()

    globalThis.themerrItemLoader.show_theme_type('movies')

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
    expect(document.getElementById('Theme Types').classList.contains('d-none')).toBe(true)
    expect(document.getElementById('Movies').classList.contains('d-none')).toBe(true)
    expect(document.getElementById('search-container').textContent).toContain('Clear Results')
    expect(document.getElementById('search-container').textContent).toContain('GoldenEye (1995)')
    expect(document.getElementById('search-container').textContent).not.toContain('Unrelated Movie')
    expect(findRequest(requests, '/ThemerrDB/movies/all_page_1.json')).toBeDefined()

    globalThis.themerrItemLoader.load_search_items('movies')
    document.querySelector('#search-container button').click()

    expect(document.getElementById('search-container').textContent).toBe('')
    expect(document.getElementById('Theme Types').classList.contains('d-none')).toBe(false)
    expect(document.getElementById('Movies').classList.contains('d-none')).toBe(false)
  })

  test('skips empty searches', () => {
    loadItemLoader()
    globalThis.themerrItemLoader.set_content_sections_hidden(false)
    document.getElementById('search_term').value = ''

    globalThis.run_search()

    expect(document.getElementById('Theme Types').classList.contains('d-none')).toBe(false)
    expect(document.getElementById('Movies').classList.contains('d-none')).toBe(true)
    expect(document.getElementById('search-container').textContent).toBe('')
  })

  test('opens a theme category from the location hash', () => {
    globalThis.history.replaceState(null, '', '/#TV%20Shows')

    loadItemLoader()

    expect(globalThis.themerrItemLoader.get_active_type()).toBe('tv_shows')
    expect(document.getElementById('TV Shows').classList.contains('d-none')).toBe(false)
    expect(document.getElementById('tv-shows-container').textContent).toContain('The Beverly Hillbillies (1962)')
  })

  test('uses the injected Read the Docs version path for JSON requests', () => {
    globalThis.history.replaceState(null, '', '/6732/')

    const {requests} = loadItemLoader({basePath: '6732'})

    expect(globalThis.themerrItemLoader.types_dict.games.base_url).toBe('/6732/games/')
    document.querySelector('[data-theme-type="games"]').click()

    expect(findRequest(requests, '/6732/games/pages.json').url).toBe('/6732/games/pages.json?_=123456789')
    expect(findRequest(requests, '/6732/games/all_page_1.json')).toBeDefined()
    expect(() => globalThis.themerrItemLoader.get_trusted_json_url('/ThemerrDB/games/pages.json'))
      .toThrow('Untrusted JSON request URL: /ThemerrDB/games/pages.json')
  })

  test('initializes immediately when loaded after DOM ready', () => {
    globalThis.history.replaceState(null, '', '/#Movies')

    loadItemLoader({readyState: 'complete'})

    expect(globalThis.themerrItemLoader.get_active_type()).toBe('movies')
    expect(document.getElementById('Movies').classList.contains('d-none')).toBe(false)
    expect(document.getElementById('movies-container').textContent).toContain('GoldenEye (1995)')
  })

  test('throws when a JSON request fails', () => {
    loadItemLoader()

    expect(() => globalThis.themerrItemLoader.get_trusted_json_url('https://example.invalid/missing.json'))
      .toThrow('Untrusted JSON request URL: https://example.invalid/missing.json')
    expect(() => globalThis.themerrItemLoader.get_trusted_json_url('https://app.lizardbyte.dev/other/missing.json'))
      .toThrow('Untrusted JSON request URL: https://app.lizardbyte.dev/other/missing.json')
    expect(globalThis.themerrItemLoader.get_trusted_json_url('https://app.lizardbyte.dev/ThemerrDB/games/pages.json'))
      .toBe('/ThemerrDB/games/pages.json?_=123456789')
    expect(() => globalThis.themerrItemLoader.request_json({
      async: false,
      success: jest.fn(),
      url: '/ThemerrDB/missing.json'
    })).toThrow('Failed to load JSON from /ThemerrDB/missing.json?_=123456789: 404')
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
