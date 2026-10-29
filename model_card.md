# DocuBot Model Card

This model card is a short reflection on your DocuBot system. Fill it out after you have implemented retrieval and experimented with all three modes:

1. Naive LLM over full docs  
2. Retrieval only  
3. RAG (retrieval plus LLM)

Use clear, honest descriptions. It is fine if your system is imperfect.

---

## 1. System Overview

**What is DocuBot trying to do?**  
Describe the overall goal in 2 to 3 sentences.

DocuBot answers questions about the Markdown and text documentation in the
`docs/` folder. It compares a simple retrieval baseline with an LLM-only
answer and a retrieval-augmented answer.

**What inputs does DocuBot take?**  
For example: user question, docs in folder, environment variables.

It takes a user question, the local documentation files, and (for modes 1
 and 3) a `GEMINI_API_KEY` environment variable.

**What outputs does DocuBot produce?**

It produces either a Gemini-generated answer, retrieved document sections, or
a Gemini answer grounded in retrieved sections. It can also refuse with
 `I do not know based on these docs.` when retrieval has no meaningful match.

---

## 2. Retrieval Design

**How does your retrieval system work?**  
Describe your choices for indexing and scoring.

- How do you turn documents into an index?
- How do you score relevance for a query?
- How do you choose top snippets?

Each document is indexed by the lowercase words it contains. Query and
section words are normalized with a regular expression; the score is the
number of query-term occurrences in a section. Documents are split into
blank-line-separated sections, the best section from each document is kept,
and the highest-scoring sections are returned. Generic question words are
ignored so they do not count as evidence.

**What tradeoffs did you make?**  
For example: speed vs precision, simplicity vs accuracy.

The design is intentionally simple and fast, but it does not understand
synonyms, word stems, or semantic similarity. Paragraph sections preserve
more context than individual lines, while limiting results to one section
per file keeps the context diverse. The tradeoff is that a relevant
paragraph can be missed when a different paragraph in the same file scores
higher.

---

## 3. Use of the LLM (Gemini)

**When does DocuBot call the LLM and when does it not?**  
Briefly describe how each mode behaves.

- Naive LLM mode:
- Retrieval only mode:
- RAG mode:

- Naive LLM mode: sends a question to Gemini without using the local
  document text in its prompt. It can sound fluent, but it is not grounded
  in this repository.
- Retrieval only mode: does not call an LLM; it prints the matching
  filename and section verbatim.
- RAG mode: retrieves sections first, then asks Gemini to answer using only
  those sections.

**What instructions do you give the LLM to keep it grounded?**  
Summarize the rules from your prompt. For example: only use snippets, say "I do not know" when needed, cite files.

The RAG prompt tells Gemini to use only the supplied snippets, not invent
functions, endpoints, or configuration values, and refuse with
`I do not know based on the docs I have.` when the snippets are insufficient.
It also asks the model to mention the files it relied on.

---

## 4. Experiments and Comparisons

Run the **same set of queries** in all three modes. Fill in the table with short notes.

You can reuse or adapt the queries from `dataset.py`.

| Query | Naive LLM: helpful or harmful? | Retrieval only: helpful or harmful? | RAG: helpful or harmful? | Notes |
|------|---------------------------------|--------------------------------------|---------------------------|-------|
| Where is the auth token generated? | Potentially fluent, but weakly grounded because the current naive implementation does not send the docs. | Accurate only when the relevant section is retrieved; otherwise it exposes raw snippets and can omit the generation paragraph. | Clear and grounded when `AUTH.md`'s generation paragraph is retrieved; fails or refuses when retrieval selects only token-validation text. | Same wording in all three modes. The source answer is `generate_access_token` in `auth_utils.py`. |
| How do I connect to the database? | Can provide a plausible generic answer, but may not follow this project's `DATABASE_URL` and SQLite/PostgreSQL details. | Evidence-based but hard to read because it prints Markdown sections. | Usually the best combination: Gemini can summarize the retrieved database configuration while staying within the snippets. | RAG still depends on retrieving the connection section. |
| Which endpoint lists all users? | May answer correctly, but there is no guarantee it used this repository's API reference. | Accurate and auditable when `API_REFERENCE.md` is returned, but not conversational. | Clear, concise, and grounded when the endpoint section is included. | The relevant evidence is `GET /api/users`. |
| Is there any mention of payment processing in these docs? | Can confidently hallucinate a payment feature unless it follows the refusal instruction. | Should return no useful match and refuse. | Should refuse because the retrieved snippets contain no payment evidence. | This is an example where refusal is more useful than a plausible answer. |

**What patterns did you notice?**  

- When does naive LLM look impressive but untrustworthy?  
- When is retrieval only clearly better?  
- When is RAG clearly better than both?

Naive generation is the most impressive-looking but least trustworthy because
the current mode does not actually include the corpus in its prompt.
Retrieval only is the easiest output to audit and is often accurate, but raw
Markdown is difficult to read. RAG is best when retrieval finds the exact
supporting section: it combines a short explanation with file-based evidence.
RAG is not automatically reliable; it cannot recover facts that retrieval
omitted.

---

## 5. Failure Cases and Guardrails

**Describe at least two concrete failure cases you observed.**  
For each one, say:

- What was the question?  
- What did the system do?  
- What should have happened instead?

**Failure case 1 — auth token generation:** For the exact question “Where is
the auth token generated?”, retrieval can select an AUTH.md token-validation
checklist instead of the paragraph stating `generate_access_token` in
`auth_utils.py`. RAG then lacks the key evidence and may refuse or answer
incompletely. It should retrieve the generation paragraph.

**Failure case 2 — unsupported topic:** For “Is there any mention of payment
processing in these docs?”, a keyword-only system can return sections merely
because they contain generic words such as “these” or “document.” The
implemented meaningful-term filter now returns no snippets, so the system
should refuse rather than summarize unrelated files.

**When should DocuBot say “I do not know based on the docs I have”?**  
Give at least two specific situations.

DocuBot should refuse when the query has no meaningful topic terms that occur
in the indexed documents, or when retrieval returns no positively scored
section. It should also refuse in RAG when the selected snippets do not
contain enough evidence to answer the specific question.

**What guardrails did you implement?**  
Examples: refusal rules, thresholds, limits on snippets, safe defaults.

The guardrails include an explicit meaningful-query-term filter, a minimum
relevance score of 1, a limit on the number of returned sections, and a RAG
prompt that forbids invention and requires an explicit refusal. Retrieval
only and RAG both use the same empty-result refusal path.

---

## 6. Limitations and Future Improvements

**Current limitations**  
List at least three limitations of your DocuBot system.

1. Keyword overlap misses synonyms and related wording.
2. The best-section-per-document rule can omit the paragraph containing the
   exact answer.
3. Naive mode is not grounded because its current implementation ignores the
   full-document argument.
4. RAG quality depends on Gemini availability, API configuration, and the
   quality of the retrieved context.

**Future improvements**  
List two or three changes that would most improve reliability or usefulness.

1. Improve retrieval with phrase matching, stemming, and term weighting so
   answer-bearing sections rank above generic mentions.
2. Return a short neighboring context window when a section matches, while
   preserving a bounded prompt size.
3. Make the naive mode either include the corpus or label itself explicitly as
   an ungrounded baseline.

---

## 7. Responsible Use

**Where could this system cause real world harm if used carelessly?**  
Think about wrong answers, missing information, or over trusting the LLM.

Incorrect documentation answers could cause developers to use the wrong
authentication, endpoint, or database configuration. An especially risky
failure is a confident answer that sounds authoritative but is not supported
by the repository. Missing or stale documentation can also cause RAG to
refuse a correct answer or recommend an incomplete implementation.

**What instructions would you give real developers who want to use DocuBot safely?**  
Write 2 to 4 short bullet points.

- Treat retrieved files and sections as evidence to verify, not as a substitute
  for testing or code review.
- Prefer refusal over a confident answer when the relevant documentation is
  missing or ambiguous.
- Keep secrets such as `GEMINI_API_KEY` out of source control and configure
  them through the environment.
- Update retrieval tests when documentation structure or terminology changes.

---
