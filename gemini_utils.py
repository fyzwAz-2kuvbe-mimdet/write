"""
gemini_utils.py
Gemini API 호출 - requests + v1beta 직접 호출 방식
(타겟 연령, 스토리 구조, 작가풍 설정 적용 버전)
"""
import re
import json
import time
import requests


MAX_TOKENS = 8192


def call_gemini(prompt: str, api_key: str, max_retries: int = 5) -> str:
    MODEL_NAME = "gemini-2.5-flash"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL_NAME}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": MAX_TOKENS,
            "responseMimeType": "application/json",
        },
    }

    wait = 15
    for attempt in range(max_retries):
        response = requests.post(url, json=payload, timeout=90)
        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        elif response.status_code == 404:
            raise Exception("404_NOT_FOUND")
        elif response.status_code == 429:
            if attempt < max_retries - 1:
                time.sleep(wait)
                wait *= 2
                continue
            raise Exception("429_TOO_MANY")
        elif response.status_code == 503:
            if attempt < max_retries - 1:
                time.sleep(wait)
                wait *= 2
                continue
            raise Exception("503_SERVICE_UNAVAILABLE")
        else:
            raise Exception(f"API 에러 ({response.status_code}): {response.text}")


# ─────────────────────────────────────────
#  JSON 파싱 (다단계 방어 로직)
# ─────────────────────────────────────────
def _sanitize_json_string(raw: str) -> str:
    """마크다운 펜스, BOM, 불필요한 앞뒤 텍스트 제거."""
    # BOM 제거
    raw = raw.lstrip("\ufeff")
    # ```json ... ``` 또는 ``` ... ``` 블록 추출 시도
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        return fence.group(1).strip()
    # 마크다운 펜스 태그만 제거
    raw = re.sub(r"```(?:json)?", "", raw).replace("```", "")
    return raw.strip()


def _extract_outermost_json(text: str) -> str:
    """텍스트에서 가장 바깥쪽 { } 블록만 잘라냄."""
    start = text.find("{")
    if start == -1:
        raise ValueError("중괄호를 찾을 수 없습니다.")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("JSON 중괄호가 닫히지 않았습니다.")


def _fix_inner_newlines(text: str) -> str:
    """JSON 문자열 값 안의 raw 줄바꿈을 \\n으로 이스케이프 (JSON 파싱 오류 방지)."""
    # 문자열 값 안의 제어문자 정리
    # json.loads가 실패할 경우를 위한 보조 처리
    return re.sub(
        r'("(?:[^"\\]|\\.)*")',
        lambda m: m.group(0).replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"),
        text,
    )


def parse_json(raw: str) -> dict:
    """
    Gemini 응답 → dict 파싱. 4단계 방어:
    1) 직접 파싱
    2) 마크다운 펜스 제거 후 파싱
    3) 가장 바깥 { } 추출 후 파싱
    4) 내부 줄바꿈 이스케이프 교정 후 파싱
    """
    # 단계 1: 그대로 시도
    try:
        return json.loads(raw)
    except Exception:
        pass

    # 단계 2: 마크다운·BOM 제거
    cleaned = _sanitize_json_string(raw)
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 단계 3: 가장 바깥 { } 블록 추출
    try:
        extracted = _extract_outermost_json(cleaned if cleaned else raw)
        return json.loads(extracted)
    except Exception:
        pass

    # 단계 4: 내부 줄바꿈 이스케이프 교정
    try:
        extracted = _extract_outermost_json(cleaned if cleaned else raw)
        fixed = _fix_inner_newlines(extracted)
        return json.loads(fixed)
    except Exception as e:
        preview = raw[:600].replace("<", "&lt;")
        raise ValueError(
            f"JSON 파싱 최종 실패: {e}\n\n"
            f"[Gemini 원본 응답 일부]\n{preview}"
        )


# ─────────────────────────────────────────
#  프롬프트 생성 (설정값 반영 및 묘사 강화)
# ─────────────────────────────────────────
def build_final_prompt(story_store: dict) -> str:
    """수집된 기승전결 데이터와 설정값을 하나의 프롬프트로 조합."""
    inputs = story_store.get("inputs", {})
    settings = story_store.get("settings", {})

    # 1. 설정값 추출
    target_age = settings.get("target_age", "전 연령대")
    plot_type = settings.get("plot_type", "일반적인 동화 전개")
    author_data = settings.get("author_style_data", {})
    
    # 2. 작가풍 상세 데이터 추출
    author_role = author_data.get("role", "상상력이 풍부한 어린이 동화 작가")
    author_style = author_data.get("style", "따뜻하고 상상력 넘치는 스타일")
    author_tone = author_data.get("tone", "친근하고 다정한")
    author_constraints = author_data.get("constraints", {})
    
    # 제약사항을 문자열로 예쁘게 풀어서 포매팅
    constraints_str = ""
    if author_constraints:
        for k, v in author_constraints.items():
            if isinstance(v, list):
                constraints_str += f"   - {k}: {', '.join(v)}\n"
            else:
                constraints_str += f"   - {k}: {v}\n"

    # 3. 사용자 입력 재료 추출
    gi    = inputs.get("기", {}).get("userText", "")
    seung = inputs.get("승", {}).get("userText", "")
    jeon  = inputs.get("전", {}).get("userText", "")
    gyeol = inputs.get("결", {}).get("userText", "")

    total_length = "500자 내외"
    part_length  = "100~120자"

    # 4. 최종 프롬프트 조립
    prompt = f"""당신은 {author_role}입니다. 
아래 제공된 기본 설정과 이야기 재료를 바탕으로 완성된 하나의 이야기를 창작해 주세요.

=== 기본 설정 ===
- 타겟 독자층: {target_age}
- 스토리 구성 방식: {plot_type}
- 작가 스타일: {author_style}
- 어조(Tone): {author_tone}
- 스타일 제약사항:
{constraints_str if constraints_str else "   - 특별한 제약사항 없음"}

=== 선택된 이야기 재료 ===
[기 - 시작]: {gi}
[승 - 전개]: {seung}
[전 - 위기]: {jeon}
[결 - 마무리]: {gyeol}

=== 가장 중요한 작성 규칙 ===
1. 타겟 독자층({target_age})이 이해하고 공감하기 쉬운 어휘와 문장 수준을 사용하세요.
2. 지정된 스토리 구성 방식({plot_type})의 특징이 잘 드러나도록 기승전결을 전개하세요.
3. 지정된 작가 스타일({author_style})과 어조({author_tone}), 제약사항을 철저히 반영하여 문장과 묘사를 구성하세요.
4. 이야기 내용 안에 큰따옴표나 작은따옴표, 줄바꿈을 절대 사용하지 마세요. 대화는 ~라고 말했어요 처럼 풀어쓰세요.
5. 전체 글자 수는 {total_length}로, 각 단계별로 {part_length} 분량의 풍부한 스토리를 적어주세요.

반드시 아래 규칙을 지켜 순수한 JSON만 응답하세요. 설명, 주석, 마크다운 펜스(```)는 절대 포함하지 마세요.
- 모든 값은 큰따옴표로 감싼 하나의 문자열이어야 합니다.
- 값 안에 큰따옴표("), 작은따옴표('), 줄바꿈(엔터), 탭을 절대 사용하지 마세요.
- 대화는 반드시 ~라고 말했어요 형식으로 풀어쓰세요.

응답 형식 (이 JSON 구조 외 다른 텍스트 없이 응답):
{{
  "title": "이야기 제목",
  "story": {{
    "기": "시작 부분 스토리",
    "승": "전개 부분 스토리",
    "전": "위기 부분 스토리",
    "결": "마무리 부분 스토리"
  }}
}}"""
    return prompt

def build_expansion_prompt(store: dict, part_num: int, chars_per_part: int) -> str:
    settings = store.get("settings", {})
    outline = store.get("outline", {})
    previous_parts = store.get("expanded_parts", [])
    part_directions = store.get("part_directions", {})

    user_direction = part_directions.get(str(part_num), "").strip()

    author_data = settings.get("author_style_data", {})
    author_role = author_data.get("role", "동화 작가")
    author_style = author_data.get("style", "따뜻한 스타일")
    author_tone = author_data.get("tone", "친근한")

    constraints_str = ""
    for k, v in author_data.get("constraints", {}).items():
        if isinstance(v, list):
            constraints_str += f"   - {k}: {', '.join(v)}\n"
        else:
            constraints_str += f"   - {k}: {v}\n"

    prev_text = ""
    for i, p in enumerate(previous_parts):
        prev_text += f"\n[파트 {i + 1}: {p.get('part_title')}]\n{p.get('content')}\n"

    direction_section = ""
    if user_direction:
        direction_section = f"""
=== 독자의 지시사항 - 반드시 최우선으로 반영하세요 ===
{user_direction}
"""

    prompt = f"""당신은 {author_role}입니다.
총 5개 파트로 구성된 장편 동화를 쓰고 있습니다. 현재 파트 {part_num} / 5 를 작성할 차례입니다.

=== 전체 동화 뼈대 ===
제목: {outline.get("title", "")}
기(시작): {outline.get("story", {}).get("기", "")}
승(전개): {outline.get("story", {}).get("승", "")}
전(위기): {outline.get("story", {}).get("전", "")}
결(마무리): {outline.get("story", {}).get("결", "")}

=== 지금까지 작성된 내용 ===
{prev_text if prev_text else "아직 작성된 내용이 없습니다. 개요의 기 부분을 참고하여 파트 1을 시작하세요."}{direction_section}
=== 작성 규칙 ===
1. 작가 스타일({author_style}), 어조({author_tone}) 및 제약사항을 완벽히 유지하세요.
{constraints_str}
2. 앞서 작성된 내용의 문맥과 흐름을 자연스럽게 이어받아 작성하세요.
3. 파트 {part_num}에 알맞은 진도를 나가세요.
   (파트1: 발단 / 파트2~3: 전개와 위기 / 파트4: 절정 / 파트5: 결말)
4. 현재 파트 분량은 대략 {chars_per_part}자 내외로 풍부하게 작성하세요.
5. 문단 구분은 실제 줄바꿈 대신 반드시 \\n 기호를 사용하세요.
6. 값 안에 큰따옴표("), 작은따옴표(')를 절대 사용하지 마세요. 대화는 ~라고 말했어요 형식으로 풀어쓰세요.
7. 설명, 주석, 마크다운 펜스(```) 없이 아래 JSON만 응답하세요:

{{
  "part_title": "파트 {part_num}의 소제목 (예: {part_num}장. 이상한 소리)",
  "content": "확장된 파트 {part_num}의 본문 전체 텍스트 (줄바꿈은 \\n 사용)"
}}"""
    return prompt
