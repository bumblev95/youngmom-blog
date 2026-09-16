import streamlit as st
from google import genai
import requests
import smtplib
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

st.set_page_config(page_title="YoungMom Canada 블로그 비서", page_icon="🍁", layout="centered")

st.title("🍁 YoungMom Canada 글 생성기")
st.caption("고화질 실제 스톡 사진과 함께 글을 완성하고, 꼼꼼히 검토한 뒤 블로그에 등록하세요.")
st.link_button("📊 내 블로그 방문자 통계 보러가기", "https://www.blogger.com/go/stats")

# 1. 환경 변수(Secrets) 연동
api_key = st.secrets.get("GEMINI_API_KEY")
sender_email = st.secrets.get("SENDER_EMAIL")
app_password = st.secrets.get("GMAIL_APP_PASSWORD")
blogger_email = st.secrets.get("BLOGGER_EMAIL")
unsplash_key = st.secrets.get("UNSPLASH_ACCESS_KEY")

if not all([api_key, sender_email, app_password, blogger_email, unsplash_key]):
    st.error("Streamlit Secrets에 필수 설정(API 키, 이메일, Unsplash 키 등)이 누락되었습니다.")
    st.stop()

# 2. 세션 상태 초기화
if "post_data" not in st.session_state:
    st.session_state.post_data = None

# 스팸 필터에 걸리지 않도록 URL을 정제하는 함수
def clean_unsplash_url(raw_url):
    if "?" in raw_url:
        base = raw_url.split("?")[0]
        return f"{base}?w=800&q=80"
    return raw_url

# Unsplash 고화질 사진 검색 함수
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

# --- [1단계: 글 재료 입력하기] ---
st.markdown("### 📝 1단계: 글 재료 입력하기")

category = st.selectbox(
    "1. 카테고리 선택",
    [
        "✏️ 기타 캐나다 일상 & 생각",
        "📑 알버타 행정 & 서류 (운전면허, 헬스케어, 연금, 혜택)",
        "🏠 렌트 & 이사 (디파짓 반환, 계약서, 인스펙션)",
        "🚗 차량 & 생활 안전 (타이어, 한파, 소비자 권리)",
        "🛒 현지 알뜰 장보기 (코스트코, 마트 꿀템/물가 비교)"
    ]
)

topic = st.text_input(
    "2. 핵심 주제", 
    placeholder="예: 요즘 화제인 AI 이야기 / 캐나다 연금 혜택 / 코스트코 장보기"
)

source_content = st.text_area(
    "3. 📰 참고할 기사나 다른 글 내용 (선택: 복사해서 붙여넣기)",
    placeholder="뉴스 기사, IT 소식, 정부 공지문, 칼럼 등 자유롭게 복사해 붙여넣으세요.",
    height=120
)

experience = st.text_area(
    "4. 💡 엄마의 실제 생각이나 한마디 (선택)", 
    placeholder="예: 뉴스 보면서 세상이 참 빠르다고 느낌 / 지인이 이거 쓰고 편하다고 했음",
    height=80
)

if st.button("🔍 고화질 사진 & 초안 만들기 (미리보기)", type="primary", use_container_width=True):
    if not topic.strip():
        st.warning("핵심 주제를 입력해 주세요.")
    else:
        with st.spinner("내용을 분석하여 블로그 글 초안과 고화질 실제 스톡 사진을 가져오고 있습니다..."):
            try:
                source_instruction = ""
                if source_content.strip():
                    source_instruction = f"""
                    [참고할 원문 데이터]:
                    \"\"\"{source_content.strip()}\"\"\"
                    - 원문의 표현을 그대로 복사하지 마세요 (표절 방지).
                    - 위 원문에서 핵심 사실, 숫자, 주요 시사점을 추출한 뒤 친근한 선배 맘의 말투로 알기 쉽게 풀어내세요.
                    """

                exp_instruction = ""
                if experience.strip():
                    exp_instruction = f"""
                    - [작성자의 생각/경험]: "{experience.strip()}"
                    - 위 생각을 글의 도입부나 마무리 소감에 자연스럽게 담아내세요.
                    """

                prompt = f"""
                당신은 캐나다에 거주하며 유용한 생활 정보, 세상 돌아가는 소식, 진솔한 생각을 나누는 친근한 인기 블로거(Youngmom-canada-life)입니다.
                독자들이 흥미롭고 편안하게 읽을 수 있는 블로그 포스팅을 작성하세요.

                [카테고리]: {category}
                [주제]: {topic}
                {source_instruction}
                {exp_instruction}

                [작성 가이드]
                1. 첫 번째 줄은 반드시 "TITLE: [주제에 맞고 매력적인 한글 블로그 제목]" 형식으로 시작하세요.
                2. 어조: 다정하고 명쾌한 어조 (~해요, ~했답니다).
                3. 구성:
                   - 도입부: 이 주제나 뉴스를 접하고 든 생각, 흥미로운 공감 질문
                   - 본문 문단 1 (핵심 이슈 및 쉬운 설명)
                   - 본문 문단 2 바로 앞 줄에 반드시 독립된 한 줄로 "[INSERT_BODY_IMAGE]" 태그 입력
                   - 본문 문단 2, 3 (우리가 주목할 점, 일상이나 실생활에 주는 영향)
                   - 맺음말: 독자들에게 건네는 따뜻한 소감과 질문
                4. 글 맨 마지막 두 줄에는 Unsplash 검색용 간결한 영어 단어/키워드(2~3단어)를 아래 형식으로 적으세요:
                   THUMBNAIL_KEYWORD: [글 전체 분위기를 표현하는 간결한 영어 검색어 2~3단어]
                   BODY_KEYWORD: [본문 세부 내용과 관련된 간결한 영어 검색어 2~3단어]
                """

                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt
                )
                full_text = response.text.strip()

                post_title = topic
                if "TITLE:" in full_text:
                    parts = full_text.split("TITLE:", 1)[1].split("\n", 1)
                    post_title = parts[0].strip()
                    main_content = parts[1] if len(parts) > 1 else ""
                else:
                    main_content = full_text

                thumb_kw = "canada lifestyle"
                body_kw = "workspace desk"

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

            except Exception as e:
                st.error(f"초안 생성 중 오류가 발생했습니다: {e}")

# --- [2단계: 엄마의 검토 및 수정 (Review)] ---
if st.session_state.post_data:
    st.divider()
    st.markdown("### 🔍 2단계: 엄마의 검토 및 사진 확인 (Review)")
    st.info("💡 글과 사진을 확인해 보세요. 사진이 마음에 안 들면 **[🔄 다른 사진 찾기]**를 누르고, 마음에 들면 아래 **[최종 발행하기]**를 누르세요!")

    reviewed_title = st.text_input(
        "블로그 제목 확인/수정", 
        value=st.session_state.post_data["title"]
    )

    st.markdown("##### 🖼️ 삽입될 고화질 실제 스톡 사진")
    col1, col2 = st.columns(2)
    
    with col1:
        st.caption(f"1. 대표 사진 (키워드: {st.session_state.post_data['thumb_kw']})")
        st.image(st.session_state.post_data["thumb_url"], use_container_width=True)
        if st.button("🔄 대표 사진 다른 걸로 바꾸기", key="regen_thumb"):
            st.session_state.post_data["thumb_page"] += 1
            new_url = get_unsplash_photo(
                st.session_state.post_data["thumb_kw"], 
                page=st.session_state.post_data["thumb_page"]
            )
            st.session_state.post_data["thumb_url"] = new_url
            st.rerun()

    with col2:
        st.caption(f"2. 본문 중간 사진 (키워드: {st.session_state.post_data['body_kw']})")
        st.image(st.session_state.post_data["body_url"], use_container_width=True)
        if st.button("🔄 본문 사진 다른 걸로 바꾸기", key="regen_body"):
            st.session_state.post_data["body_page"] += 1
            new_url = get_unsplash_photo(
                st.session_state.post_data["body_kw"], 
                page=st.session_state.post_data["body_page"]
            )
            st.session_state.post_data["body_url"] = new_url
            st.rerun()

    reviewed_body = st.text_area(
        "본문 내용 확인/수정", 
        value=st.session_state.post_data["body"],
        height=350
    )

    col_send, col_cancel = st.columns([3, 1])
    with col_send:
        if st.button("🚀 검토 완료! 블로그에 최종 발행하기", type="primary", use_container_width=True):
            with st.spinner("구글 스팸 필터를 우회하여 안전하게 발행 중입니다..."):
                try:
                    thumb_url = st.session_state.post_data["thumb_url"]
                    body_url = st.session_state.post_data["body_url"]

                    body_img_html = f'<p style="text-align:center; margin:25px 0;"><img src="{body_url}" style="max-width:100%; height:auto; border-radius:8px;" alt="본문 이미지"></p>'

                    if "[INSERT_BODY_IMAGE]" in reviewed_body:
                        html_body_text = reviewed_body.replace("[INSERT_BODY_IMAGE]", body_img_html)
                    else:
                        html_body_text = reviewed_body + body_img_html

                    formatted_body = html_body_text.strip().replace("\n", "<br>")
                    
                    final_html = f"""<html><body><div style="font-family: sans-serif; line-height: 1.8; font-size: 16px; color: #222;"><p style="text-align:center; margin-bottom:20px;"><img src="{thumb_url}" style="max-width:100%; height:auto; border-radius:8px;" alt="대표 이미지"></p>{formatted_body}</div></body></html>"""

                    # 구글 스팸 필터를 통과하기 위한 multipart/alternative 표준 포맷
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

                    st.success(f"🎉 성공적으로 등록되었습니다! '{reviewed_title}'")
                    st.balloons()
                    st.session_state.post_data = None

                except Exception as e:
                    st.error(f"발행 중 오류가 발생했습니다: {e}")

    with col_cancel:
        if st.button("❌ 취소", use_container_width=True):
            st.session_state.post_data = None
            st.rerun()
