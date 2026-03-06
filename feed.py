# -*- coding: utf-8 -*-
"""
feed.py
SNS 피드 UI - 동화 목록, 상세보기, 좋아요, 댓글, 팔로우
"""
import streamlit as st
from db import (
    get_feed, get_story, get_user, get_user_stories,
    get_comments, add_comment,
    toggle_like, is_liked,
    toggle_follow, is_following,
    upload_story,
)


# ─────────────────────────────────────────
#  피드 메인
# ─────────────────────────────────────────
def render_feed():
    user = st.session_state.get("user")

    # 상단: 내 프로필 / 피드 탭
    if user:
        feed_tab, profile_tab = st.tabs(["📚 전체 피드", "👤 내 프로필"])
        with feed_tab:
            render_story_list(user)
        with profile_tab:
            render_my_profile(user)
    else:
        st.info("💡 로그인하면 동화를 업로드하고 좋아요, 댓글을 남길 수 있어요!")
        render_story_list(None)


# ─────────────────────────────────────────
#  동화 목록
# ─────────────────────────────────────────
def render_story_list(user):
    # 동화 상세 보기 상태
    if st.session_state.get("viewing_sid"):
        render_story_detail(st.session_state.viewing_sid, user)
        if st.button("← 목록으로", key="back_to_feed"):
            st.session_state.viewing_sid = None
            st.rerun()
        return

    st.markdown("### 📖 동화 피드")
    try:
        stories = get_feed(limit=20)
    except Exception as e:
        st.error(f"피드를 불러오지 못했어요: {e}")
        return

    if not stories:
        st.caption("아직 업로드된 동화가 없어요. 첫 번째 작가가 되어보세요!")
        return

    for story in stories:
        render_story_card(story, user)
        st.markdown("<hr style='margin:0.5rem 0;opacity:0.15'>", unsafe_allow_html=True)


# ─────────────────────────────────────────
#  동화 카드 (목록용)
# ─────────────────────────────────────────
def render_story_card(story: dict, user):
    sid      = story.get("sid", "")
    title    = story.get("title", "제목 없음")
    nickname = story.get("nickname", "익명")
    preview  = story.get("preview", "")
    likes    = story.get("like_count", 0)
    comments = story.get("comment_count", 0)
    created  = story.get("created_at", "")[:10]
    uid      = story.get("uid", "")

    liked = is_liked(user["uid"], sid) if user else False
    heart = "❤️" if liked else "🤍"

    st.markdown(f"""
    <div style='background:#1a1a2e;border:1px solid #2a2a3e;border-radius:12px;
                padding:1rem 1.2rem;margin:0.5rem 0'>
      <div style='font-size:0.8rem;color:#a78bfa;margin-bottom:0.3rem'>
        ✍️ {nickname} &nbsp;·&nbsp; {created}
      </div>
      <div style='font-size:1.15rem;font-weight:bold;color:#f0f0f0;margin-bottom:0.4rem'>
        📖 {title}
      </div>
      <div style='font-size:0.9rem;color:#aaa;line-height:1.6'>{preview}</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
    with col1:
        if st.button(f"{heart} {likes}", key=f"like_{sid}"):
            if not user:
                st.warning("로그인이 필요해요!")
            else:
                toggle_like(user["uid"], sid)
                st.rerun()
    with col2:
        if st.button(f"💬 {comments}", key=f"comment_btn_{sid}"):
            st.session_state.viewing_sid = sid
            st.rerun()
    with col3:
        if st.button("📖 읽기", key=f"read_{sid}"):
            st.session_state.viewing_sid = sid
            st.rerun()
    with col4:
        if user and user.get("uid") != uid:
            following = is_following(user["uid"], uid)
            label = "✅ 팔로잉" if following else "➕ 팔로우"
            if st.button(label, key=f"follow_{sid}_{uid}"):
                toggle_follow(user["uid"], uid)
                st.rerun()


# ─────────────────────────────────────────
#  동화 상세 보기
# ─────────────────────────────────────────
def render_story_detail(sid: str, user):
    story = get_story(sid)
    if not story:
        st.error("동화를 찾을 수 없어요.")
        return

    title    = story.get("title", "제목 없음")
    nickname = story.get("nickname", "익명")
    parts    = story.get("parts", [])
    likes    = story.get("like_count", 0)
    uid      = story.get("uid", "")
    created  = story.get("created_at", "")[:10]

    # 작가 정보
    author = get_user(uid) or {}
    followers = author.get("follower_count", 0)

    st.markdown(f"""
    <div style='text-align:center;padding:1.5rem 0 0.5rem'>
      <div style='font-size:1.8rem;font-weight:bold;color:#f0f0f0'>📖 {title}</div>
      <div style='color:#a78bfa;margin-top:0.3rem'>✍️ {nickname} · {created}</div>
    </div>
    """, unsafe_allow_html=True)

    # 팔로우 + 좋아요 버튼
    col1, col2 = st.columns(2)
    with col1:
        if user and user.get("uid") != uid:
            following = is_following(user["uid"], uid)
            label = f"✅ 팔로잉 ({followers})" if following else f"➕ 팔로우 ({followers})"
            if st.button(label, use_container_width=True, key=f"follow_detail_{uid}"):
                toggle_follow(user["uid"], uid)
                st.rerun()
    with col2:
        liked = is_liked(user["uid"], sid) if user else False
        heart = "❤️" if liked else "🤍"
        if st.button(f"{heart} 좋아요 {likes}", use_container_width=True, key=f"like_detail_{sid}"):
            if not user:
                st.warning("로그인이 필요해요!")
            else:
                toggle_like(user["uid"], sid)
                st.rerun()

    st.markdown("---")

    # 본문
    for p in parts:
        p_title   = p.get("part_title", "")
        p_content = p.get("content", "").replace("\\n", "\n")
        st.markdown(f"""
        <div style='background:#1a1a1a;border-left:4px solid #7c3aed;border-radius:10px;
                    padding:1.2rem 1.5rem;margin-bottom:1rem'>
          <div style='font-size:1.1rem;font-weight:bold;color:#a78bfa;margin-bottom:0.6rem'>
            🔖 {p_title}
          </div>
          <div style='font-size:1rem;line-height:1.9;color:#d0d0d0;white-space:pre-wrap'>
            {p_content}
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 댓글
    st.markdown("### 💬 댓글")
    comments = get_comments(sid)
    for c in comments:
        st.markdown(
            f"<div style='background:#1e1e2e;border-radius:8px;padding:0.6rem 1rem;margin:0.3rem 0'>"
            f"<span style='color:#a78bfa;font-size:0.85rem'>✍️ {c.get('nickname','익명')}</span>"
            f"<br><span style='color:#e0e0e0'>{c.get('text','')}</span></div>",
            unsafe_allow_html=True
        )

    if user:
        comment_text = st.text_input("댓글 입력", key=f"comment_input_{sid}",
                                     placeholder="따뜻한 댓글을 남겨주세요 💬",
                                     label_visibility="collapsed")
        if st.button("댓글 등록", key=f"comment_submit_{sid}"):
            if comment_text.strip():
                add_comment(user["uid"], user["nickname"], sid, comment_text.strip())
                st.rerun()
    else:
        st.caption("댓글을 남기려면 로그인해주세요.")


# ─────────────────────────────────────────
#  내 프로필
# ─────────────────────────────────────────
def render_my_profile(user):
    uid      = user.get("uid", "")
    nickname = user.get("nickname", "")
    profile  = get_user(uid) or {}

    col1, col2, col3 = st.columns(3)
    col1.metric("📖 동화", profile.get("story_count", 0))
    col2.metric("👥 팔로워", profile.get("follower_count", 0))
    col3.metric("➕ 팔로잉", profile.get("following_count", 0))

    st.markdown(f"### ✍️ {nickname}")
    bio = st.text_area("자기소개", value=profile.get("bio", ""),
                       key="bio_input", placeholder="작가 소개를 입력해주세요",
                       height=80)
    if st.button("저장", key="bio_save"):
        from db import update_user_bio
        update_user_bio(uid, bio)
        st.success("저장됐어요!")

    st.markdown("---")
    st.markdown("### 📚 내가 쓴 동화")
    try:
        my_stories = get_user_stories(uid)
    except Exception as e:
        st.error(f"동화 목록을 불러오지 못했어요: {e}")
        return

    if not my_stories:
        st.caption("아직 작성한 동화가 없어요. 동화 만들기 탭에서 첫 작품을 완성해보세요!")
        return

    for story in my_stories:
        render_story_card(story, user)


# ─────────────────────────────────────────
#  동화 업로드 버튼 (render_final_book에서 호출)
# ─────────────────────────────────────────
def render_upload_button(store: dict):
    user = st.session_state.get("user")
    if not user:
        st.info("💡 동화를 SNS에 공유하려면 로그인해주세요!")
        return

    outline  = store.get("outline") or {}
    parts    = store.get("expanded_parts", [])
    settings = store.get("settings", {})
    title    = outline.get("title", "우리가 만든 동화")

    if st.session_state.get("story_uploaded"):
        st.success("✅ 이미 업로드된 동화예요!")
        return

    if st.button("🌐 SNS에 공개하기", type="primary", use_container_width=True):
        try:
            sid = upload_story(
                uid=user["uid"],
                nickname=user["nickname"],
                title=title,
                parts=parts,
                settings=settings,
            )
            st.session_state.story_uploaded = True
            st.success(f"🎉 '{title}' 이(가) 피드에 공개됐어요!")
            st.rerun()
        except Exception as e:
            st.error(f"업로드 실패: {e}")
