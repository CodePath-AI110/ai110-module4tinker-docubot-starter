"""
Core DocuBot class responsible for:
- Loading documents from the docs/ folder
- Building a simple retrieval index (Phase 1)
- Retrieving relevant snippets (Phase 1)
- Supporting retrieval only answers
- Supporting RAG answers when paired with Gemini (Phase 2)
"""

import os
import glob
import re


MIN_RELEVANCE_SCORE = 1
STOP_WORDS = {
    "a", "an", "and", "are", "about", "be", "does", "for", "how", "i",
    "in", "is", "it", "me", "of", "on", "or", "the", "this", "to", "what",
    "when", "where", "which", "who", "why", "with", "you", "docs", "document",
    "documentation", "mention", "tell", "any", "there", "these",
}


class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None):
        """
        docs_folder: directory containing project documentation files
        llm_client: optional Gemini client for LLM based answers
        """
        self.docs_folder = docs_folder
        self.llm_client = llm_client

        # Load documents into memory
        self.documents = self.load_documents()  # List of (filename, text)

        # Build a retrieval index (implemented in Phase 1)
        self.index = self.build_index(self.documents)

    # -----------------------------------------------------------
    # Document Loading
    # -----------------------------------------------------------

    def load_documents(self):
        """
        Loads all .md and .txt files inside docs_folder.
        Returns a list of tuples: (filename, text)
        """
        docs = []
        pattern = os.path.join(self.docs_folder, "*.*")
        for path in glob.glob(pattern):
            if path.endswith(".md") or path.endswith(".txt"):
                with open(path, "r", encoding="utf8") as f:
                    text = f.read()
                filename = os.path.basename(path)
                docs.append((filename, text))
        return docs

    # -----------------------------------------------------------
    # Index Construction (Phase 1)
    # -----------------------------------------------------------

    def build_index(self, documents):
        """
        TODO (Phase 1):
        Build a tiny inverted index mapping lowercase words to the documents
        they appear in.

        Example structure:
        {
            "token": ["AUTH.md", "API_REFERENCE.md"],
            "database": ["DATABASE.md"]
        }

        Keep this simple: split on whitespace, lowercase tokens,
        ignore punctuation if needed.
        """
        index = {}
        for filename, text in documents:
            words = set(re.findall(r"\b\w+\b", text.lower()))
            for word in words:
                index.setdefault(word, []).append(filename)
        return index

    # -----------------------------------------------------------
    # Scoring and Retrieval (Phase 1)
    # -----------------------------------------------------------

    def score_document(self, query, text):
        """
        TODO (Phase 1):
        Return a simple relevance score for how well the text matches the query.

        Suggested baseline:
        - Convert query into lowercase words
        - Count how many appear in the text
        - Return the count as the score
        """
        query_words = self._meaningful_query_words(query)
        document_words = re.findall(r"\b\w+\b", text.lower())
        return sum(document_words.count(word) for word in query_words)

    def _meaningful_query_words(self, query):
        """Return query terms that describe a topic rather than ask a question."""
        return {
            word
            for word in re.findall(r"\b\w+\b", query.lower())
            if word not in STOP_WORDS
        }

    def _split_into_sections(self, text):
        """Split a document into non-empty, newline-separated paragraphs."""
        return [
            section.strip()
            for section in re.split(r"\n\s*\n", text.strip())
            if section.strip()
        ]

    def retrieve(self, query, top_k=3):
        """
        TODO (Phase 1):
        Use the index and scoring function to select top_k relevant document
        sections.

        Return a list of (filename, text) sorted by score descending.
        """
        if top_k <= 0:
            return []

        query_words = self._meaningful_query_words(query)
        if not query_words:
            return []

        candidate_files = {
            filename
            for word in query_words
            for filename in self.index.get(word, [])
        }

        scored_results = []
        for document_number, (filename, text) in enumerate(self.documents):
            if filename in candidate_files:
                document_sections = []
                for section_number, section in enumerate(
                    self._split_into_sections(text)
                ):
                    score = self.score_document(query, section)
                    if score > 0:
                        document_sections.append(
                            (score, section_number, filename, section)
                        )
                if document_sections:
                    scored_results.append(
                        min(
                            document_sections,
                            key=lambda result: (-result[0], result[1]),
                        )
                    )

        scored_results.sort(key=lambda result: (-result[0], result[1]))
        if not scored_results or scored_results[0][0] < MIN_RELEVANCE_SCORE:
            return []

        return [
            (filename, section) for _, _, filename, section in scored_results[:top_k]
        ]

    # -----------------------------------------------------------
    # Answering Modes
    # -----------------------------------------------------------

    def answer_retrieval_only(self, query, top_k=3):
        """
        Phase 1 retrieval only mode.
        Returns raw snippets and filenames with no LLM involved.
        """
        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        formatted = []
        for filename, text in snippets:
            formatted.append(f"[{filename}]\n{text}\n")

        return "\n---\n".join(formatted)

    def answer_rag(self, query, top_k=3):
        """
        Phase 2 RAG mode.
        Uses student retrieval to select snippets, then asks Gemini
        to generate an answer using only those snippets.
        """
        if self.llm_client is None:
            raise RuntimeError(
                "RAG mode requires an LLM client. Provide a GeminiClient instance."
            )

        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        return self.llm_client.answer_from_snippets(query, snippets)

    # -----------------------------------------------------------
    # Bonus Helper: concatenated docs for naive generation mode
    # -----------------------------------------------------------

    def full_corpus_text(self):
        """
        Returns all documents concatenated into a single string.
        This is used in Phase 0 for naive 'generation only' baselines.
        """
        return "\n\n".join(text for _, text in self.documents)
