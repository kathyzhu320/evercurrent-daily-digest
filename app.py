"""One-page reviewer demo. Gate 1 decides stories; this file only presents them."""
from datetime import timezone
from html import escape
import os
import streamlit as st
from src.config import PHASES, TOPICS, load_config
from src.demo import build_demo_digest, record_feedback, top3_jaccard
from src.display import format_persona_label
from src.ingestion import load_messages, load_personas
from src.personalization import make_context
from src.pipeline import build_ranked_digest
from src.presentation import CATEGORY_ORDER, relationship_label, score_rows, source_rows, story_marker, why_this_matters
from src.summarizer import SummaryCache, deterministic_summary, provider_from_environment

st.set_page_config(page_title='EverCurrent · Atlas Daily Digest', page_icon='⚡', layout='wide')
st.markdown('''<style>
:root { --ink:#12253f; --teal:#087d83; --muted:#52677e; --surface:#f4f8fa; }
.block-container { max-width:1220px; padding-top:2rem; }
h1,h2,h3 { color:var(--ink); letter-spacing:-.025em; }
[data-testid="stSidebar"] { background:#edf5f6; }
.hero { background:linear-gradient(115deg,#11263e,#155b69); color:#fff; border-radius:16px;
        padding:1.6rem 2rem; margin-bottom:1.2rem; }
.hero h1 { color:#fff; margin:0; font-size:2rem; }
.hero p { color:#d5edf1; margin:.45rem 0 0; }
.story-kicker { color:#087d83; font-size:.78rem; font-weight:700; letter-spacing:.09em; text-transform:uppercase; }
.story-meta { color:#52677e; font-size:.88rem; }
.small-note { color:#52677e; font-size:.84rem; }
</style>''', unsafe_allow_html=True)

cfg = load_config()
messages = load_messages(cfg=cfg)
personas = load_personas()
if 'feedback_events' not in st.session_state:
    st.session_state.feedback_events = {}
if 'feedback_sequence' not in st.session_state:
    st.session_state.feedback_sequence = 0

st.sidebar.title('EverCurrent')
st.sidebar.caption('Project Atlas · deterministic Daily Digest')
selected_id = st.sidebar.selectbox('Persona', list(personas),
                                   format_func=lambda persona_id: format_persona_label(personas[persona_id]))
persona = personas[selected_id]
st.sidebar.caption(f'Role: {persona.role} · fixed by persona')
st.sidebar.selectbox('Project', ['Project Atlas'], disabled=True)
phase = st.sidebar.selectbox('Phase', PHASES, index=PHASES.index(cfg['default_phase']))
priorities = st.sidebar.multiselect(
    'Current priorities', TOPICS, default=persona.default_priorities,
    format_func=lambda topic: topic.replace('_', ' ').title(), key=f'priorities-{persona.persona_id}')
st.sidebar.button('Generate / Refresh Digest', type='primary', use_container_width=True)
live = st.sidebar.toggle('Live OpenAI summary (optional)', value=False)
if live and (not (os.environ.get('OPENAI_API_KEY') or '').strip()
             or not (os.environ.get('OPENAI_MODEL') or '').strip()):
    st.sidebar.info('Live summaries need both OPENAI_API_KEY and OPENAI_MODEL. Deterministic summaries remain available.')
st.sidebar.caption(f"Fixed as-of · {cfg['as_of']}\n\nLookback · {cfg['lookback_hours']} hours (UTC)")

context = make_context(persona, cfg, phase=phase, priorities=tuple(priorities),
                       feedback=st.session_state.feedback_events.get(persona.persona_id, ()))
cache = SummaryCache()
provider = provider_from_environment(live)
demo = build_demo_digest(context, messages, cfg, cache=cache, provider=provider)

st.markdown('<div class="hero"><h1>Adaptive Daily Digest</h1>'
            '<p>Project Atlas · selected engineering signals, grounded in authorized Slack sources</p></div>',
            unsafe_allow_html=True)
st.caption(f"{format_persona_label(persona)} · {phase} · As of {cfg['as_of']} · "
           f"{len(demo.result.eligible_ids)} eligible authorized messages · "
           f"{len(persona.channels)} accessible channels · 72-hour lookback")

digest_tab, compare_tab = st.tabs(['My Digest', 'Compare personas'])
with digest_tab:
    st.markdown('### What matters today')
    st.caption('Ranking selects up to five stories. Summaries describe only those selected authorized facts.')
    for category in CATEGORY_ORDER:
        section = [entry for entry in demo.items if entry.ranked.category == category]
        if not section:
            continue
        st.subheader(category)
        for entry in section:
            ranked = entry.ranked
            story = ranked.story
            rep = story.representative
            with st.container(border=True):
                left, right = st.columns([5, 1])
                with left:
                    st.markdown(f'<div class="story-kicker">{escape(story.story_id)} · '
                                f'{escape(rep.topics[0].replace("_", " "))}</div>', unsafe_allow_html=True)
                    st.markdown(f'**{entry.summary.text}**')
                with right:
                    st.metric('Final score', f'{ranked.score.final_score:.4f}')
                marker = story_marker(story)
                if marker:
                    (st.warning if marker.startswith('Conflict') else st.info)(marker)
                if ranked.protected:
                    st.caption('Protected by Severity Floor')
                st.markdown(f'**Why it matters:** {why_this_matters(ranked)}')
                st.caption(f'Source: #{rep.channel} · {rep.timestamp.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC · {rep.message_id}')
                with st.expander('Why ranked? · six signal breakdown'):
                    st.table(score_rows(ranked))
                    st.write(f'**Final Score:** {ranked.score.final_score:.6f}')
                    st.write('**Matched priorities:** ' + (', '.join(ranked.score.matched_priorities) or 'none'))
                    st.write('**Role topics:** ' + (', '.join(ranked.score.role_topics) or 'none'))
                    st.write('**Phase topics:** ' + (', '.join(ranked.score.phase_topics) or 'none'))
                    st.write('**Owns ∩ affects:** ' + (', '.join(ranked.score.owns_affects) or 'none'))
                    st.write(f'**Severity Floor:** eligible={ranked.score.floor_eligible}, protected={ranked.protected}')
                    st.caption(f'Summary mode: {entry.summary.mode}' + (' · cache hit' if entry.summary.from_cache else '')
                               + (f' · fallback: {entry.summary.fallback_reason}' if entry.summary.fallback_reason else ''))
                if story.relationships:
                    with st.expander('Relationship evidence · differences and updates'):
                        for relation in story.relationships:
                            st.markdown(f'**{relationship_label(relation)}** · {" / ".join(relation.source_ids)}')
                            st.caption(relation.evidence)
                        if story.identifier_differences:
                            st.json(story.identifier_differences)
                with st.expander(f'Original source messages ({len(story.source_message_ids)})'):
                    for source in source_rows(story):
                        st.markdown(f'**{source["ID"]}** · {source["Channel"]} · {source["UTC timestamp"]} · {source["Role"]}')
                        st.code(source['Text'], language=None)
                a, b, spacer = st.columns([1, 1, 4])
                for column, label, value in ((a, 'Relevant', True), (b, 'Not Relevant', False)):
                    with column:
                        if st.button(label, key=f'{label}-{persona.persona_id}-{story.story_id}'):
                            sequence = st.session_state.feedback_sequence + 1
                            st.session_state.feedback_sequence = sequence
                            event_id = f'UI-{persona.persona_id}-{sequence:04d}'
                            updated = record_feedback(st.session_state.feedback_events.get(persona.persona_id, ()),
                                                      ranked, persona.persona_id, context.as_of, value, event_id)
                            st.session_state.feedback_events[persona.persona_id] = updated
                            st.rerun()

with compare_tab:
    st.markdown('### Same messages. Different priorities.')
    st.caption(f"Project Atlas · {phase} · fixed {cfg['as_of']} · each persona keeps their own current priorities and feedback.")
    comparison_ids = st.multiselect('Compare personas', list(personas), default=['sarah', 'raj', 'marcus'],
                                    format_func=lambda id: format_persona_label(personas[id]), max_selections=5)
    if len(comparison_ids) < 2:
        st.info('Select at least two personas to compare.')
    else:
        compare_results = {}
        for id in comparison_ids:
            p = personas[id]
            selected = st.session_state.get(f'priorities-{id}', p.default_priorities)
            c = make_context(p, cfg, phase=phase, priorities=tuple(selected),
                             feedback=st.session_state.feedback_events.get(id, ()))
            compare_results[id] = build_ranked_digest(c, messages, cfg)
        cols = st.columns(len(comparison_ids))
        for col, id in zip(cols, comparison_ids):
            p = personas[id]
            with col:
                st.subheader(format_persona_label(p))
                st.caption(f'{p.role} · priorities: {", ".join(st.session_state.get(f"priorities-{id}", p.default_priorities))}')
                for index, ranked in enumerate(compare_results[id].digest[:3], 1):
                    with st.container(border=True):
                        st.markdown(f'**{index}. {ranked.story.story_id}** · {ranked.score.final_score:.4f}')
                        st.write(deterministic_summary(ranked.story))
                        st.caption(f'#{ranked.story.representative.channel} · {ranked.story.representative.message_id}')
        st.markdown('#### Top-3 overlap')
        ids = list(comparison_ids)
        for i, first in enumerate(ids):
            for second in ids[i+1:]:
                left = {r.story.story_id for r in compare_results[first].digest[:3]}
                right = {r.story.story_id for r in compare_results[second].digest[:3]}
                st.write(f'**{format_persona_label(personas[first])} / {format_persona_label(personas[second])}:** '
                         f'{len(left & right)} shared · Jaccard {top3_jaccard(compare_results[first], compare_results[second]):.2f}')
                st.caption('Shared: ' + (', '.join(sorted(left & right)) or 'none') +
                           ' · Unique: ' + ', '.join(sorted(left ^ right)))
        st.caption('Differences reflect role, ownership, accessible channels, selected priorities and feedback; no ranking is changed for presentation.')
