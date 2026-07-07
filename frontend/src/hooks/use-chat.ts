import { useState, useCallback } from 'react';
import { api } from '../lib/api';
import type { QueryResponse, RenderedChart } from '../types';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  charts?: RenderedChart[];
  sql?: string | null;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (
    datasetId: string,
    question: string,
    options?: { model?: string; provider?: string; systemPromptKey?: string },
  ) => {
    // Add user message
    const userMsg: ChatMessage = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError(null);

    try {
      const res: QueryResponse = await api.query({
        dataset_id: datasetId,
        question,
        ...options,
        system_prompt_key: options?.systemPromptKey || 'data_analyst',
      });

      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: res.error || res.answer,
        charts: res.rendered_charts?.length ? res.rendered_charts : undefined,
        sql: res.sql,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      return res;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Query failed';
      setError(msg);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${msg}` },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, loading, error, sendMessage, clearMessages };
}
