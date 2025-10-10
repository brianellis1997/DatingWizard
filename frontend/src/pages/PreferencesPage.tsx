import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useDropzone } from 'react-dropzone';
import { preferencesApi } from '../services/api';
import { Upload, X, Plus } from 'lucide-react';

export default function PreferencesPage() {
  const queryClient = useQueryClient();
  const [newTrait, setNewTrait] = useState('');
  const [newInterest, setNewInterest] = useState('');

  const { data: preferences } = useQuery({
    queryKey: ['preferences'],
    queryFn: preferencesApi.getPreferences,
  });

  const { data: referenceImages } = useQuery({
    queryKey: ['reference-images'],
    queryFn: preferencesApi.listReferenceImages,
  });

  const { data: traits } = useQuery({
    queryKey: ['traits'],
    queryFn: preferencesApi.listTraits,
  });

  const { data: interests } = useQuery({
    queryKey: ['interests'],
    queryFn: preferencesApi.listInterests,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => preferencesApi.uploadReferenceImage(file, 'general'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reference-images'] }),
  });

  const deleteImageMutation = useMutation({
    mutationFn: preferencesApi.deleteReferenceImage,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reference-images'] }),
  });

  const updatePrefsMutation = useMutation({
    mutationFn: preferencesApi.updatePreferences,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['preferences'] }),
  });

  const addTraitMutation = useMutation({
    mutationFn: preferencesApi.addTrait,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['traits'] });
      setNewTrait('');
    },
  });

  const deleteTraitMutation = useMutation({
    mutationFn: preferencesApi.deleteTrait,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['traits'] }),
  });

  const addInterestMutation = useMutation({
    mutationFn: (interest: string) => preferencesApi.addInterest(interest, false),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['interests'] });
      setNewInterest('');
    },
  });

  const deleteInterestMutation = useMutation({
    mutationFn: preferencesApi.deleteInterest,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['interests'] }),
  });

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'image/*': ['.png', '.jpg', '.jpeg'] },
    onDrop: (files) => files.forEach((file) => uploadMutation.mutate(file)),
  });

  return (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Preferences</h2>

      {/* Reference Images */}
      <section className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
          Reference Images
        </h3>

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
              : 'border-gray-300 dark:border-gray-600 hover:border-blue-400'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
          <p className="text-gray-600 dark:text-gray-400">
            {isDragActive ? 'Drop images here' : 'Drag & drop images or click to upload'}
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mt-6">
          {referenceImages?.map((img) => (
            <div key={img.id} className="relative group">
              <img
                src={`http://localhost:8000/${img.thumbnail_path || img.file_path}`}
                alt="Reference"
                className="w-full h-32 object-cover rounded-lg"
              />
              <button
                onClick={() => deleteImageMutation.mutate(img.id)}
                className="absolute top-2 right-2 bg-red-500 text-white p-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Weights */}
      {preferences && (
        <section className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
            Importance Weights
          </h3>

          <div className="space-y-4">
            {(['physical_weight', 'personality_weight', 'interest_weight'] as const).map((key) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {key.replace('_weight', '').charAt(0).toUpperCase() +
                    key.replace('_weight', '').slice(1)}
                  : {(preferences[key] * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={preferences[key] * 100}
                  onChange={(e) =>
                    updatePrefsMutation.mutate({ [key]: Number(e.target.value) / 100 })
                  }
                  className="w-full"
                />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Personality Traits */}
      <section className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
          Personality Traits
        </h3>

        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={newTrait}
            onChange={(e) => setNewTrait(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && newTrait && addTraitMutation.mutate(newTrait)}
            placeholder="Add trait..."
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white"
          />
          <button
            onClick={() => newTrait && addTraitMutation.mutate(newTrait)}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {traits?.map((trait) => (
            <span
              key={trait.id}
              className="inline-flex items-center gap-2 px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full"
            >
              {trait.trait}
              <button onClick={() => deleteTraitMutation.mutate(trait.id)}>
                <X className="w-4 h-4" />
              </button>
            </span>
          ))}
        </div>
      </section>

      {/* Shared Interests */}
      <section className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
          Shared Interests
        </h3>

        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={newInterest}
            onChange={(e) => setNewInterest(e.target.value)}
            onKeyPress={(e) =>
              e.key === 'Enter' && newInterest && addInterestMutation.mutate(newInterest)
            }
            placeholder="Add interest..."
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white"
          />
          <button
            onClick={() => newInterest && addInterestMutation.mutate(newInterest)}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {interests?.map((interest) => (
            <span
              key={interest.id}
              className="inline-flex items-center gap-2 px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full"
            >
              {interest.interest}
              <button onClick={() => deleteInterestMutation.mutate(interest.id)}>
                <X className="w-4 h-4" />
              </button>
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}
