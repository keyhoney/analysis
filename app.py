import streamlit as st
import openai
import json
import io
from fpdf import FPDF

st.set_page_config(page_title="AI 학생부 분석기", layout="wide")
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("📘 AI 기반 학생부 분석기 (Streamlit)")

# 사용자 입력
with st.sidebar:
    desired_major = st.text_input("희망 학과 (예: 컴퓨터공학과)")
    university_level = st.selectbox("목표 대학 수준", ["상위권", "중위권", "하위권"])
    uploaded_file = st.file_uploader("학생부 JSON 파일 업로드", type="json")

report_texts = []

# 분석 실행 조건 확인
if uploaded_file and desired_major and university_level:
    try:
        data = json.load(uploaded_file)
    except json.JSONDecodeError:
        st.error("유효한 JSON 형식의 파일이 아닙니다.")
        st.stop()

    st.success("파일이 성공적으로 업로드되었습니다. GPT 분류 및 분석을 시작합니다.")

    # GPT 분류 및 종합 평가 요청
    gpt_classify_prompt = (
        f"희망 학과는 '{desired_major}'입니다. 다음은 학생부 항목별 텍스트입니다. 각 항목을 '창의적 체험활동' 또는 '세특' 중 하나로 분류하고,\n"
        f"각 항목에 대해 다음을 작성해줘:\n"
        f"1. 분류 결과 (창의적 체험활동 / 세특)\n"
        f"2. 핵심 강점 여러 가지 (5개 이상)\n"
        f"3. 약점 또는 보완점\n"
        f"4. 추가 제안 (입시나 자기소개서 활용 관점에서)\n"
        f"5. 해당 활동/세특이 드러내는 교육부 핵심역량 (문제해결력, 의사소통능력, 정보처리능력, 공동체역량, 자기관리역량, 창의적사고력 중 해당되는 것들을 나열하고 이유 설명)\n"
        f"6. 이 항목이 유리한 전공 분야 추천 (2~3개)\n"
        f"7. 추천 전공과 희망 학과 간의 적합성 평가\n"
        f"8. 이 항목이 전체 학생부에서 차지하는 입시 전략상 우선순위 (상 / 중 / 하)와 그 이유\n"
        f"9. 전체 학생부 내용을 종합해 학생에게 효과적인 입시 전략 방향 제안 (최종적으로 1개만)\n"
        f"형식은 JSON으로, 예시: {{\"자율활동\": {{\"type\": \"창의적 체험활동\", \"strengths\": [...], \"weakness\": ..., \"suggestion\": ..., \"core_competencies\": ..., \"majors\": [...], \"major_fit\": ..., \"priority\": ..., \"strategy_summary\": ... }}}}\n\n"
        f"{json.dumps(data, ensure_ascii=False)}"
    )

    classify_response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": gpt_classify_prompt}],
        temperature=0.3,
    )

    try:
        analysis = json.loads(classify_response.choices[0].message.content)
    except json.JSONDecodeError:
        st.error("GPT 분석 결과를 파싱할 수 없습니다. 원시 내용을 확인해 주세요.")
        st.write(classify_response.choices[0].message.content)
        st.stop()

    strategy_summary = ""
    # 창체/세특 구분 후 분석 출력
    for section, result in analysis.items():
        with st.expander(f"📂 {section} ({result.get('type')})"):
            st.markdown(f"**✔️ 강점**\n- " + "\n- ".join(result.get("strengths", [])))
            st.markdown(f"**⚠️ 약점**\n- {result.get('weakness', '없음')}")
            st.markdown(f"**💡 제안**\n- {result.get('suggestion', '없음')}")
            st.markdown(f"**🧠 핵심역량 매핑**\n- {result.get('core_competencies', '없음')}")
            st.markdown(f"**🎯 추천 전공 분야**\n- " + ", ".join(result.get("majors", [])))
            st.markdown(f"**🔗 희망 학과와의 적합성**\n- {result.get('major_fit', '정보 없음')}")
            st.markdown(f"**📌 전략적 우선순위 제안**\n- {result.get('priority', '정보 없음')}")
            if result.get("strategy_summary") and not strategy_summary:
                strategy_summary = result.get("strategy_summary")

            # PDF에 저장할 텍스트 구성
            section_report = (
                f"[{section} - {result.get('type')}]
"
                f"✔️ 강점:
- " + "\n- ".join(result.get("strengths", [])) + "\n"
                f"⚠️ 약점: {result.get('weakness', '')}\n"
                f"💡 제안: {result.get('suggestion', '')}\n"
                f"🧠 핵심역량: {result.get('core_competencies', '')}\n"
                f"🎯 추천 전공: {', '.join(result.get('majors', []))}\n"
                f"🔗 적합성 평가: {result.get('major_fit', '')}\n"
                f"📌 우선순위: {result.get('priority', '')}\n\n"
            )
            report_texts.append(section_report)

    if strategy_summary:
        st.subheader("🧭 종합 입시 전략 제안")
        st.markdown(strategy_summary)
        report_texts.append("[종합 전략 제안]\n" + strategy_summary + "\n")

    # PDF 저장 기능
    if st.button("📄 분석 결과 PDF 저장"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for block in report_texts:
            for line in block.split("\n"):
                pdf.multi_cell(0, 10, line)
        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        st.download_button(
            label="📥 PDF 다운로드",
            data=pdf_output.getvalue(),
            file_name="student_analysis_report.pdf",
            mime="application/pdf"
        )
else:
    st.info("왼쪽 사이드바에서 모든 입력을 완료하면 분석 결과가 표시됩니다.")
