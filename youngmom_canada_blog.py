import streamlit as st
from google import genai
import urllib.parse
import smtplib
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

st.set_page_config(page_title="YoungMom Canada 블로그 비서", page_icon="🍁", layout="centered")

st.title("🍁 YoungMom Canada 글 생성기")
st.caption("뉴스, 시사, 캐나다 일상 등 어떤 이야기든 엄마만의 감성 글로 풀어내고 검토 후 등록하세요.")

# 1. 환경 변수(Secrets) 연동
api_key = st.secrets.get("GEMINI_API_KEY")
sender_email = st.secrets.get("SENDER_EMAIL")
app_password = st.secrets.get("GMAIL_APP_PASSWORD")
blogger_email = st.secrets.get("BLOGGER_EMAIL")

if not all([api_key, sender_email, app_password, blogger_email]):
    st.error("Streamlit Secrets에 필수 설정(API 키, 이메일 정보)이 누락되었습니다.")
    st.stop()

# 2. 세션 상태 초기화
if "post_data" not in st.session_state:
    st.session_state.post_data = None

# 고화질 실사 사진 URL 생성 함수 (Flux 모델)
def generate_flux_image_url(prompt_text, width, height, seed):
    camera_style = ", authentic editorial lifestyle photography, shot on 35mm lens, soft natural lighting, cozy tone, realistic texture, 8k resolution, highly detailed, photorealistic, no 3d render, no cgi, no text, no watermark"
    enhanced_prompt = prompt_text + camera_style
    encoded = urllib.parse.quote(enhanced_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&model=flux&nologo=true&seed={seed}"

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
    placeholder="뉴스 기사, IT 소식, 정부 공지문, 칼럼 등 자유롭게 복사해 붙여넣으세요.\n(AI가 핵심 팩트를 추출해 읽기 편한 친근한 글로 재가공합니다)",
    height=120
)

experience = st.text_area(
    "4. 💡 엄마의 실제 생각이나 한마디 (선택)", 
    placeholder="예: 뉴스 보면서 세상이 참 빠르다고 느낌 / 지인이 이거 쓰고 편하다고 했음\n(비워두셔도 자연스럽게 글이 완성됩니다)",
    height=80
)

if st.button("🔍 고화질 사진 & 초안 만들기 (미리보기)", type="primary", use_container_width=True):
    if not topic.strip():
        st.warning("핵심 주제를 입력해 주세요.")
    else:
        with st.spinner("내용을 분석하여 블로그 글 초안과 고화질 사진 2장을 생성하고 있습니다..."):
            try:
                # 참고 기사/자료 지침
                source_instruction = ""
                if source_content.strip():
                    source_instruction = f"""
                    [참고할 원문 데이터]:
                    \"\"\"{source_content.strip()}\"\"\"
                    - 원문의 표현을 그대로 복사하지 마세요 (표절 방지).
                    - 위 원문에서 핵심 사실, 숫자, 주요 시사점을 추출한 뒤, 이웃과 대화하듯 알기 쉽고 흥미롭게 풀어내세요.
                    """

                # 개인 경험/생각 지침
                exp_instruction = ""
                if experience.strip():
                    exp_instruction = f"""
                    - [작성자의 생각/경험]: "{experience.strip()}"
                    - 위 생각을 글의 도입부나 마무리 소감에 자연스럽게 담아내세요.
                    """

                prompt = f"""
                당신은 캐나다에 거주하며 유용한 생활 정보, 세상 돌아가는 소식, 진솔한 생각을 나누는 친근한 인기 블로거(Youngmom-canada-life)입니다.
                독자들이 재미있고 유익하게 읽을 수 있는 매력적인 블로그 글을 작성하세요.

                [카테고리]: {category}
                [주제]: {topic}
                {source_instruction}
                {exp_instruction}

                [작성 가이드]
                1. 첫 번째 줄은 반드시 "TITLE: [주제에 맞고 클릭하고 싶은 한글 블로그 제목]" 형식으로 시작하세요.
                2. 어조: 다정하고 명쾌한 어조 (~해요, ~했답니다). 어려운 전문 용어나 기술 뉴스도 누구나 쉽게 이해할 수 있게 설명하세요.
                3. 구성:
                   - 도입부: 이 주제나 뉴스를 접하고 든 생각, 흥미로운 공감 질문
                   - 본문 문단 1 (핵심 이슈 및 쉬운 설명)
                   - 본문 문단 2 바로 앞 줄에 반드시 독립된 한 줄로 "[INSERT_BODY_IMAGE]" 태그 입력
                   - 본문 문단 2, 3 (우리가 주목할 점, 일상이나 실생활에 주는 영향)
                   - 맺음말: 독자들에게 건네는 따뜻한 소감과 질문
                4. 글 맨 마지막 두 줄에는 반드시 아래 형식으로 사진 묘사를 적으세요:
                   THUMBNAIL_PROMPT: [Editorial lifestyle photograph representing '{topic}', natural daylight, cozy atmosphere]
                   BODY_PROMPT: [Close-up detailed photo of hands, documents, tech devices or desk scene related to '{topic}']
                """

                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt
                )
                full_text = response.text.strip()

                # 1) 제목 추출 (안전 파싱)
                post_title = topic
                if "TITLE:" in full_text:
                    parts = full_text.split("TITLE:", 1)[1].split("\n", 1)
                    post_title = parts[0].strip()
                    main_content = parts[1] if len(parts) > 1 else ""
                else:
                    main_content = full_text

                # 2) 프롬프트 분리 및 본문 추출 (안전 파싱)
                thumb_prompt = f"Warm modern photo about {topic}, clean lifestyle aesthetic"
                body_prompt = f"Detailed close up desk scene with notebook, pen or device related to {topic}"

                if "THUMBNAIL_PROMPT:" in main_content:
                    split_body, prompt_tail = main_content.rsplit("THUMBNAIL_PROMPT:", 1)
                    final_body = split_body.strip()
                    if "BODY_PROMPT:" in prompt_tail:
                        t_part, b_part = prompt_tail.split("BODY_PROMPT:", 1)
                        thumb_prompt = t_part.strip()
                        body_prompt = b_part.strip()
                    else:
                        thumb_prompt = prompt_tail.strip()
                else:
                    final_body = main_content.strip()

                # 혹시라도 파싱 문제로 본문이 비었을 때를 대비한 안전장치
                if not final_body:
                    final_body = full_text

                # 랜덤 시드 생성
                thumb_seed = random.randint(1000, 999999)
                body_seed = random.randint(1000, 999999)

                thumb_url = generate_flux_image_url(thumb_prompt, 1000, 580, thumb_seed)
                body_url = generate_flux_image_url(body_prompt, 1000, 520, body_seed)

                # 세션에 최종 저장
                st.session_state.post_data = {
                    "title": post_title,
                    "body": final_body,
                    "thumb_prompt": thumb_prompt,
                    "body_prompt": body_prompt,
                    "thumb_seed": thumb_seed,
                    "body_seed": body_seed,
                    "thumb_url": thumb_url,
                    "body_url": body_url
                }

            except Exception as e:
                st.error(f"초안 생성 중 오류가 발생했습니다: {e}")

# --- [2단계: 엄마의 검토 및 수정 (Review)] ---
if st.session_state.post_data:
    st.divider()
    st.markdown("### 🔍 2단계: 엄마의 검토 및 사진 확인 (Review)")
    st.info("💡 글과 사진을 확인해 보세요. 사진이 마음에 안 들면 **[🔄 다른 사진 뽑기]**를 누르고, 마음에 들면 아래 **[최종 발행하기]**를 누르세요!")

    # 1. 제목 수정
    reviewed_title = st.text_input(
        "블로그 제목 확인/수정", 
        value=st.session_state.post_data["title"]
    )

    # 2. 이미지 미리보기 및 다시 뽑기
    st.markdown("##### 🖼️ 삽입될 실사 사진")
    col1, col2 = st.columns(2)
    
    with col1:
        st.caption("1. 대표 사진 (썸네일)")
        st.image(st.session_state.post_data["thumb_url"], use_container_width=True)
        if st.button("🔄 대표 사진 다른 걸로 바꾸기", key="regen_thumb"):
            new_seed = random.randint(1000, 999999)
            st.session_state.post_data["thumb_seed"] = new_seed
            st.session_state.post_data["thumb_url"] = generate_flux_image_url(
                st.session_state.post_data["thumb_prompt"], 1000, 580, new_seed
            )
            st.rerun()

    with col2:
        st.caption("2. 본문 중간 사진")
        st.image(st.session_state.post_data["body_url"], use_container_width=True)
        if st.button("🔄 본문 사진 다른 걸로 바꾸기", key="regen_body"):
            new_seed = random.randint(1000, 999999)
            st.session_state.post_data["body_seed"] = new_seed
            st.session_state.post_data["body_url"] = generate_flux_image_url(
                st.session_state.post_data["body_prompt"], 1000, 520, new_seed
            )
            st.rerun()

    # 3. 본문 수정
    reviewed_body = st.text_area(
        "본문 내용 확인/수정 (문장을 직접 추가하거나 고치실 수 있습니다)", 
        value=st.session_state.post_data["body"],
        height=350
    )

    # 4. 최종 발행 버튼
    col_send, col_cancel = st.columns([3, 1])
    with col_send:
        if st.button("🚀 검토 완료! 블로그에 최종 발행하기", type="primary", use_container_width=True):
            with st.spinner("블로그에 최종 글과 고화질 사진을 등록하고 있습니다..."):
                try:
                    thumb_url = st.session_state.post_data["thumb_url"]
                    body_url = st.session_state.post_data["body_url"]

                    body_img_html = f"""
                    <div style="text-align: center; margin: 30px 0;">
                        <img src="{body_url}" style="width: 100%; max-width: 750px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);" alt="관련 사진" />
                    </div>
                    """

                    if "[INSERT_BODY_IMAGE]" in reviewed_body:
                        html_body_text = reviewed_body.replace("[INSERT_BODY_IMAGE]", body_img_html)
                    else:
                        html_body_text = reviewed_body + body_img_html

                    formatted_body = html_body_text.strip().replace("\n", "<br>")
                    final_html = f"""
                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.85; font-size: 16px; color: #333;">
                        <div style="text-align: center; margin-bottom: 25px;">
                            <img src="{thumb_url}" style="width: 100%; max-width: 800px; border-radius: 10px;" alt="대표 사진" />
                        </div>
                        {formatted_body}
                    </div>
                    """

                    msg = MIMEMultipart()
                    msg['Subject'] = reviewed_title
                    msg['From'] = sender_email
                    msg['To'] = blogger_email
                    msg.attach(MIMEText(final_html, 'html', 'utf-8'))

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
