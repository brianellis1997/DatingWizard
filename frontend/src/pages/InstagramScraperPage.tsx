import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { instagramApi } from '../services/api';
import { Search, Instagram, CheckCircle, XCircle, ThumbsUp, ThumbsDown, Star, Loader2, Hash } from 'lucide-react';
import type { InstagramResult, InstagramSearch } from '../types';

export default function InstagramScraperPage() {
  const [hashtag, setHashtag] = useState('');
  const [username, setUsername] = useState('');
  const [limit, setLimit] = useState(20);
  const [minScore, setMinScore] = useState(0.6);
  const queryClient = useQueryClient();

  // Fetch recent searches
  const { data: searches = [] } = useQuery({
    queryKey: ['instagram-searches'],
    queryFn: () => instagramApi.listSearches(0, 10),
  });

  // Fetch recent results
  const { data: results = [], refetch: refetchResults } = useQuery({
    queryKey: ['instagram-results'],
    queryFn: () => instagramApi.listResults(0, 20, false),
  });

  // Scrape hashtag mutation
  const scrapeHashtagMutation = useMutation({
    mutationFn: (data: { query: string; limit: number; minScore: number }) =>
      instagramApi.scrapeHashtag(data.query, data.limit, data.minScore),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instagram-searches'] });
      setHashtag('');
      alert('Hashtag scraping started in background! This will take several hours with conservative rate limiting.');
    },
  });

  // Scrape username mutation
  const scrapeUsernameMutation = useMutation({
    mutationFn: (username: string) => instagramApi.scrapeUsername(username),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instagram-results'] });
      setUsername('');
      refetchResults();
    },
  });

  // Feedback mutation
  const feedbackMutation = useMutation({
    mutationFn: ({ resultId, feedback }: { resultId: number; feedback: 'like' | 'dislike' | 'super_like' }) =>
      instagramApi.submitFeedback(resultId, feedback),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instagram-results'] });
      refetchResults();
    },
  });

  const handleHashtagSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hashtag.trim()) return;

    const cleanHashtag = hashtag.replace('#', '').trim();
    scrapeHashtagMutation.mutate({
      query: cleanHashtag,
      limit,
      minScore,
    });
  };

  const handleUsernameSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) return;

    const cleanUsername = username.replace('@', '').trim();
    scrapeUsernameMutation.mutate(cleanUsername);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Instagram className="w-8 h-8 text-pink-500" />
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Instagram Scraper</h2>
      </div>

      <p className="text-gray-600 dark:text-gray-400">
        Automatically scrape Instagram profiles, classify them with CLIP, and collect training data.
      </p>

      {/* Scraping Forms */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Hashtag Scraping */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Hash className="w-5 h-5" />
            Scrape by Hashtag
          </h3>

          <form onSubmit={handleHashtagSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Hashtag
              </label>
              <input
                type="text"
                value={hashtag}
                onChange={(e) => setHashtag(e.target.value)}
                placeholder="fitness, travel, etc."
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Profiles to Scrape: {limit}
              </label>
              <input
                type="range"
                min="5"
                max="60"
                step="5"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="w-full"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Estimated time: {Math.round((limit * 6.5) / 60)} hours
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Min Score: {(minScore * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                className="w-full"
              />
            </div>

            <button
              type="submit"
              disabled={scrapeHashtagMutation.isPending || !hashtag.trim()}
              className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-3 rounded-lg font-semibold hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {scrapeHashtagMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Search className="w-5 h-5" />
                  Start Scraping
                </>
              )}
            </button>

            <p className="text-xs text-gray-500 dark:text-gray-400">
              Conservative rate limiting: 5-8 min between profiles, 1 hour pause every 20 profiles
            </p>
          </form>
        </div>

        {/* Username Scraping */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Instagram className="w-5 h-5" />
            Scrape by Username
          </h3>

          <form onSubmit={handleUsernameSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Instagram Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="username"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>

            <button
              type="submit"
              disabled={scrapeUsernameMutation.isPending || !username.trim()}
              className="w-full bg-pink-500 text-white px-6 py-3 rounded-lg font-semibold hover:bg-pink-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {scrapeUsernameMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Scraping...
                </>
              ) : (
                <>
                  <Search className="w-5 h-5" />
                  Scrape Profile
                </>
              )}
            </button>

            <p className="text-xs text-gray-500 dark:text-gray-400">
              Test with a single profile before batch scraping
            </p>
          </form>
        </div>
      </div>

      {/* Recent Searches */}
      {searches.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Recent Searches</h3>
          <div className="space-y-3">
            {searches.map((search: InstagramSearch) => (
              <div
                key={search.id}
                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
              >
                <div>
                  <p className="font-semibold text-gray-900 dark:text-white">#{search.query}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {search.total_found} profiles scraped, {search.matches_found} matches
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-500">
                    {new Date(search.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Limit: {search.limit}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-500">
                    Min: {(search.min_score * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results Grid */}
      {results.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
            Scraped Profiles ({results.length})
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {results.map((result: InstagramResult) => (
              <div
                key={result.id}
                className="bg-white dark:bg-gray-800 rounded-lg shadow p-4"
              >
                {/* Screenshot */}
                {result.screenshot_path && (
                  <div className="mb-3">
                    <img
                      src={`http://localhost:8000/${result.screenshot_path}`}
                      alt={result.username}
                      className="w-full h-48 object-cover rounded-lg"
                      onError={(e) => {
                        console.error('Failed to load image:', result.screenshot_path);
                        e.currentTarget.style.display = 'none';
                      }}
                    />
                  </div>
                )}

                {/* Profile Info */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-gray-900 dark:text-white">
                        @{result.username}
                      </p>
                      {result.name && (
                        <p className="text-sm text-gray-600 dark:text-gray-400">{result.name}</p>
                      )}
                    </div>
                    {result.is_match !== undefined && (
                      <div className="flex-shrink-0">
                        {result.is_match ? (
                          <CheckCircle className="w-6 h-6 text-green-500" />
                        ) : (
                          <XCircle className="w-6 h-6 text-red-500" />
                        )}
                      </div>
                    )}
                  </div>

                  {/* Scores */}
                  {result.confidence_score !== undefined && (
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600 dark:text-gray-400">Confidence</span>
                        <span className="font-semibold text-gray-900 dark:text-white">
                          {(result.confidence_score * 100).toFixed(1)}%
                        </span>
                      </div>
                      {result.physical_score !== undefined && (
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-500 dark:text-gray-500">Physical</span>
                          <span className="text-gray-700 dark:text-gray-300">
                            {(result.physical_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}
                      {result.personality_score !== undefined && (
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-500 dark:text-gray-500">Personality</span>
                          <span className="text-gray-700 dark:text-gray-300">
                            {(result.personality_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}
                      {result.interest_score !== undefined && (
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-500 dark:text-gray-500">Interests</span>
                          <span className="text-gray-700 dark:text-gray-300">
                            {(result.interest_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Bio Preview */}
                  {result.bio && (
                    <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                      {result.bio}
                    </p>
                  )}

                  {/* Feedback Buttons */}
                  <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                    {!result.user_feedback ? (
                      <div className="flex gap-2">
                        <button
                          onClick={() => feedbackMutation.mutate({ resultId: result.id, feedback: 'dislike' })}
                          className="flex-1 px-3 py-2 bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/40 flex items-center justify-center gap-1 text-sm"
                        >
                          <ThumbsDown className="w-4 h-4" />
                          Dislike
                        </button>
                        <button
                          onClick={() => feedbackMutation.mutate({ resultId: result.id, feedback: 'like' })}
                          className="flex-1 px-3 py-2 bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/40 flex items-center justify-center gap-1 text-sm"
                        >
                          <ThumbsUp className="w-4 h-4" />
                          Like
                        </button>
                        <button
                          onClick={() => feedbackMutation.mutate({ resultId: result.id, feedback: 'super_like' })}
                          className="flex-1 px-3 py-2 bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400 rounded-lg hover:bg-yellow-200 dark:hover:bg-yellow-900/40 flex items-center justify-center gap-1 text-sm"
                        >
                          <Star className="w-4 h-4" />
                          Super
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <div
                          className={`px-4 py-2 rounded-lg text-center text-sm font-semibold ${
                            result.user_feedback === 'dislike'
                              ? 'bg-red-500 text-white'
                              : result.user_feedback === 'like'
                              ? 'bg-green-500 text-white'
                              : 'bg-yellow-500 text-white'
                          }`}
                        >
                          {result.user_feedback === 'dislike' && '👎 Disliked'}
                          {result.user_feedback === 'like' && '👍 Liked'}
                          {result.user_feedback === 'super_like' && '⭐ Super Liked'}
                        </div>
                        <button
                          onClick={() => instagramApi.removeFeedback(result.id).then(() => refetchResults())}
                          className="w-full text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                        >
                          Revert Feedback
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Instagram Link */}
                  {result.url && (
                    <a
                      href={result.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block text-xs text-blue-500 hover:text-blue-600 text-center"
                    >
                      View on Instagram →
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {results.length === 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
          <Instagram className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            No scraped profiles yet
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Start by scraping a single username to test, then launch hashtag scraping overnight.
          </p>
        </div>
      )}
    </div>
  );
}
