import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useDropzone } from 'react-dropzone';
import { classificationApi, resultsApi } from '../services/api';
import { Upload, CheckCircle, XCircle, ThumbsUp, ThumbsDown, Star } from 'lucide-react';
import type { ClassificationResult } from '../types';

export default function ClassifyPage() {
  const [results, setResults] = useState<ClassificationResult[]>([]);
  const queryClient = useQueryClient();

  const classifyMutation = useMutation({
    mutationFn: classificationApi.classifyScreenshot,
    onSuccess: (data) => {
      setResults((prev) => [data, ...prev]);
      queryClient.invalidateQueries({ queryKey: ['overview-stats'] });
    },
  });

  const feedbackMutation = useMutation({
    mutationFn: ({ resultId, feedback }: { resultId: number; feedback: 'like' | 'dislike' | 'super_like' }) =>
      resultsApi.submitFeedback(resultId, feedback),
    onSuccess: (updatedResult) => {
      // Update the result in the local state
      setResults((prev) =>
        prev.map((r) => (r.id === updatedResult.id ? updatedResult : r))
      );
      queryClient.invalidateQueries({ queryKey: ['overview-stats'] });
    },
  });

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'image/*': ['.png', '.jpg', '.jpeg'] },
    onDrop: (files) => files.forEach((file) => classifyMutation.mutate(file)),
  });

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Classify Profiles</h2>

      {/* Upload Zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 bg-white dark:bg-gray-800'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="w-16 h-16 mx-auto mb-4 text-gray-400" />
        <p className="text-xl text-gray-600 dark:text-gray-400 mb-2">
          {isDragActive ? 'Drop screenshots here' : 'Drag & drop profile screenshots'}
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-500">
          Supports PNG, JPG, JPEG
        </p>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Results</h3>

          {results.map((result) => (
            <div
              key={result.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow p-6"
            >
              <div className="flex items-start gap-6">
                {/* Status Icon */}
                <div className="flex-shrink-0">
                  {result.is_match ? (
                    <div className="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
                      <CheckCircle className="w-10 h-10 text-green-600 dark:text-green-400" />
                    </div>
                  ) : (
                    <div className="w-16 h-16 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
                      <XCircle className="w-10 h-10 text-red-600 dark:text-red-400" />
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {result.is_match ? '✅ MATCH' : '❌ NO MATCH'}
                    </h4>
                    <span className="text-2xl font-bold text-gray-900 dark:text-white">
                      {(result.confidence_score * 100).toFixed(1)}%
                    </span>
                  </div>

                  {/* Profile Info */}
                  {(result.name || result.age) && (
                    <p className="text-gray-700 dark:text-gray-300 mb-2">
                      {result.name}{result.age && `, ${result.age}`}
                    </p>
                  )}

                  {result.bio && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                      {result.bio.substring(0, 150)}
                      {result.bio.length > 150 && '...'}
                    </p>
                  )}

                  {/* Component Scores */}
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <ScoreBar label="Physical" value={result.physical_score} color="blue" />
                    <ScoreBar
                      label="Personality"
                      value={result.personality_score}
                      color="purple"
                    />
                    <ScoreBar label="Interests" value={result.interest_score} color="green" />
                  </div>

                  {/* Reasons */}
                  {result.reasons.length > 0 && (
                    <div className="mb-4">
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        💡 Reasons:
                      </p>
                      <ul className="list-disc list-inside space-y-1">
                        {result.reasons.map((reason) => (
                          <li
                            key={reason.id}
                            className="text-sm text-gray-600 dark:text-gray-400"
                          >
                            {reason.reason}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Feedback Buttons */}
                  <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                      🎯 Help improve the model:
                    </p>
                    <div className="flex gap-3">
                      <button
                        onClick={() => feedbackMutation.mutate({ resultId: result.id, feedback: 'dislike' })}
                        disabled={feedbackMutation.isPending}
                        className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                          result.user_feedback === 'dislike'
                            ? 'bg-red-500 text-white'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-red-100 dark:hover:bg-red-900/30'
                        }`}
                      >
                        <ThumbsDown className="w-5 h-5" />
                        Dislike
                      </button>

                      <button
                        onClick={() => feedbackMutation.mutate({ resultId: result.id, feedback: 'like' })}
                        disabled={feedbackMutation.isPending}
                        className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                          result.user_feedback === 'like'
                            ? 'bg-green-500 text-white'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-green-100 dark:hover:bg-green-900/30'
                        }`}
                      >
                        <ThumbsUp className="w-5 h-5" />
                        Like
                      </button>

                      <button
                        onClick={() => feedbackMutation.mutate({ resultId: result.id, feedback: 'super_like' })}
                        disabled={feedbackMutation.isPending}
                        className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                          result.user_feedback === 'super_like'
                            ? 'bg-yellow-500 text-white'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-yellow-100 dark:hover:bg-yellow-900/30'
                        }`}
                      >
                        <Star className="w-5 h-5" />
                        Super Like
                      </button>
                    </div>

                    {result.user_feedback && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
                        ✓ Feedback recorded - this helps train the model!
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface ScoreBarProps {
  label: string;
  value: number;
  color: 'blue' | 'purple' | 'green';
}

function ScoreBar({ label, value, color }: ScoreBarProps) {
  const colors = {
    blue: 'bg-blue-500',
    purple: 'bg-purple-500',
    green: 'bg-green-500',
  };

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600 dark:text-gray-400">{label}</span>
        <span className="font-medium text-gray-900 dark:text-white">
          {(value * 100).toFixed(0)}%
        </span>
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div
          className={`${colors[color]} h-2 rounded-full transition-all`}
          style={{ width: `${value * 100}%` }}
        />
      </div>
    </div>
  );
}
