# Demo video script

**Target 2:45.** Covers the four graded requirements: explain the problem, show the product, demonstrate local Ollama, cover one technical trade-off. Camera on throughout, picture-in-picture over the screen recording.

---

## Pre-flight

1. **Docker running**, stack up:
   ```bash
   docker compose -f C:\Users\bhusa\Downloads\lenny-growth-assistant\docker-compose.yml up -d
   ```
2. **Warm the model.** Ask one throwaway question, then delete that chat. Cold start is ~40s, warm is ~15s.
3. **Clear the sidebar** so old chats are not in frame.
4. **Two tabs**: the app on `localhost:8000`, and a terminal.
5. **Browser at ~1280px** so all three panes fit.
6. Confirm health is clean:
   ```bash
   curl -s http://localhost:8000/api/health
   ```
   You want `"status": "ok"` and an empty `checks` array.

**Do not run a live Gemini generation on camera.** The free-tier quota was spent measuring essay output and resets on its own schedule. Showing it as `ready` in the status panel proves the toggle without risking a 429 mid-take.

**Every answer takes ~15 seconds.** Each beat below is written so you ask, then keep talking.

---

## [1 of 4: THE PROBLEM] — 0:00, on camera

Lenny's Podcast is the highest-signal corpus in product and growth. It's also about three quarters of a million words, which makes it completely unusable at the moment you actually need it. Tuesday afternoon, mid-decision.

The workaround most teams use is asking a general chatbot. That's the dangerous one, because it answers every product question confidently, and its wrong answers look exactly like its right ones.

So I built an assistant where you can check the answer.

---

## [2 of 4: THE PRODUCT] — 0:25

**Type:** `How do you know when you have product/market fit?` — hit Enter immediately, then talk.

Behind this, every turn does the same thing. It searches 1,420 passages from 60 sources using hybrid retrieval, keyword search plus vector search, and only then calls the model, with the evidence already in hand.

**When it lands: click "Show sources", then click a source title.**

Every claim carries a marker, and every marker resolves to a real passage. And these aren't decorative. Clicking one opens the episode at the timestamp the quote came from.

**Let the tab load, come back.**

That's the difference between a citation and a link.

### 1:10 — the refusal

**Type:** `How do I replace the timing belt on a Honda Civic?`

Now watch what happens when the corpus doesn't cover something.

**It returns almost instantly. Pause and let it sit.**

Under a second, because it never called the model at all. Retrieval scores how much of your question actually exists in the corpus, and below a measured threshold it stops and says so.

A system that always answers can't be trusted on the answers it should give. That's the feature, not the limitation.

### 1:32 — artifacts

**Click the Artifact pill. Type:** `Make an HTML one-pager on running effective user interviews` — keep talking.

It also generates documents. This is model-written HTML, which means it's untrusted input. The model wrote it after reading my message and passages retrieved for me.

**Panel opens. Click the "Blocked" tab.**

So it renders in a sandboxed iframe with zero permissions, behind a server-side sanitiser and a locked-down content security policy. Three independent layers, and this tab shows you exactly what was stripped.

---

## [3 of 4: LOCAL OLLAMA] — 1:55

**Point at the line under an answer: `ollama · llama3.2 · 14.3s`.**

Everything you've seen ran entirely on my laptop. Llama 3.2 through Ollama generating, nomic-embed-text doing the vector search, Postgres with pgvector storing it. No API key touched any of that.

**Terminal:**
```bash
ollama ps
```

There's the model, resident in memory.

**Back to the app. Open the status panel in the sidebar.**

And the provider is a config switch, not a code change. Gemini is configured here and showing as ready. One environment variable moves the whole system to it, with a fallback chain if a provider goes down. Adding Gemini took one factory function, because the abstraction was already the right shape.

---

## [4 of 4: THE TRADE-OFF] — 2:15, back to camera

One trade-off worth naming. The obvious design is to give the model a search tool and let it decide when to use it. I tried that, and this model won't do it reliably. It skips the search and answers from memory, which is exactly the failure the product exists to prevent.

So retrieval isn't the model's decision. Every grounded turn searches first, always.

What I gave up is multi-hop reasoning. A question needing two chained lookups only gets one round of evidence. What I got back is grounding that behaves identically on a two-gigabyte local model and a frontier one.

For an assistant whose entire value is trustworthy citations, predictable beats clever. That's the call I'd defend.

**Stop recording. No sign-off.**

---

## Variants

**Cut to 2:00:** drop the artifact beat (1:32–1:55). Never cut the refusal or the trade-off.

**Extend to 3:00:** after the first answer, add *"And it holds context"* → ask `What about for B2B?` → show it stays on topic. Fifteen seconds, demonstrates the session requirement explicitly.

**If asked about essay quality:** the honest line is *"the skill encodes the Ship 30 principles as data and validates every draft against them. On a 2 GB local model it meets some constraints per run and the validator reports the rest; on Gemini it meets the full spec about half the time. I measured it rather than guessed, and it's documented."*

---

## Delivery notes

- **Say numbers.** 1,420 passages, 60 sources, under a second, 14 seconds. Specifics read as someone who measured.
- **Don't apologise for llama3.2's thin prose.** If you feel the urge, say *"the architecture is model-independent, this is a 2 GB model on a laptop"*.
- **Let the refusal land.** Pause a beat. Most submissions can't show one.
- **One take is fine.** The assignment judges judgment, not editing.
- **Upload to YouTube as Unlisted**, then paste the link into the submission form.
