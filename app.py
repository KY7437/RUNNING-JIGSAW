
import streamlit as st
import re
import csv
import io
import threading
from difflib import SequenceMatcher

st.set_page_config(
    page_title="Group Dictation Challenge",
    page_icon="📝",
    layout="centered"
)

# =====================================
# 1. 기본 지문
# =====================================

DEFAULT_PASSAGE = """On New Year’s Eve, Emily was cleaning her room when she discovered an old notebook under her desk. Inside, she found a list of New Year’s resolutions she had written a year earlier: exercise every morning, read thirty books, and improve her English.

However, she had given up on most of her goals before February. “Why did I fail to keep my promises?” she wondered. She realized that her goals had been too ambitious, and she had expected immediate results.

During dinner, Emily shared her concerns with her older brother. He listened carefully and said, “You don’t have to change your entire life overnight. Why don’t you start with something small?”

His advice inspired her to make a more realistic plan. Instead of exercising every morning, she would take a twenty-minute walk three times a week. Instead of reading thirty books, she would read ten pages a day. She also decided to keep an English diary every weekend.

Emily knew that following her new plan wouldn’t always be easy; there would be challenges, unexpected events, and moments when she wanted to give up. However, she promised herself that she would keep trying, even if she made mistakes.

As the clock struck midnight, Emily opened her notebook and wrote one final sentence: “This year, I don’t have to be perfect. I just have to be better than I was yesterday!”"""


# =====================================
# 2. 여러 접속자가 공유하는 메모리
# =====================================

@st.cache_resource
def get_shared_data():
    return {
        "passage": DEFAULT_PASSAGE,
        "group_count": 4,
        "answers": {},
        "finished": False,
        "revealed": False,
        "lock": threading.RLock()
    }

data = get_shared_data()


# =====================================
# 3. 채점 함수
# =====================================

def normalize_word(word):
    word = word.replace("’", "'")
    return re.sub(r"[^\w'-]", "", word).casefold()


def calculate_score(original, answer):

    original_words = original.split()
    answer_words = answer.split()

    original_norm = [normalize_word(w) for w in original_words]
    answer_norm = [normalize_word(w) for w in answer_words]

    matcher = SequenceMatcher(
        None,
        original_norm,
        answer_norm,
        autojunk=False
    )

    correct = 0
    details = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                correct += 1
                details.append({
                    "status": "correct",
                    "original": original_words[i],
                    "answer": answer_words[j]
                })

        elif tag == "replace":

            original_part = original_words[i1:i2]
            answer_part = answer_words[j1:j2]

            paired = min(len(original_part), len(answer_part))

            for i in range(paired):
                details.append({
                    "status": "incorrect",
                    "original": original_part[i],
                    "answer": answer_part[i]
                })

            for word in original_part[paired:]:
                details.append({
                    "status": "missing",
                    "original": word,
                    "answer": "(누락)"
                })

            for word in answer_part[paired:]:
                details.append({
                    "status": "extra",
                    "original": "(없음)",
                    "answer": word
                })

        elif tag == "delete":
            for word in original_words[i1:i2]:
                details.append({
                    "status": "missing",
                    "original": word,
                    "answer": "(누락)"
                })

        elif tag == "insert":
            for word in answer_words[j1:j2]:
                details.append({
                    "status": "extra",
                    "original": "(없음)",
                    "answer": word
                })

    total = len(original_words)
    score = round(correct / max(total, 1) * 100, 1)

    return correct, total, score, details


# =====================================
# 4. 화면 선택
# =====================================

st.title("📝 Group Dictation Challenge")
st.caption("Read · Remember · Reconstruct")

mode = st.radio(
    "접속 화면",
    ["학생용", "교사용"],
    horizontal=True
)

st.divider()


# =====================================
# 5. 학생용 화면
# =====================================

if mode == "학생용":

    st.header("👥 Group Submission")

    with data["lock"]:
        finished = data["finished"]
        revealed = data["revealed"]
        group_count = data["group_count"]

    if finished:

        st.warning("받아쓰기 활동이 종료되었습니다.")

        if revealed:
            st.success("결과가 공개되었습니다!")

        st.stop()

    st.write("모둠을 선택하고 받아쓰기한 내용을 입력하세요.")

    group_names = [
        f"Group {i}" for i in range(1, group_count + 1)
    ]

    selected_group = st.selectbox(
        "우리 모둠",
        group_names
    )

    with data["lock"]:
        saved_answer = data["answers"].get(selected_group, "")

    with st.form(f"form_{selected_group}"):

        answer = st.text_area(
            "받아쓰기 답안",
            value=saved_answer,
            height=300,
            placeholder="Write your dictation here..."
        )

        submitted = st.form_submit_button(
            "답안 제출하기",
            type="primary",
            use_container_width=True
        )

    if submitted:

        with data["lock"]:

            if data["finished"]:
                st.error("이미 활동이 종료되었습니다.")

            else:
                data["answers"][selected_group] = answer
                st.success(
                    f"{selected_group} 답안이 제출되었습니다!"
                )

    with data["lock"]:
        current_answer = data["answers"].get(selected_group, "")

    if current_answer:
        st.info("현재 제출된 답안이 있습니다. 다시 제출하면 수정됩니다.")
    else:
        st.caption("아직 제출된 답안이 없습니다.")


# =====================================
# 6. 교사용 화면
# =====================================

elif mode == "교사용":

    # 교사 비밀번호 확인
    if not st.session_state.get("teacher_authenticated", False):

        st.subheader("🔐 Teacher Login")

        password = st.text_input(
            "교사 비밀번호",
            type="password"
        )

        if st.button("로그인", type="primary"):

            correct_password = st.secrets.get(
                "TEACHER_PASSWORD",
                "change-this-password"
            )

            if password == correct_password:
                st.session_state.teacher_authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")

        st.stop()

    st.header("👩‍🏫 Teacher Dashboard")

    # ---------------------------------
    # 활동 설정
    # ---------------------------------

    with data["lock"]:
        finished = data["finished"]
        revealed = data["revealed"]
        current_passage = data["passage"]
        current_count = data["group_count"]

    st.subheader("1. Activity Settings")

    with st.form("settings_form"):

        new_passage = st.text_area(
            "정답 원문 (학생 화면에는 표시되지 않음)",
            value=current_passage,
            height=250,
            disabled=finished
        )

        new_count = st.number_input(
            "모둠 수",
            min_value=1,
            max_value=20,
            value=current_count,
            step=1,
            disabled=finished
        )

        save_settings = st.form_submit_button(
            "설정 저장",
            disabled=finished
        )

    if save_settings:

        with data["lock"]:
            data["passage"] = new_passage
            data["group_count"] = int(new_count)

        st.success("설정이 저장되었습니다.")
        st.rerun()

    st.divider()

    # ---------------------------------
    # 제출 현황
    # ---------------------------------

    st.subheader("2. Submission Status")

    if st.button("🔄 제출 현황 새로고침"):

        st.rerun()

    with data["lock"]:

        answers_snapshot = dict(data["answers"])
        group_count = data["group_count"]

    submitted_count = 0

    for i in range(1, group_count + 1):

        group = f"Group {i}"
        answer = answers_snapshot.get(group, "")

        if answer.strip():
            submitted_count += 1
            status = "✅ 제출 완료"
        else:
            status = "⏳ 대기 중"

        st.write(f"**{group}** — {status}")

    st.write(
        f"제출 현황: {submitted_count} / {group_count}개 모둠"
    )

    st.progress(submitted_count / max(group_count, 1))

    st.divider()

    # ---------------------------------
    # 활동 제어
    # ---------------------------------

    st.subheader("3. Activity Control")

    if not finished:

        if st.button(
            "활동 종료",
            type="primary",
            use_container_width=True
        ):

            with data["lock"]:
                data["finished"] = True

            st.rerun()

    else:

        st.warning("활동이 종료되었습니다.")

        if not revealed:

            if st.button(
                "🏆 결과 공개하기",
                type="primary",
                use_container_width=True
            ):

                with data["lock"]:
                    data["revealed"] = True

                st.rerun()

        else:
            st.success("결과가 공개되었습니다.")

    st.divider()

    # ---------------------------------
    # 결과 확인
    # ---------------------------------

    if revealed:

        st.subheader("4. Final Results")

        with data["lock"]:
            passage = data["passage"]
            answers_snapshot = dict(data["answers"])
            group_count = data["group_count"]

        results = []

        for i in range(1, group_count + 1):

            group = f"Group {i}"
            answer = answers_snapshot.get(group, "")

            correct, total, score, details = calculate_score(
                passage,
                answer
            )

            results.append({
                "group": group,
                "correct": correct,
                "total": total,
                "score": score,
                "details": details
            })

        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        st.subheader("🏆 Leaderboard")

        for rank, result in enumerate(results, 1):

            st.markdown(
                f"### {rank}위 — {result['group']}"
            )

            st.metric(
                "정답 단어",
                f"{result['correct']} / {result['total']}",
                f"{result['score']}%"
            )

            st.progress(result["score"] / 100)

        st.divider()

        st.subheader("Word-by-word Feedback")

        for result in results:

            with st.expander(result["group"]):

                for item in result["details"]:

                    if item["status"] == "correct":
                        st.success(
                            f"✓ {item['original']}"
                        )

                    elif item["status"] == "incorrect":
                        st.error(
                            f"✗ 정답: {item['original']} | "
                            f"입력: {item['answer']}"
                        )

                    elif item["status"] == "missing":
                        st.warning(
                            f"△ 누락: {item['original']}"
                        )

                    elif item["status"] == "extra":
                        st.error(
                            f"+ 추가: {item['answer']}"
                        )

        # CSV 다운로드
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)

        writer.writerow([
            "Group",
            "Correct Words",
            "Total Words",
            "Score"
        ])

        for result in results:
            writer.writerow([
                result["group"],
                result["correct"],
                result["total"],
                result["score"]
            ])

        st.download_button(
            "📥 결과 CSV 다운로드",
            data=csv_buffer.getvalue().encode("utf-8-sig"),
            file_name="dictation_results.csv",
            mime="text/csv"
        )

    st.divider()

    # ---------------------------------
    # 새 활동 초기화
    # ---------------------------------

    with st.expander("새 활동 준비"):

        st.warning(
            "초기화하면 모든 모둠의 제출 답안과 활동 상태가 사라집니다."
        )

        confirm_reset = st.checkbox(
            "초기화에 동의합니다."
        )

        if st.button(
            "새 활동 초기화",
            disabled=not confirm_reset
        ):

            with data["lock"]:

                data["answers"] = {}
                data["finished"] = False
                data["revealed"] = False

            st.success("새 활동을 시작할 수 있습니다.")
            st.rerun()


st.divider()

st.caption(
    "Group Dictation Challenge | Powered by Streamlit"
)
