import streamlit as st
from google import genai
import requests
import smtplib
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

st.set_page_config(page_title="YoungMom Canada 블로그 비서", page_icon="🍁", layout="centered")

st.title("🍁 YoungMom Canada 오리지널 글 생성기")
st.caption("구글 애드센스 E-E-A-T(실제 경험·현장 디테일) 기준을 충족하는 진짜 현지 맘 스타일 글을 작성합니다.")
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

if "post_data" not in st.session_state:
    st.session_state.post_data = None

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

# --- [1단계: 글 재료 입력하기] ---
st.markdown("### 📝 1단계: 글 재료 입력하기")

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
    placeholder="예: 코스트코 10월 필수 알뜰템 / 겨울 스노우타이어 교체 비용 비교 / 렌트 디파짓 떼이지 않는 법"
)

experience = st.text_area(
    "3. 💡 엄마의 실제 경험·생각·상황 한마디 (★핵심 치트키!)", 
    placeholder="짧게 써도 좋습니다!\n예: 지난주에 코스트코 갔다가 올리브유 가격 보고 기절함 / 작년에 타이어 예약 늦어서 3주 기다렸던 기억 / 집주인이 벽 못 자국으로 50불 깎으려고 했음",
    height=90
)

source_content = st.text_area(
    "4. 📰 참고할 뉴스, 공지, 기사 링크나 텍스트 (선택)",
    placeholder="참고하고 싶은 최신 뉴스나 정부 정책 내용이 있다면 편하게 붙여넣으세요.",
    height=100
)

if st.button("✨ 사람 냄새 100% 오리지널 글 초안 만들기", type="primary", use_container_width=True):
    if not topic.strip():
        st.warning("핵심 주제를 입력해 주세요.")
    else:
        with st.spinner("구글 E-E-A-T 기준을 만족하는 진짜 현지 맘의 오리지널 글을 집필하고 있습니다..."):
            try:
                exp_detail = experience.strip() if experience.strip() else "현지에서 직접 장을 보고 살림을 꾸리며 몸으로 부딪치고 배운 솔직한 경험"
                
                source_guide = ""
                if source_content.strip():
                    source_guide = f"""
                    [참고 팩트 데이터]:
                    {source_content.strip()}
                    (주의: 위 내용을 요약하듯 베끼지 말고, 핵심 사실만 취한 뒤 철저히 현지 맘의 시각과 언어로 재해석하세요.)
                    """

                prompt = f"""
                당신은 캐나다 알버타에 거주하는 이민/정착 선배이자 현실감 넘치는 살림꾼 블로거 'YoungMom'입니다.
                구글 애드센스 심사 봇이 판별하는 'AI 생성 저가치 콘텐츠(Low Value Content)' 규정을 완벽하게 피하고, 
                진짜 현지 사람이 직접 발로 뛰며 겪은 경험(E-E-A-T)이 뚝뚝 묻어나는 블로그 글을 써야 합니다.

                [글 정보]
                - 카테고리: {category}
                - 주제: {topic}
                - 작성자의 실제 상황/경험/한마디: "{exp_detail}"
                {source_guide}

                [필수 집필 규칙 - AI 냄새 완전 제거]
                1. 첫 줄은 반드시 "TITLE: [현지 맘의 생생한 느낌이 살아있는 매력적인 제목]" 으로 작성하세요.
                2. 절대로 백과사전식 설명, 기계적인 말투(~에 대해 알아보겠습니다, 장단점을 살펴보겠습니다 등)를 쓰지 마세요.
                3. 친한 이웃 엄마나 동생에게 커피 마시며 솔직하게 털어놓듯 다정하고 똑 부러지는 말투(~해요, ~더라고요, ~했답니다)를 쓰세요.
                4. [실제 경험]을 글의 오프닝(도입부)에 아주 생생한 상황 묘사(시간, 감정, 당황했던 순간 등)로 풀어내세요.
                5. 글 본문에 구체적인 현지 디테일(대략적인 현지 달러 금액 $, 대기 시간, 매장 이름, 브랜드명, 현실적인 주의점)을 2개 이상 반드시 포함하세요.
                6. 구성:
                   - 도입부: 작성자의 실제 경험/생각을 바탕으로 한 현실 공감 오프닝
                   - 본문 1: 직접 부딪치며 알게 된 핵심 팁 (구체적인 방법과 비용 꿀팁)
                   - 본문 2 직전에 반드시 독립된 한 줄로 "[INSERT_BODY_IMAGE]" 태그 넣기
                   - 본문 2: 현지 초보들이 가장 많이 실수하는 현실적인 주의사항
                   - 맺음말: 독자들에게 따뜻한 응원과 "여러분은 어떠신가요?" 묻는 소통형 마무리
                7. 글 맨 마지막 두 줄:
                   THUMBNAIL_KEYWORD: [글 분위기에 맞는 간결한 영어 스톡 검색어 2~3단어]
                   BODY_KEYWORD: [본문 내용에 맞는 간결한 영어 스톡 검색어 2~3단어]
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

                thumb_kw = "canada daily life"
                body_kw = "grocery shopping"

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

# --- [2단계: 엄마의 검토 및 사진 확인] ---
if st.session_state.post_data:
    st.divider()
    st.markdown("### 🔍 2단계: 엄마의 검토 및 최종 발행 (Review)")
    st.info("💡 글과 사진을 확인해 보세요. 내용이 마음에 들면 아래 **[최종 발행하기]**를 누르시면 됩니다!")

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
        st.caption(f"2. 본문 사진 (키워드: {st.session_state.post_data['body_kw']})")
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
        if st.button("🚀 검토 완료! 블로그에 최종 발행하기", type="primary", use_container_width=True):
            with st.spinner("구글 스팸 필터를 우회하여 안전하게 발행 중입니다..."):
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

                    st.success(f"🎉 성공적으로 등록되었습니다! '{reviewed_title}'")
                    st.balloons()
                    st.session_state.post_data = None

                except Exception as e:
                    st.error(f"발행 중 오류가 발생했습니다: {e}")

    with col_cancel:
        if st.button("❌ 취소", use_container_width=True):
            st.session_state.post_data = None
            st.rerun()

    with st.expander("📌 메일 쿨타임 대비: 본문 HTML 복사 코드"):
        st.caption("단시간 연속 발행으로 메일이 튕겼을 때, 아래 코드를 복사해 Blogger 글쓰기(HTML 모드)에 바로 붙여넣으세요.")
        st.code(final_html, language="html")
