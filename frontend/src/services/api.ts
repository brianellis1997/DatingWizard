// API Service for Dating Wizard Backend

import axios from 'axios';
import type {
  ReferenceImage,
  Preference,
  Keyword,
  Trait,
  Interest,
  ClassificationResult,
  ClassifierStats,
  ResultsStats,
  InstagramSearch,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Preferences API
export const preferencesApi = {
  // Reference Images
  uploadReferenceImage: async (file: File, category: string, description?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);
    if (description) formData.append('description', description);

    const { data } = await api.post<ReferenceImage>('/preferences/reference-images', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  listReferenceImages: async () => {
    const { data } = await api.get<ReferenceImage[]>('/preferences/reference-images');
    return data;
  },

  deleteReferenceImage: async (id: number) => {
    await api.delete(`/preferences/reference-images/${id}`);
  },

  // Preferences
  getPreferences: async () => {
    const { data } = await api.get<Preference>('/preferences');
    return data;
  },

  updatePreferences: async (updates: Partial<Preference>) => {
    const { data } = await api.put<Preference>('/preferences', updates);
    return data;
  },

  // Keywords
  addKeyword: async (keyword: string, type: 'positive' | 'negative' | 'required') => {
    const { data } = await api.post<Keyword>('/preferences/keywords', {
      keyword,
      keyword_type: type,
    });
    return data;
  },

  listKeywords: async () => {
    const { data } = await api.get<Keyword[]>('/preferences/keywords');
    return data;
  },

  deleteKeyword: async (id: number) => {
    await api.delete(`/preferences/keywords/${id}`);
  },

  // Traits
  addTrait: async (trait: string) => {
    const { data } = await api.post<Trait>('/preferences/traits', { trait });
    return data;
  },

  listTraits: async () => {
    const { data } = await api.get<Trait[]>('/preferences/traits');
    return data;
  },

  deleteTrait: async (id: number) => {
    await api.delete(`/preferences/traits/${id}`);
  },

  // Interests
  addInterest: async (interest: string, is_dealbreaker: boolean = false) => {
    const { data } = await api.post<Interest>('/preferences/interests', {
      interest,
      is_dealbreaker,
    });
    return data;
  },

  listInterests: async () => {
    const { data } = await api.get<Interest[]>('/preferences/interests');
    return data;
  },

  deleteInterest: async (id: number) => {
    await api.delete(`/preferences/interests/${id}`);
  },
};

// Classification API
export const classificationApi = {
  classifyScreenshot: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const { data } = await api.post<ClassificationResult>('/classify/screenshot', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  classifyBatch: async (files: File[]) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    const { data } = await api.post('/classify/batch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  getResult: async (id: number) => {
    const { data } = await api.get<ClassificationResult>(`/classify/results/${id}`);
    return data;
  },
};

// Results API
export const resultsApi = {
  getHistory: async (skip: number = 0, limit: number = 20, matchesOnly: boolean = false) => {
    const { data } = await api.get<ClassificationResult[]>('/results/history', {
      params: { skip, limit, matches_only: matchesOnly },
    });
    return data;
  },

  getMatches: async (skip: number = 0, limit: number = 20) => {
    const { data } = await api.get<ClassificationResult[]>('/results/matches', {
      params: { skip, limit },
    });
    return data;
  },

  deleteResult: async (id: number) => {
    await api.delete(`/results/${id}`);
  },

  getOverviewStats: async () => {
    const { data } = await api.get<ResultsStats>('/results/stats/overview');
    return data;
  },

  getClassifierStats: async () => {
    const { data } = await api.get<ClassifierStats>('/results/stats/classifier');
    return data;
  },
};

// Instagram API
export const instagramApi = {
  search: async (query: string, limit: number = 20, minScore: number = 0.6) => {
    const { data } = await api.post<InstagramSearch>('/instagram/search', {
      query,
      limit,
      min_score: minScore,
    });
    return data;
  },

  listSearches: async (skip: number = 0, limit: number = 20) => {
    const { data } = await api.get<InstagramSearch[]>('/instagram/searches', {
      params: { skip, limit },
    });
    return data;
  },

  getSearch: async (id: number) => {
    const { data } = await api.get<InstagramSearch>(`/instagram/searches/${id}`);
    return data;
  },
};

export default api;
