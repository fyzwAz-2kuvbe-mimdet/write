# -*- coding: utf-8 -*-
"""
auth.py
Firebase Authentication - 이메일/비밀번호 로그인, 회원가입
Firebase Auth REST API 직접 호출 방식 (firebase-admin 불필요)
"""
import requests
import streamlit as st
from db import get_user, create_user


def get_api_key() -> str:
    return st.secrets.get("FIREBASE_WEB_API_KEY", "")


SIGN_UP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signUp"
SIGN_IN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"


# ─────────────────────────────────────────
#  회원가입
# ─────────────────────────────────────────
def sign_up(email: str, password: str, nickname: str) -> dict:
    resp = requests.post(SIGN_UP_URL, json={
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }, params={"key": get_api_key()})
    data = resp.json()
    if "error" in data:
        raise Exception(data["error"]["message"])
    uid = data["localId"]
    create_user(uid, nickname, email)
    return {"uid": uid, "email": email, "nickname": nickname}


# ─────────────────────────────────────────
#  로그인
# ─────────────────────────────────────────
def sign_in(email: str, password: str) -> dict:
    resp = requests.post(SIGN_IN_URL, json={
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }, params={"key": get_api_key()})
    data = resp.json()
    if "error" in data:
        raise Exception(data["error"]["message"])
    uid = data["localId"]
    user = get_user(uid)
    if not user:
        create_user(uid, email.split("@")[0], email)
        user = get_user(uid)
    return user


# ─────────────────────────────────────────
#  UI
# ─────────────────────────────────────────
def render_auth():
    """로그인/회원가입 UI. 로그인 성공 시 session_state.user 에 저장"""
    if st.session_state.get("user"):
        user = st.session_state.user
        st.markdown(
            f"<div style='text-align:right;color:#a78bfa;font-size:0.85rem'>"
            f"✍️ {user['nickname']} 님</div>",
            unsafe_allow_html=True
        )
        if st.button("로그아웃", key="logout_btn"):
            st.session_state.user = None
            st.rerun()
        return

    tab_in, tab_up = st.tabs(["🔐 로그인", "📝 회원가입"])

    with tab_in:
        email = st.text_input("이메일", key="login_email")
        pw    = st.text_input("비밀번호", type="password", key="login_pw")
        if st.button("로그인", type="primary", use_container_width=True, key="login_btn"):
            if not email or not pw:
                st.warning("이메일과 비밀번호를 입력해주세요.")
            else:
                try:
                    user = sign_in(email, pw)
                    st.session_state.user = user
                    st.success(f"환영해요, {user['nickname']} 님!")
                    st.rerun()
                except Exception as e:
                    err = str(e)
                    if "EMAIL_NOT_FOUND" in err or "INVALID_PASSWORD" in err:
                        st.error("이메일 또는 비밀번호가 틀렸어요.")
                    elif "INVALID_LOGIN_CREDENTIALS" in err:
                        st.error("이메일 또는 비밀번호가 틀렸어요.")
                    else:
                        st.error(f"로그인 실패: {err}")

    with tab_up:
        nickname = st.text_input("닉네임 (작가명)", key="signup_nick")
        email2   = st.text_input("이메일", key="signup_email")
        pw2      = st.text_input("비밀번호 (6자 이상)", type="password", key="signup_pw")
        if st.button("회원가입", type="primary", use_container_width=True, key="signup_btn"):
            if not nickname or not email2 or not pw2:
                st.warning("모든 항목을 입력해주세요.")
            elif len(pw2) < 6:
                st.warning("비밀번호는 6자 이상이어야 해요.")
            else:
                try:
                    user = sign_up(email2, pw2, nickname)
                    st.session_state.user = user
                    st.success(f"가입 완료! 환영해요, {nickname} 님!")
                    st.rerun()
                except Exception as e:
                    err = str(e)
                    if "EMAIL_EXISTS" in err:
                        st.error("이미 사용 중인 이메일이에요.")
                    else:
                        st.error(f"회원가입 실패: {err}")
