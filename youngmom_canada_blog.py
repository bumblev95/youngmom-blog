import streamlit as st
from google import genai
import requests
import smtplib
import random
import time
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

st.set_page_config(page_title="YoungMom Canada 블로그 비서", page_icon="🍁", layout="centered")

st.title("🍁 YoungMom Canada 인터뷰형 글 생성기")
st.caption("AI 에디터의 간결한 질문과 현장 디테일로 구글 E-E-A-T 기준을 충족합니다.")
st.link_button("📊 내 블로그 방문자 통계 보러가기", "https://www.blogger.com/go/stats")

# 1. 환경 변수 연동
api_key = st.secrets.get("GEMINI_API_KEY")
sender_email = st.secrets.get("SENDER_EMAIL")
app_password = st.secrets.get("GMAIL_APP_PASSWORD")
blogger_email = st.secrets.get("BLOGGER_EMAIL")
unsplash_key = st.secrets.get("UNSPLASH_ACCESS_KEY")

if not all([api_key, sender_email, app_password, blogger_email, unsplash_key]):
    st.error("Streamlit Secrets에 필수 설정(API 키, 이메일, Unsplash 키 등)이 누락되었습니다.")
    st.stop()

# 세션 상태 관리
if "interview_questions" not in st.session_state:
    st.session_state.interview_questions = None
if "post_data" not in st.session_state:
    st.session_state.post_data = None
if "draft_inputs" not in st.session_state:
    st.session_state.draft_inputs = {}
if "last_api_call" not in st.session_state:
    st.session_state.last_api_call = 0.0

# 429 방지용 쿨타임 검사 (기본 12초 대기)
def enforce_cooldown(cooldown_seconds=12):
    now = time.time()
    elapsed = now - st.session_state.last_api_call
    if elapsed < cooldown_seconds:
        wait_time = int(cooldown_seconds - elapsed) + 1
        st.warning(f"⏳ 서버 안정화 대기 중이에요! **{wait_time}초**만 천천히 기다렸다가 눌러주세요.")
        return False
    st.session_state.last_api_call = now
    return True

def clean_unsplash_url(raw_url):
    if "?" in raw_url:
        base = raw_url.split("?")[0]
        return f"{base}?w=800&q=80"
    return raw_url

def get_unsplash_photo(query_keyword, page=1):
    try:
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query_keyword,
            "page": page,
            "per_page": 1,
            "orientation": "landscape",
            "client_id": unsplash_key
        }
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("results"):
                raw_link = data["results"][0]["urls"]["regular"]
                return clean_unsplash_url(raw_link)
    except Exception:
        pass
    fallback_seed = random.randint(1, 100)
    return f"https://images.unsplash.com/photo-1517048676732-d65bc937f952?w=800&q=80&sig={fallback_seed}"

def file_to_base64_src(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    b64_str = base64.b64encode(bytes_data).decode()
    mime = uploaded_file.type or "image/jpeg"
    return f"data:{mime};base64,{b64_str}"

client = genai.Client(api_key=api_key)

# 429 / 503 대응 폴백 함수 (3.8 우선, 실패 시 3.6 백업)
def generate_content_with_fallback(prompt_text):
    models_to_try = ["gemini-3.8-flash", "gemini-3.6-flash"]
    last_err = None
    for m in models_to_try:
        try:
            resp = client.models.generate_content(
                model=m,
                contents=prompt_text
            )
            if resp and resp.text:
                return resp.text.strip()
        except Exception as e:
            last_err = e
            time.sleep(4)
            continue
    raise last_err

# --- [1단계: 기본 글감 입력] ---
st.markdown("### 📝 1단계: 글 주제 & 기본 경험 던져주기")

category = st.selectbox(
    "1. 카테고리 선택",
    [
        "🛒 현지 알뜰 장보기 (코스트코, 마트 꿀템/물가 비교)",
        "🚗 차량 & 생활 안전 (타이어, 한파, 정비소, 보험)",
        "🏠 렌트 & 이사 (디파짓 반환, 계약서, 인스펙션, 가구 정리)",
        "📑 알버타 행정 & 서류 (운전면허, 헬스케어, 차일드베네핏, 세금)",
        "✏️ 리얼 캐나다 일상 (육아, 로컬 마켓, 날씨, 이민 생각)"
    ]
)

topic = st.text_input(
    "2. 핵심 주제", 
    placeholder="예: 코스트코 장보기 / 겨울 스노우타이어 교체 비용 / 렌트 디파짓 떼이지 않는 법"
)

initial_exp = st.text_area(
    "3. 생각나는 경험이나 상황 (짧게 메모하듯 적으셔도 OK)", 
    placeholder="예: 올리브유 사러 갔다가 25불 찍혀서 놀람 / 정비소 예약 놓쳐서 2주 기다림 / 서류 하나 빠져서 레지스트리 헛걸음함",
    height=90
)

st.caption("💡 **글이 훨씬 진짜처럼 살아나는 꿀팁:** 대략적인 금액($), 방문했던 매장 위치, 혹은 당황했던 실패담 같은 사소한 디테일을 위 3번에 함께 적어주시면 AI가 훨씬 풍성하게 살려냅니다.")

ref_data = st.text_area(
    "4. 참고 자료나 뉴스 링크/내용 (선택)",
    placeholder="기사나 공식 안내문 내용이 있다면 편하게 복사해서 붙여넣으세요.",
    height=70
)

# [신규] 사진 검색어 사전 지정 (선택)
with st.expander("🖼️ 사진 검색어 미리 정하기 (선택 - 비워두면 AI가 자동 추천)"):
    st.caption("원하는 사진 분위기가 있다면 영문 키워드로 적어주세요. 비워두시면 본문 내용에 맞춰 AI가 알아서 검색해 옵니다.")
    pre_thumb_kw = st.text_input("대표 사진 검색어", placeholder="예: costco grocery / winter tire car / highway alberta")
    pre_body_kw = st.text_input("본문 사진 검색어", placeholder="예: supermarket shopping / car repair mechanic / living room rent")

col_ask, col_direct = st.columns(2)

with col_ask:
    if st.button("🎙️ AI 에디터에게 질문받기 (추천!)", type="primary", use_container_width=True):
        if not topic.strip():
            st.warning("주제를 먼저 입력해 주세요.")
        else:
            if enforce_cooldown(12):
                with st.spinner("AI 에디터가 꼭 필요한 핵심 질문만 간결하게 추리고 있습니다..."):
                    try:
                        q_prompt = f"""
                        주제: '{topic}', 작성자 경험 메모: '{initial_exp}'
                        참고 자료: '{ref_data}'

                        구글 애드센스 E-E-A-T 통과를 위해 독자들이 궁금해할 핵심 현장 디테일 질문 딱 3가지만 작성하세요.

                        [출력 절대 규칙 - 위반 금지]
                        1. 인사말, 서론, 공감 멘트, 격려 문구, 예시 설명 등 부연설명을 절대로 쓰지 마세요.
                        2. 오직 질문 3개만 번호(1., 2., 3.) 매겨 각 한 줄씩 간결하고 명확하게 질문하세요.
                        3. 질문 내용: 구체적 비용($), 지점/위치, 소요/대기 시간, 꼭 전하고 싶은 주의사항 위주.
                        """
                        questions_text = generate_content_with_fallback(q_prompt)
                        st.session_state.interview_questions = questions_text
                        st.session_state.draft_inputs = {
                            "category": category,
                            "topic": topic,
                            "initial_exp": initial_exp,
                            "ref_data": ref_data,
                            "pre_thumb_kw": pre_thumb_kw.strip(),
                            "pre_body_kw": pre_body_kw.strip()
                        }
                        st.session_state.post_data = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"질문 생성 중 지연 발생: {e}")

with col_direct:
    if st.button("⏩ 질문 없이 바로 글 생성하기", use_container_width=True):
        st.session_state.interview_questions = ""
        st.session_state.draft_inputs = {
            "category": category,
            "topic": topic,
            "initial_exp": initial_exp,
            "ref_data": ref_data,
            "pre_thumb_kw": pre_thumb_kw.strip(),
            "pre_body_kw": pre_body_kw.strip()
        }
        st.rerun()

# --- [2단계: AI 에디터 질문에 답하기] ---
if st.session_state.interview_questions is not None and not st.session_state.post_data:
    st.divider()
    st.markdown("### 💬 2단계: AI 에디터 인터뷰")
    
    if st.session_state.interview_questions != "":
        st.info("💡 **AI 에디터의 핵심 질문:**\n\n" + st.session_state.interview_questions)
        user_answers = st.text_area(
            "엄마의 답변 (단어나 짧은 문장으로 편하게 툭툭 적으세요!)",
            placeholder="예:\n1. 코스트코 남쪽 지점이었고 총 650불 들었어요.\n2. 예약 깜빡해서 2주 기다렸네요.\n3. 스틸 림 미리 사두는 게 공임비 아끼는 길이에요.",
            height=110
        )
    else:
        user_answers = ""

    if st.button("✨ 인터뷰 답변 녹여서 풍성한 장문 원고 집필하기", type="primary", use_container_width=True):
        if enforce_cooldown(12):
            with st.spinner("구글 E-E-A-T 고품질 기준(1,500자 이상)에 맞춰 본문과 태그를 작성 중입니다..."):
                try:
                    saved = st.session_state.draft_inputs

                    write_prompt = f"""
                    당신은 캐나다 알버타에 거주하는 이민 선배이자 솔직하고 다정한 인기 살림 블로거 'YoungMom'입니다.
                    구글 애드센스 심사 봇이 인정할 수 있도록 충분한 분량(공백 제외 1,500자 내외)과 깊이 있는 1인칭 E-E-A-T 원고를 집필하세요.

                    [기본 정보]
                    - 카테고리: {saved['category']}
                    - 핵심 주제: {saved['topic']}
                    - 작성자의 기본 경험/메모: {saved['initial_exp']}
                    - 참고 자료: {saved['ref_data']}
                    - 작성자의 현장 인터뷰 답변: "{user_answers}"

                    [필수 집필 규칙]
                    1. 첫 줄: 반드시 "TITLE: [현지 맘의 느낌이 살아있는 매력적인 제목]"
                    2. 기계식 어조 절대 금지 (~에 대해 알아보겠습니다 등 배제).
                    3. 이웃에게 커피 마시며 솔직하게 털어놓듯 다정하고 똑 부러지는 말투(~해요, ~더라고요, ~했답니다).
                    4. 경험 메모와 인터뷰 답변에 나온 구체적인 금액($), 위치, 대기 시간, 실수담을 오프닝과 본문에 생생하게 녹여내세요. (중복되는 내용은 자연스럽게 하나로 통합)
                    5. 구성:
                       - 도입부: 실제 겪은 일화와 감정 묘사를 담은 현실 공감 오프닝
                       - 본문 1: 직접 부딪치며 배운 실전 노하우와 구체적 비용($), 절약 요령
                       - 본문 2 직전 줄에 독립된 한 줄로 "[INSERT_BODY_IMAGE]" 태그 넣기
                       - 본문 2: 현지 초보들이 가장 흔히 겪는 실수/실패담과 현실적인 대처법
                       - 본문 3: 알아두면 유용한 꿀팁 한 가지 더 (추천 루틴, 시간대, 서류 등)
                       - 맺음말: 독자들에게 건네는 따뜻한 응원 및 소통 질문
                    6. 글 맨 마지막 세 줄:
                       TAGS: [블로그 검색 최적화용 쉼표 구분 태그 3~4개, 예: 캐나다생활, 알버타이민, 코스트코꿀팁]
                       THUMBNAIL_KEYWORD: [글 분위기 영어 스톡 검색어 2~3단어]
                       BODY_KEYWORD: [본문 세부 내용 영어 스톡 검색어 2~3단어]
                    """

                    full_text = generate_content_with_fallback(write_prompt)

                    post_title = saved['topic']
                    if "TITLE:" in full_text:
                        parts = full_text.split("TITLE:", 1)[1].split("\n", 1)
                        post_title = parts[0].strip()
                        main_content = parts[1] if len(parts) > 1 else ""
                    else:
                        main_content = full_text

                    tags_str = "캐나다생활, 알버타살림, 캐나다이민"
                    thumb_kw = "canada daily life"
                    body_kw = "lifestyle living"

                    # 태그 및 이미지 키워드 추출
                    if "TAGS:" in main_content:
                        split_body, tail = main_content.rsplit("TAGS:", 1)
                        final_body = split_body.strip()
                        lines = tail.strip().split("\n")
                        tags_str = lines[0].strip()
                        for line in lines[1:]:
                            if "THUMBNAIL_KEYWORD:" in line:
                                thumb_kw = line.split("THUMBNAIL_KEYWORD:", 1)[1].strip()
                            elif "BODY_KEYWORD:" in line:
                                body_kw = line.split("BODY_KEYWORD:", 1)[1].strip()
                    elif "THUMBNAIL_KEYWORD:" in main_content:
                        split_body, kw_tail = main_content.rsplit("THUMBNAIL_KEYWORD:", 1)
                        final_body = split_body.strip()
                        if "BODY_KEYWORD:" in kw_tail:
                            t_part, b_part = kw_tail.split("BODY_KEYWORD:", 1)
                            thumb_kw = t_part.strip()
                            body_kw = b_part.strip()
                        else:
                            thumb_kw = kw_tail.strip()
                    else:
                        final_body = main_content.strip()

                    if not final_body:
                        final_body = full_text

                    # 사용자가 1단계에서 직접 입력한 검색어가 있으면 AI 추천값 대신 최우선 적용
                    if saved.get("pre_thumb_kw"):
                        thumb_kw = saved["pre_thumb_kw"]
                    if saved.get("pre_body_kw"):
                        body_kw = saved["pre_body_kw"]

                    thumb_url = get_unsplash_photo(thumb_kw, page=1)
                    body_url = get_unsplash_photo(body_kw, page=1)

                    st.session_state.post_data = {
                        "title": post_title,
                        "body": final_body,
                        "tags": tags_str,
                        "thumb_kw": thumb_kw,
                        "body_kw": body_kw,
                        "thumb_page": 1,
                        "body_page": 1,
                        "thumb_url": thumb_url,
                        "body_url": body_url
                    }
                    st.session_state.interview_questions = None
                    st.rerun()

                except Exception as e:
                    st.error(f"글 집필 중 일시적 오류: {e}")

# --- [3단계: 검토, 분량 늘리기 및 최종 발행] ---
if st.session_state.post_data:
    st.divider()
    st.markdown("### 🔍 3단계: 최종 검토 및 분량 조절")

    reviewed_title = st.text_input("블로그 제목", value=st.session_state.post_data["title"])

    st.markdown("##### 🖼️ 삽입될 사진 관리 (내 폰 사진 올리기 또는 검색)")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**1. 대표 사진**")
        st.image(st.session_state.post_data["thumb_url"], use_container_width=True)
        
        uploaded_thumb = st.file_uploader("📸 내 폰 사진으로 넣기 (대표)", type=["jpg", "jpeg", "png", "webp"], key="upload_thumb")
        if uploaded_thumb is not None:
            st.session_state.post_data["thumb_url"] = file_to_base64_src(uploaded_thumb)
            st.success("대표 사진이 내 사진으로 교체되었습니다!")
            st.rerun()

        new_thumb_kw = st.text_input("스톡 사진 검색어(영문)", value=st.session_state.post_data["thumb_kw"], key="kw_thumb")
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            if st.button("🔍 검색", key="search_thumb"):
                st.session_state.post_data["thumb_kw"] = new_thumb_kw
                st.session_state.post_data["thumb_page"] = 1
                st.session_state.post_data["thumb_url"] = get_unsplash_photo(new_thumb_kw, page=1)
                st.rerun()
        with subcol2:
            if st.button("🔄 다음 사진", key="next_thumb"):
                st.session_state.post_data["thumb_page"] += 1
                st.session_state.post_data["thumb_url"] = get_unsplash_photo(
                    st.session_state.post_data["thumb_kw"], 
                    page=st.session_state.post_data["thumb_page"]
                )
                st.rerun()

    with col2:
        st.markdown("**2. 본문 사진**")
        st.image(st.session_state.post_data["body_url"], use_container_width=True)

        uploaded_body = st.file_uploader("📸 내 폰 사진으로 넣기 (본문)", type=["jpg", "jpeg", "png", "webp"], key="upload_body")
        if uploaded_body is not None:
            st.session_state.post_data["body_url"] = file_to_base64_src(uploaded_body)
            st.success("본문 사진이 내 사진으로 교체되었습니다!")
            st.rerun()

        new_body_kw = st.text_input("스톡 사진 검색어(영문)", value=st.session_state.post_data["body_kw"], key="kw_body")
        subcol3, subcol4 = st.columns(2)
        with subcol3:
            if st.button("🔍 검색", key="search_body"):
                st.session_state.post_data["body_kw"] = new_body_kw
                st.session_state.post_data["body_page"] = 1
                st.session_state.post_data["body_url"] = get_unsplash_photo(new_body_kw, page=1)
                st.rerun()
        with subcol4:
            if st.button("🔄 다음 사진", key="next_body"):
                st.session_state.post_data["body_page"] += 1
                st.session_state.post_data["body_url"] = get_unsplash_photo(
                    st.session_state.post_data["body_kw"], 
                    page=st.session_state.post_data["body_page"]
                )
                st.rerun()

    st.markdown("---")

    if st.button("➕ 본문 살 붙여서 더 길게 늘리기 (실전 팁 & Q&A 추가)", use_container_width=True):
        if enforce_cooldown(12):
            with st.spinner("기존 글 흐름을 유지하며 경험 디테일과 꿀팁을 확장하고 있습니다..."):
                try:
                    expand_prompt = f"""
                    당신은 캐나다 생활 블로거 'YoungMom'입니다.
                    아래 블로그 글의 흐름과 말투(~해요, ~했답니다)를 완벽히 유지하면서 분량을 1.5배 수준으로 확장하세요:

                    [추가 내용]
                    1. 현지에서 겪은 구체적인 상황 묘사 강화
                    2. 독자 실전 자주 묻는 질문(Q&A) 2가지를 본문 하단에 자연스럽게 추가
                    3. 본문 중간에 독립된 한 줄로 "[INSERT_BODY_IMAGE]" 태그 필수 유지

                    [기존 글]:
                    {st.session_state.post_data['body']}
                    """
                    expanded_text = generate_content_with_fallback(expand_prompt)
                    st.session_state.post_data["body"] = expanded_text
                    st.success("글 분량이 풍성하게 확장되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"분량 확장 오류: {e}")

    # 실시간 글자 수(공백 제외) 신호등 배지 계산
    raw_body_text = st.session_state.post_data["body"].replace("[INSERT_BODY_IMAGE]", "")
    char_count_no_spaces = len(raw_body_text.replace(" ", "").replace("\n", ""))

    if char_count_no_spaces >= 1200:
        st.success(f"🟢 **현재 본문 글자 수:** 공백 제외 **{char_count_no_spaces:,}자** (구글 고품질 E-E-A-T 기준 충족! ✅)")
    else:
        st.warning(f"🟠 **현재 본문 글자 수:** 공백 제외 **{char_count_no_spaces:,}자** (조금 짧아요! 위의 '➕ 본문 살 붙여서 더 길게 늘리기' 버튼을 눌러보세요.)")

    reviewed_body = st.text_area("본문 내용", value=st.session_state.post_data["body"], height=380)

    reviewed_tags = st.text_input("🏷️ 추천 태그 (쉼표로 구분되어 글 맨 아래에 자동 첨부됩니다)", value=st.session_state.post_data.get("tags", "캐나다생활, 알버타살림, 캐나다이민"))

    thumb_url = st.session_state.post_data["thumb_url"]
    body_url = st.session_state.post_data["body_url"]
    body_img_html = f'<p style="text-align:center; margin:25px 0;"><img src="{body_url}" style="max-width:100%; height:auto; border-radius:8px;" alt="본문 이미지"></p>'

    if "[INSERT_BODY_IMAGE]" in reviewed_body:
        html_body_text = reviewed_body.replace("[INSERT_BODY_IMAGE]", body_img_html)
    else:
        html_body_text = reviewed_body + body_img_html

    tag_list = [t.strip() for t in reviewed_tags.split(",") if t.strip()]
    hashtags_html = " ".join([f"#{t.replace('#', '')}" for t in tag_list])
    tag_footer = f'<p style="margin-top:35px; color:#666; font-size:14px;"><b>태그:</b> {hashtags_html}</p>'

    formatted_body = html_body_text.strip().replace("\n", "<br>")
    final_html = f"""<html><body><div style="font-family: sans-serif; line-height: 1.8; font-size: 16px; color: #222;"><p style="text-align:center; margin-bottom:20px;"><img src="{thumb_url}" style="max-width:100%; height:auto; border-radius:8px;" alt="대표 이미지"></p>{formatted_body}{tag_footer}</div></body></html>"""

    col_send, col_cancel = st.columns([3, 1])
    with col_send:
        if st.button("🚀 블로그에 최종 발행하기", type="primary", use_container_width=True):
            with st.spinner("발행 중입니다..."):
                try:
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = reviewed_title
                    msg['From'] = sender_email
                    msg['To'] = blogger_email

                    plain_text = reviewed_body.replace("[INSERT_BODY_IMAGE]", "") + f"\n\n태그: {hashtags_html}"
                    part1 = MIMEText(plain_text, 'plain', 'utf-8')
                    part2 = MIMEText(final_html, 'html', 'utf-8')

                    msg.attach(part1)
                    msg.attach(part2)

                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                        server.login(sender_email, app_password)
                        server.send_message(msg)

                    st.success(f"🎉 성공적으로 등록되었습니다: '{reviewed_title}'")
                    st.balloons()
                    st.session_state.post_data = None
                    st.session_state.interview_questions = None

                except Exception as e:
                    st.error(f"발행 오류: {e}")

    with col_cancel:
        if st.button("❌ 취소 및 다시 쓰기", use_container_width=True):
            st.session_state.post_data = None
            st.session_state.interview_questions = None
            st.rerun()

    with st.expander("📌 본문 HTML 복사 코드"):
        st.code(final_html, language="html")
