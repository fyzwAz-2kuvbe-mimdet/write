# -*- coding: utf-8 -*-
"""
app.py
✨ 동화 만들기 마법사 - 장편 확장 버전 (5단계 릴레이 소설)
"""
import os
import time
import datetime
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from gemini_utils import call_gemini, parse_json, build_final_prompt, build_expansion_prompt
from auth import render_auth
from feed import render_feed, render_upload_button

load_dotenv()

# ==========================================
#  상수 및 설정 데이터
# ==========================================
STAGES = ["기", "승", "전", "결"]
STAGE_NAMES = {"기": "시작", "승": "전개", "전": "위기", "결": "마무리"}
STAGE_ICONS = {"기": "🌱", "승": "🚀", "전": "⚡", "결": "🌈"}

TARGET_AGES = ["4~7세", "7~9세", "10~13세", "14~16세", "직접 입력"]
PLOT_TYPES = ["성장과 모험", "결점의 재발견", "반복과 확장", "부메랑 효과", "비밀공유와 들통"]
TARGET_LENGTHS = {
    "짧은 동화 (약 3,000자)": 3000,
    "일반 동화 (약 5,000자)": 5000,
    "긴 동화 (약 7,500자)": 7500,
    "장편 동화 (약 10,000자)": 10000,
}

AUTHOR_STYLES = {
    "생텍쥐페리 (어린왕자)": {
        "role": "20년 경력의 동화 작가",
        "style": "생텍쥐페리 (어린왕자)",
        "tone": "시적, 철학적, 담백함",
        "constraints": {
            "sentence_structure": "짧고 여운이 남는 문장",
            "key_elements": ["상징적 사물", "어른들의 모순 비판", "관계에 대한 정의"],
        },
    },
    "J.K. 롤링 (해리포터)": {
        "role": "판타지 세계관 설계자",
        "style": "J.K. 롤링 (해리포터)",
        "tone": "박진감 넘침, 세밀한 묘사, 신비로움",
        "constraints": {
            "vocabulary": ["창의적인 주문 이름", "독특한 마법 도구", "고유 명사"],
            "narrative": "치밀한 복선과 반전",
            "world_building": "풍부한 형용사를 사용한 시각적 묘사",
        },
    },
    "이솝 (이솝우화)": {
        "role": "지혜로운 우화 작가",
        "style": "이솝 (이솝우화)",
        "tone": "명확함, 교훈적, 객관적",
        "constraints": {
            "characters": "의인화된 동물",
            "length": "매우 짧고 강렬함",
            "mandatory_ending": "마지막에 반드시 '교훈'을 한 문장으로 명시할 것",
        },
    },
    "김영하 (냉소적 유머와 통찰)": {
        "role": "냉철한 시선의 현대 소설가",
        "style": "김영하 (냉소적 유머와 통찰)",
        "tone": "건조함, 세련됨, 지적임",
        "constraints": {
            "perspective": "일상의 낯설게 하기",
            "emotional_level": "감상주의 배제",
            "description": "인물의 심리적 갈등과 날카로운 관찰",
        },
    },
    "진 웹스터 (키다리 아저씨)": {
        "role": "긍정 에너지가 넘치는 스토리텔러",
        "style": "진 웹스터 (키다리 아저씨)",
        "tone": "발랄함, 수다스러움, 따뜻함",
        "constraints": {
            "format": "1인칭 편지 형식 (서간체)",
            "punctuation": "느낌표와 의문문의 적절한 활용",
            "atmosphere": "일상의 소소한 발견과 유머",
        },
    },
    "제인 오스틴 (오만과 편견)": {
        "role": "클래식하고 위트 있는 근대 소설가",
        "style": "제인 오스틴 (오만과 편견)",
        "tone": "우아함, 냉철한 풍자, 예리한 관찰",
        "constraints": {
            "vocabulary": ["격식 있는 말투", "미묘한 감정 묘사", "예법과 도덕"],
            "narrative": "인물 간의 사소한 오해와 그것이 풀리는 과정",
            "atmosphere": "차분하고 교양 있는 숲속 티타임 같은 분위기",
        },
    },
    "이슬아 (일간 이슬아)": {
        "role": "매일 글을 쓰는 성실한 에세이스트",
        "style": "이슬아 (일간 이슬아)",
        "tone": "솔직함, 씩씩함, 구체적이고 다정함",
        "constraints": {
            "format": "오늘 겪은 일을 들려주는 듯한 1인칭 고백체",
            "description": "관념적이지 않고 몸의 감각이나 구체적인 사물을 묘사",
            "emotional_level": "과장되지 않은 담백한 감동",
        },
    },
}

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

st.set_page_config(page_title="✨ 장편 동화 마법사", page_icon="📖", layout="centered")

def render_floating_cat():
    components.html(
        "<script>"
        "(function(){"
        "var p=window.parent,d=p.document;"
        "if(p._catReady)return;"
        "p._catReady=true;"
        "var c=d.createElement('div');"
        "c.id='neko';"
        "c.innerHTML='&#x1F431;';"
        "c.style.cssText='position:fixed;top:0;left:0;font-size:32px;"
        "pointer-events:none;user-select:none;z-index:99999;"
        "transition:transform 0.1s ease-out;"
        "transform:translate(-99px,-99px)';"
        "d.body.appendChild(c);"
        "var lx=0;"
        "d.addEventListener('mousemove',function(e){"
        "var f=e.clientX-lx<0?' scaleX(-1)':'';"
        "lx=e.clientX;"
        "c.style.transform='translate('+(e.clientX+8)+'px,'+(e.clientY+8)+'px)'+f;"
        "});"
        "})();"
        "</script>",
        height=0,
    )

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&family=Black+Han+Sans&display=swap');

/* 전체 다크 배경 */
html, body, [class*="css"], .stApp {
    font-family: 'Jua', sans-serif !important;
    background-color: #0e0e0e !important;
    color: #f0f0f0 !important;
}
.block-container { background-color: #0e0e0e !important; }

/* 헤더 */
.main-title {
    font-family: 'Black Han Sans', sans-serif !important;
    font-size: 2.2rem; text-align: center;
    background: linear-gradient(135deg, #a78bfa, #f093fb);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.sub-title { text-align: center; color: #888; margin-bottom: 1.5rem; font-size: 0.95rem; }

/* 진행 단계 뱃지 */
.stage-badge { display: inline-block; padding: 0.35rem 1.1rem; border-radius: 999px; font-size: 0.85rem; font-weight: bold; margin: 0.2rem; }
.stage-active { background: #7c3aed; color: white; }
.stage-done   { background: #4ecdc4; color: white; }
.stage-wait   { background: #2a2a2a; color: #666; border: 1px solid #333; }

/* AI 질문 박스 */
.ai-box { background: #1a1a2e; border: 1.5px solid #7c3aed; border-radius: 14px; padding: 1rem 1.2rem; margin: 1rem 0; }
.ai-box-label { font-size: 0.8rem; color: #a78bfa; font-weight: bold; }
.ai-box-question { font-size: 1.1rem; color: #f0f0f0; line-height: 1.7; margin-top: 0.3rem; }

/* 이야기 재료 박스 */
.story-user { background: #1a1a2e; border-left: 4px solid #7c3aed; border-radius: 10px; padding: 0.7rem 1rem; margin: 0.4rem 0; color: #ccc; }
.story-label { font-size: 0.75rem; font-weight: bold; margin-bottom: 0.3rem; color: #a78bfa; }

/* 챕터 박스 */
.chapter-box { background: #1a1a1a; border-left: 5px solid #7c3aed; border-radius: 10px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.4); }
.chapter-title { font-family: 'Black Han Sans', sans-serif; font-size: 1.4rem; margin-bottom: 0.8rem; color: #f0f0f0; }
.chapter-text  { font-size: 1.05rem; line-height: 1.9; color: #d0d0d0; white-space: pre-wrap; }

/* 설정 박스 */
.setup-box { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px; padding: 1.5rem; margin-bottom: 1.5rem; }

/* Streamlit 기본 요소 다크 오버라이드 */
.stButton > button {
    background: #1e1e1e !important;
    color: #f0f0f0 !important;
    border: 1px solid #333 !important;
    border-radius: 8px !important;
    font-family: 'Jua', sans-serif !important;
}
.stButton > button:hover {
    background: #2a2a2a !important;
    border-color: #7c3aed !important;
}
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #1e1e1e !important;
    color: #f0f0f0 !important;
    border: 1px solid #333 !important;
    border-radius: 8px !important;
}
[data-testid="stSelectbox"] > div {
    background: #1e1e1e !important;
    color: #f0f0f0 !important;
    border: 1px solid #333 !important;
}
.stProgress > div > div { background: #7c3aed !important; }
[data-testid="stSidebar"] { background: #111 !important; }
[data-testid="stSidebar"] * { color: #ccc !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
#  세션 초기화
# ─────────────────────────────────────────
def init_store():
    if "setup_complete" not in st.session_state:
        st.session_state.setup_complete = False
    if "author_phase_complete" not in st.session_state:
        st.session_state.author_phase_complete = False
    if "store" not in st.session_state:
        st.session_state.store = {
            "meta": {
                "sessionId": f"session_{int(time.time())}",
                "startedAt": datetime.datetime.now().isoformat(),
            },
            "settings": {},
            "inputs": {},
            "outline": None,        # 1차 뼈대 저장소
            "expanded_parts": [],   # 5단계 파트 배열
        }
    if "current_stage" not in st.session_state:
        st.session_state.current_stage = 0
    if "finished" not in st.session_state:
        st.session_state.finished = False
    if "gemini_error" not in st.session_state:
        st.session_state.gemini_error = None
    if "generating" not in st.session_state:
        st.session_state.generating = False
    if "part_reviewing" not in st.session_state:
        # 파트 생성 후 검토 중 상태 (True면 결과 확인 화면 표시)
        st.session_state.part_reviewing = False


def get_api_key() -> str:
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY", "")


# ─────────────────────────────────────────
#  중간 저장 / 불러오기
# ─────────────────────────────────────────
def save_draft():
    """현재 진행 상태를 Firebase에 저장"""
    user = st.session_state.get("user")
    if not user:
        return
    try:
        from db import get_db
        db = get_db()
        db.collection("drafts").document(user["uid"]).set({
            "uid": user["uid"],
            "store": st.session_state.store,
            "current_stage": st.session_state.current_stage,
            "setup_complete": st.session_state.setup_complete,
            "author_phase_complete": st.session_state.author_phase_complete,
            "finished": st.session_state.finished,
            "saved_at": datetime.datetime.now().isoformat(),
        })
        st.toast("💾 진행 상태가 저장됐어요!", icon="✅")
    except Exception as e:
        st.toast(f"저장 실패: {e}", icon="❌")


def load_draft():
    """Firebase에서 저장된 진행 상태 불러오기"""
    user = st.session_state.get("user")
    if not user:
        return False
    try:
        from db import get_db
        db = get_db()
        doc = db.collection("drafts").document(user["uid"]).get()
        if not doc.exists:
            return False
        data = doc.to_dict()
        st.session_state.store               = data["store"]
        st.session_state.current_stage       = data["current_stage"]
        st.session_state.setup_complete      = data["setup_complete"]
        st.session_state.author_phase_complete = data["author_phase_complete"]
        st.session_state.finished            = data["finished"]
        st.session_state.generating          = False
        st.session_state.part_reviewing      = False
        st.session_state.gemini_error        = None
        return data.get("saved_at", "")
    except Exception as e:
        st.error(f"불러오기 실패: {e}")
        return False


def render_draft_controls():
    """저장/불러오기 버튼 UI - 사이드바에 표시"""
    user = st.session_state.get("user")
    if not user:
        return
    st.markdown("---")
    st.markdown("### 💾 진행 상태")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 저장", use_container_width=True, key="save_draft_btn"):
            save_draft()
    with col2:
        if st.button("📂 불러오기", use_container_width=True, key="load_draft_btn"):
            saved_at = load_draft()
            if saved_at:
                st.success(f"불러옴!\n{saved_at[:16]}")
                st.rerun()
            else:
                st.info("저장된 내용이 없어요.")


# ─────────────────────────────────────────
#  뼈대 + 파트 1개씩 생성 로직
# ─────────────────────────────────────────
def generate_next_part():
    """뼈대가 없으면 먼저 생성, 이후 다음 파트 1개만 생성하고 검토 상태로 전환."""
    api_key = get_api_key()
    if not api_key:
        st.session_state.gemini_error = "API 키 없음: Streamlit Secrets에 GEMINI_API_KEY를 설정해 주세요."
        st.session_state.generating = False
        return

    st.session_state.gemini_error = None
    store = st.session_state.store

    try:
        # 1. 뼈대(개요) 생성 - 아직 없을 때만
        if store.get("outline") is None:
            outline_prompt = build_final_prompt(store)
            raw_outline = call_gemini(outline_prompt, api_key)
            store["outline"] = parse_json(raw_outline)

        # 2. 다음 파트 1개만 생성
        current_idx = len(store["expanded_parts"]) + 1
        target_len = store["settings"].get("target_length", 5000)
        chars_per_part = target_len // 5

        part_prompt = build_expansion_prompt(store, current_idx, chars_per_part)
        raw_part = call_gemini(part_prompt, api_key)
        part_json = parse_json(raw_part)
        store["expanded_parts"].append(part_json)

        st.session_state.generating = False

        # 5파트 모두 완료 시 완성
        if len(store["expanded_parts"]) >= 5:
            st.session_state.finished = True
        else:
            # 검토 화면으로 전환
            st.session_state.part_reviewing = True

    except Exception as e:
        import traceback
        err = str(e)
        full_err = traceback.format_exc()
        if "404" in err:
            st.session_state.gemini_error = "404_NOT_FOUND"
        elif "429" in err or "Too Many Requests" in err:
            st.session_state.gemini_error = "429_TOO_MANY"
        elif "503" in err or "Service Unavailable" in err:
            st.session_state.gemini_error = "503_SERVICE_UNAVAILABLE"
        else:
            # 전체 traceback을 에러 메시지에 포함
            st.session_state.gemini_error = f"{err}\n\n[상세]\n{full_err}"
        st.session_state.generating = False


def submit_answer(user_text: str):
    stage = STAGES[st.session_state.current_stage]
    st.session_state.store["inputs"][stage] = {
        "id": stage,
        "stage": stage,
        "stageName": STAGE_NAMES[stage],
        "userText": user_text,
        "timestamp": datetime.datetime.now().isoformat(),
    }
    if st.session_state.current_stage < len(STAGES) - 1:
        st.session_state.current_stage += 1
    else:
        # 마지막 단계 완료 → 작가풍 선택 단계로 이동
        st.session_state.current_stage += 1


# ─────────────────────────────────────────
#  UI 렌더링 함수들
# ─────────────────────────────────────────
def render_header():
    st.markdown('<div class="main-title">✨ 장편 동화 만들기 마법사 ✨</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">뼈대를 만들고 5단계로 스토리를 확장해 드려요! 📖</div>', unsafe_allow_html=True)


def render_setup_phase():
    st.markdown('<div class="setup-box">', unsafe_allow_html=True)
    st.markdown("### ⚙️ 동화의 뼈대 설정하기")
    st.caption("어떤 스타일의 동화를 만들고 싶나요? 먼저 기본 설정을 마쳐주세요.")

    # 1. 대상 연령
    st.markdown("**1. 누구를 위한 동화인가요?** 🎯")
    age_cols = st.columns(2)
    for i, age in enumerate([a for a in TARGET_AGES if a != "직접 입력"]):
        if age_cols[i % 2].button(age, key=f"age_{i}", use_container_width=True):
            st.session_state["sel_target"] = age

    sel_target = st.session_state.get("sel_target", "")
    custom_target = st.text_input(
        "직접 입력 (선택 사항)", max_chars=50,
        key=f"cus_target_{sel_target}",
        value=sel_target,
        placeholder="또는 여기에 직접 입력 (예: 30대 직장인)",
        label_visibility="collapsed",
    )
    final_target = custom_target.strip()

    st.markdown("<hr style='margin:1rem 0; opacity: 0.3;'>", unsafe_allow_html=True)

    # 2. 스토리 구성
    st.markdown("**2. 어떤 이야기 구조를 원하시나요?** 🗺️")
    plot_cols = st.columns(2)
    for i, plot in enumerate(PLOT_TYPES):
        if plot_cols[i % 2].button(plot, key=f"plot_{i}", use_container_width=True):
            st.session_state["sel_plot"] = plot

    sel_plot = st.session_state.get("sel_plot", "")
    custom_plot = st.text_input(
        "직접 입력 (선택 사항)", max_chars=50,
        key=f"cus_plot_{sel_plot}",
        value=sel_plot,
        placeholder="또는 여기에 직접 입력",
        label_visibility="collapsed",
    )
    final_plot = custom_plot.strip()

    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("이야기 재료 고르기 시작! 🚀", type="primary", use_container_width=True):
        if not final_target:
            st.warning("대상 연령을 선택하거나 직접 입력해 주세요!")
            return
        if not final_plot:
            st.warning("이야기 구조를 선택하거나 직접 입력해 주세요!")
            return
        st.session_state.store["settings"] = {
            "target_age": final_target,
            "plot_type": final_plot,
            "author_name": None,
            "author_style_data": {},
        }
        st.session_state.setup_complete = True
        st.rerun()


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
    for s in STAGES:
        d = inputs.get(s)
        if d:
            st.markdown(f"""
            <div style="background:#1e1e2e;border:1px solid #333;border-radius:10px;
                        padding:0.8rem 1rem;margin:0.3rem 0;">
              <span style="font-size:0.75rem;color:#a78bfa;font-weight:bold;">
                {STAGE_ICONS[s]} {s} - {d['stageName']}
              </span><br>
              <span style="color:#e0e0e0;font-size:1rem;">{d['userText']}</span>
            </div>""", unsafe_allow_html=True)


def render_input_area():
    stage = STAGES[st.session_state.current_stage]
    q = STAGE_QUESTIONS[stage]

    st.markdown(f"""
    <div class="ai-box">
      <div class="ai-box-label">🧚 {st.session_state.current_stage + 1} / {len(STAGES)} 단계</div>
      <div class="ai-box-question">{q['question']}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("**선택지를 고르거나 직접 입력하세요:**")
    cols = st.columns(2)
    for i, s in enumerate(q["suggestions"]):
        if cols[i % 2].button(s, key=f"sugg_{stage}_{i}", use_container_width=True):
            st.session_state[f"ta_{stage}"] = s

    user_input = st.text_area(
        "직접 입력",
        max_chars=100,
        height=80,
        key=f"ta_{stage}",
        label_visibility="collapsed",
        placeholder="직접 입력하거나 위 버튼을 눌러주세요",
    )

    val = user_input.strip()

    is_last = st.session_state.current_stage == len(STAGES) - 1
    btn_label = "작가풍 선택하러 가기 ✍️" if is_last else "다음 단계로 →"

    if st.button(btn_label, type="primary", use_container_width=True):
        if not val:
            st.warning("선택지를 고르거나 직접 입력해 주세요!")
        elif is_last and not get_api_key():
            st.error("🔑 Gemini API 키가 없어요! Streamlit Secrets를 확인해 주세요.")
        else:
            submit_answer(val)
            st.rerun()


def render_author_phase():
    st.markdown('<div class="setup-box">', unsafe_allow_html=True)
    st.markdown("### ✍️ 마지막 단계! 작가풍과 분량 선택")
    st.caption("이야기 재료가 모두 모였어요! 책의 분위기와 길이를 정해주세요.")

    author_choice = st.selectbox("1. 작가풍 선택", list(AUTHOR_STYLES.keys()))
    length_choice = st.selectbox("2. 목표 글자 수 (분량)", list(TARGET_LENGTHS.keys()), index=1)

    selected_style = AUTHOR_STYLES[author_choice]
    st.markdown(f"""
    <div class="ai-box">
      <div class="ai-box-label">✍️ 선택된 작가풍 미리보기</div>
      <div class="ai-box-question"><b>어조:</b> {selected_style['tone']}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("✨ 5단계 릴레이 동화 작성 시작!", type="primary", use_container_width=True):
        st.session_state.store["settings"]["author_name"] = author_choice
        st.session_state.store["settings"]["author_style_data"] = AUTHOR_STYLES[author_choice]
        st.session_state.store["settings"]["target_length"] = TARGET_LENGTHS[length_choice]
        st.session_state.author_phase_complete = True
        st.session_state.generating = True
        st.rerun()


def render_generating_screen():
    st.markdown("### 📚 장편 동화 집필소")
    st.caption("AI 작가가 파트를 집필하고 있습니다. 잠시만 기다려주세요!")

    # generating 플래그가 True일 때만 실제 생성 실행
    if st.session_state.generating:
        generate_next_part()

    if st.session_state.gemini_error:
        err = st.session_state.gemini_error
        if err == "429_TOO_MANY":
            st.warning("⏳ 서버 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요!")
        elif err == "503_SERVICE_UNAVAILABLE":
            st.warning("🚦 구글 서버 과부하 상태입니다. 잠시 후 다시 시도해 주세요!")
        elif err == "404_NOT_FOUND":
            st.error("🔍 모델을 찾을 수 없어요. API 키와 결제 계정을 확인해 주세요.")
        else:
            st.error("❌ 오류가 발생했습니다.")
            with st.expander("🔍 에러 상세 보기 (클릭)", expanded=True):
                st.code(err, language="text")
        # 에러 시 rerun 하지 않음 → 화면에 에러 메시지 유지
        if st.button("🔄 다시 시도", type="primary", use_container_width=True):
            st.session_state.gemini_error = None
            st.session_state.generating = True
            st.rerun()
    elif not st.session_state.generating:
        # 정상 완료 시에만 rerun
        st.rerun()


def render_part_review():
    """파트 생성 후 결과 확인 + 다음 파트 지시 입력 화면."""
    store = st.session_state.store
    parts = store.get("expanded_parts", [])
    total_parts = 5
    done = len(parts)
    next_idx = done + 1

    # 진행 상황 바
    st.progress(done / total_parts)
    st.markdown(
        f"<div style='text-align:center;margin-bottom:1rem'>"
        f"<b style='font-size:1.1rem'>✅ 파트 {done} / {total_parts} 완성!</b></div>",
        unsafe_allow_html=True,
    )

    # 지금까지 작성된 파트 모두 표시
    for i, p in enumerate(parts):
        p_title   = p.get("part_title", f"파트 {i + 1}")
        p_content = p.get("content", "").replace("\\n", "\n")
        is_latest = (i == done - 1)
        border_color = "#f093fb" if is_latest else "#667eea"
        label = " <span style='font-size:0.8rem;color:#f093fb'>← 방금 완성</span>" if is_latest else ""
        st.markdown(f"""
        <div style='background:#fcfcfc;border-left:5px solid {border_color};border-radius:10px;
                    padding:1.5rem;margin-bottom:1rem;box-shadow:0 2px 5px rgba(0,0,0,0.05)'>
          <div style='font-family:"Black Han Sans",sans-serif;font-size:1.2rem;
                      margin-bottom:0.8rem;color:#333'>
            🔖 {p_title}{label}
          </div>
          <div style='font-size:1rem;line-height:1.9;color:#2c2c54;white-space:pre-wrap'>{p_content}</div>
        </div>""", unsafe_allow_html=True)

    # 오류 처리
    if st.session_state.gemini_error:
        err = st.session_state.gemini_error
        if err == "429_TOO_MANY":
            st.warning("⏳ 서버 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요!")
        elif err == "503_SERVICE_UNAVAILABLE":
            st.warning("🚦 구글 서버 과부하 상태입니다. 잠시 후 다시 시도해 주세요!")
        else:
            st.error(f"오류: {err}")
        if st.button("🔄 이 파트 다시 생성", type="primary", use_container_width=True):
            # 마지막 파트 제거 후 재생성
            store["expanded_parts"] = parts[:-1] if parts else []
            st.session_state.gemini_error = None
            st.session_state.generating = True
            st.session_state.part_reviewing = False
            st.rerun()
        return

    # 다음 파트 지시 입력
    st.markdown("---")
    st.markdown(f"### 💬 파트 {next_idx} 지시하기")
    st.caption(
        f"방금 완성된 파트 {done}을 읽고, 수정 사항이나 파트 {next_idx}의 방향을 자유롭게 적어주세요. "
        "비워두면 AI가 자동으로 이어 씁니다."
    )

    direction = st.text_area(
        "지시 입력",
        height=120,
        key=f"direction_part_{next_idx}",
        label_visibility="collapsed",
        placeholder=(
            f"예) 3파트에서 주인공이 너무 빨리 위기를 극복했어. 좀 더 힘들게 해줘. "
            f"그리고 {next_idx}파트는 친구와의 갈등을 중심으로 써줘."
        ),
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"✨ 파트 {next_idx} 작성 시작!", type="primary", use_container_width=True):
            # 지시사항 저장
            if "part_directions" not in store:
                store["part_directions"] = {}
            store["part_directions"][str(next_idx)] = direction.strip()
            st.session_state.part_reviewing = False
            st.session_state.generating = True
            st.rerun()
    with col2:
        if st.button("⏭️ 지시 없이 바로 진행", use_container_width=True):
            if "part_directions" not in store:
                store["part_directions"] = {}
            store["part_directions"][str(next_idx)] = ""
            st.session_state.part_reviewing = False
            st.session_state.generating = True
            st.rerun()


def render_final_book():
    if st.session_state.gemini_error:
        err = st.session_state.gemini_error
        if err == "429_TOO_MANY":
            st.warning("⏳ 서버에 요청이 너무 많습니다. 1분 후 이어쓰기를 눌러주세요!")
        elif err == "503_SERVICE_UNAVAILABLE":
            st.warning("🚦 구글 서버 과부하 상태입니다. 잠시 후 이어쓰기를 눌러주세요!")
        elif err == "404_NOT_FOUND":
            st.error("🔍 모델을 찾을 수 없어요. API 키와 결제 계정을 확인해 주세요.")
        else:
            with st.expander("⚠️ 오류 상세 보기", expanded=False):
                st.code(err)

        if st.button("🔄 끊긴 파트부터 이어쓰기", type="primary", use_container_width=True):
            st.session_state.gemini_error = None
            st.session_state.generating = True
            st.rerun()
        return

    outline = st.session_state.store.get("outline") or {}
    parts   = st.session_state.store.get("expanded_parts", [])
    title   = outline.get("title", "우리가 만든 동화")

    st.markdown(f"""
    <div style='text-align:center;padding:1.5rem 0'>
      <div style='font-size:3rem'>🎉</div>
      <div style='font-family:"Black Han Sans",sans-serif;font-size:1.8rem;
                  background:linear-gradient(135deg,#f093fb,#667eea);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent'>
        완성된 장편 동화책!
      </div>
      <div style='font-size:1.4rem;color:#333;margin-top:0.5rem'>📖 {title}</div>
    </div>""", unsafe_allow_html=True)

    total_chars = 0
    full_text_export = f"📖 {title}\n\n"

    for i, p in enumerate(parts):
        p_title   = p.get("part_title", f"파트 {i + 1}")
        p_content = p.get("content", "").replace("\\n", "\n")
        total_chars += len(p_content)
        full_text_export += f"[{p_title}]\n{p_content}\n\n"

        st.markdown(f"""
        <div class="chapter-box">
          <div class="chapter-title">🔖 {p_title}</div>
          <div class="chapter-text">{p_content}</div>
        </div>""", unsafe_allow_html=True)

    st.caption(f"📝 최종 작성된 총 글자 수: {total_chars:,}자")
    st.balloons()

    full_text_export += f"\n총 {total_chars:,}자"

    # SNS 업로드
    st.markdown("---")
    render_upload_button(st.session_state.store)
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 텍스트로 저장", full_text_export, file_name=f"{title}.txt", use_container_width=True)
    with col2:
        if st.button("🔄 새 이야기 만들기", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def render_sidebar():
    with st.sidebar:
        if st.session_state.get("setup_complete"):
            s = st.session_state.store.get("settings", {})
            st.markdown("### ⚙️ 설정 내역")
            st.markdown(f"**🎯 타겟:** {s.get('target_age')}")
            st.markdown(f"**🗺️ 구조:** {s.get('plot_type')}")
            author = s.get("author_name")
            if author:
                st.markdown(f"**✍️ 작가풍:** {author}")
                st.markdown(f"**📏 목표 분량:** {s.get('target_length', 0):,}자")
            else:
                st.markdown("**✍️ 작가풍:** 스토리 완성 후 선택")
            st.markdown("---")

        inputs = st.session_state.store.get("inputs", {})
        if inputs:
            st.markdown("### 📋 수집된 재료")
            for s in STAGES:
                d = inputs.get(s)
                if d:
                    st.markdown(
                        f"**{STAGE_ICONS[s]} {s} - {d['stageName']}**\n\n"
                        f"<span style='color:#555;font-size:0.9rem'>{d['userText']}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown("<hr style='margin:0.5rem 0;opacity:0.2'>", unsafe_allow_html=True)

        # 파트 진행 현황
        parts = st.session_state.store.get("expanded_parts", [])
        if parts:
            st.markdown("### 📖 파트 진행 현황")
            for i, p in enumerate(parts):
                st.markdown(f"✅ **파트 {i+1}**: {p.get('part_title', '')}")
            remaining = 5 - len(parts)
            if remaining > 0:
                st.markdown(f"⏳ 남은 파트: {remaining}개")

        render_draft_controls()


# ─────────────────────────────────────────
#  메인
# ─────────────────────────────────────────
def main():
    init_store()
    render_header()

    # 로그인 상태 표시 (우상단)
    render_auth()

    # 메인 탭
    tab_make, tab_feed = st.tabs(["✨ 동화 만들기", "📚 동화 피드"])

    with tab_make:
        render_sidebar()
        if not st.session_state.setup_complete:
            render_setup_phase()
        elif st.session_state.finished:
            render_final_book()
        elif st.session_state.generating:
            render_generating_screen()
        elif st.session_state.part_reviewing:
            render_part_review()
        elif st.session_state.current_stage >= len(STAGES) and not st.session_state.author_phase_complete:
            render_author_phase()
        elif st.session_state.current_stage < len(STAGES):
            render_progress()
            render_collected_inputs()
            render_input_area()

    with tab_feed:
        render_feed()

    if not st.session_state.generating:
        render_floating_cat()


if __name__ == "__main__":
    main()
