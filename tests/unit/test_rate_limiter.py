"""
test_rate_limiter.py

This module contains unit tests for the RateLimiter class. The RateLimiter class is responsible for
controlling API request frequency to ensure compliance with API rate limits. Tests in this module
validate that the rate limiter correctly throttles requests according to specified rates.
"""
# standard imports
import math
import time
import threading

# local imports
from src.updater import RateLimiter


class TestRateLimiter:
    """Test suite for the RateLimiter class."""

    def test_rate_limiter_initialization(self):
        """Test that RateLimiter initializes with correct parameters."""
        limiter = RateLimiter(max_requests_per_second=10)

        assert limiter.max_requests_per_second == 10
        assert math.isclose(limiter.min_interval, 0.1, rel_tol=1e-09, abs_tol=1e-09)
        assert limiter.last_request_time == 0
        assert limiter.lock is not None

    def test_rate_limiter_allows_immediate_first_request(self):
        """Test that first request doesn't incur delay."""
        limiter = RateLimiter(max_requests_per_second=10)

        start_time = time.time()
        limiter.wait()
        elapsed_time = time.time() - start_time

        # First request should be nearly instant (less than 50ms)
        assert elapsed_time < 0.05

    def test_rate_limiter_enforces_minimum_interval(self):
        """Test that rate limiter enforces minimum interval between requests."""
        limiter = RateLimiter(max_requests_per_second=10)  # min_interval = 0.1 seconds

        limiter.wait()
        start_time = time.time()
        limiter.wait()
        elapsed_time = time.time() - start_time

        # Second request should be delayed by approximately min_interval
        assert elapsed_time >= 0.09  # Allow small margin for execution time

    def test_rate_limiter_tmdb_40_requests_per_second(self):
        """Test TMDB rate limiter (40 requests/second = 0.025s per request)."""
        limiter = RateLimiter(max_requests_per_second=40)

        assert math.isclose(limiter.min_interval, 0.025, rel_tol=1e-09, abs_tol=1e-09)

        # Make multiple requests and measure throughput
        start_time = time.time()
        for _ in range(10):
            limiter.wait()
        elapsed_time = time.time() - start_time

        # 10 requests should take approximately 9 * 0.025 = 0.225 seconds
        # (first request is immediate, then 9 intervals)
        assert elapsed_time >= 0.22
        assert elapsed_time < 0.35  # Allow some margin

    def test_rate_limiter_igdb_4_requests_per_second(self):
        """Test IGDB rate limiter (4 requests/second = 0.25s per request)."""
        limiter = RateLimiter(max_requests_per_second=4)

        assert math.isclose(limiter.min_interval, 0.25, rel_tol=1e-09, abs_tol=1e-09)

        # Make multiple requests and measure throughput
        start_time = time.time()
        for _ in range(3):
            limiter.wait()
        elapsed_time = time.time() - start_time

        # 3 requests should take approximately 2 * 0.25 = 0.5 seconds
        # (first request is immediate, then 2 intervals)
        assert elapsed_time >= 0.49
        assert elapsed_time < 0.65  # Allow some margin

    def test_rate_limiter_thread_safe(self):
        """Test that rate limiter is thread-safe across multiple threads."""
        limiter = RateLimiter(max_requests_per_second=10)
        request_times = []
        lock = threading.Lock()

        def make_requests(thread_id):
            """Function to make requests from a thread."""
            for _ in range(5):
                limiter.wait()
                with lock:
                    request_times.append(time.time())

        # Create and start multiple threads
        threads = []
        for t_id in range(3):
            thread = threading.Thread(target=make_requests, args=(t_id,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify that all requests were made
        assert len(request_times) == 15  # 3 threads * 5 requests

        # Verify that requests are throttled appropriately
        # Sort request times and check intervals
        request_times.sort()
        intervals = [request_times[i + 1] - request_times[i] for i in range(len(request_times) - 1)]

        # Most intervals should be around min_interval (0.1s for 10 req/s)
        avg_interval = sum(intervals) / len(intervals)
        assert avg_interval >= 0.09  # Allow small margin

    def test_rate_limiter_handles_fractional_rates(self):
        """Test that rate limiter correctly handles fractional rates."""
        limiter = RateLimiter(max_requests_per_second=2.5)

        assert math.isclose(limiter.min_interval, 0.4, rel_tol=1e-09, abs_tol=1e-09)  # 1 / 2.5

    def test_rate_limiter_variable_request_rates(self):
        """Test rate limiter with different request rates."""
        test_cases = [
            (1, 1.0),  # 1 request/second = 1.0 second interval
            (2, 0.5),  # 2 requests/second = 0.5 second interval
            (5, 0.2),  # 5 requests/second = 0.2 second interval
            (10, 0.1),  # 10 requests/second = 0.1 second interval
            (40, 0.025),  # 40 requests/second = 0.025 second interval (TMDB)
            (100, 0.01),  # 100 requests/second = 0.01 second interval
        ]

        for rate, expected_interval in test_cases:
            limiter = RateLimiter(max_requests_per_second=rate)
            assert math.isclose(limiter.min_interval, expected_interval, rel_tol=1e-09, abs_tol=1e-09)
            assert limiter.max_requests_per_second == rate

    def test_rate_limiter_multiple_sequential_waits(self):
        """Test that multiple sequential waits maintain rate limit."""
        limiter = RateLimiter(max_requests_per_second=5)  # 0.2s per request

        start_time = time.time()
        for _ in range(5):
            limiter.wait()
        total_time = time.time() - start_time

        # 5 requests should take approximately 4 * 0.2 = 0.8 seconds
        # (first request is immediate, then 4 intervals)
        assert total_time >= 0.78
        assert total_time < 1.0  # Allow some margin

    def test_rate_limiter_updates_last_request_time(self):
        """Test that rate limiter updates last_request_time correctly."""
        limiter = RateLimiter(max_requests_per_second=10)

        initial_time = limiter.last_request_time
        assert initial_time == 0

        limiter.wait()
        first_call_time = limiter.last_request_time
        assert first_call_time > 0
        assert first_call_time > initial_time

        limiter.wait()
        second_call_time = limiter.last_request_time
        assert second_call_time >= first_call_time
