"""
基于语义相似度的递归分块模块
在递归分块基础上，根据 embedding 相似度动态合并/切分，使块内语义更连贯
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
from .splitter import FinancialTextSplitter, TextChunk

logger = logging.getLogger(__name__)

# 默认 768 维，与 text2vec-base-chinese 一致
DEFAULT_EMBEDDING_DIM = 768


class SemanticRecursiveSplitter:
    """
    语义递归分块器：先按结构递归分块，再根据相邻块语义相似度合并小块或保持切分。
    - 相邻块相似度高 -> 合并为一块（保持语义连贯）
    - 相邻块相似度低 -> 保持边界（主题切换）
    """

    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 90,
        min_chunk_size: int = 150,
        similarity_merge_threshold: float = 0.75,
        similarity_split_low: float = 0.45,
        use_embedding: bool = True,
        embedding_model: str = "shibing624/text2vec-base-chinese",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.similarity_merge_threshold = similarity_merge_threshold
        self.similarity_split_low = similarity_split_low
        self.use_embedding = use_embedding
        self._vectorizer = None
        self._model_name = embedding_model

    def _get_vectorizer(self):
        if self._vectorizer is None and self.use_embedding:
            try:
                from app.Embedding.sbert_vectorization import SBertVectorizer
                self._vectorizer = SBertVectorizer(model_name=self._model_name)
            except Exception as e:
                logger.warning(f"SBert 加载失败，将退化为结构分块: {e}")
                self.use_embedding = False
        return self._vectorizer

    def split_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
        """
        先递归结构分块，再按语义相似度动态合并/保持边界。
        """
        base_splitter = FinancialTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            min_chunk_size=self.min_chunk_size,
        )
        chunks = base_splitter.split_text(text, metadata)
        if not chunks or not self.use_embedding:
            return chunks

        vec = self._get_vectorizer()
        if vec is None:
            return chunks

        # 获取每块文本的向量
        texts = [c.text for c in chunks]
        try:
            vectors = vec.vectorize_texts(texts, normalize=True)
        except Exception as e:
            logger.warning(f"语义向量化失败，返回结构分块: {e}")
            return chunks

        # 按相似度合并相邻块
        merged: List[Tuple[str, int, int, Dict[str, Any]]] = []
        i = 0
        while i < len(chunks):
            current_text = chunks[i].text
            current_start = chunks[i].start_pos
            current_end = chunks[i].end_pos
            current_meta = dict(chunks[i].metadata) if chunks[i].metadata else {}

            j = i + 1
            while j < len(chunks):
                next_text = chunks[j].text
                # 用当前块末尾与下一块的相似度决定是否合并
                left_idx = j - 1
                sim = float(vec.similarity(vectors[left_idx], vectors[j]))
                if sim >= self.similarity_merge_threshold and (
                    len(current_text) + len(next_text) <= self.chunk_size * 1.5
                ):
                    current_text = current_text + "\n\n" + next_text
                    current_end = chunks[j].end_pos
                    current_meta.update(chunks[j].metadata or {})
                    j += 1
                    i = j - 1
                else:
                    break
            merged.append((current_text, current_start, current_end, current_meta))
            i = j if j > i + 1 else i + 1

        # 若合并后某块过长，在语义低相似处再切
        result: List[TextChunk] = []
        for idx, (seg_text, seg_start, seg_end, seg_meta) in enumerate(merged):
            if len(seg_text) <= self.chunk_size * 1.2:
                result.append(
                    TextChunk(
                        text=seg_text,
                        chunk_id=seg_meta.get("chunk_id", f"semantic_{idx}_{seg_start}_{seg_end}"),
                        start_pos=seg_start,
                        end_pos=seg_end,
                        metadata={**seg_meta, "split_mode": "semantic"}
                    )
                )
                continue
            sub_chunks = self._split_long_by_similarity(seg_text, seg_start, vec)
            for sc in sub_chunks:
                result.append(sc)
        return result

    def _split_long_by_similarity(
        self, text: str, global_start: int, vectorizer
    ) -> List[TextChunk]:
        """对过长段落按句子切分后，用相邻句向量相似度找切分点。"""
        sentences = self._sentence_split(text)
        if len(sentences) <= 1:
            return [
                TextChunk(
                    text=text,
                    chunk_id=f"semantic_0_{global_start}",
                    start_pos=global_start,
                    end_pos=global_start + len(text),
                    metadata={"split_mode": "semantic"}
                )
            ]
        try:
            vecs = vectorizer.vectorize_texts(sentences, normalize=True)
        except Exception:
            return [
                TextChunk(
                    text=text,
                    chunk_id=f"semantic_0_{global_start}",
                    start_pos=global_start,
                    end_pos=global_start + len(text),
                    metadata={"split_mode": "semantic"}
                )
            ]
        boundaries = [0]
        for k in range(1, len(sentences)):
            sim = float(vectorizer.similarity(vecs[k - 1], vecs[k]))
            if sim < self.similarity_split_low:
                boundaries.append(k)
        boundaries.append(len(sentences))
        out = []
        pos = 0
        for bi in range(len(boundaries) - 1):
            seg_sentences = sentences[boundaries[bi]:boundaries[bi + 1]]
            seg_text = "".join(seg_sentences)
            if not seg_text.strip():
                continue
            start_pos = global_start + pos
            end_pos = start_pos + len(seg_text)
            pos += len(seg_text)
            out.append(
                TextChunk(
                    text=seg_text,
                    chunk_id=f"semantic_{len(out)}_{start_pos}",
                    start_pos=start_pos,
                    end_pos=end_pos,
                    metadata={"split_mode": "semantic"}
                )
            )
        return out

    @staticmethod
    def _sentence_split(text: str) -> List[str]:
        import re
        parts = re.split(r'(?<=[。！？.!?])\s*', text)
        return [p.strip() for p in parts if p.strip()]
