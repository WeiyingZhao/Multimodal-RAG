/* eslint-disable @typescript-eslint/no-explicit-any */
// Chat API adapter
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  references?: Array<{
    id: string;
    title: string;
    content: string;
    source: string;
  }>;
}

export interface StreamingResponse {
  type: 'content_delta' | 'message_complete' | 'error';
  content?: string;
  full_content?: string;
  error?: string;
  timestamp: string;
  references?: Array<any>;
}

// Content block interface (supports multimodal)
export interface ContentBlock {
  type: 'text' | 'image' | 'audio' | 'pdf';
  content: string;
  thumbnail?: string;
  transcription?: string; // Audio transcription text
  filename?: string; // PDF filename
  filesize?: number; // PDF file size
}

export interface ChatRequest {
  content: string;
  content_blocks?: ContentBlock[];
  pdf_chunks?: any[];  // PDF document chunk information for reference tracing
  history: Array<{
    role: string;
    content: string;
    content_blocks?: ContentBlock[];
  }>;
  model?: string;
  knowledge_base?: string;
}

const API_BASE_URL = 'http://localhost:8000';

export class ChatAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Streaming chat interface
   */
  async *streamChat(request: ChatRequest): AsyncGenerator<StreamingResponse, void, unknown> {
    try {
      console.log('🌐 Initiating API request to:', `${this.baseUrl}/api/chat/stream`);
      console.log('📤 Request data:', {
        content: request.content,
        content_blocks_count: request.content_blocks?.length || 0,
        audio_blocks: request.content_blocks?.filter(b => b.type === 'audio').length || 0,
        has_transcription: request.content_blocks?.some(b => b.type === 'audio' && b.transcription) || false,
        pdf_chunks_count: request.pdf_chunks?.length || 0,
        history_count: request.history?.length || 0,
        model: request.model
      });

      // Debug PDF chunks
      if (request.pdf_chunks && request.pdf_chunks.length > 0) {
        console.log('📚 Frontend sending PDF chunks count:', request.pdf_chunks.length);
        console.log('📚 Frontend PDF chunks preview:', request.pdf_chunks.slice(0, 2));
      } else {
        console.log('📚 Frontend has no PDF chunks data');
      }

      // Show detailed content_blocks
      if (request.content_blocks && request.content_blocks.length > 0) {
        console.log('📋 Detailed content_blocks:', request.content_blocks.map(b => ({
          type: b.type,
          hasContent: !!b.content,
          hasTranscription: !!b.transcription,
          transcriptionPreview: b.transcription ? b.transcription.substring(0, 50) + '...' : 'N/A'
        })));
      }
      
      const response = await fetch(`${this.baseUrl}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          content: request.content,
          content_blocks: request.content_blocks || [],
          pdf_chunks: request.pdf_chunks || [],
          history: request.history,
          model: request.model || 'gpt-4o',
          knowledge_base: request.knowledge_base || 'default'
        }),
      });

      console.log('📡 Received response, status code:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ HTTP error:', response.status, errorText);
        throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        console.error('❌ Unable to get response stream reader');
        throw new Error('Unable to read response stream');
      }

      console.log('📖 Starting to read streaming response...');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          console.log('✅ Streaming response reading complete');
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        console.log('📋 Received data chunk, buffer length:', buffer.length);

        // Process Server-Sent Events format
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep the last line (might be incomplete)

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              console.log('✨ Parsed SSE data:', data.type, data.content?.substring(0, 30));
              yield data as StreamingResponse;

              // If completion or error signal received, stop parsing
              if (data.type === 'message_complete' || data.type === 'error') {
                console.log('🏁 Received completion or error signal, ending stream');
                return;
              }
            } catch (e) {
              console.warn('⚠️ Failed to parse SSE data:', e, 'raw line:', line);
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming chat request failed:', error);
      yield {
        type: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString()
      };
    }
  }

  /**
   * Synchronous chat interface
   */
  async chat(request: ChatRequest): Promise<ChatMessage> {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: request.content,
          content_blocks: request.content_blocks || [],
          pdf_chunks: request.pdf_chunks || [],
          history: request.history,
          model: request.model || 'gpt-4o',
          knowledge_base: request.knowledge_base || 'default'
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return {
        role: result.role,
        content: result.content,
        timestamp: result.timestamp,
        references: result.references
      };
    } catch (error) {
      console.error('Synchronous chat request failed:', error);
      throw error;
    }
  }

  /**
   * Get available models list
   */
  async getModels(): Promise<Array<{id: string, name: string, description: string}>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/models`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.models;
    } catch (error) {
      console.error('Failed to fetch models list:', error);
      throw error;
    }
  }

  /**
   * Get knowledge bases list
   */
  async getKnowledgeBases(): Promise<Array<{id: string, name: string, description: string}>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/knowledge-bases`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.knowledge_bases;
    } catch (error) {
      console.error('Failed to fetch knowledge bases list:', error);
      throw error;
    }
  }

  /**
   * Health check
   */
  async health(): Promise<{status: string, version: string}> {
    try {
      const response = await fetch(`${this.baseUrl}/`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }
}

// Create default instance
export const chatAPI = new ChatAPI(); 