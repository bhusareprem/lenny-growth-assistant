"""The Ship 30 for 30 essay skill.

The brief asks for the writing principles to be *encoded in the skill* rather
than stuffed into an ad-hoc prompt. So they live here as structured data, read
from the published Ship 30 for 30 material (sources listed in `SOURCES`), and
they are used twice:

1. **Composed into the prompt** - deterministically, in a fixed order, so the
   instruction block is byte-stable across turns and cacheable.
2. **Checked against the output** - `critique()` measures the draft against the
   same rules that produced it. A draft that misses them gets one targeted
   repair pass naming the specific failures, instead of a vague "try again".

That second use is the point. A prompt can only ask; a validator can tell you
whether you got it, which is what makes essay quality a measurable property
rather than a vibe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SOURCES = [
    "https://www.ship30for30.com/post/how-to-write-an-atomic-essay-a-beginners-guide",
    "https://www.ship30for30.com/post/6-proven-single-sentence-openers-to-hook-your-reader-s-attention",
    "https://www.ship30for30.com/post/flawless-formatting-a-step-by-step-guide-to-make-anything-you-write-easy-to-read-and-skimmable",
]

TARGET_WORDS = 1250
# The brief says "approximately 1,250 words". +/-20% is what a human editor
# would accept; outside it, the draft gets a repair pass.
WORD_FLOOR = 1000
WORD_CEILING = 1500


@dataclass(frozen=True, slots=True)
class Opener:
    name: str
    rule: str
    example: str


# The six single-sentence openers, from the Ship 30 for 30 hook guide.
OPENERS: tuple[Opener, ...] = (
    Opener(
        "Strong declarative sentence",
        "Plant your flag in the ground. No hedging.",
        "Being physically fit isn't a hobby, it's a lifestyle.",
    ),
    Opener(
        "Thought-provoking question",
        "Ask something the reader is already asking themselves.",
        "Is there such a thing as complete happiness?",
    ),
    Opener(
        "Controversial opinion",
        "Challenge conventional wisdom, but stay believable and defensible.",
        "ChatGPT is overused and overhyped.",
    ),
    Opener(
        "Moment in time",
        "Ground the reader in a specific date, time, scene or setting.",
        "In 1982, David Ogilvy wrote a memo titled 'How to write.'",
    ),
    Opener(
        "Vulnerable statement",
        "Share a real struggle, then connect it to what the reader gains.",
        "For the first 10 years of my career, I was a terrible husband.",
    ),
    Opener(
        "Weird, unique insight",
        "Lead with a surprising fact that provokes curiosity.",
        "Texas is not the largest state in the US. Alaska is.",
    ),
)

# The five things a Ship 30 headline has to do.
HEADLINE_ELEMENTS: tuple[str, ...] = (
    "who the piece is for",
    "what it is about",
    "how the reader should feel",
    "the outcome or promise",
    "how much information to expect",
)

FORMATTING_RULES: tuple[str, ...] = (
    "Open the piece, and every section, with a single sentence.",
    "If you are listing anything, ever, make it a bulleted list, written as "
    "markdown lines beginning with '- '.",
    "Use bolded subheads to signal where the reader is in the argument; "
    "split the piece into roughly equal chunks so each section is a milestone.",
    "Use the 1/3/1 rhythm (or 1/4/1, 1/5/1): open with one clear sentence, "
    "build over the next few, close the point with one sentence.",
    "In every section, wrap the one sentence a skimmer must read in double "
    "asterisks, like **this**. Bold nothing else - bolding everything "
    "bolds nothing.",
    "Keep paragraphs short and leave white space between them.",
)

NARRATIVE_ARC: tuple[str, ...] = (
    "Hook - one sentence, using one of the six opener types.",
    "Stakes - why this matters now, and to whom.",
    "Body - three to five sections, each a single idea with a bolded subhead.",
    "Evidence - concrete specifics from the transcripts, attributed to the guest.",
    "Takeaway - one specific, usable action, not a summary.",
)

CARDINAL_RULE = (
    "Deliver exactly what the headline promises. If the headline says "
    "'5 lessons', the essay contains exactly five."
)


def principles_block() -> str:
    """Render the encoded principles as the instruction block for the model.

    Note what is deliberately *absent*: `Opener.example`. Those examples are
    real Ship 30 material and stay in the data as documentation, but injecting
    them into the prompt made llama3.2 open an essay with "Being physically fit
    isn't a hobby, it's a lifestyle" - copied verbatim. It is the same failure
    as the `[n]` placeholder: anything concrete in the instructions is
    something a small model reproduces rather than imitates. The rules teach
    the six shapes without handing over a sentence to steal.
    """
    openers = "\n".join(
        f"  {i}. {o.name} - {o.rule}" for i, o in enumerate(OPENERS, start=1)
    )
    formatting = "\n".join(f"  - {rule}" for rule in FORMATTING_RULES)
    arc = "\n".join(f"  {i}. {step}" for i, step in enumerate(NARRATIVE_ARC, start=1))
    headline = ", ".join(HEADLINE_ELEMENTS)

    return f"""SHIP 30 FOR 30 WRITING PRINCIPLES (follow all of them)

TITLE: a single H1. A good headline signals {headline}.

OPENING LINE: exactly one sentence, and it must be one of these six types:
{openers}

STRUCTURE:
{arc}

FORMATTING:
{formatting}

CARDINAL RULE: {CARDINAL_RULE}

LENGTH: approximately {TARGET_WORDS} words total. With 4 body sections that is
roughly 300 words each - write full paragraphs, not summaries. A section of two
or three sentences is too short.

Measured note for maintainers, not the model: adding an explicit upper bound
here ("never more than N words", "a section over 400 words is too long")
backfired badly - it cut typical output from ~1,400 words to ~700 and took the
citations with it. Models optimise hard against the most specific recent
constraint. The ceiling is enforced by the validator after the fact instead,
where it costs nothing if it never fires."""


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

H1_RE = re.compile(r"^#\s+\S", re.M)
H2_RE = re.compile(r"^#{2,3}\s+\S", re.M)
BULLET_RE = re.compile(r"^\s*[-*+]\s+\S", re.M)
BOLD_RE = re.compile(r"\*\*[^*\n]{2,}\*\*")
CITATION_RE = re.compile(r"\[(\d{1,2})\]")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(slots=True)
class Critique:
    """The result of measuring a draft against the encoded principles."""

    word_count: int
    failures: list[str]
    warnings: list[str]
    # Stable identifiers for the failures, in the same order. Comparing codes
    # rather than counts is what lets the orchestrator tell "this revision is
    # better" from "this revision traded one defect for another".
    codes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict:
        return {
            "word_count": self.word_count,
            "passed": self.passed,
            "failures": self.failures,
            "warnings": self.warnings,
        }

    def repair_instruction(self) -> str:
        """A precise, addressable revision brief - never 'make it better'."""
        items = "\n".join(f"- {f}" for f in self.failures + self.warnings)
        return (
            "Your draft misses these required elements. Revise it, keeping every "
            "factual claim and every numbered citation exactly as it is, and output "
            "the full corrected essay only:\n"
            f"{items}"
        )


def word_count(text: str) -> int:
    """Count prose words, ignoring markdown syntax so formatting is not scored."""
    stripped = re.sub(r"[#*_`>\[\]()-]", " ", text)
    return len([w for w in stripped.split() if any(c.isalnum() for c in w)])


def first_sentence(body: str) -> str:
    """The first sentence of prose after the H1 title."""
    lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines:
        return ""
    return SENTENCE_SPLIT_RE.split(lines[0])[0].strip()


def critique(text: str, *, require_citations: bool = True) -> Critique:
    """Measure a draft. `failures` block acceptance; `warnings` are advisory."""
    failures: list[str] = []
    warnings: list[str] = []
    codes: list[str] = []
    words = word_count(text)

    if words < WORD_FLOOR:
        sections = max(1, len(H2_RE.findall(text)))
        needed = TARGET_WORDS - words
        codes.append("length_short")
        failures.append(
            f"Too short: {words} words, and it needs about {TARGET_WORDS}. "
            f"Add roughly {needed} more words by expanding each of your "
            f"{sections} sections to about {TARGET_WORDS // max(sections, 1)} "
            "words. Go deeper on the excerpts you already cite - add the "
            "specifics, the numbers and the named examples they contain. "
            "Do not add claims the excerpts do not support, and do not add "
            "new sections."
        )
    elif words > WORD_CEILING:
        # Arithmetic, like the too-short case. "Tighten it" is not a brief a
        # model can execute; "remove 480 words" is. Capable models overshoot as
        # readily as small ones undershoot.
        excess = words - TARGET_WORDS
        codes.append("length_long")
        failures.append(
            f"Too long: {words} words, and it needs about {TARGET_WORDS}. "
            f"Remove roughly {excess} words. Tighten sentence by sentence and "
            "cut repetition and throat-clearing. Keep every section, every "
            "bullet and every citation - the length must come out of the prose, "
            "not the structure."
        )

    if not H1_RE.search(text):
        codes.append("no_h1")
        failures.append("No H1 title. Start with a single '# Headline' line.")

    headings = len(H2_RE.findall(text))
    if headings < 3:
        codes.append("few_sections")
        failures.append(
            f"Only {headings} section headings. Use at least 3 '## Subhead' "
            "sections so the piece is skimmable."
        )

    if not BULLET_RE.search(text):
        # Showing the literal markdown works where the rule alone does not.
        # Unlike a hook sentence, copying a *formatting* pattern is the desired
        # outcome, so a concrete example is safe here - see principles_block().
        codes.append("no_bullets")
        failures.append(
            "No bulleted list. Find a paragraph that enumerates things and "
            "convert it to a markdown list, exactly this shape:\n"
            "- First point\n- Second point\n- Third point"
        )

    bolds = len(BOLD_RE.findall(text))
    if bolds == 0:
        codes.append("no_bold")
        failures.append(
            "No bold emphasis. In each section, wrap the one sentence a skimmer "
            "must read in double asterisks, exactly this shape:\n"
            "**This is the sentence that carries the section.**"
        )
    elif bolds > 25:
        warnings.append(
            f"{bolds} bolded spans is too many - bolding everything bolds nothing."
        )

    opener = first_sentence(text)
    if not opener:
        codes.append("no_opener")
        failures.append("No opening line found beneath the title.")
    elif len(opener.split()) > 35:
        warnings.append(
            "The opening line runs long. Ship 30 openers are a single, tight sentence."
        )

    if require_citations and not CITATION_RE.search(text):
        codes.append("no_citations")
        failures.append(
            "No numbered citations. Every claim drawn from the transcripts must "
            "carry its excerpt number in square brackets, like [3]."
        )

    return Critique(
        word_count=words, failures=failures, warnings=warnings, codes=codes
    )


def system_prompt() -> str:
    """The full system prompt for the essay skill."""
    return f"""You are a senior product-growth writer producing an essay in the \
Ship 30 for 30 style, grounded strictly in excerpts from Lenny's Podcast.

{principles_block()}

GROUNDING RULES (these outrank every style rule above):
- Use ONLY the numbered excerpts provided. Do not add outside facts, statistics
  or names.
- Every substantive claim ends with the number of the excerpt it came from, in
  square brackets - for example: "Most teams over-index on the loudest users [4]."
  Use the excerpt's own number.
- Attribute opinions to the person who said them: "As Adam Mosseri put it, ..."
- If the excerpts do not support a section you planned, cut the section. Never
  invent an anecdote to fill a gap.

Output the essay as GitHub-flavoured Markdown. No preamble, no sign-off, no
meta-commentary about the excerpts."""
