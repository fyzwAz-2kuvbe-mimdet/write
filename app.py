"""
app.py
✨ 동화 만들기 마법사 - Streamlit 버전
Gemini 요청 1회 방식
"""
import os
import time
import datetime
import streamlit as st
from dotenv import load_dotenv
from gemini_utils import call_gemini, parse_json, build_final_prompt

load_dotenv()

STAGES = ["기", "승", "전", "결"]
STAGE_NAMES = {"기": "시작", "승": "전개", "전": "위기", "결": "마무리"}
STAGE_ICONS = {"기": "🌱", "승": "🚀", "전": "⚡", "결": "🌈"}

STAGE_QUESTIONS = {
    "기": {
        "question": "동화의 주인공은 누구인가요? 🐰",
        "suggestions": ["토끼 소녀 달이", "용감한 소년 하늘이", "작은 마법사 별이", "강아지 친구 뭉치"],
    },
    "승": {
        "question": "어떤 신나는 일이 생겼나요? 🚀",
        "suggestions": ["보물 지도를 발견했어요", "무서운 괴물이 나타났어요", "새로운 친구를 만났어요", "마법 문을 발견했어요"],
    },
    "전": {
        "question": "갑자기 어떤 위기가 찾아왔나요? ⚡",
        "suggestions": ["친구가 위험에 빠졌어요", "보물이 사라졌어요", "길을 잃어버렸어요", "마법이 풀려버렸어요"],
    },
    "결": {
        "question": "어떻게 문제를 해결했나요? 🌈",
        "suggestions": ["모두 힘을 합쳐 해결했어요", "마법의 힘으로 이겼어요", "용기를 내서 해냈어요", "친구의 도움으로 성공했어요"],
    },
}

st.set_page_config(
    page_title="✨ 동화 만들기 마법사",
    page_icon="📖",
    layout="centered",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&family=Black+Han+Sans&display=swap');
html, body, [class*="css"] { font-family: 'Jua', sans-serif !important; }

.main-title {
    font-family: 'Black Han Sans', sans-serif !important;
    font-size: 2.4rem;
    text-align: center;
    background: linear-gradient(135deg, #667eea, #f093fb);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.sub-title { text-align: center; color: #888; margin-bottom: 1.5rem; }

.stage-badge {
    display: inline-block;
    padding: 0.3rem 1rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: bold;
    margin: 0.2rem;
}
.stage-active { background: linear-gradient(135deg, #667eea, #f093fb); color: white; }
.stage-done   { background: #4ecdc4; color: white; }
.stage-wait   { background: #e0e0e0; color: #888; }

.ai-box {
    background: linear-gradient(135deg, #fff9c4, #ffe082);
    border: 2px solid #ffd700;
    border-radius: 16px;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
}
.ai-box-label    { font-size: 0.8rem; color: #6b4226; font-weight: bold; }
.ai-box-question { font-size: 1.1rem; color: #2c2c54; line-height: 1.7; margin-top: 0.3rem; }

.story-user {
    background: linear-gradient(135deg, #f0f4ff, #f8f0ff);
    border-left: 4px solid #c9b8f8;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin: 0.4rem 0;
}
.story-label { font-size: 0.75rem; font-weight: bold; margin-bottom: 0.3rem; }

.chapter-기 { background:#fff0f0; border-left:5px solid #ff6b6b; border-radius:10px; padding:1rem; margin-bottom:1rem; }
.chapter-승 { background:#fff8f0; border-left:5px solid #ffb347; border-radius:10px; padding:1rem; margin-bottom:1rem; }
.chapter-전 { background:#f0fff8; border-left:5px solid #4ecdc4; border-radius:10px; padding:1rem; margin-bottom:1rem; }
.chapter-결 { background:#f5f0ff; border-left:5px solid #c9b8f8; border-radius:10px; padding:1rem; margin-bottom:1rem; }
.chapter-title { font-weight:bold; font-size:1rem; margin-bottom:0.4rem; }
.chapter-text  { font-size:1.05rem; line-height:1.9; color:#2c2c54; }

.prompt-box {
    background: #f8f8f8;
    border: 1px solid #ddd;
    border-radius: 10px;
    padding: 1rem;
    font-size: 0.85rem;
    color: #444;
    white-space: pre-wrap;
    word-break: break-all;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
#  세션 초기화
# ─────────────────────────────────────────
def init_store():
    if "store" not in st.session_state:
        st.session_state.store = {
            "meta": {
                "sessionId": f"session_{int(time.time())}",
                "startedAt": datetime.datetime.now().isoformat(),
            },
            "inputs": {},
            "finalBook": None,
        }
    if "current_stage" not in st.session_state:
        st.session_state.current_stage = 0
    if "finished" not in st.session_state:
        st.session_state.finished = False
    if "gemini_error" not in st.session_state:
        st.session_state.gemini_error = None


def save_input(stage_id: str, user_text: str):
    st.session_state.store["inputs"][stage_id] = {
        "id": stage_id,
        "stage": stage_id,
        "stageName": STAGE_NAMES[stage_id],
        "userText": user_text,
        "timestamp": datetime.datetime.now().isoformat(),
    }


def get_api_key() -> str:
    """Streamlit Secrets에서 API 키를 가져옵니다."""
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY", "")


# ─────────────────────────────────────────
#  Gemini 1회 호출
# ─────────────────────────────────────────
def generate_final():
    api_key = get_api_key()
    if not api_key:
        st.session_state.gemini_error = "API 키 없음: Streamlit Secrets에 GEMINI_API_KEY를 설정해 주세요."
        st.session_state.finished = True
        return

    prompt = build_final_prompt(st.session_state.store)

    try:
        # call_gemini 자체에 @st.cache_data 적용됨
        # 동일 프롬프트면 API 재호출 없이 캐시 반환
        raw = call_gemini(prompt, api_key)
        parsed = parse_json(raw)
        st.session_state.store["finalBook"] = parsed
        st.session_state.gemini_error = None
    except Exception as e:
        err = str(e)
        if "404" in err:
            st.session_state.gemini_error = "404_NOT_FOUND"
        elif "429" in err or "Too Many Requests" in err:
            st.session_state.gemini_error = "429_TOO_MANY"
        else:
            st.session_state.gemini_error = err
        fallback = {
            s: st.session_state.store["inputs"].get(s, {}).get("userText", "")
            for s in STAGES
        }
        st.session_state.store["finalBook"] = {
            "title": "우리가 함께 만든 동화",
            "story": fallback,
        }
    st.session_state.finished = True


# ─────────────────────────────────────────
#  답변 제출
# ─────────────────────────────────────────
def submit_answer(user_text: str):
    stage = STAGES[st.session_state.current_stage]
    save_input(stage, user_text)

    if st.session_state.current_stage < len(STAGES) - 1:
        # 다음 단계로 이동 (Gemini 호출 없음)
        st.session_state.current_stage += 1
    else:
        # 기승전결 모두 완료 → Gemini에 딱 1번 요청
        generate_final()


# ─────────────────────────────────────────
#  UI
# ─────────────────────────────────────────
def render_header():
    st.markdown('<div class="main-title">✨ 동화 만들기 마법사 ✨</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">기승전결을 골라주면 동화를 완성해 드려요! 📖</div>', unsafe_allow_html=True)


def render_progress():
    idx = st.session_state.current_stage
    badges = ""
    for i, s in enumerate(STAGES):
        if i < idx:     cls = "stage-done"
        elif i == idx:  cls = "stage-active"
        else:           cls = "stage-wait"
        badges += f'<span class="stage-badge {cls}">{STAGE_ICONS[s]} {s}({STAGE_NAMES[s]})</span>'
    st.markdown(f'<div style="text-align:center;margin-bottom:0.8rem">{badges}</div>', unsafe_allow_html=True)
    st.progress(idx / len(STAGES))


def render_collected_inputs():
    inputs = st.session_state.store["inputs"]
    if not inputs:
        return
    st.markdown("##### 📋 지금까지 고른 이야기 재료")
    for s in STAGES:
        d = inputs.get(s)
        if d:
            st.markdown(f"""
            <div class="story-user">
              <div class="story-label" style="color:#667eea">{STAGE_ICONS[s]} {s} - {d['stageName']}</div>
              {d['userText']}
            </div>""", unsafe_allow_html=True)


def render_input_area():
    stage = STAGES[st.session_state.current_stage]
    q = STAGE_QUESTIONS[stage]

    st.markdown(f"""
    <div class="ai-box">
      <div class="ai-box-label">🧚 {st.session_state.current_stage + 1} / {len(STAGES)} 단계</div>
      <div class="ai-box-question">{q['question']}</div>
    </div>""", unsafe_allow_html=True)

    # 선택지 버튼 클릭 시 selected_text에 저장
    st.markdown("**선택지를 고르거나 직접 입력하세요:**")
    cols = st.columns(2)
    for i, s in enumerate(q["suggestions"]):
        if cols[i % 2].button(s, key=f"sugg_{stage}_{i}", use_container_width=True):
            st.session_state[f"selected_{stage}"] = s

    # 선택된 값 또는 기존 입력값을 textarea 기본값으로
    selected = st.session_state.get(f"selected_{stage}", "")
    prev     = st.session_state.get(f"input_{stage}", "")
    default  = selected if selected else prev

    user_input = st.text_area(
        "직접 입력",
        value=default,
        max_chars=100,
        height=80,
        key=f"textarea_{stage}_{selected}",
        label_visibility="collapsed",
        placeholder="직접 입력하거나 위 버튼을 눌러주세요",
    )

    # 최종 입력값 저장
    final_val = user_input.strip() if user_input.strip() else selected.strip()
    if final_val:
        st.session_state[f"input_{stage}"] = final_val

    is_last = st.session_state.current_stage == len(STAGES) - 1
    btn_label = "✨ 동화 완성하기!" if is_last else "다음 단계로 →"

    if st.button(btn_label, type="primary", use_container_width=True):
        val = st.session_state.get(f"input_{stage}", "").strip()
        if not val:
            st.warning("선택지를 고르거나 직접 입력해 주세요!")
        elif is_last and not get_api_key():
            st.error("🔑 Gemini API 키가 없어요! Streamlit Secrets를 확인해 주세요.")
        else:
            if is_last:
                with st.spinner("🧚 Gemini가 동화를 완성하는 중... (잠시만요!)"):
                    submit_answer(val)
            else:
                submit_answer(val)
            st.rerun()


def render_final_book():
    if st.session_state.gemini_error:
        if st.session_state.gemini_error == "429_TOO_MANY":
            st.warning("⏳ 현재 요청이 너무 많아요. 약 1분 후 아래 버튼을 눌러 다시 시도해 주세요!")
        elif st.session_state.gemini_error == "404_NOT_FOUND":
            st.error("🔍 모델을 찾을 수 없어요. API 키가 올바른지, 결제 계정이 연결되어 있는지 확인해 주세요.")
        else:
            with st.expander("⚠️ Gemini 오류 상세 보기", expanded=False):
                st.code(st.session_state.gemini_error)
                st.caption("Streamlit Cloud > Settings > Secrets > GEMINI_API_KEY 확인")

        if st.button("🔄 Gemini로 다시 시도", type="primary"):
            # 캐시 초기화 후 재시도
            call_gemini.clear()
            st.session_state.gemini_error = None
            st.session_state.finished = False
            st.session_state.store["finalBook"] = None
            with st.spinner("🧚 Gemini에게 다시 요청 중..."):
                generate_final()
            st.rerun()
        st.markdown("---")

    book  = st.session_state.store["finalBook"]
    title = book.get("title", "우리가 만든 동화")
    story = book.get("story", {})

    st.markdown(f"""
    <div style="text-align:center;padding:1.5rem 0">
      <div style="font-size:3rem">🎉</div>
      <div style="font-family:'Black Han Sans',sans-serif;font-size:1.8rem;
                  background:linear-gradient(135deg,#f093fb,#667eea);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent">
        완성된 동화책!
      </div>
      <div style="font-size:1.2rem;color:#555;margin-top:0.3rem">📖 {title}</div>
    </div>""", unsafe_allow_html=True)

    total_chars = 0
    for s in STAGES:
        text = story.get(s) or st.session_state.store["inputs"].get(s, {}).get("userText", "")
        total_chars += len(text)
        st.markdown(f"""
        <div class="chapter-{s}">
          <div class="chapter-title">{STAGE_ICONS[s]} {s} - {STAGE_NAMES[s]}</div>
          <div class="chapter-text">{text}</div>
        </div>""", unsafe_allow_html=True)

    st.caption(f"📝 총 글자 수: {total_chars}자")
    st.balloons()

    with st.expander("🔍 Gemini에 보낸 프롬프트 확인"):
        prompt = build_final_prompt(st.session_state.store)
        st.markdown(f'<div class="prompt-box">{prompt}</div>', unsafe_allow_html=True)
        st.caption(f"프롬프트 글자 수: {len(prompt)}자")

    full_text = f"📖 {title}\n\n"
    for s in STAGES:
        full_text += f"[{s} - {STAGE_NAMES[s]}]\n{story.get(s, '')}\n\n"
    full_text += f"\n총 {total_chars}자"

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 텍스트로 저장", full_text,
                           file_name=f"{title}.txt", use_container_width=True)
    with col2:
        if st.button("🔄 새 이야기 만들기", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def render_sidebar():
    with st.sidebar:
        st.markdown("### 📋 수집된 이야기 재료")
        inputs = st.session_state.store.get("inputs", {})
        if not inputs:
            st.caption("아직 선택한 내용이 없어요")
            return
        for s in STAGES:
            d = inputs.get(s)
            if d:
                st.markdown(f"**{STAGE_ICONS[s]} {s} - {d['stageName']}**")
                st.caption(d["userText"])
                st.markdown("---")


# ─────────────────────────────────────────
#  메인
# ─────────────────────────────────────────
def main():
    init_store()
    render_header()
    render_sidebar()

    if st.session_state.finished:
        render_final_book()
    else:
        render_progress()
        render_collected_inputs()
        render_input_area()


if __name__ == "__main__":
    main()
