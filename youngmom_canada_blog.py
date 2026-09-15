import streamlit as st
from google import genai
import urllib.parse
import smtplib
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

st.set_page_config(page_title="YoungMom Canada 블로그 비서", page_icon="🍁", layout="centered")

st.title("🍁 YoungMom Canada 글 생성기")
st.caption("고화질 실사 사진과 함께 글을 완성하고, 꼼꼼히 검토한 뒤 블로그에 등록하세요.")

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

# 고화질 실사 사진 URL 생성 함수 (Flux 모델 + 시드 적용)
def generate_flux_image_url(prompt_text, width, height, seed):
    camera_style = ", authentic lifestyle photography, shot on 35mm lens, soft natural lighting, warm tone, realistic texture, 8k resolution, highly detailed, photorealistic, no 3d render, no cgi, no text, no watermark"
    enhanced_prompt = prompt_text + camera_style
    encoded = urllib.parse.quote(enhanced_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&model=flux&nologo=true&seed={seed}"

# --- [1단계: 입력 섹션] ---
st.markdown("### 📝 1단계: 글 재료 입력하기")

category = st.selectbox(
    "1. 카테고리 선택",
    [
        "🏠 렌트 & 이사 (디파짓 반환, 계약서, 인스펙션)",
        "📑 알버타 행정 & 서류 (운전면허, 헬스케어, 연금, 혜택)",
        "🚗 겨울철 차량 & 생활 안전 (타이어, 한파 대비, 대출 주의)",
        "🛒 현지 알뜰 장보기 (코스트코, 마트 꿀템/물가 비교)",
        "✏️ 기타 캐나다 일상"
    ]
)

topic = st.text_input(
    "2. 핵심 주제", 
    placeholder="예: 캐나다 연금(CPP/OAS) 신청 자격과 받는 시기"
)

source_content = st.text_area(
    "3. 📰 참고할 기사나 다른 글 내용 (선택: 복사해서 붙여넣기)",
    placeholder="뉴스 기사, 정부 공지문, 카페 글 등 참고하고 싶은 원문을 통째로 붙여넣으세요.\n(AI가 핵심 사실만 뽑아 완전히 새로운 엄마만의 글로 다시 씁니다)",
    height=120
)

experience = st.text_area(
    "4. 💡 엄마의 실제 경험이나 생각 (선택: 한 줄만 편하게)", 
    placeholder="예: 주변 지인이 은퇴 나이 다 됐는데 신청 늦게 해서 손해 봤다고 들었음\n(비워두셔도 자연스럽게 완성됩니다)",
    height=80
)

if st.button("🔍 고화질 사진 & 초안 만들기 (미리보기)", type="primary", use_container_width=True):
    if not topic.strip():
        st.warning("핵심 주제를 입력해 주세요.")
    else:
        with st.spinner("고화질 실사 이미지 2장과 실전 포스팅 초안을 생성하는 중입니다..."):
            try:
                source_instruction = ""
                if source_content.strip():
                    source_instruction = f"""
                    [참고할 원문 데이터]:
                    \"\"\"{source_content.strip()}\"\"\"
                    - 핵심 지침: 원문의 문장을 절대 그대로 베끼지 마세요(구글 유사문서 방지).
                    - 위 원문에서 '핵심 사실(팩트), 숫자, 날짜, 신청 요건'만 정확히 추출한 뒤, 캐나다 교민의 시선에서 다정하고 똑부러진 선배 맘의 말투로 100% 새롭게 재창작하세요.
                    """

                exp_instruction = ""
                if experience.strip():
                    exp_instruction = f"""
                    - [엄마의 실제 경험/생각]: "{experience.strip()}"
                    - 지침: 위 경험을 글 도입부의 생생한 계기나 본문 팁 중 하나로 자연스럽게 녹여내세요.
                    """
                else:
                    exp_instruction = "- 지침: 알버타 교민들이 가장 흔히 겪는 현실적인 고민이나 궁금증을 서두에 배치해 공감을 얻으세요."

                prompt = f"""
                당신은 캐나다 알버타에서 유용한 생활 꿀팁을 전하는 인기 블로거(Youngmom-canada-life)입니다.
                블로그스팟에 발행할 실용적이고 신뢰도 높은 포스팅을 작성하세요.

                [카테고리]: {category}
                [주제]: {topic}
                {source_instruction}
                {exp_instruction}

                [필수 작성 규칙]
                1. 첫 줄은 반드시 "TITLE: [한글 블로그 제목]" 형식이어야 합니다.
                2. 불필요한 검색 찌꺼기 텍스트(A, Alberta.ca 등) 절대 금지.
                3. 구성:
                   - 도입부: 이 주제를 다루게 된 계기 또는 공감 질문
                   - 본문 팁 1번
                   - 본문 팁 2번 바로 직전 줄에 반드시 "[INSERT_BODY_IMAGE]" 태그 삽입
                   - 본문 팁 2번, 3번 (상세 해결책 및 핵심 정보)
                   - 실전 템플릿: 관공서/현지에 문의할 때 쓰는 간단한 영어 문장 박스
                   - 요약: [한눈에 보는 핵심 요약] (화살표 ↓ 활용)
                   - 다정한 맺음말
                4. 글 맨 마지막 2줄 (고품질 사진 묘사):
                   THUMBNAIL_PROMPT: [Professional editorial photo of a real Canadian lifestyle scene related to '{topic}', cozy atmosphere, natural daylight]
                   BODY_PROMPT: [High quality close-up photo of paperwork, checklist, desk workspace, or hands handling documents related to '{topic}']
                """

                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt
                )
                full_text = response.text

                # 제목 분리
                post_title = topic
                if "TITLE:" in full_text:
                    parts = full_text.split("TITLE:", 1)[1].split("\n", 1)
                    post_title = parts[0].strip()
                    full_text = parts[1] if len(parts) > 1 else ""

                # 이미지 프롬프트 분리
                thumb_prompt = f"Warm cozy real photograph of Canadian home and daily life regarding {topic}"
                body_prompt = f"Detailed photography of documents, notes, checklist on a clean wooden desk related to {topic}"

                if "THUMBNAIL_PROMPT:" in full_text and "BODY_PROMPT:" in full_text:
                    main_body, prompts_part = full_text.rsplit("THUMBNAIL_PROMPT:", 1)
                    thumb_part, body_part = prompts_part.split("BODY_PROMPT:", 1)
                    thumb_prompt = thumb_part.strip()
                    body_prompt = body_part.strip()
                else:
                    main_body = full_text

                # 랜덤 시드로 첫 이미지 생성
                thumb_seed = random.randint(1000, 999999)
                body_seed = random.randint(1000, 999999)

                thumb_url = generate_flux_image_url(thumb_prompt, 1000, 580, thumb_seed)
                body_url = generate_flux_image_url(body_prompt, 1000, 520, body_seed)

                # 세션에 저장
                st.session_state.post_data = {
                    "title": post_title,
                    "body": main_body.strip(),
                    "thumb_prompt": thumb_prompt,
                    "body_prompt": body_prompt,
                    "thumb_seed": thumb_seed,
                    "body_seed": body_seed,
                    "thumb_url": thumb_url,
                    "body_url": body_url
                }

            except Exception as e:
                st.error(f"초안 생성 중 오류가 발생했습니다: {e}")

# --- [2단계: 검토 및 최종 발행 섹션] ---
if st.session_state.post_data:
    st.divider()
    st.markdown("### 🔍 2단계: 엄마의 검토 및 사진 확인 (Review)")
    st.info("💡 사진과 글을 확인하세요. 사진이 마음에 안 들면 **[🔄 다른 사진 뽑기]**를 누르면 바로 바뀝니다!")

    # 1. 제목 수정
    reviewed_title = st.text_input(
        "블로그 제목 확인/수정", 
        value=st.session_state.post_data["title"]
    )

    # 2. 이미지 미리보기 및 다시 뽑기 버튼
    st.markdown("##### 🖼️ 삽입될 실사 사진 (Flux 모델)")
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
        "본문 내용 확인/수정 (직접 글을 수정하실 수 있습니다)", 
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
                        <img src="{body_url}" style="width: 100%; max-width: 750px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);" alt="팁 관련 사진" />
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
category = st.selectbox(
    "1. 카테고리 선택",
    [
        "🏠 렌트 & 이사 (디파짓 반환, 계약서 확인, 인스펙션)",
        "📑 알버타 행정 & 서류 (운전면허 교환, 헬스케어 카드, 유심)",
        "🚗 겨울철 차량 & 생활 안전 (스노우 타이어, 블록히터, 한파 대비)",
        "🛒 현지 알뜰 장보기 (코스트코, 수퍼스토어 꿀템/가격 비교)",
        "✏️ 기타 직접 입력"
    ]
)

topic = st.text_input(
    "2. 핵심 주제", 
    placeholder="예: 무빙아웃 인스펙션 집주인 보증금 공제 분쟁"
)

experience = st.text_area(
    "3. 💡 실제 겪으신 일이나 기억나는 상황 (한 줄만 적어주세요)", 
    placeholder="예: 이사 나갈 때 벽에 못 자국 2개 있다고 $150 깎겠다고 해서 당황했음\n(비워두셔도 자연스러운 예시로 글이 완성됩니다)",
    height=85
)

# 3. 자동 생성 및 전송 로직
if st.button("🚀 블로그에 글 & 사진 2장 바로 등록하기", type="primary", use_container_width=True):
    if not topic:
        st.warning("주제를 입력해 주세요.")
    else:
        with st.spinner("경험담을 반영해 사진 2장과 실전 포스팅을 완성하여 블로그로 전송 중입니다..."):
            try:
                # 경험담 입력 여부에 따른 프롬프트 분기
                if experience.strip():
                    exp_rule = f"""
                    - [필수 반영 경험담]: "{experience.strip()}"
                    - 지침: 위 경험을 글 도입부에 생생한 계기("저희도 이번에 이사하면서 ~한 일을 겪었거든요")로 자연스럽게 풀어내고, 본문 해결 팁 중 하나에서 이 사례를 어떻게 해결했는지 직접 다루세요.
                    """
                else:
                    exp_rule = """
                    - 지침: 알버타 교민들이 렌트나 현지 생활 중 흔히 겪는 가장 현실적인 당황스러운 상황 1가지를 자연스러운 경험담처럼 서두에 배치하세요.
                    """

                prompt = f"""
                당신은 캐나다 알버타에서 생활하는 인기 블로그(Youngmom-canada-life) 운영자입니다.
                구글 블로그스팟에 등록할 실전 정보 글을 작성하세요.

                [카테고리]: {category}
                [주제]: {topic}
                {exp_rule}

                [필수 작성 규칙]
                1. 첫 줄은 반드시 "TITLE: [한글 블로그 제목]" 형식으로 작성하세요.
                2. 말투: 다정하면서도 명쾌한 선배 맘 안내형 구어체 (~하는 것이 안전합니다, ~확인해 보세요).
                3. 검색 찌꺼기 텍스트(A, Alberta.ca, +1 등) 절대 금지.
                4. 본문 구성:
                   - 도입부: 실제 겪은 상황 공유 및 공감 질문
                   - 본문 팁 1번
                   - 본문 팁 2번 바로 직전 줄에 정확히 "[INSERT_BODY_IMAGE]" 태그를 한 줄로 삽입하세요.
                   - 본문 팁 2번, 3번 (현지 대응 수칙)
                   - 실전 템플릿: 집주인이나 관공서에 바로 복사해 보낼 수 있는 간단한 영어 문자/이메일 박스
                   - 요약: [한눈에 보는 순서 요약] (화살표 ↓ 활용)
                   - 따뜻한 마무리 맺음말
                5. 글 맨 마지막에 아래 2줄을 정확히 작성하세요:
                   THUMBNAIL_PROMPT: [글 전체를 상징하는 따뜻한 캐나다 일상 실사 사진 영문 묘사]
                   BODY_PROMPT: [본문 팁과 관련된 서류, 노트북, 체크리스트 등 디테일한 오브젝트 사진 영문 묘사]
                """

                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt
                )
                full_text = response.text

                # 제목 추출
                post_title = "캐나다 알버타 실전 생활 꿀팁"
                if "TITLE:" in full_text:
                    parts = full_text.split("TITLE:", 1)[1].split("\n", 1)
                    post_title = parts[0].strip()
                    full_text = parts[1] if len(parts) > 1 else ""

                # 이미지 프롬프트 추출
                thumb_prompt = f"Cozy realistic photo about {topic} in Alberta Canada, warm aesthetic"
                body_prompt = f"Close up photo of documents, checklist, or home details related to {topic}, bright lighting"

                if "THUMBNAIL_PROMPT:" in full_text and "BODY_PROMPT:" in full_text:
                    main_body, prompts_part = full_text.rsplit("THUMBNAIL_PROMPT:", 1)
                    thumb_part, body_part = prompts_part.split("BODY_PROMPT:", 1)
                    thumb_prompt = thumb_part.strip()
                    body_prompt = body_part.strip()
                else:
                    main_body = full_text

                # 이미지 URL 생성 (무료 고화질 엔드포인트)
                thumb_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(thumb_prompt)}?width=900&height=550&nologo=true"
                body_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(body_prompt)}?width=900&height=500&nologo=true"

                # 본문 중간 이미지 태그 치환
                body_img_html = f"""
                <div style="text-align: center; margin: 30px 0;">
                    <img src="{body_url}" style="width: 100%; max-width: 750px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);" alt="관련 팁 사진" />
                </div>
                """

                if "[INSERT_BODY_IMAGE]" in main_body:
                    html_body_text = main_body.replace("[INSERT_BODY_IMAGE]", body_img_html)
                else:
                    html_body_text = main_body + body_img_html

                # 줄바꿈 및 전체 HTML 패키징 (상단 썸네일 + 본문 + 중간 이미지)
                formatted_body = html_body_text.strip().replace("\n", "<br>")
                final_html = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.85; font-size: 16px; color: #333;">
                    <div style="text-align: center; margin-bottom: 25px;">
                        <img src="{thumb_url}" style="width: 100%; max-width: 800px; border-radius: 10px;" alt="대표 사진" />
                    </div>
                    {formatted_body}
                </div>
                """

                # 이메일 전송 (Blogger Mail2Blogger)
                msg = MIMEMultipart()
                msg['Subject'] = post_title
                msg['From'] = sender_email
                msg['To'] = blogger_email
                msg.attach(MIMEText(final_html, 'html', 'utf-8'))

                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(sender_email, app_password)
                    server.send_message(msg)

                st.success(f"🎉 전송 완료! 블로그에 '{post_title}' 글이 성공적으로 등록되었습니다.")

                # 화면 미리보기
                st.markdown("### 🖼️ 첨부된 이미지 2장 미리보기")
                col1, col2 = st.columns(2)
                with col1:
                    st.caption("1. 상단 대표 사진 (썸네일)")
                    st.image(thumb_url, use_container_width=True)
                with col2:
                    st.caption("2. 본문 중간 사진 (시선 환기용)")
                    st.image(body_url, use_container_width=True)

                st.markdown("### 📝 전송된 포스팅 내용")
                st.markdown(main_body.replace("[INSERT_BODY_IMAGE]", "\n\n*(여기에 2번째 사진이 자동 배치되었습니다)*\n\n"))

            except Exception as e:
                st.error(f"등록 중 오류가 발생했습니다: {e}")
