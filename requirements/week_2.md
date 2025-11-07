# Week 2 Requirements - PDFs, VLM, Ranking

## Objective
Add PDF processing, visual language model capabilities, and advanced ranking to the system.

## Core Components

### 1. PDF Processing Pipeline
- Implement Nougat/Marker PDF parser as primary method
- Add DeepSeek-OCR as fallback option
- Integrate Qwen-VL worker on separate vLLM server for visual content
- Process order: Download → Nougat/Marker → optional DeepSeek-OCR → Qwen-VL if figures present

### 2. Visual Language Model (VLM) Processing
- Set up dedicated vLLM server for VLM/OCR workloads
- Implement targeted OCR for specific page ranges and regions
- Process figures and tables with VLM for auto-captions
- Only run VLM on figures/regions, not entire documents

### 3. Advanced Ranking System
- Implement fusion ranking: z(BM25) + z(cosine)
- Set configurable thresholds τ1/τ2 for rank-based filtering
- Implement early dropping of low-ranked items
- Support field boosts (title > abstract/readme)

### 4. Enhanced API Surface
- Implement `/pdf/parse` endpoint: parse & store markdown
- Implement `/ocr/run` endpoint: targeted OCR (page ranges/regions)
- Implement `/graph/link` endpoint: build edges for IDs
- Implement `/search` endpoint: lexical+vector fusion query

### 5. Quality and Evaluation Systems
- Implement small golden set for TL;DR prompts
- Create regression tests for summaries (length, coverage, hallucination flags)
- Build retrieval sanity tests where top-K must contain known neighbors

## Acceptance Criteria
- [ ] Figures and tables get auto-captions through VLM processing
- [ ] Ranked list for last 48 hours looks sensible and relevant
- [ ] Queue system never blocks hot jobs due to VLM/OCR workloads
- [ ] PDF parsing handles various formats successfully
- [ ] Auto-captions are accurate and useful
- [ ] Fusion ranking provides better results than individual methods

## Key Design Decisions
- GPU planning: One model per vLLM process; separate text vs VLM servers
- Background OCR only when hot queue low and GPU < ~60% util
- PDF pipeline order: Nougat/Marker → OCR fallback → VLM on figures only
- Page/region targeting to avoid whole-document VLM runs

## Metrics to Monitor
- OCR/VLM GPU utilization
- Drop rate from rank thresholds
- Processing time for different PDF types
- Accuracy of auto-captions on figures/tables