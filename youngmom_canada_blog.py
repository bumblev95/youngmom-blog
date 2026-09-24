import streamlit as st
from google import genai
import requests
import smtplib
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

st.set_page_config(page_title="YoungMom Canada 블로그 비서", page_icon="🍁", layout="centered")

st.title("🍁 YoungMom Canada 인터뷰형 글 생성기")
st.caption("AI 에디터의 질문과 현장 디테일, 넉넉한 분량으로 구글 E-E-A-T 기준을 충족합니다.")
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

client = genai.Client(api_key=api_key)

# 503 서버 과부하 자동 우회(Fallback) 함수
def generate_content_with_fallback(prompt_text):
    models_to_try = ["gemini-3.6-flash", "gemini-2.5-flash"]
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
    "3. 생각나는 경험이나 상황 (짧아도 OK)", 
    placeholder="예: 올리브유 사러 갔다가 가격 보고 놀람 / 정비소 예약 놓쳐서 고생함 / 벽 못 자국 때문에 집주인이랑 실랑이함",
    height=80
)

ref_data = st.text_area(
    "4. 참고 자료나 뉴스 링크/내용 (선택)",
    placeholder="기사나 공지문 내용이 있다면 편하게 붙여넣으세요.",
    height=80
)

col_ask, col_direct = st.columns(2)

with col_ask:
    if st.button("🎙️ AI 에디터에게 질문받기 (추천!)", type="primary", use_container_width=True):
        if not topic.strip():
            st.warning("주제를 먼저 입력해 주세요.")
        else:
            with st.spinner("AI 에디터가 질문을 준비하고 있습니다 (서버 혼잡 시 자동 우회)..."):
                try:
                    q_prompt = f"""
                    당신은 노련한 캐나다 생활 블로그 편집자입니다.
                    주제: '{topic}', 작성자 경험: '{initial_exp}'
                    참고 자료: '{ref_data}'

                    이 글이 구글 애드센스의 '저가치 콘텐츠' 판정을 피하고 100% 사람 냄새 나는 E-E-A-T 글이 되도록, 
                    작성자에게 현장 디테일을 물어볼 질문 2~3가지만 다정하게 작성해 주세요.
                    (구체적 비용 $, 시간, 장소, 실패담이나 주의할 점 위주)
                    """
                    questions_text = generate_content_with_fallback(q_prompt)
                    st.session_state.interview_questions = questions_text
                    st.session_state.draft_inputs = {
                        "category": category,
                        "topic": topic,
                        "initial_exp": initial_exp,
                        "ref_data": ref_data
                    }
                    st.session_state.post_data = None
                    st.rerun()
                except Exception as e:
                    st.error(f"질문 생성 오류: {e}")

with col_direct:
    if st.button("⏩ 질문 없이 바로 글 생성하기", use_container_width=True):
        st.session_state.interview_questions = ""
        st.session_state.draft_inputs = {
            "category": category,
            "topic": topic,
            "initial_exp": initial_exp,
            "ref_data": ref_data
        }
        st.rerun()

# --- [2단계: AI 에디터 질문에 답하기] ---
if st.session_state.interview_questions is not None and not st.session_state.post_data:
    st.divider()
    st.markdown("### 💬 2단계: AI 에디터 인터뷰")
    
    if st.session_state.interview_questions != "":
        st.info("💡 **AI 에디터의 질문:**\n\n" + st.session_state.interview_questions)
        user_answers = st.text_area(
            "엄마의 답변 (단어나 짧은 문장으로 대충 적으셔도 살을 붙여드립니다!)",
            placeholder="예:\n1. 25불 정도였고 남쪽 코스트코였어요.\n2. 예약 앱을 미리 안 봐서 3주 밀린 게 멘붕이었죠.\n3. 영수증 사진 꼭 찍어두라고 하고 싶어요.",
            height=120
        )
    else:
        user_answers = ""

    if st.button("✨ 인터뷰 답변 녹여서 풍성한 장문 원고 집필하기", type="primary", use_container_width=True):
        with st.spinner("구글 고품질 기준(1,500자 이상)에 맞춰 본문을 작성 중입니다..."):
            try:
                saved = st.session_state.draft_inputs
                write_prompt = f"""
                당신은 캐나다 알버타에 거주하는 이민 선배이자 솔직하고 다정한 인기 살림 블로거 'YoungMom'입니다.
                구글 애드센스 심사 봇이 인정할 수 있도록 충분한 분량(공백 제외 1,500자 내외)과 깊이 있는 1인칭 E-E-A-T 원고를 집필하세요.

                [기본 정보]
                - 카테고리: {saved['category']}
                - 핵심 주제: {saved['topic']}
                - 초기 생각: {saved['initial_exp']}
                - 참고 자료: {saved['ref_data']}
                - 작성자가 직접 답한 현장 인터뷰 내용: "{user_answers}"

                [필수 집필 규칙]
                1. 첫 줄: 반드시 "TITLE: [현지 맘의 느낌이 살아있는 매력적인 제목]"
                2. 절대로 짧게 요약하지 말고, 각 문단마다 상황 설명과 구체적 묘사를 풍부하게 전개하세요.
                3. 기계식 어조 절대 금지 (~에 대해 알아보겠습니다 등 배제).
                4. 다정하고 똑 부러지는 말투(~해요, ~더라고요, ~했답니다).
                5. 구성:
                   - 도입부: 작성자의 실제 경험/인터뷰 내용을 바탕으로 한 현실 공감 오프닝 (상황과 감정 묘사)
                   - 본문 1: 직접 부딪치며 배운 실전 노하우와 상세 비용($), 절약 요령
                   - 본문 2 직전 줄에 독립된 한 줄로 "[INSERT_BODY_IMAGE]" 태그 넣기
                   - 본문 2: 현지 초보들이 가장 흔히 겪는 실수와 현실적인 대처법
                   - 본문 3: 알아두면 유용한 꿀팁 한 가지 더 (추천 앱, 방문 시간대, 서류 등)
                   - 맺음말: 독자들에게 건네는 따뜻한 응원 및 댓글 유도 질문
                6. 글 맨 마지막 두 줄:
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

                thumb_kw = "canada daily life"
                body_kw = "lifestyle living"

                if "THUMBNAIL_KEYWORD:" in main_content:
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

                thumb_url = get_unsplash_photo(thumb_kw, page=1)
                body_url = get_unsplash_photo(body_kw, page=1)

                st.session_state.post_data = {
                    "title": post_title,
                    "body": final_body,
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
                st.error(f"글 집필 중 오류 발생: {e}")

# --- [3단계: 검토, 분량 늘리기 및 최종 발행] ---
if st.session_state.post_data:
    st.divider()
    st.markdown("### 🔍 3단계: 최종 검토 및 분량 조절")
    st.info("💡 본문 분량이 아쉽다면 아래 **[➕ 본문 살 붙여서 더 길게 늘리기]** 버튼을 눌러보세요!")

    reviewed_title = st.text_input("블로그 제목", value=st.session_state.post_data["title"])

    st.markdown("##### 🖼️ 삽입될 고화질 사진")
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"1. 대표 사진 ({st.session_state.post_data['thumb_kw']})")
        st.image(st.session_state.post_data["thumb_url"], use_container_width=True)
        if st.button("🔄 대표 사진 변경", key="regen_thumb"):
            st.session_state.post_data["thumb_page"] += 1
            st.session_state.post_data["thumb_url"] = get_unsplash_photo(
                st.session_state.post_data["thumb_kw"], 
                page=st.session_state.post_data["thumb_page"]
            )
            st.rerun()

    with col2:
        st.caption(f"2. 본문 사진 ({st.session_state.post_data['body_kw']})")
        st.image(st.session_state.post_data["body_url"], use_container_width=True)
        if st.button("🔄 본문 사진 변경", key="regen_body"):
            st.session_state.post_data["body_page"] += 1
            st.session_state.post_data["body_url"] = get_unsplash_photo(
                st.session_state.post_data["body_kw"], 
                page=st.session_state.post_data["body_page"]
            )
            st.rerun()

    if st.button("➕ 본문 살 붙여서 더 길게 늘리기 (실전 팁 & Q&A 추가)", use_container_width=True):
        with st.spinner("기존 글 흐름을 유지하며 경험 디테일과 꿀팁을 확장하고 있습니다..."):
            try:
                expand_prompt = f"""
                당신은 캐나다 생활 블로거 'YoungMom'입니다.
                아래 작성된 기존 블로그 글의 분량이 다소 짧아 보강이 필요합니다.
                기존 글의 어조(~해요, ~했답니다)와 흐름을 그대로 유지하면서, 
                본문에 다음 내용을 추가하여 전체 분량을 1.5배~2배 수준으로 대폭 늘려 다시 작성해 주세요:

                [추가/보강할 내용]
                1. 현지에서 직접 겪은 구체적인 사례나 상황 묘사 보강
                2. 독자들이 가장 궁금해할 만한 '실전 자주 묻는 질문(Q&A) 2가지'를 본문 후반부에 자연스럽게 추가
                3. 반드시 본문 중간에 독립된 한 줄로 "[INSERT_BODY_IMAGE]" 태그 유지

                [기존 글]:
                {st.session_state.post_data['body']}
                """
                expanded_text = generate_content_with_fallback(expand_prompt)
                st.session_state.post_data["body"] = expanded_text
                st.success("글 분량이 풍성하게 확장되었습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"분량 확장 오류: {e}")

    reviewed_body = st.text_area("본문 내용", value=st.session_state.post_data["body"], height=400)

    thumb_url = st.session_state.post_data["thumb_url"]
    body_url = st.session_state.post_data["body_url"]
    body_img_html = f'<p style="text-align:center; margin:25px 0;"><img src="{body_url}" style="max-width:100%; height:auto; border-radius:8px;" alt="본문 이미지"></p>'

    if "[INSERT_BODY_IMAGE]" in reviewed_body:
        html_body_text = reviewed_body.replace("[INSERT_BODY_IMAGE]", body_img_html)
    else:
        html_body_text = reviewed_body + body_img_html

    formatted_body = html_body_text.strip().replace("\n", "<br>")
    final_html = f"""<html><body><div style="font-family: sans-serif; line-height: 1.8; font-size: 16px; color: #222;"><p style="text-align:center; margin-bottom:20px;"><img src="{thumb_url}" style="max-width:100%; height:auto; border-radius:8px;" alt="대표 이미지"></p>{formatted_body}</div></body></html>"""

    col_send, col_cancel = st.columns([3, 1])
    with col_send:
        if st.button("🚀 블로그에 최종 발행하기", type="primary", use_container_width=True):
            with st.spinner("발행 중입니다..."):
                try:
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = reviewed_title
                    msg['From'] = sender_email
                    msg['To'] = blogger_email

                    plain_text = reviewed_body.replace("[INSERT_BODY_IMAGE]", "")
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
