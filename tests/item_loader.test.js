/**
 * @jest-environment jsdom
 *
 * @file Tests for the static site item loader.
 */
/* global document, KeyboardEvent, window */

const fs = require('fs')
const path = require('path')
const vm = require('vm')

const {
  afterEach,
  beforeEach,
  describe,
  expect,
  jest,
  test
} = require('@jest/globals')

const ITEM_LOADER_PATH = path.join(__dirname, '..', 'gh-pages-template', 'assets', 'js', 'item_loader.js')

/**
 * Build the page nodes expected by item_loader.js.
 *
 * @returns {void}
 */
function buildDocument() {
  document.body.innerHTML = `
    <form id="searchForm">
      <select id="search_type">
        <option value="0">Games</option>
        <option selected value="3">Movies</option>
      </select>
      <input id="search_term" value="goldeneye">
      <button type="button">Search</button>
    </form>
    <div id="search-container"></div>
    <section id="Games"><div id="games-container"></div></section>
    <section id="Game Collections"><div id="game-collections-container"></div></section>
    <section id="Game Franchises"><div id="game-franchises-container"></div></section>
    <section id="Movies"><div id="movies-container"></div></section>
    <section id="Movie Collections"><div id="movie-collections-container"></div></section>
  `
}

describe('item loader search', () => {
  let ajax
  let initialLoad
  let readyCallbacks
  let scriptContext

  beforeEach(() => {
    buildDocument()
    initialLoad = true
    readyCallbacks = []
    ajax = jest.fn(options => {
      if (options.url.endsWith('pages.json')) {
        options.success({pages: initialLoad ? 0 : 1})
        return
      }

      if (options.url.endsWith('all_page_1.json')) {
        options.success([{id: 710, title: 'GoldenEye'}])
        return
      }

      if (options.url.endsWith('/themoviedb/710.json')) {
        options.success({
          id: 710,
          overview: 'A movie summary.',
          poster_path: '/goldeneye.jpg',
          release_date: '1995-11-16',
          title: 'GoldenEye',
          youtube_theme_url: 'https://www.youtube.com/watch?v=abc123'
        })
        return
      }

      throw new Error(`Unexpected ajax url: ${options.url}`)
    })
    const jquery = jest.fn(() => ({
      ready: callback => readyCallbacks.push(callback)
    }))
    jquery.ajax = ajax
    jquery.ajaxSetup = jest.fn()
    scriptContext = {
      $: jquery,
      console,
      document,
      encodeURIComponent,
      FormData,
      setTimeout,
      window
    }
    scriptContext.changeVideo = jest.fn()
    scriptContext.levenshteinDistance = jest.fn(() => 100)
    scriptContext.rankingSorter = jest.fn((scoreKey, titleKey) => (left, right) => (
      right[scoreKey] - left[scoreKey] || left[titleKey].localeCompare(right[titleKey])
    ))
    scriptContext.globalThis = scriptContext
    vm.createContext(scriptContext)
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  test('searches cached page data and clears search results', () => {
    vm.runInContext(fs.readFileSync(ITEM_LOADER_PATH, 'utf8'), scriptContext, {
      filename: ITEM_LOADER_PATH
    })
    for (let callback of readyCallbacks) {
      callback()
    }
    initialLoad = false

    document.getElementById('searchForm').dispatchEvent(new KeyboardEvent('keypress', {
      bubbles: true,
      key: 'Enter'
    }))

    expect(scriptContext.levenshteinDistance).toHaveBeenCalledWith('goldeneye', 'goldeneye')
    expect(document.getElementById('Movies').classList.contains('d-none')).toBe(true)
    expect(document.getElementById('search-container').textContent).toContain('Clear Results')
    expect(document.getElementById('search-container').textContent).toContain('GoldenEye (1995)')
    expect(ajax).toHaveBeenCalledWith(expect.objectContaining({
      url: 'https://app.lizardbyte.dev/ThemerrDB/movies/all_page_1.json'
    }))

    document.querySelector('#search-container button').click()

    expect(document.getElementById('search-container').textContent).toBe('')
    expect(document.getElementById('Movies').classList.contains('d-none')).toBe(false)
  })
})
