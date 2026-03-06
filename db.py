# -*- coding: utf-8 -*-
"""
db.py
Firebase Firestore 연동 - 유저, 동화, 좋아요, 댓글, 구독
"""
import streamlit as st
import datetime

# ─────────────────────────────────────────
#  Firebase 초기화 (Streamlit Secrets 사용)
# ─────────────────────────────────────────
def get_db():
    """Firestore 클라이언트 반환 (캐싱)"""
    import firebase_admin
    from firebase_admin import credentials, firestore

    if "firebase_app" not in st.session_state:
        if not firebase_admin._apps:
            cred_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        st.session_state["firebase_app"] = True

    return firestore.client()


# ─────────────────────────────────────────
#  유저
# ─────────────────────────────────────────
def get_user(uid: str) -> dict | None:
    db = get_db()
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def create_user(uid: str, nickname: str, email: str):
    db = get_db()
    db.collection("users").document(uid).set({
        "uid": uid,
        "nickname": nickname,
        "email": email,
        "bio": "",
        "created_at": datetime.datetime.now().isoformat(),
        "story_count": 0,
        "follower_count": 0,
        "following_count": 0,
    })


def update_user_bio(uid: str, bio: str):
    get_db().collection("users").document(uid).update({"bio": bio})


# ─────────────────────────────────────────
#  동화 업로드 / 조회
# ─────────────────────────────────────────
def upload_story(uid: str, nickname: str, title: str, parts: list, settings: dict) -> str:
    """완성된 동화를 Firestore에 저장하고 doc id 반환"""
    db = get_db()
    full_text = "\n\n".join([p.get("content", "") for p in parts])
    preview = full_text[:120] + "..." if len(full_text) > 120 else full_text

    doc_ref = db.collection("stories").document()
    doc_ref.set({
        "sid": doc_ref.id,
        "uid": uid,
        "nickname": nickname,
        "title": title,
        "parts": parts,
        "preview": preview,
        "settings": settings,
        "like_count": 0,
        "comment_count": 0,
        "created_at": datetime.datetime.now().isoformat(),
    })
    # 유저 story_count 증가
    db.collection("users").document(uid).update({
        "story_count": firestore_increment(1)
    })
    return doc_ref.id


def get_feed(limit: int = 20) -> list:
    """최신순 동화 피드"""
    db = get_db()
    docs = (db.collection("stories")
              .order_by("created_at", direction="DESCENDING")
              .limit(limit)
              .stream())
    return [d.to_dict() for d in docs]


def get_user_stories(uid: str) -> list:
    """특정 유저의 동화 목록"""
    db = get_db()
    docs = (db.collection("stories")
              .where("uid", "==", uid)
              .order_by("created_at", direction="DESCENDING")
              .stream())
    return [d.to_dict() for d in docs]


def get_story(sid: str) -> dict | None:
    db = get_db()
    doc = db.collection("stories").document(sid).get()
    return doc.to_dict() if doc.exists else None


# ─────────────────────────────────────────
#  좋아요
# ─────────────────────────────────────────
def toggle_like(uid: str, sid: str) -> bool:
    """좋아요 토글. True=좋아요 추가, False=취소"""
    db = get_db()
    like_ref = db.collection("likes").document(f"{uid}_{sid}")
    story_ref = db.collection("stories").document(sid)

    if like_ref.get().exists:
        like_ref.delete()
        story_ref.update({"like_count": firestore_increment(-1)})
        return False
    else:
        like_ref.set({"uid": uid, "sid": sid,
                      "created_at": datetime.datetime.now().isoformat()})
        story_ref.update({"like_count": firestore_increment(1)})
        return True


def is_liked(uid: str, sid: str) -> bool:
    db = get_db()
    return db.collection("likes").document(f"{uid}_{sid}").get().exists


# ─────────────────────────────────────────
#  댓글
# ─────────────────────────────────────────
def add_comment(uid: str, nickname: str, sid: str, text: str):
    db = get_db()
    db.collection("comments").add({
        "uid": uid,
        "nickname": nickname,
        "sid": sid,
        "text": text,
        "created_at": datetime.datetime.now().isoformat(),
    })
    db.collection("stories").document(sid).update({
        "comment_count": firestore_increment(1)
    })


def get_comments(sid: str) -> list:
    db = get_db()
    docs = (db.collection("comments")
              .where("sid", "==", sid)
              .order_by("created_at")
              .stream())
    return [d.to_dict() for d in docs]


# ─────────────────────────────────────────
#  구독/팔로우
# ─────────────────────────────────────────
def toggle_follow(follower_uid: str, target_uid: str) -> bool:
    """팔로우 토글. True=팔로우, False=언팔"""
    db = get_db()
    follow_ref = db.collection("follows").document(f"{follower_uid}_{target_uid}")

    if follow_ref.get().exists:
        follow_ref.delete()
        db.collection("users").document(follower_uid).update(
            {"following_count": firestore_increment(-1)})
        db.collection("users").document(target_uid).update(
            {"follower_count": firestore_increment(-1)})
        return False
    else:
        follow_ref.set({
            "follower_uid": follower_uid,
            "target_uid": target_uid,
            "created_at": datetime.datetime.now().isoformat(),
        })
        db.collection("users").document(follower_uid).update(
            {"following_count": firestore_increment(1)})
        db.collection("users").document(target_uid).update(
            {"follower_count": firestore_increment(1)})
        return True


def is_following(follower_uid: str, target_uid: str) -> bool:
    db = get_db()
    return db.collection("follows").document(
        f"{follower_uid}_{target_uid}").get().exists


# ─────────────────────────────────────────
#  Firestore increment 헬퍼
# ─────────────────────────────────────────
def firestore_increment(n: int):
    from google.cloud.firestore_v1 import transforms
    return transforms.INCREMENT(n)
