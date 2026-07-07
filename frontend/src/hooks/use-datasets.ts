import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';
import type { DatasetInfo, DatasetListItem } from '../types';

export function useDatasets() {
  const [datasets, setDatasets] = useState<DatasetListItem[]>([]);
  const [activeDataset, setActiveDataset] = useState<DatasetInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const list = await api.listDatasets();
      setDatasets(list);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const uploadFile = async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.uploadFile(file);
      setActiveDataset(res.dataset);
      await refresh();
      return res;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Upload failed';
      setError(msg);
      throw e;
    } finally {
      setLoading(false);
    }
  };

  const connectDb = async (config: Parameters<typeof api.connectDb>[0]) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.connectDb(config);
      setActiveDataset(res.dataset);
      await refresh();
      return res;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Connection failed';
      setError(msg);
      throw e;
    } finally {
      setLoading(false);
    }
  };

  const selectDataset = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const info = await api.getDataset(id);
      setActiveDataset(info);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to load dataset';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const removeDataset = useCallback(async (id: string) => {
    try {
      await api.deleteDataset(id);
      if (activeDataset?.id === id) setActiveDataset(null);
      await refresh();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to remove';
      setError(msg);
    }
  }, [activeDataset, refresh]);

  return {
    datasets, activeDataset, loading, error,
    uploadFile, connectDb, selectDataset, removeDataset, refresh,
  };
}
