import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import type { ModelInfo } from '../types';

export function useModels() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<ModelInfo | null>(null);

  useEffect(() => {
    api.listModels().then((list) => {
      setModels(list);
      if (list.length > 0 && !selectedModel) {
        setSelectedModel(list[0]);
      }
    }).catch(() => {});
  }, []);

  return { models, selectedModel, setSelectedModel };
}
