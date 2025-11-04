/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, useRef } from "react";
import { NavigationBar } from "./components/NavigationBar";
import { Sidebar } from "./components/Sidebar";
import { chatAPI } from "./api/chat";
import { TopBar } from "./components/TopBar";
import { MessageBubble, Message, Reference } from "./components/MessageBubble";
import { ReferenceDrawer } from "./components/ReferenceDrawer";
import { InputBar } from "./components/InputBar";
import { TopProgressBar } from "./components/TopProgressBar";
import { MiniWaveform } from "./components/MiniWaveform";
import { LogDrawer } from "./components/LogDrawer";
import { Toast, ToastMessage } from "./components/Toast";
import { ParticleBackground } from "./components/ParticleBackground";

import { Alert, AlertDescription } from "./components/ui/alert";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./components/ui/dialog";

interface ParseStep {
  key: string;
  label: string;
  completed: boolean;
}

interface LogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
  details?: string;
}

interface ConversationItem {
  id: string;
  title: string;
  timestamp: Date;
  messageCount: number;
}

export default function App() {
  // State management
  const [knowledgeBase, setKnowledgeBase] = useState("default");
  const [model, setModel] = useState("gpt-4o");
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [referenceDrawerOpen, setReferenceDrawerOpen] = useState(false);
  const [selectedReferences, setSelectedReferences] = useState<Reference[]>([]);
  const [selectedReference, setSelectedReference] = useState<Reference | undefined>();
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  // Sidebar state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [conversations, setConversations] = useState<ConversationItem[]>([
    {
      id: '1',
      title: 'Multimodal RAG System Architecture Design',
      timestamp: new Date(Date.now() - 86400000),
      messageCount: 12
    },
    {
      id: '2',
      title: 'Vector Database Optimization Strategy',
      timestamp: new Date(Date.now() - 172800000),
      messageCount: 8
    },
    {
      id: '3',
      title: 'OCR Technology in Document Parsing',
      timestamp: new Date(Date.now() - 259200000),
      messageCount: 15
    }
  ]);
  const [activeConversationId, setActiveConversationId] = useState<string>('1');

  // PDF parsing progress related
  const [parseProgress, setParseProgress] = useState({
    isVisible: false,
    fileName: "",
    progress: 0,
    currentStep: "upload",
    logs: [] as LogEntry[]
  });
  const [logDrawerOpen, setLogDrawerOpen] = useState(false);

  // Audio processing related
  const [audioFile, setAudioFile] = useState<{ name: string; duration: number } | null>(null);
  const [transcription, setTranscription] = useState("");
  const [isTranscribing, setIsTranscribing] = useState(false);

  // Pending images
  const [pendingImages, setPendingImages] = useState<Array<{
    id: string;
    file: File;
    dataUrl: string;
    thumbnail: string;
  }>>([]);

  // Pending PDFs
  const [pendingPDFs, setPendingPDFs] = useState<Array<{
    id: string;
    file: File;
    filename: string;
    size: number;
    processed?: boolean;
    chunks?: Array<{
      id: string;
      content: string;
      metadata: any;
    }>;
  }>>([]);

  // Pending audios
  const [pendingAudios, setPendingAudios] = useState<Array<{
    id: string;
    file: File;
    filename: string;
    duration: number;
    transcription?: string;
    processed?: boolean;
  }>>([]);

  // PDF processing progress
  const [pdfProcessing, setPdfProcessing] = useState<{
    isProcessing: boolean;
    progress: number;
    step: string;
    message: string;
  }>({
    isProcessing: false,
    progress: 0,
    step: '',
    message: ''
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Parse step definitions
  const parseSteps: ParseStep[] = [
    { key: "upload", label: "Upload", completed: false },
    { key: "ocr", label: "OCR", completed: false },
    { key: "segment", label: "Segment", completed: false },
    { key: "vectorize", label: "Vectorize", completed: false },
    { key: "store", label: "Store", completed: false }
  ];

  // Mock reference data (updated to new Reference interface)
  // Commented out unused mock data
  // const mockReferences: Reference[] = [
  //   {
  //     id: 1,
  //     text: "Important information from technical specification document...",
  //     source: "Technical Specifications.pdf",
  //     page: 15,
  //     chunk_id: 0,
  //     source_info: "Technical Specifications.pdf - Page 15"
  //   },
  //   {
  //     id: 2,
  //     text: "Operating instructions from user manual...",
  //     source: "User Manual.pdf",
  //     page: 8,
  //     chunk_id: 1,
  //     source_info: "User Manual.pdf - Page 8"
  //   }
  // ];

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollAreaRef.current) {
      // Delayed scroll to ensure content is rendered
      const scrollToBottom = () => {
        if (scrollAreaRef.current) {
          const element = scrollAreaRef.current;
          element.scrollTop = element.scrollHeight - element.clientHeight;
        }
      };

      // Immediate scroll
      scrollToBottom();
      // Delayed scroll to ensure content is fully rendered
      setTimeout(scrollToBottom, 100);
    }
  }, [messages]);

  // Auto-scroll during streaming response
  useEffect(() => {
    if (isStreaming && scrollAreaRef.current) {
      const scrollToBottom = () => {
        if (scrollAreaRef.current) {
          const element = scrollAreaRef.current;
          element.scrollTop = element.scrollHeight - element.clientHeight;
        }
      };

      const interval = setInterval(scrollToBottom, 300);
      return () => clearInterval(interval);
    }
  }, [isStreaming]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setReferenceDrawerOpen(false);
        setLogDrawerOpen(false);
        setSettingsOpen(false);
        setHelpOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Send message
  const handleSend = async () => {
    if ((!inputValue.trim() && pendingImages.length === 0 && pendingAudios.length === 0) || isStreaming) return;

    const currentInput = inputValue;
    
    // Build user message (including text, images, and PDF info)
    const contentBlocks: any[] = [];

    // Add text content
    if (currentInput.trim()) {
      contentBlocks.push({ type: 'text', content: currentInput });
    }

    // Add pending images
    if (pendingImages.length > 0) {
      console.log('🖼️ Sending message with images:', pendingImages.length);
      pendingImages.forEach(img => {
        contentBlocks.push({
          type: 'image',
          content: img.dataUrl,
          thumbnail: img.thumbnail
        });
      });
    }

    // Add pending audios
    if (pendingAudios.length > 0) {
      console.log('🎙️ Sending message with audios:', pendingAudios.length);
      pendingAudios.forEach((audio, index) => {
        console.log(`🎵 Audio ${index + 1}:`, {
          filename: audio.filename,
          hasTranscription: !!audio.transcription,
          transcriptionPreview: audio.transcription?.substring(0, 100) + '...'
        });
        contentBlocks.push({
          type: 'audio',
          content: '', // Audio file not directly transmitted
          transcription: audio.transcription || ''
        });
      });
    }

    // Process PDF documents (if any)
    let pdfDocuments = null;
    if (pendingPDFs.length > 0) {
      console.log('📄 Sending message with PDFs:', pendingPDFs.length);
      // Create separate content blocks for each PDF document
      pendingPDFs.forEach(pdf => {
        contentBlocks.push({
          type: 'pdf',
          content: pdf.filename,
          filename: pdf.filename,
          filesize: pdf.size
        });
      });
      pdfDocuments = pendingPDFs;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      contentBlocks: contentBlocks,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue("");
            clearPendingImages(); // Clear pending images
        clearPendingAudios(); // Clear pending audios
    setIsStreaming(true);

    try {
      // Prepare chat history (maintain multimodal structure)
      const history = messages.map(msg => ({
        role: msg.role,
        content: msg.contentBlocks.map(block => block.content).join(''), // Compatible with plain text
        content_blocks: msg.contentBlocks.map(block => ({
          type: block.type,
          content: block.content,
          thumbnail: block.thumbnail,
          transcription: block.transcription // Preserve audio transcription info
        }))
      }));

      console.log('📜 Passing conversation history to API:', history.length, 'messages');
      if (history.length > 0) {
        console.log('📝 Recent history preview:', history.slice(-2).map(h => ({
          role: h.role,
          content_blocks_count: h.content_blocks.length,
          has_transcription: h.content_blocks.some(b => b.transcription)
        })));
      }

      // Create assistant message for streaming updates
      const assistantMessageId = (Date.now() + 1).toString();
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        contentBlocks: [{ type: 'text', content: '' }],
        references: [],
        timestamp: new Date(),
        isStreaming: true
      };

      setMessages(prev => [...prev, assistantMessage]);

              // If there are PDFs, use preprocessed chunks (PDFs are now processed on upload)
        let pdfContent = '';
        let allProcessedPdfChunks: any[] = []; // Directly collect PDF chunks, not dependent on state

        if (pdfDocuments && pdfDocuments.length > 0) {
          console.log('📚 Collecting processed PDF documents...');

          // Collect all processed PDF document content and chunks
          for (const pdf of pdfDocuments) {
            console.log(`📄 Using PDF: ${pdf.filename}, processed: ${pdf.processed}`);

            // Check if PDF is already processed
            if (pdf.processed && pdf.chunks && pdf.chunks.length > 0) {
              // Use preprocessed chunks
              const pdfTexts = pdf.chunks.map((chunk: any) => chunk.content).join('\n\n');
              pdfContent += `\n\n=== PDF Document: ${pdf.filename} ===\n${pdfTexts}`;

              // Collect PDF chunks for references
              allProcessedPdfChunks = allProcessedPdfChunks.concat(pdf.chunks);
              console.log(`✅ PDF ${pdf.filename} used, text length: ${pdfTexts.length}, chunks: ${pdf.chunks.length}`);
            } else {
              // PDF not processed or processing failed, attempt to process
              console.warn(`⚠️ PDF ${pdf.filename} not preprocessed, processing now...`);
              try {
                const chunks = await processPDF(pdf);
                if (chunks && chunks.length > 0) {
                  const pdfTexts = chunks.map((chunk: any) => chunk.content).join('\n\n');
                  pdfContent += `\n\n=== PDF Document: ${pdf.filename} ===\n${pdfTexts}`;
                  allProcessedPdfChunks = allProcessedPdfChunks.concat(chunks);
                  console.log(`✅ PDF ${pdf.filename} processed, chunks: ${chunks.length}`);
                }
              } catch (error) {
                console.error(`PDF ${pdf.filename} processing failed:`, error);

                // Remove failed PDF from pending queue
                setPendingPDFs(prev => prev.filter(p => p.id !== pdf.id));

                // Display error message in chat
                const errorMsg: Message = {
                  id: Date.now().toString(),
                  role: 'assistant',
                  contentBlocks: [{
                    type: 'text',
                    content: `Error processing PDF document "${pdf.filename}": ${error instanceof Error ? error.message : 'Unknown error'}`
                  }],
                  timestamp: new Date()
                };
                setMessages(prev => [...prev, errorMsg]);

                // Continue processing other PDFs
                continue;
              }
            }
          }
          console.log('✅ All PDFs collected, total content length:', pdfContent.length, ', total chunks:', allProcessedPdfChunks.length);

          // Note: Don't clear PDF pending here as we still need to use PDF chunk info later
        }

        // Call backend streaming API
        // Build API request content_blocks
        const apiContentBlocks: Array<{
          type: 'image' | 'audio';
          content: string;
          thumbnail?: string;
          transcription?: string;
        }> = [];

        // Add image content blocks
        if (pendingImages.length > 0) {
          pendingImages.forEach(img => {
            apiContentBlocks.push({
              type: 'image' as const,
              content: img.dataUrl,
              thumbnail: img.thumbnail
            });
          });
        }

        // Add audio content blocks
        if (pendingAudios.length > 0) {
          console.log('🔊 Adding audio to API request, count:', pendingAudios.length);
          pendingAudios.forEach((audio, index) => {
            console.log(`🎵 Adding audio ${index + 1} to API:`, {
              filename: audio.filename,
              hasTranscription: !!audio.transcription,
              transcriptionLength: audio.transcription?.length || 0
            });
            apiContentBlocks.push({
              type: 'audio' as const,
              content: '', // Audio file not directly transmitted
              transcription: audio.transcription || ''
            });
          });
        }

        console.log('📋 Final apiContentBlocks:', apiContentBlocks.map(b => ({
          type: b.type,
          hasContent: !!b.content,
          hasTranscription: !!b.transcription
        })));

        // Note: Don't concatenate PDF content to user input in frontend
        // Backend will automatically process pdf_chunks and add to message, avoiding duplication
        const fullUserInput = currentInput;

        console.log('📤 User input length sent to backend:', fullUserInput.length);
        console.log('📤 User input preview:', fullUserInput.substring(0, 200) + (fullUserInput.length > 200 ? '...' : ''));

        // PDF processing debug info
        if (allProcessedPdfChunks.length > 0) {
          console.log('📚 ===== PDF Processing Debug Info =====');
          console.log('  - PDF document count:', pdfDocuments?.length || 0);
          console.log('  - Extracted text chunks:', allProcessedPdfChunks.length);
          console.log('  - PDF total content length:', pdfContent.length, 'characters');
          console.log('  - Chunk preview:', allProcessedPdfChunks.slice(0, 2).map((c: any) => ({
            id: c.id,
            contentPreview: c.content?.substring(0, 50) + '...',
            source: c.metadata?.source
          })));
          console.log('  ⚠️ Note: PDF content will be automatically added to AI prompt by backend');
        }

        let fullContent = '';
        for await (const chunk of chatAPI.streamChat({
          content: fullUserInput,
          content_blocks: apiContentBlocks,
          pdf_chunks: allProcessedPdfChunks,
          history: history,
          model: model,
          knowledge_base: knowledgeBase
        })) {
        if (chunk.type === 'content_delta' && chunk.content) {
          fullContent += chunk.content;

          // Update message content
          setMessages(prev => prev.map(msg =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  contentBlocks: [{ type: 'text', content: fullContent }]
                }
              : msg
          ));
        } else if (chunk.type === 'message_complete') {
          // Message complete
          console.log('🏁 Message complete, reference count:', chunk.references?.length || 0);
          if (chunk.references && chunk.references.length > 0) {
            console.log('📚 Reference details:', chunk.references);
          }

          setMessages(prev => prev.map(msg =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  isStreaming: false,
                  references: chunk.references || []
                }
              : msg
          ));
          setIsStreaming(false);

          // Clear pending after chat completion
          clearPendingPDFs();
          clearPendingAudios();
          break;
        } else if (chunk.type === 'error') {
          console.error('Chat error:', chunk.error);
          // Display error message
          setMessages(prev => prev.map(msg =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  contentBlocks: [{ type: 'text', content: `Sorry, an error occurred: ${chunk.error}` }],
                  isStreaming: false
                }
              : msg
          ));
          setIsStreaming(false);

          // Clear pending on error as well
          clearPendingPDFs();
          clearPendingAudios();
          break;
        }
      }
    } catch (error) {
      console.error('API call failed:', error);

      // Display error toast
      setToast({
        id: Date.now().toString(),
        type: 'error',
        title: 'Connection Failed',
        description: 'Unable to connect to backend service, please check if service is running'
      });

      setIsStreaming(false);

      // Clear pending on exception as well
      clearPendingPDFs();
      clearPendingAudios();
    }
  };

  // Stop generation
  const handleStop = () => {
    setIsStreaming(false);
    setMessages(prev => prev.map(msg => ({ ...msg, isStreaming: false })));
  };

  // Reference click handler
  const handleReferenceClick = (references: Reference[]) => {
    console.log('🔍 Reference clicked:', references);

    if (references.length > 0) {
      const ref = references[0];

      // Display toast notification
      showToast({
        id: Date.now().toString(),
        type: 'info',
        title: `Reference Source: ${ref.source_info}`,
        description: ref.text.substring(0, 100) + (ref.text.length > 100 ? '...' : '')
      });

      // Preserve original reference panel functionality
      setSelectedReferences(references);
      setSelectedReference(references[0]);
      setReferenceDrawerOpen(true);
    }
  };

//   // PDF 上传处理 (old version - unused, using handleUploadPDFNew instead)
//   // eslint-disable-next-line @typescript-eslint/no-unused-vars
//   const handleUploadPDF = async (file: File) => {
//     setParseProgress({
//       isVisible: true,
//       fileName: file.name,
//       progress: 0,
//       currentStep: "upload",
//       logs: []
//     });
// 
//     // 模拟解析过程
//     const steps = ["upload", "ocr", "segment", "vectorize", "store"];
//     let currentStepIndex = 0;
// 
//     const processStep = async () => {
//       const step = steps[currentStepIndex];
//       const stepProgress = ((currentStepIndex + 1) / steps.length) * 100;
// 
//       // 添加日志
//       const logEntry = {
//         timestamp: new Date().toLocaleTimeString(),
//         level: 'info' as const,
//         message: `开始${parseSteps.find(s => s.key === step)?.label}阶段`,
//         details: step === 'ocr' ? '使用 Tesseract OCR 引擎进行文字识��' : undefined
//       };
// 
//       setParseProgress(prev => ({
//         ...prev,
//         progress: stepProgress,
//         currentStep: step,
//         logs: [...prev.logs, logEntry]
//       }));
// 
//       if (currentStepIndex < steps.length - 1) {
//         currentStepIndex++;
//         setTimeout(processStep, 1500);
//       } else {
//         // 完成
//         setTimeout(() => {
//           setParseProgress(prev => ({ ...prev, isVisible: false }));
//           showToast({
//             id: Date.now().toString(),
//             type: 'success',
//             title: 'PDF 解析完成',
//             description: `${file.name} 已成功加入知识库`
//           });
//         }, 1000);
//       }
//     };
// 
//     processStep();
//   };

  // Image upload handler (staged, not auto-sent)
  const handleUploadImage = async (file: File) => {
    console.log('🖼️ Starting image upload processing:', file.name, file.size);

    if (isStreaming) {
      console.log('❌ Currently streaming response, skipping image upload');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const imageData = e.target?.result as string;
      console.log('📁 Image read complete, data length:', imageData.length);

      // Add image to staging area
      const pendingImage = {
        id: Date.now().toString(),
        file: file,
        dataUrl: imageData,
        thumbnail: imageData
      };

      setPendingImages(prev => [...prev, pendingImage]);
      console.log('📌 Image staged, waiting for user question');

      showToast({
        id: Date.now().toString(),
        type: 'info',
        title: 'Image Uploaded',
        description: 'Please enter your question, then click send'
      });
    };

    reader.readAsDataURL(file);
  };

  // Clear pending images
  const clearPendingImages = () => {
    setPendingImages([]);
  };

  // Clear pending PDFs
  const clearPendingPDFs = () => {
    setPendingPDFs([]);
  };

  // Clear pending audios
  const clearPendingAudios = () => {
    setPendingAudios([]);
  };



  // Simplified PDF upload handler (staging version)
  const handleUploadPDFNew = async (file: File) => {
    if (isStreaming || pdfProcessing.isProcessing) return;

    console.log('📄 PDF upload:', file.name, file.size);

    // Validate file size (50MB limit)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      showToast({
        id: Date.now().toString(),
        type: 'error',
        title: 'PDF File Too Large',
        description: `File size ${(file.size / 1024 / 1024).toFixed(1)}MB exceeds limit (50MB)`
      });
      return;
    }

    // Add PDF to staging area
    const pendingPDF = {
      id: Date.now().toString(),
      file: file,
      filename: file.name,
      size: file.size,
      processed: false
    };

    setPendingPDFs(prev => [...prev, pendingPDF]);

    showToast({
      id: Date.now().toString(),
      type: 'info',
      title: 'PDF Processing',
      description: `Parsing ${file.name}...`
    });

    // Process PDF immediately
    try {
      const chunks = await processPDF(pendingPDF);
      if (chunks && chunks.length > 0) {
        setPendingPDFs(prev => prev.map(p =>
          p.id === pendingPDF.id
            ? { ...p, processed: true, chunks }
            : p
        ));
        showToast({
          id: Date.now().toString(),
          type: 'success',
          title: 'PDF Processing Complete',
          description: `${file.name} parsed, ${chunks.length} document chunks. Please enter your question and send.`
        });
      } else {
        throw new Error('Failed to extract any content');
      }
    } catch (error) {
      console.error('PDF processing failed:', error);
      // Remove failed PDF from queue
      setPendingPDFs(prev => prev.filter(p => p.id !== pendingPDF.id));
      // Toast already displayed in processPDF
    }
  };

  // PDF processing function
  const processPDF = async (pdfFile: {id: string, file: File}) => {
    console.log('🚀 Starting PDF processing:', pdfFile.file.name);

    setPdfProcessing({
      isProcessing: true,
      progress: 0,
      step: 'preparing',
      message: 'Preparing to process PDF...'
    });

    try {
      // Convert PDF to base64
      const reader = new FileReader();
      const fileData = await new Promise<string>((resolve, reject) => {
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(pdfFile.file);
      });

      console.log('📤 Calling PDF processing API');

      // Call PDF processing API
      const response = await fetch('http://localhost:8000/api/pdf/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: fileData,
          filename: pdfFile.file.name
        })
      });

      if (!response.body) {
        throw new Error('Response body is empty');
      }

      const reader2 = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';  // Used to store incomplete data

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader2.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Split by lines for processing
        const lines = buffer.split('\n');
        // Keep the last line (might be incomplete)
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (data === '[DONE]') continue;
            if (!data) continue;  // Skip empty data

            try {
              const parsed = JSON.parse(data);
              console.log('📦 PDF processing progress:', parsed);

              if (parsed.type === 'progress') {
                setPdfProcessing({
                  isProcessing: true,
                  progress: parsed.progress || 0,
                  step: parsed.step || '',
                  message: parsed.message || ''
                });
              } else if (parsed.type === 'result') {
                // Processing complete, save result to state (for UI display)
                setPendingPDFs(prev => prev.map(pdf =>
                  pdf.id === pdfFile.id
                    ? { ...pdf, processed: true, chunks: parsed.chunks }
                    : pdf
                ));
                console.log('✅ PDF processing complete, chunk count:', parsed.chunks?.length);
                return parsed.chunks; // Return document chunks
              } else if (parsed.type === 'error') {
                throw new Error(parsed.error);
              }
            } catch (e) {
              console.warn('Failed to parse PDF processing response:', e, 'data:', data.slice(0, 200));
              // Skip unparseable data, continue processing
              continue;
            }
          }
        }
      }

      // Process final buffer data
      if (buffer.trim() && buffer.startsWith('data: ')) {
        const data = buffer.slice(6).trim();
        if (data !== '[DONE]' && data) {
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === 'result') {
              setPendingPDFs(prev => prev.map(pdf =>
                pdf.id === pdfFile.id
                  ? { ...pdf, processed: true, chunks: parsed.chunks }
                  : pdf
              ));
              console.log('✅ PDF processing complete (buffer), chunk count:', parsed.chunks?.length);
              return parsed.chunks;
            }
          } catch (e) {
            console.warn('Failed to parse buffer PDF response:', e);
          }
        }
      }

    } catch (error) {
      console.error('PDF processing failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      showToast({
        id: Date.now().toString(),
        type: 'error',
        title: 'PDF Processing Failed',
        description: `Error processing ${pdfFile.file.name}: ${errorMessage}`
      });
      throw error;
    } finally {
      setPdfProcessing({
        isProcessing: false,
        progress: 0,
        step: '',
        message: ''
      });
    }
  };

  // Audio upload handler
  const handleUploadAudio = async (file: File) => {
    console.log('🎙️ Audio upload:', file.name, file.size);

    try {
      showToast({
        id: Date.now().toString(),
        type: 'info',
        title: 'Processing Audio...',
        description: 'Please wait, transcribing speech to text'
      });

      // Call backend audio processing API
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/api/audio/process', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Audio processing failed');
      }

      const result = await response.json();
      console.log('✅ Audio processing successful:', result);

      // Create pending audio object
      const pendingAudio = {
        id: Date.now().toString(),
        file: file,
        filename: result.filename,
        duration: result.duration,
        transcription: result.transcription,
        processed: true
      };

      // Add to pending list
      setPendingAudios(prev => [...prev, pendingAudio]);

      showToast({
        id: Date.now().toString(),
        type: 'success',
        title: 'Audio Processing Complete',
        description: `Transcription: ${result.transcription.substring(0, 50)}${result.transcription.length > 50 ? '...' : ''}`
      });

    } catch (error) {
      console.error('❌ Audio processing failed:', error);
      showToast({
        id: Date.now().toString(),
        type: 'error',
        title: 'Audio Processing Failed',
        description: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  };

  // Audio transcription
  const handleTranscribe = () => {
    setIsTranscribing(true);

    setTimeout(() => {
      const mockTranscription = "Hello, I would like to learn about the technical implementation details of multimodal RAG systems, especially best practices for handling images and documents.";
      setTranscription(mockTranscription);
      setInputValue(mockTranscription);
      setIsTranscribing(false);
      setAudioFile(null);

      showToast({
        id: Date.now().toString(),
        type: 'success',
        title: 'Transcription Complete',
        description: 'Speech content has been inserted into input box'
      });
    }, 3000);
  };

  // New conversation
  const handleNewConversation = () => {
    const newId = Date.now().toString();
    const newConversation: ConversationItem = {
      id: newId,
      title: 'New Conversation',
      timestamp: new Date(),
      messageCount: 0
    };
    setConversations(prev => [newConversation, ...prev]);
    setActiveConversationId(newId);
    setMessages([]);
  };

  // Select conversation
  const handleConversationSelect = (id: string) => {
    setActiveConversationId(id);
    // Can load corresponding conversation message history here
    setMessages([]);
  };

  // Show toast
  const showToast = (message: ToastMessage) => {
    setToast(message);
  };

  return (
    <div className="h-screen bg-background flex flex-col relative overflow-hidden">
      {/* Particle background */}
      <ParticleBackground />

              {/* Navigation bar */}
        <NavigationBar />

      {/* Main content area */}
      <div className="flex-1 flex relative min-h-0">
        {/* Sidebar */}
        <Sidebar
          isCollapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          conversations={conversations}
          activeConversationId={activeConversationId}
          onConversationSelect={handleConversationSelect}
          onNewConversation={handleNewConversation}
          onSettings={() => setSettingsOpen(true)}
          onHelp={() => setHelpOpen(true)}
        />

        {/* Main chat area */}
        <div className="flex-1 flex flex-col relative min-h-0">
          {/* Top bar */}
          <TopBar
            knowledgeBase={knowledgeBase}
            model={model}
            onKnowledgeBaseChange={setKnowledgeBase}
            onModelChange={setModel}
            onSettings={() => setSettingsOpen(true)}
            onHelp={() => setHelpOpen(true)}
          />

          {/* Top progress bar */}
          <TopProgressBar
            isVisible={parseProgress.isVisible}
            fileName={parseProgress.fileName}
            progress={parseProgress.progress}
            currentStep={parseProgress.currentStep}
            steps={parseSteps.map(step => ({
              ...step,
              completed: parseSteps.indexOf(step) < parseSteps.findIndex(s => s.key === parseProgress.currentStep)
            }))}
            onClose={() => setParseProgress(prev => ({ ...prev, isVisible: false }))}
            onViewLog={() => setLogDrawerOpen(true)}
          />

          {/* Message area */}
          <div className={`flex-1 relative ${parseProgress.isVisible ? 'mt-24' : ''}`} style={{ minHeight: 0 }}>
            <div
              ref={scrollAreaRef}
              className="absolute inset-0 overflow-y-auto overflow-x-hidden chat-scroll"
            >
              <div className="max-w-4xl mx-auto px-6 py-6 space-y-4 relative z-10 min-h-full">
                {messages.length === 0 && (
                  <div className="text-center py-16">
                    <div className="w-20 h-20 bg-gradient-to-br from-gray-800 to-gray-900 dark:from-gray-100 dark:to-gray-200 rounded-2xl mx-auto mb-8 flex items-center justify-center shadow-2xl">
                      <span className="text-white dark:text-black text-2xl font-bold">RAG</span>
                    </div>
                    <h2 className="text-3xl text-foreground mb-4 font-semibold">
                      Welcome to Multimodal RAG Workbench
                    </h2>
                    <p className="text-muted-foreground text-lg mb-10 max-w-2xl mx-auto">
                      Powered by advanced AI technology, providing professional document analysis, image understanding, and audio processing capabilities
                    </p>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
                      <div className="p-6 bg-card backdrop-blur-sm rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500 hover:shadow-lg transition-all duration-300 group">
                        <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg mx-auto mb-4 flex items-center justify-center shadow-lg group-hover:scale-105 group-hover:shadow-blue-200 transition-all duration-300">
                          <span className="text-white text-lg">📝</span>
                        </div>
                        <p className="text-sm font-medium text-card-foreground group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">Q&A</p>
                      </div>
                      <div className="p-6 bg-card backdrop-blur-sm rounded-lg border border-gray-200 dark:border-gray-600 hover:border-green-300 dark:hover:border-green-500 hover:shadow-lg transition-all duration-300 group">
                        <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-green-600 rounded-lg mx-auto mb-4 flex items-center justify-center shadow-lg group-hover:scale-105 group-hover:shadow-green-200 transition-all duration-300">
                          <span className="text-white text-lg">🖼️</span>
                        </div>
                        <p className="text-sm font-medium text-card-foreground group-hover:text-green-600 dark:group-hover:text-green-400 transition-colors">Image Analysis</p>
                      </div>
                      <div className="p-6 bg-card backdrop-blur-sm rounded-lg border border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-500 hover:shadow-lg transition-all duration-300 group">
                        <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg mx-auto mb-4 flex items-center justify-center shadow-lg group-hover:scale-105 group-hover:shadow-purple-200 transition-all duration-300">
                          <span className="text-white text-lg">🎙️</span>
                        </div>
                        <p className="text-sm font-medium text-card-foreground group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">Audio Transcription</p>
                      </div>
                      <div className="p-6 bg-card backdrop-blur-sm rounded-lg border border-gray-200 dark:border-gray-600 hover:border-orange-300 dark:hover:border-orange-500 hover:shadow-lg transition-all duration-300 group">
                        <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-orange-600 rounded-lg mx-auto mb-4 flex items-center justify-center shadow-lg group-hover:scale-105 group-hover:shadow-orange-200 transition-all duration-300">
                          <span className="text-white text-lg">📄</span>
                        </div>
                        <p className="text-sm font-medium text-card-foreground group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors">PDF Parsing</p>
                      </div>
                    </div>
                  </div>
                )}

                {messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    onReferenceClick={handleReferenceClick}
                  />
                ))}

                {/* Audio waveform card */}
                {audioFile && (
                  <div className="max-w-md">
                    <MiniWaveform
                      fileName={audioFile.name}
                      duration={audioFile.duration}
                      onTranscribe={handleTranscribe}
                      isTranscribing={isTranscribing}
                      transcription={transcription}
                    />
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>
          </div>

          {/* Input bar */}
          <InputBar
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSend}
            onStop={handleStop}
            onUploadPDF={handleUploadPDFNew}
            onUploadImage={handleUploadImage}
            onUploadAudio={handleUploadAudio}
            isStreaming={isStreaming}
            pendingImages={pendingImages}
            onRemoveImage={(id) => setPendingImages(prev => prev.filter(img => img.id !== id))}
                    pendingPDFs={pendingPDFs}
        onRemovePDF={(id) => setPendingPDFs(prev => prev.filter(pdf => pdf.id !== id))}
        pdfProcessing={pdfProcessing}
        pendingAudios={pendingAudios}
        onRemoveAudio={(id) => setPendingAudios(prev => prev.filter(audio => audio.id !== id))}
          />
        </div>
      </div>

      {/* Reference drawer */}
      <ReferenceDrawer
        isOpen={referenceDrawerOpen}
        onClose={() => setReferenceDrawerOpen(false)}
        references={selectedReferences}
        selectedReference={selectedReference}
        onReferenceSelect={setSelectedReference}
      />

      {/* Log drawer */}
      <LogDrawer
        isOpen={logDrawerOpen}
        onClose={() => setLogDrawerOpen(false)}
        logs={parseProgress.logs}
        fileName={parseProgress.fileName}
      />

      {/* Toast */}
      <Toast
        message={toast}
        onClose={() => setToast(null)}
      />

      {/* Settings dialog */}
      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>System Settings</DialogTitle>
            <DialogDescription>
              Configure parameters and preferences for the Multimodal RAG system
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Alert>
              <AlertDescription>
                Settings feature is under development. Stay tuned for more customization options.
              </AlertDescription>
            </Alert>
          </div>
        </DialogContent>
      </Dialog>

      {/* Help dialog */}
      <Dialog open={helpOpen} onOpenChange={setHelpOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Help</DialogTitle>
            <DialogDescription>
              Learn how to use the features of the Multimodal RAG Workbench
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <h4 className="font-medium mb-2">Keyboard Shortcuts</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Enter: Send message</li>
                <li>• Shift + Enter: New line</li>
                <li>• Ctrl/Cmd + U: Upload PDF</li>
                <li>• Ctrl/Cmd + I: Upload image</li>
                <li>• Esc: Close popup</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2">Supported File Formats</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• PDF: Supports OCR text recognition</li>
                <li>• Images: JPG, PNG, WebP and other common formats</li>
                <li>• Audio: MP3, WAV, M4A and other formats</li>
              </ul>
            </div>
          </div>
        </DialogContent>
      </Dialog>


    </div>
  );
}