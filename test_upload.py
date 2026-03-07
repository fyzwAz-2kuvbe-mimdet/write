# -*- coding: utf-8 -*-
"""
test_upload.py
Firebase 업로드 기능 테스트 - Gemini API 호출 없이 더미 데이터로 테스트
실행: streamlit run test_upload.py
"""
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="업로드 테스트", page_icon="🧪", layout="centered")
st.title("🧪 Firebase 업로드 테스트")

# ─────────────────────────────────────────
# 더미 동화 데이터
# ─────────────────────────────────────────
DUMMY_STORE = {
    "settings": {
        "target_age": "7~9세",
        "plot_type": "성장과 모험",
        "author_name": "이솝 (이솝우화)",
        "author_style_data": {"role": "우화 작가", "style": "이솝", "tone": "교훈적", "constraints": {}},
        "target_length": 3000,
    },
    "inputs": {
        "기": {"userText": "토끼 소녀 달이"},
        "승": {"userText": "보물 지도를 발견했어요"},
        "전": {"userText": "길을 잃어버렸어요"},
        "결": {"userText": "친구의 도움으로 성공했어요"},
    },
    "outline": {
        "title": "달이의 보물찾기 [테스트]",
        "story": {
            "기": "토끼 소녀 달이가 숲에서 살았어요.",
            "승": "어느 날 보물 지도를 발견했어요.",
            "전": "깊은 숲에서 길을 잃고 말았어요.",
            "결": "다람쥐 친구의 도움으로 집에 돌아왔어요.",
        },
    },
    "expanded_parts": [
        {
            "part_title": "1장. 숲속의 아침",
            "content": "토끼 소녀 달이는 매일 아침 숲속을 산책했어요. 하얀 털과 긴 귀가 특징인 달이는 호기심이 많은 아이였어요. 오늘도 어김없이 숲을 걷던 달이는 땅에 떨어진 낡은 종이 한 장을 발견했어요.",
        },
        {
            "part_title": "2장. 보물 지도",
            "content": "종이를 펼쳐보니 보물 지도였어요! 달이의 눈이 반짝였어요. 지도에는 커다란 나무 옆에 X 표시가 되어 있었어요. 달이는 가슴이 두근거리며 모험을 시작했어요.",
        },
        {
            "part_title": "3장. 길을 잃다",
            "content": "깊은 숲속으로 들어갈수록 길이 복잡해졌어요. 결국 달이는 길을 잃고 말았어요. 사방이 어두워지고 무서운 소리가 들려왔어요. 달이는 눈물이 날 것 같았어요.",
        },
        {
            "part_title": "4장. 친구의 도움",
            "content": "그때 다람쥐 친구 도토리가 나타났어요. 달이가 걱정되어 뒤따라온 것이었어요. 두 친구는 함께 지도를 다시 살펴보았어요. 협력하면 못할 일이 없다는 것을 깨달았어요.",
        },
        {
            "part_title": "5장. 진짜 보물",
            "content": "마침내 X 표시가 있는 곳에 도착했어요. 하지만 보물 상자 안에는 금은보화 대신 작은 편지가 있었어요. 편지에는 이렇게 쓰여 있었어요. 진짜 보물은 함께하는 친구라고 말했어요. 달이와 도토리는 환하게 웃었어요.",
        },
    ],
}

# ─────────────────────────────────────────
# 로그인 섹션
# ─────────────────────────────────────────
st.markdown("### 1단계: 로그인")

try:
    from auth import render_auth
    render_auth()
except Exception as e:
    st.error(f"auth 모듈 오류: {e}")
    st.stop()

user = st.session_state.get("user")
if not user:
    st.info("로그인 후 업로드 테스트를 진행할 수 있어요.")
    st.stop()

st.success(f"✅ 로그인됨: {user['nickname']}")

# ─────────────────────────────────────────
# 더미 데이터 확인
# ─────────────────────────────────────────
st.markdown("---")
st.markdown("### 2단계: 테스트 동화 데이터 확인")
with st.expander("더미 동화 내용 보기"):
    st.json(DUMMY_STORE["outline"])
    for p in DUMMY_STORE["expanded_parts"]:
        st.markdown(f"**{p['part_title']}**")
        st.caption(p["content"])

# ─────────────────────────────────────────
# 업로드 테스트
# ─────────────────────────────────────────
st.markdown("---")
st.markdown("### 3단계: Firebase 업로드 테스트")

if st.session_state.get("test_uploaded"):
    st.success(f"✅ 업로드 성공! SID: {st.session_state.get('test_sid')}")
    if st.button("다시 테스트"):
        st.session_state.test_uploaded = False
        st.rerun()
else:
    if st.button("🚀 더미 동화 업로드 테스트", type="primary", use_container_width=True):
        try:
            from db import upload_story
            sid = upload_story(
                uid=user["uid"],
                nickname=user["nickname"],
                title=DUMMY_STORE["outline"]["title"],
                parts=DUMMY_STORE["expanded_parts"],
                settings=DUMMY_STORE["settings"],
            )
            st.session_state.test_uploaded = True
            st.session_state.test_sid = sid
            st.success(f"✅ 업로드 성공! SID: {sid}")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 업로드 실패: {e}")

# ─────────────────────────────────────────
# 피드 조회 테스트
# ─────────────────────────────────────────
st.markdown("---")
st.markdown("### 4단계: 피드 조회 테스트")
if st.button("📚 피드 불러오기"):
    try:
        from db import get_feed
        stories = get_feed(limit=5)
        st.success(f"✅ 피드 조회 성공! {len(stories)}개 동화")
        for s in stories:
            st.markdown(f"- **{s.get('title')}** by {s.get('nickname')} (좋아요: {s.get('like_count', 0)})")
    except Exception as e:
        st.error(f"❌ 피드 조회 실패: {e}")
