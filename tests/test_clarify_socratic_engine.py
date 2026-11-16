"""Tests verifying the Deep Socratic Grilling & Intent Extraction Engine."""

from __future__ import annotations


def test_clarify_purges_question_quotas_and_batch_ceilings(clarify_template_text: str) -> None:
    """US1: Clarify template must have zero references to 5-question round caps or question quotas."""
    # Negative assertions: No quota or round limit language
    assert "Batch in rounds of up to 5 questions" not in clarify_template_text
    assert "exceeds question quota" not in clarify_template_text
    assert "up to 5 per round" not in clarify_template_text
    assert "up to 5 questions" not in clarify_template_text


def test_specify_purges_inline_tables_and_question_limits(specify_template_text: str) -> None:
    """US1: Specify template must not run inline question tables or clamp clarifications."""
    # Negative assertions
    assert "Maximum 3 [NEEDS CLARIFICATION] markers" not in specify_template_text
    assert "| Option | Answer | Implications |" not in specify_template_text
    assert "Make informed guesses" not in specify_template_text
    assert "Your choice: _[Wait for user response]_" not in specify_template_text


def test_clarify_hypothesis_first_and_confidence_scoring(clarify_template_text: str) -> None:
    """US2: Clarify template must mandate opening with HYPOTHESIS and CONFIDENCE score."""
    assert "HYPOTHESIS:" in clarify_template_text
    assert "CONFIDENCE:" in clarify_template_text
    assert "missing:" in clarify_template_text
    assert "0–100%" in clarify_template_text or "0-100%" in clarify_template_text


def test_clarify_guess_attached_protocol_and_table_ban(clarify_template_text: str) -> None:
    """US3: Clarify template must enforce guess-attached questions and ban markdown choice tables."""
    assert "**Question:**" in clarify_template_text
    assert "**Why it matters:**" in clarify_template_text
    assert "**My Guess:**" in clarify_template_text
    # Markdown survey table format must be eliminated from interactive questioning
    assert "| Option | Description |" not in clarify_template_text
    # Bulleted options must be used for discrete architectural forks
    assert "- Option A:" in clarify_template_text
    assert "- Option B:" in clarify_template_text


def test_clarify_user_feedback_and_abdication_handling(clarify_template_text: str) -> None:
    """US3: Clarify must handle guess corrections without defense and reject 'whatever you think' abdication."""
    assert "User Corrects a Guess" in clarify_template_text
    assert "User Abdication" in clarify_template_text
    assert "Whatever you think" in clarify_template_text
    assert "without defensive rationalization" in clarify_template_text


def test_clarify_persists_confirmed_intent_in_spec(clarify_template_text: str) -> None:
    """US5/FR-010: Clarify must persist Confirmed Intent & Non-Goals in spec and allow it in validation headings."""
    assert "### Confirmed Intent & Non-Goals" in clarify_template_text
    assert "allowed new headings: `## Clarifications`, `### Session YYYY-MM-DD`, `### Confirmed Intent & Non-Goals`" in clarify_template_text


def test_specify_reserves_clarifications_section(specify_template_text: str) -> None:
    """US1/FR-009: Specify template must explicitly note that Clarifications and Confirmed Intent are reserved."""
    assert "The `## Clarifications` section and its `### Confirmed Intent & Non-Goals` subsection in `spec-template.md` are strictly reserved" in specify_template_text


def test_spec_template_includes_confirmed_intent_block(spec_template_text: str) -> None:
    """US6: spec-template.md must include the Confirmed Intent & Non-Goals section under Clarifications."""
    assert "## Clarifications" in spec_template_text
    assert "### Confirmed Intent & Non-Goals" in spec_template_text
    assert "- **Outcome**:" in spec_template_text
    assert "- **Out of scope**:" in spec_template_text


def test_debug_template_hypothesis_and_confidence(debug_template_text: str) -> None:
    """US6: debug command template must feature falsifiable hypothesis and confidence score."""
    assert "initial confidence score (0–100%)" in debug_template_text.lower()
    assert "| Hypothesis | Initial Confidence | Evidence | Result |" in debug_template_text


def test_clarify_anti_rationalization_and_pre_mortem_probing(clarify_template_text: str) -> None:
    """US4: Clarify template must include Want vs. Should Want filter and 6-month pre-mortem probe."""
    assert "If you didn't have to justify this to anyone, what would you actually want" in clarify_template_text
    assert "Pre-Mortem" in clarify_template_text or "pre-mortem" in clarify_template_text
    assert "6 months" in clarify_template_text or "six months" in clarify_template_text


def test_clarify_confirmed_intent_and_95_percent_stop(clarify_template_text: str) -> None:
    """US5: Clarify template must enforce 95% confidence stop and 6-line Confirmed Intent schema."""
    assert "Here is the confirmed intent:" in clarify_template_text
    assert "- Outcome:" in clarify_template_text
    assert "- User:" in clarify_template_text
    assert "- Why now:" in clarify_template_text
    assert "- Success:" in clarify_template_text
    assert "- Constraint:" in clarify_template_text
    assert "- Out of scope:" in clarify_template_text
    assert "95%" in clarify_template_text


def test_clarify_originates_autonomous_questions_beyond_specify_markers(clarify_template_text: str) -> None:
    """Clarify template must mandate autonomous deep-dive inquiry beyond pre-existing specify markers."""
    assert "AUTONOMOUS DEEP-DIVE INVARIANT" in clarify_template_text
    assert "Autonomous Question Origination Beyond Specify" in clarify_template_text
    assert "NOT limited to pre-existing `[NEEDS CLARIFICATION]` markers" in clarify_template_text
